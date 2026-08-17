package cl.alonso.bunker

import android.content.Context
import android.webkit.JavascriptInterface
import org.json.JSONArray
import org.json.JSONObject

/**
 * The only door between the interface and everything that can lose data. Five methods.
 *
 * Everything reachable from here is reachable from any script the WebView runs, so the surface is
 * kept to what `queue.js` actually calls and nothing else. No method takes a URL, a path or a file
 * name: `encolar` refuses any verb outside `Transmisor.RUTAS` (in `ColaStore`, where every caller
 * routes through), and the routes themselves live natively and are never supplied by the page.
 *
 * `assets` and `avisar` are injected for the same reason `Transmisor` injects `poster`: it is what
 * makes the rules below provable on the JVM, with no WorkManager and no network.
 */
class Puente(
    private val context: Context,
    private val store: ColaStore,
    private val assets: AssetStore = AssetStore(context),
    private val avisar: () -> Unit = { SyncWorker.ahora(context) },
) {

    @JavascriptInterface
    fun encolar(verbo: String, payloadJson: String): Int {
        // Throws on a failed write, and that is deliberate: the exception crosses back into JS as
        // an error, the sheet stays open, and the user is not told a capture was saved when it was
        // not. `avisar` is AFTER the write and outside any catch, so a refused capture also never
        // schedules a flush for something that does not exist.
        val n = store.encolar(verbo, payloadJson)
        avisar()
        return n
    }

    @JavascriptInterface
    fun pendientes(): Int = store.pendientes()

    @JavascriptInterface
    fun listar(): String = JSONArray().apply {
        store.items().forEach {
            put(
                JSONObject().apply {
                    put("id", it.id)
                    put("verbo", it.verbo)
                    // An object, not the stored string: app.js reads `item.payload.pages`, and
                    // handing it the raw text makes every field in the Purgatorio read
                    // `undefined` with nothing reporting an error.
                    put("payload", JSONObject(it.payload))
                    // `it.error` is null for a capture that has not failed yet, and JSONObject
                    // DROPS a null value rather than storing one — so the key would be absent
                    // instead of null, and `item.error` in JS reads undefined either way.
                    put("error", it.error ?: JSONObject.NULL)
                }
            )
        }
    }.toString()

    @JavascriptInterface
    fun descartar(id: String) = store.descartar(id)

    /**
     * A sixth method the plan did not have, and the reason is `transmitir()` in app.js: it calls
     * `Cola.vaciar`, whose body is the localStorage flush. In the APK that would read an empty
     * store while the real queue sits in SQLite — the chip tap would do nothing, silently, for
     * ever.
     *
     * It only asks. The flush is the worker's and its result arrives through the notification and
     * the next snapshot, so nothing here can report "3 transmitted" and the caller must not
     * pretend otherwise.
     *
     * Redundant with the flush `MainActivity` already schedules on window focus, and kept anyway:
     * when the exact-alarm permission was declined the automatic path is the slow one, and this
     * chip is then the only way to make the queue move now.
     */
    @JavascriptInterface
    fun sincronizar() = avisar()

    /**
     * The escape hatch. Drops the downloaded generation so the next launch serves the assets
     * bundled in the APK.
     *
     * Without it a bad deploy from the laptop leaves the phone running broken UI with no way back
     * except reinstalling — which is exactly the fragility the APK was supposed to remove.
     *
     * Destroys no captures: the queue is `ColaStore`'s and is not touched here. And it only takes
     * effect on the NEXT launch, because `AssetStore.handler` resolves the directory once at
     * start — swapping mid-session would run one version's HTML against another's JS. The caller
     * has to say so.
     */
    @JavascriptInterface
    fun revertirAssets() = assets.volverALoEmpaquetado()

    /**
     * The cached snapshot, in an envelope. The WebView makes no network request of its own, so
     * this is the only way the page learns anything about the server.
     *
     * An envelope and not the bare payload because **the bridge answering is not evidence of a
     * link**: it hands back whatever was last stored, which may be days old. Freshness and
     * reachability are two more facts and only the native side knows them.
     */
    @JavascriptInterface
    fun estado(): String = JSONObject().apply {
        put("estado", JSONObject(assets.estadoCacheado()))
        put("sincronizado", assets.sincronizadoEn())
        put("en_linea", assets.ultimoContactoOk())
    }.toString()
}
