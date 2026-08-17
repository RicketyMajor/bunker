package cl.alonso.bunker

import android.content.Context
import android.webkit.WebResourceResponse
import androidx.webkit.WebViewAssetLoader
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.IOException
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

    /**
     * When the snapshot was last replaced, epoch ms, 0 when never. Read by the bridge because
     * the WebView cannot tell a fresh snapshot from a three-day-old one — both arrive the same
     * way — and "the inventory is stale" is the one thing the staleness warning exists to say.
     */
    fun sincronizadoEn(): Long = prefs.getLong("estado_en", 0)

    /**
     * Whether the last attempt to refresh actually reached the server. Deliberately NOT derived
     * from `sincronizadoEn`: a snapshot that has not changed in a week is indistinguishable from
     * one refreshed a second ago against an unchanged database, so freshness cannot answer
     * "is there a link right now".
     */
    fun ultimoContactoOk(): Boolean = prefs.getBoolean("contacto_ok", false)

    fun refrescarEstado(): Boolean = try {
        val texto = fetch(BuildConfig.BUNKER_URL + "/api/movil/estado/")
        // Parsed before it is stored, against the plan. `leer` only throws on a 4xx/5xx, so an
        // HTML error page served with a 200 would replace a good snapshot with something
        // `estadoCacheado` can do nothing with but degrade to "{}" — and a blank phone with the
        // laptop off is the exact failure this cache exists to prevent.
        JSONObject(texto)
        guardarEstado(texto)
        anotarContacto(true)
        true
    } catch (e: Exception) {
        // Written in this branch too, and that is the point: without it the chip would keep
        // claiming EN LÍNEA from a contact that succeeded days ago.
        anotarContacto(false)
        false  // No signal is the normal condition; the previous snapshot stands.
    }

    private fun anotarContacto(ok: Boolean) {
        prefs.edit().putBoolean("contacto_ok", ok).apply()
    }

    // --- The assets ---------------------------------------------------------------------

    fun revisarAssets(): Boolean = try {
        val manifiesto = JSONObject(fetch(BuildConfig.BUNKER_URL + "/api/movil/assets/"))
        val version = manifiesto.getString("version")
        // `hayGeneracionValida` and not the recorded version alone. The two used to be conflated,
        // and the moment the recorded directory stopped existing — swept by `handler` below, wiped
        // by a storage cleanup, truncated by an interrupted write — nothing ever re-downloaded it:
        // this returned early for ever and `handler` served the packaged assets for ever. Found by
        // review 2026-08-15, and it is the half that made the sweep race permanent.
        if (version == prefs.getString("assets_version", null) && hayGeneracionValida(version)) {
            false
        } else {
            val archivos = manifiesto.getJSONObject("files")
            // Joined against BUNKER_URL, against the plan, which passes the value straight to
            // URL(). `/api/movil/assets/` answers RELATIVE paths — Task 4 chose them so the APK
            // is not at the mercy of a reflected Host header — and a relative path reaches URL()
            // as a MalformedURLException that the catch below swallows whole.
            val bajados = archivos.keys().asSequence()
                .associateWith { fetch(BuildConfig.BUNKER_URL + archivos.getString(it)) }
            // Staging and recording are ONE critical section against `handler`'s sweep, which
            // deletes every directory that is not the recorded version — and between the two
            // statements below, the generation just downloaded is exactly such a directory. The
            // download itself stays outside the lock: it is the slow part and it touches nothing.
            synchronized(CANDADO) {
                prepararGeneracion(version, bajados)
                // The version is recorded only once every file is on disk. Recording it first
                // would mark a half-downloaded set as installed and there would be no way back.
                if (hayGeneracionValida(version)) {
                    prefs.edit().putString("assets_version", version).apply()
                    true
                } else false
            }
        }
    } catch (e: Exception) {
        false
    }

    fun prepararGeneracion(version: String, archivos: Map<String, String>) {
        // `version` and every key are used as path segments and both arrive from the server's
        // manifest. Our own Django over the tailnet bounds what can turn up; it does not validate
        // it, and this is the trust boundary — a `..` in either one writes outside filesDir, and a
        // name carrying a subdirectory throws into the blanket catch above and fails silently for
        // ever. `REQUERIDOS` is already the set of names this app will serve.
        require(version.isNotEmpty() && version.all { it.isLetterOrDigit() }) {
            "la version del manifiesto no es un hash: $version"
        }
        // Shape and membership are two different failures, and collapsing them into one `require`
        // froze updates for ever: a name that is merely UNKNOWN — the day the server ships a
        // fourth asset — threw into the blanket catch above, so every installed phone stopped
        // updating, silently and permanently, because of a file it did not even need. A name that
        // is not a plain filename is the trust boundary and stays fatal.
        require(archivos.keys.all { it.isNotEmpty() && !it.contains('/') && !it.contains("..") }) {
            "el manifiesto nombra una ruta, no un archivo: ${archivos.keys}"
        }
        val dir = File(generaciones, version).apply { mkdirs() }
        archivos.filterKeys { it in REQUERIDOS }
            .forEach { (nombre, contenido) -> File(dir, nombre).writeText(contenido) }
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
        // Superseded generations are deleted HERE and not in `revisarAssets`, which runs from the
        // worker while the app may be open and serving the very directory it would remove.
        // At launch nothing is being served yet, so this is the one safe moment as far as the
        // WebView goes — but NOT as far as the worker goes, which `MainActivity` wakes on the very
        // same event. So the read, the sweep and the validity check are one critical section:
        // `revisarAssets` stages a generation and records it as two steps, and a sweep landing
        // between them deletes the directory the recorded version is about to name.
        val dir = synchronized(CANDADO) {
            val version = prefs.getString("assets_version", null)
            generaciones.listFiles()?.forEach { if (it.name != version) it.deleteRecursively() }
            version?.let { File(generaciones, it) }?.takeIf { hayGeneracionValida(version) }
        }

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

        // Guards the generations directory. `handler` sweeps it and `revisarAssets` stages into
        // it, from the Activity and the worker respectively, on the same event.
        private val CANDADO = Any()

        // ponytail: the code check is explicit now, like Transmisor.postReal's. The claim that
        // used to stand here — "a non-2xx already throws on `inputStream`" — was false from the
        // moment redirects were turned off: `inputStream` throws only from 400 up. Ceiling that
        // remains: a 2xx carrying the wrong content is still indistinguishable from a good one,
        // and `hayGeneracionValida` only asks whether the files are non-empty. Upgrade path is a
        // hash or a content-type check, the day an asset arrives corrupted with a 200.
        fun leerReal(url: String): String {
            val con = (URL(url).openConnection() as HttpURLConnection).apply {
                connectTimeout = 10_000; readTimeout = 15_000
                // Redirects off, for the same reason postReal turns them off. A captive portal
                // answering 200 with an HTML login page passes every check this class makes —
                // the three files are non-empty — so that page gets written as app.js and served
                // to the WebView. Following a redirect is how it arrives.
                instanceFollowRedirects = false
            }
            return try {
                // Before reading, and not after: with redirects off the 3xx body is returned
                // verbatim — a captive portal's login page, or the tailnet's own 502 — and
                // everything downstream of here treats a non-empty string as an asset.
                if (con.responseCode !in 200..299) {
                    throw IOException("HTTP ${con.responseCode} pidiendo $url")
                }
                con.inputStream.bufferedReader().readText()
            } finally {
                // In a `finally` because being offline is the NORMAL condition here, and the
                // disconnect used to sit after the throwing call — so the failure path, the
                // common one, leaked the connection every time.
                con.disconnect()
            }
        }
    }
}
