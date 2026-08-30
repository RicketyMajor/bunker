package cl.alonso.bunker

import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.io.IOException
import java.net.ServerSocket
import kotlin.concurrent.thread

@RunWith(RobolectricTestRunner::class)
class AssetStoreTest {

    private fun store() = AssetStore(ApplicationProvider.getApplicationContext())

    /** The manifest exactly as `/api/movil/assets/` answered it on 2026-08-15 — relative paths. */
    private fun manifiesto(version: String) = """
        {"version":"$version","files":{
          "app.html":"/movil/asset/app.html",
          "main.js":"/static/movil/dist/main.js",
          "selftest.js":"/static/movil/dist/selftest.js"}}
    """.trimIndent()

    private fun conFetch(fetch: (String) -> String) =
        AssetStore(ApplicationProvider.getApplicationContext(), fetch)

    @Test
    fun `sin snapshot devuelve un objeto vacio, no null`() {
        // main.js does JSON.parse on this. "" or null would throw inside the WebView, where the
        // only symptom is a blank screen with the reason in a console the phone has not got.
        assertEquals("{}", store().estadoCacheado())
    }

    @Test
    fun `el inventario sobrevive por viejo que sea el snapshot`() {
        // These two used to be a pair about `habitos_pendientes`, the one list the server derived
        // from today's weekday: kept past midnight it offered habits the server answered 409 to,
        // so `estadoCacheado` emptied it. That list left with the Posada split on 2026-08-27 and
        // what remains is inventory, which does not expire. What still has to hold is that age
        // changes NOTHING — the old code reached into the snapshot on a clock condition, and this
        // is what says it no longer does.
        val s = store()
        val cuerpo = """{"libros":[{"id":9}],"peliculas":[],"albums":[]}"""
        s.guardarEstado(cuerpo, System.currentTimeMillis() - 26 * 60 * 60 * 1000)
        val ayer = s.estadoCacheado()
        s.guardarEstado(cuerpo, System.currentTimeMillis())
        assertEquals("la edad del snapshot cambio lo que se lee", s.estadoCacheado(), ayer)
        assertTrue("perdio el inventario", ayer.contains("\"libros\""))
    }

    @Test
    fun `una generacion a medias no se instala`() {
        // A partially downloaded set means the HTML of one version running the JS of another.
        val s = store()
        s.prepararGeneracion("abc123", mapOf("app.html" to "<html>", "main.js" to "x"))
        assertFalse("instalo una generacion sin selftest.js", s.hayGeneracionValida("abc123"))
        s.prepararGeneracion("abc123", mapOf("app.html" to "<html>", "main.js" to "x",
                                             "selftest.js" to "y"))
        assertTrue(s.hayGeneracionValida("abc123"))
    }

    @Test
    fun `volver a lo empaquetado borra la generacion`() {
        val s = store()
        s.prepararGeneracion("abc123", mapOf("app.html" to "<html>", "main.js" to "x",
                                             "selftest.js" to "y"))
        s.volverALoEmpaquetado()
        assertFalse(s.hayGeneracionValida("abc123"))
    }

    // --- Beyond the plan, which leaves `revisarAssets` and `refrescarEstado` untested ---------

    @Test
    fun `las rutas del manifiesto se piden absolutas`() {
        // The plan passes the manifest's value straight to URL(). `/api/movil/assets/` answers
        // RELATIVE paths — Task 4 chose them deliberately — so that is a MalformedURLException
        // the outer catch swallows: `revisarAssets` would return false for ever, silently.
        val pedidas = mutableListOf<String>()
        val s = conFetch { url ->
            pedidas.add(url)
            if (url.endsWith("/api/movil/assets/")) manifiesto("v1") else "contenido"
        }
        assertTrue(s.revisarAssets())
        assertEquals(4, pedidas.size) // the manifest plus the three files
        assertTrue(
            "una ruta viajo relativa: $pedidas",
            pedidas.all { it.startsWith(BuildConfig.BUNKER_URL + "/") },
        )
    }

    @Test
    fun `una descarga interrumpida no registra la version`() {
        // The next run must retry. Recording the version first would mark a half-downloaded set
        // as installed and leave no way back on a phone with no signal.
        val s = conFetch { url ->
            when {
                url.endsWith("/api/movil/assets/") -> manifiesto("v2")
                url.endsWith("selftest.js") -> throw java.io.IOException("se corto")
                else -> "contenido"
            }
        }
        assertFalse(s.revisarAssets())
        assertFalse(s.hayGeneracionValida("v2"))
        // And it is still not installed on the second look, i.e. the version was never recorded.
        var pidioArchivos = false
        val s2 = conFetch { url ->
            if (url.endsWith("/api/movil/assets/")) manifiesto("v2")
            else { pidioArchivos = true; "contenido" }
        }
        assertTrue(s2.revisarAssets())
        assertTrue("no reintento la descarga", pidioArchivos)
    }

