package cl.alonso.bunker

import android.content.Context
import android.webkit.WebResourceResponse
import androidx.webkit.WebViewAssetLoader
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.util.Calendar

/**
 * Two jobs that share one rule: what the WebView is handed must never be half of something.
 *
 * The snapshot is here rather than in localStorage because the WebView makes no network request
 * of its own — its origin is appassets.androidplatform.net, so every call to the tailnet would be
 * cross-origin and would need CORS headers Django does not send.
 *
 * `fetch` is injected for the same reason `Transmisor`'s `poster` is: every rule below — what is
 * requested, when a version is recorded, what is allowed to replace a good snapshot — is then
 * provable on the JVM with no network.
 */
class AssetStore(
    private val context: Context,
    private val fetch: (url: String) -> String = ::leerReal,
) {

    private val prefs = context.getSharedPreferences("transmisor", Context.MODE_PRIVATE)
    private val generaciones = File(context.filesDir, "generaciones")

    // --- The snapshot -------------------------------------------------------------------

    fun guardarEstado(json: String, cuando: Long = System.currentTimeMillis()) {
        prefs.edit().putString("estado", json).putLong("estado_en", cuando).apply()
    }

    fun estadoCacheado(): String {
        val json = prefs.getString("estado", null) ?: return "{}"
        val cuando = prefs.getLong("estado_en", 0)
        return try {
            val o = JSONObject(json)
            // Every list in the snapshot is day-independent except this one.
            if (!esHoy(cuando)) o.put("habitos_pendientes", JSONArray())
            o.toString()
        } catch (e: Exception) {
            "{}"
        }
    }

    private fun esHoy(cuando: Long): Boolean {
        if (cuando == 0L) return false
        val a = Calendar.getInstance().apply { timeInMillis = cuando }
        val b = Calendar.getInstance()
        return a.get(Calendar.YEAR) == b.get(Calendar.YEAR) &&
            a.get(Calendar.DAY_OF_YEAR) == b.get(Calendar.DAY_OF_YEAR)
    }

    fun refrescarEstado(): Boolean = try {
        val texto = fetch(BuildConfig.BUNKER_URL + "/api/movil/estado/")
        // Parsed before it is stored, against the plan. `leer` only throws on a 4xx/5xx, so an
        // HTML error page served with a 200 would replace a good snapshot with something
        // `estadoCacheado` can do nothing with but degrade to "{}" — and a blank phone with the
        // laptop off is the exact failure this cache exists to prevent.
        JSONObject(texto)
        guardarEstado(texto)
        true
    } catch (e: Exception) {
        false  // No signal is the normal condition; the previous snapshot stands.
    }

    // --- The assets ---------------------------------------------------------------------

    fun revisarAssets(): Boolean = try {
        val manifiesto = JSONObject(fetch(BuildConfig.BUNKER_URL + "/api/movil/assets/"))
        val version = manifiesto.getString("version")
        if (version == prefs.getString("assets_version", null)) {
            false
        } else {
            val archivos = manifiesto.getJSONObject("files")
            // Joined against BUNKER_URL, against the plan, which passes the value straight to
            // URL(). `/api/movil/assets/` answers RELATIVE paths — Task 4 chose them so the APK
            // is not at the mercy of a reflected Host header — and a relative path reaches URL()
            // as a MalformedURLException that the catch below swallows whole.
            val bajados = archivos.keys().asSequence()
                .associateWith { fetch(BuildConfig.BUNKER_URL + archivos.getString(it)) }
            prepararGeneracion(version, bajados)
            // The version is recorded only once every file is on disk. Recording it first would
            // mark a half-downloaded set as installed and there would be no way back.
            if (hayGeneracionValida(version)) {
                prefs.edit().putString("assets_version", version).apply()
                true
            } else false
        }
    } catch (e: Exception) {
        false
    }

    fun prepararGeneracion(version: String, archivos: Map<String, String>) {
        val dir = File(generaciones, version).apply { mkdirs() }
        archivos.forEach { (nombre, contenido) -> File(dir, nombre).writeText(contenido) }
    }

    fun hayGeneracionValida(version: String): Boolean {
        val dir = File(generaciones, version)
        return REQUERIDOS.all { File(dir, it).let { f -> f.exists() && f.length() > 0 } }
    }

    fun volverALoEmpaquetado() {
        generaciones.deleteRecursively()
        prefs.edit().remove("assets_version").apply()
    }

    /**
     * Resolved once, at construction of the handler — which happens at launch. A generation
     * staged while the app is running is therefore not served until the next start: swapping
     * mid-session means the HTML of one version running the JS of another.
     */
    fun handler(): WebViewAssetLoader.PathHandler {
        val version = prefs.getString("assets_version", null)
        val dir = version?.let { File(generaciones, it) }?.takeIf { hayGeneracionValida(version) }

        // Superseded generations are deleted HERE and not in `revisarAssets`, which runs from the
        // worker while the app may be open and serving the very directory it would remove.
        // At launch nothing is being served yet, so this is the one safe moment.
        generaciones.listFiles()?.forEach { if (it.name != version) it.deleteRecursively() }

        val empaquetados = WebViewAssetLoader.AssetsPathHandler(context)

        return WebViewAssetLoader.PathHandler { ruta ->
            val nombre = ruta.substringAfterLast('/')
            val descargado = dir?.let { File(it, nombre) }?.takeIf { it.exists() }
            if (descargado != null) {
                WebResourceResponse(tipoMime(nombre), "utf-8", descargado.inputStream())
            } else {
                empaquetados.handle("movil/$nombre")
            }
        }
    }

    private fun tipoMime(nombre: String) = when {
        nombre.endsWith(".js") -> "application/javascript"
        nombre.endsWith(".html") -> "text/html"
        else -> "text/plain"
    }

    companion object {
        val REQUERIDOS = listOf("app.html", "app.js", "queue.js")

        // ponytail: no redirect guard and no response-code check, unlike Transmisor.postReal —
        // these are GETs, so a followed redirect costs a wrong body, not a deleted capture, and
        // a non-2xx already throws on `inputStream`. Ceiling: a 200 carrying the wrong content
        // is indistinguishable from a good one here. Upgrade path is the same check postReal
        // has, the day an asset arrives corrupted on the phone.
        fun leerReal(url: String): String {
            val con = (URL(url).openConnection() as HttpURLConnection).apply {
                connectTimeout = 10_000; readTimeout = 15_000
            }
            val texto = con.inputStream.bufferedReader().readText()
            con.disconnect()
            return texto
        }
    }
}
