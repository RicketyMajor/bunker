package cl.alonso.bunker

import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class Respuesta(val codigo: Int, val cuerpo: String)

data class Resultado(
    val enviados: Int,
    val pendientes: Int,
    val retirados: Int,
    val alcanzoElServidor: Boolean,
    val hechos: List<String>,
)

/**
 * Applies the one rule the whole system rests on: a dispatch leaves the queue only when the
 * server answered 2xx. Everything else — no signal, a 4xx, a 5xx — keeps it.
 *
 * `poster` is injected rather than called directly so every rule here is provable on the JVM
 * with no network and no emulator.
 */
class Transmisor(
    private val store: ColaStore,
    private val poster: (url: String, cuerpo: String) -> Respuesta = ::postReal,
) {

    fun vaciar(): Resultado = synchronized(CANDADO) {
        var enviados = 0
        var retirados = 0
        var alcanzoElServidor = false
        val hechos = mutableListOf<String>()

        // Snapshot the ids up front. Anything enqueued while this runs is simply not in this
        // list and is left alone — which is what makes a capture made mid-flush survive.
        for (item in store.items()) {
            val ruta = RUTAS[item.verbo]
            if (ruta == null) {
                // Its route is gone from the URL conf too, so it can never be accepted. The one
                // exception to "leaves only on a 2xx", narrow because it cannot succeed later.
                store.descartar(item.id)
                retirados++
                continue
            }
            // The try covers the POST and nothing else. Wrapping the two store writes as well
            // would turn a failed `descartar` after a 2xx into a silent re-send — the capture
            // stays queued and is posted again, and `log_pages` counts a second reading session.
            val r = try {
                poster(BuildConfig.BUNKER_URL + ruta, item.payload)
            } catch (e: Exception) {
                // Not marked as an error: no signal is the normal condition, not a failure, and
                // writing "sin enlace" over a real 409 would erase the reason that matters.
                continue
            }
            alcanzoElServidor = true
            if (r.codigo in 200..299) {
                store.descartar(item.id)
                enviados++
                leerHecho(r.cuerpo)?.let { hechos.add(it) }
            } else {
                store.marcarError(item.id, motivo(r))
            }
        }
        Resultado(enviados, store.pendientes(), retirados, alcanzoElServidor, hechos)
    }

    private fun leerHecho(cuerpo: String): String? = try {
        JSONObject(cuerpo).optString("feedback").ifBlank { null }
    } catch (e: Exception) { null }

    /** Three response shapes reach here, the same three queue.js documents. */
    private fun motivo(r: Respuesta): String = try {
        val j = JSONObject(r.cuerpo)
        j.optString("message").ifBlank { null }
            ?: j.optString("error").ifBlank { null }
            ?: j.keys().asSequence()
                .mapNotNull { j.optJSONArray(it)?.optString(0) }
                .firstOrNull { it.isNotBlank() }
            ?: "HTTP ${r.codigo}"
    } catch (e: Exception) { "HTTP ${r.codigo}" }

    companion object {
        // Static and not per-instance on purpose: the flusher that matters runs in SyncWorker
        // (Task 8) while the activity can trigger another, and two Transmisor instances over the
        // same store is exactly the double-send this lock exists to prevent. A per-instance lock
        // reads tidier and does not hold.
        private val CANDADO = Any()

        // Must stay identical to RUTAS in queue.js. Task 10 asserts that they are.
        val RUTAS = mapOf(
            "paginas" to "/api/books/tracker/pages/",
            "terminar_libro" to "/api/books/tracker/finish/",
            "terminar_peli" to "/api/movies/tracker/finish/",
            "terminar_disco" to "/api/music/tracker/finish/",
            "habito" to "/posada/api/habits/complete/",
            "sesion" to "/posada/api/session/record/",
            "escaneo_libro" to "/api/books/inbox/",
            "escaneo_peli" to "/api/movies/inbox/",
            "escaneo_disco" to "/api/music/inbox/",
            "wishlist_libro" to "/api/books/wishlist/add/",
            "wishlist_peli" to "/api/movies/wishlist/",
            "wishlist_disco" to "/api/music/wishlist/",
        )

        // ponytail: the only untested code in this class, deliberately — every check injects
        // `poster`, and exercising this one needs a socket. What was verified instead is its
        // assumption: the three error shapes `motivo()` parses, read off the twelve endpoints on
        // 2026-08-15. Ceiling: the socket itself, `instanceFollowRedirects` and `disconnect()`
        // not being in a `finally` are all unproven. Upgrade path is Task 8's flush on the phone,
        // which is the first time this runs for real — verify it there rather than mocking a
        // server here.
        fun postReal(url: String, cuerpo: String): Respuesta {
            val con = (URL(url).openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                setRequestProperty("Content-Type", "application/json")
                doOutput = true
                connectTimeout = 10_000
                readTimeout = 15_000
                // Off, and this is the whole reason: a followed 301/302 is re-issued as a GET
                // with the body dropped, so a redirect anywhere in front of Django would answer
                // 200 for a request that recorded nothing — and a 2xx is what deletes the
                // capture. A 3xx must reach `vaciar` as the non-2xx it is.
                instanceFollowRedirects = false
            }
            con.outputStream.use { it.write(cuerpo.toByteArray()) }
            val codigo = con.responseCode
            val texto = (if (codigo in 200..299) con.inputStream else con.errorStream)
                ?.bufferedReader()?.readText() ?: ""
            con.disconnect()
            return Respuesta(codigo, texto)
        }
    }
}