    @Test
    fun `una version registrada cuyo directorio desaparecio se vuelve a bajar`() {
        // The defect this replaces: `revisarAssets` compared only the recorded version, so once
        // its directory was gone the early return fired for ever and `handler` fell back to the
        // packaged assets permanently. Deleting the directory by hand is not a contrived case —
        // `handler`'s own sweep did exactly this to a generation being staged.
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        AssetStore(ctx) { url ->
            if (url.endsWith("/api/movil/assets/")) manifiesto("v9") else "contenido"
        }.revisarAssets()

        val dir = java.io.File(ctx.filesDir, "generaciones/v9")
        assertTrue("la generacion no llego a instalarse", dir.exists())
        dir.deleteRecursively()

        var bajo = false
        val s = AssetStore(ctx) { url ->
            if (url.endsWith("/api/movil/assets/")) manifiesto("v9") else { bajo = true; "contenido" }
        }
        assertTrue("no reinstalo la generacion que falta", s.revisarAssets())
        assertTrue("se quedo con la version registrada y nunca volvio a bajar", bajo)
        assertTrue(s.hayGeneracionValida("v9"))
    }

    @Test
    fun `un manifiesto con un nombre de archivo con ruta es rechazado`() {
        // `version` and the keys become path segments. Our own Django bounds what can arrive; it
        // does not validate it, and this is the trust boundary.
        val s = store()
        for (malo in listOf("../fuera", "v1/anidado", "")) {
            try {
                s.prepararGeneracion(malo, mapOf("app.html" to "x", "main.js" to "x",
                                                 "selftest.js" to "x"))
                throw AssertionError("acepto una version con ruta: $malo")
            } catch (e: IllegalArgumentException) { /* esperado */ }
        }
        try {
            s.prepararGeneracion("abc", mapOf("../../settings.py" to "x"))
            throw AssertionError("acepto un nombre de archivo con ruta")
        } catch (e: IllegalArgumentException) { /* esperado */ }
        assertFalse("escribio algo fuera de su directorio",
                    java.io.File(ApplicationProvider.getApplicationContext<android.content.Context>()
                        .filesDir, "fuera").exists())
    }

    @Test
    fun `la misma version no se vuelve a descargar`() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        AssetStore(ctx) { url ->
            if (url.endsWith("/api/movil/assets/")) manifiesto("v3") else "contenido"
        }.revisarAssets()

        var bajo = false
        val s = AssetStore(ctx) { url ->
            if (url.endsWith("/api/movil/assets/")) manifiesto("v3") else { bajo = true; "x" }
        }
        assertFalse("dijo que instalo algo nuevo", s.revisarAssets())
        assertFalse("volvio a bajar una version ya instalada", bajo)
    }

    @Test
    fun `un cuarto asset en el servidor no congela las actualizaciones`() {
        // The freeze this replaces: membership in REQUERIDOS was a `require`, so the day the
        // server shipped a file this version does not know about, the exception went into the
        // blanket catch and every installed phone stopped updating — silently, permanently, and
        // over a file it did not need. Unknown names are ignored; names with a path still throw,
        // which is the check above this one.
        val s = conFetch { url ->
            if (url.endsWith("/api/movil/assets/")) {
                """{"version":"v9","files":{"app.html":"/a","main.js":"/b",
                   "selftest.js":"/c","sw.js":"/d"}}"""
            } else "contenido"
        }
        assertTrue("un archivo de mas congelo la instalacion", s.revisarAssets())
        assertTrue("no instalo los tres que si conoce", s.hayGeneracionValida("v9"))
    }

    @Test
    fun `un 302 no se instala como si fuera un asset`() {
        // The one place in this class that touches a real socket, so the one check that needs
        // one — twelve lines of ServerSocket, no dependency. With `instanceFollowRedirects` off,
        // `inputStream` throws only from 400 up: the body of a captive portal's redirect comes
        // back as an ordinary string, gets written as `main.js`, and passes `hayGeneracionValida`,
        // which only asks whether the file is non-empty.
        val server = ServerSocket(0)
        thread {
            runCatching {
                server.accept().use {
                    it.getOutputStream().write(
                        ("HTTP/1.1 302 Found\r\nLocation: /login\r\n" +
                         "Content-Length: 5\r\n\r\nhola!").toByteArray()
                    )
                }
            }
        }
        server.use {
            assertThrows(IOException::class.java) {
                AssetStore.leerReal("http://127.0.0.1:${it.localPort}/api/movil/assets/")
            }
        }
    }

    @Test
    fun `una respuesta que no es JSON no pisa el snapshot bueno`() {
        // Django answering an HTML error page with a 200 is the case: `leer` only throws on a
        // 4xx/5xx. Storing it would replace a good snapshot with something `estadoCacheado`
        // can only degrade to "{}" — the phone would go blank with the laptop off.
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        val bueno = """{"libros":[{"id":9}]}"""
        AssetStore(ctx).guardarEstado(bueno, System.currentTimeMillis())
        val s = AssetStore(ctx) { "<html>Server Error</html>" }
        assertFalse(s.refrescarEstado())
        assertTrue("piso el snapshot bueno", s.estadoCacheado().contains("\"libros\""))
    }
}
