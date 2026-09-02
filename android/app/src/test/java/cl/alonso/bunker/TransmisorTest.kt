package cl.alonso.bunker

import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.net.InetAddress
import java.net.ServerSocket
import kotlin.concurrent.thread

@RunWith(RobolectricTestRunner::class)
class TransmisorTest {

    private fun store() = ColaStore(ApplicationProvider.getApplicationContext())

    @Test
    fun `un 2xx borra la captura`() {
        val s = store()
        s.encolar("paginas", """{"pages":12}""")
        val r = Transmisor(s) { _, _ -> Respuesta(201, """{"feedback":"12 páginas."}""") }.vaciar()
        assertEquals(1, r.enviados)
        assertEquals(0, s.pendientes())
        assertEquals(listOf("12 páginas."), r.hechos)
    }

    @Test
    fun `un fallo de red NO borra la captura`() {
        val s = store()
        s.encolar("paginas", """{"pages":12}""")
        val r = Transmisor(s) { _, _ -> throw java.io.IOException("sin ruta") }.vaciar()
        assertEquals(0, r.enviados)
        assertEquals(1, s.pendientes())
        assertTrue("no debio creer que alcanzo el servidor", !r.alcanzoElServidor)
    }

    @Test
    fun `un fallo de red no escribe un motivo sobre uno real`() {
        // Beyond the plan. A 409 marks the reason the capture is stuck; the next flush with no
        // signal must not overwrite it with "sin enlace" — that erases the only thing that tells
        // Alonso why the item is in the Purgatorio.
        val s = store()
        s.encolar("paginas", """{"pages":3}""")
        Transmisor(s) { _, _ -> Respuesta(409, """{"message":"Esa página ya se anotó hoy."}""") }.vaciar()
        Transmisor(s) { _, _ -> throw java.io.IOException("sin ruta") }.vaciar()
        assertEquals("Esa página ya se anotó hoy.", s.items()[0].error)
    }

    @Test
    fun `un 4xx conserva la captura con el motivo real`() {
        val s = store()
        s.encolar("paginas", """{"pages":3}""")
        val r = Transmisor(s) { _, _ ->
            Respuesta(409, """{"message":"Esa página ya se anotó hoy."}""")
        }.vaciar()
        assertEquals(1, s.pendientes())
        assertEquals("Esa página ya se anotó hoy.", s.items()[0].error)
        assertTrue("un 409 SI alcanzo el servidor", r.alcanzoElServidor)
    }

    @Test
    fun `un 500 conserva la captura`() {
        // Beyond the plan. A 5xx is the case the queue exists for as much as a 4xx: `finish_book`
        // answered 201 and then 500'd for real, and an item dropped on a 5xx is a capture lost.
        val s = store()
        s.encolar("paginas", """{"pages":12}""")
        val r = Transmisor(s) { _, _ -> Respuesta(500, "<html>Server Error</html>") }.vaciar()
        assertEquals(0, r.enviados)
        assertEquals(1, s.pendientes())
        assertEquals("HTTP 500", s.items()[0].error)
    }

    @Test
    fun `el motivo se lee de las tres formas que el servidor responde`() {
        // Beyond the plan. `motivo()` parses three shapes and the plan's own check exercises only
        // `message` — but that is the shape of 2 of the 12 routes. Read off the code 2026-08-15:
        // posada answers {"status","message"}, the collection views answer {"error"}, and the DRF
        // ViewSets (the three inbox routes, wishlist_peli, wishlist_disco) answer a serializer
        // dict. A motivo that falls through to "HTTP 400" is a Purgatorio entry that says nothing.
        fun motivoDe(cuerpo: String): String {
            val s = store()
            s.encolar("paginas", """{"pages":1}""")
            Transmisor(s) { _, _ -> Respuesta(400, cuerpo) }.vaciar()
            return s.items()[0].error!!
        }
        assertEquals(
            "La página no puede ser negativa.",
            motivoDe("""{"error":"La página no puede ser negativa."}"""),
        )
        assertEquals(
            "This field is required.",
            motivoDe("""{"barcode":["This field is required."]}"""),
        )
        assertEquals("HTTP 400", motivoDe("<html>Bad Request</html>"))
    }

    @Test
    fun `un verbo retirado se descarta una vez y no cuenta como enviado`() {
        // Changed from the plan: `encolar` refuses an unknown verb now, so the row is seeded
        // straight into SQLite. That is also the only way it happens in the wild — a dispatch an
        // older version left behind whose verb was retired since — and it is the same correction
        // v1's selftest needed, for the same reason.
        val s = store()
        s.pendientes() // opens the database, so the table exists to seed
        sembrarDirecto("minutos", """{"minutes":45}""")
        assertEquals(1, s.pendientes())
        val r = Transmisor(s) { _, _ -> throw AssertionError("no debio llamar al servidor") }.vaciar()
        assertEquals(1, r.retirados)
        assertEquals(0, r.enviados)
        assertEquals(0, s.pendientes())
    }

    @Test
    fun `encolar rechaza un verbo que vaciar borraria`() {
        // The other half of the rule above, and the one that matters at a call site: what
        // `vaciar` deletes without asking, `encolar` must never have accepted.
        val s = store()
        try {
            s.encolar("paginass", """{"pages":3}""") // the typo that costs a capture
            throw AssertionError("encolar acepto un verbo sin ruta")
        } catch (e: IllegalArgumentException) {
            assertTrue(e.message!!.contains("paginass"))
        }
        assertEquals(0, s.pendientes())
    }

    private fun sembrarDirecto(verbo: String, payload: String) {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        val ruta = ctx.getDatabasePath("cola.db").path
        android.database.sqlite.SQLiteDatabase.openDatabase(
            ruta, null, android.database.sqlite.SQLiteDatabase.OPEN_READWRITE
        ).use { db ->
            db.execSQL(
                "INSERT INTO despachos (id, verbo, payload, creado) VALUES (?, ?, ?, ?)",
                arrayOf(java.util.UUID.randomUUID().toString(), verbo, payload, System.currentTimeMillis()),
            )
        }
    }

    @Test
    fun `una captura hecha durante el vaciado no se pierde`() {
        // The defect queue.js documents in its longest comment, now in Kotlin without that
        // comment to guard it. The poster enqueues mid-flush, exactly as a tap would.
        val s = store()
        s.encolar("paginas", """{"pages":1}""")
        val r = Transmisor(s) { _, _ ->
            s.encolar("wishlist_libro", """{"title":"Dune"}""")
            Respuesta(201, "{}")
        }.vaciar()
        assertEquals(1, r.enviados)
        assertEquals(1, s.pendientes())
        assertEquals("wishlist_libro", s.items()[0].verbo)
    }

    @Test
    fun `dos vaciados solapados no transmiten nada dos veces`() {
        val s = store()
        s.encolar("paginas", """{"pages":1}""")
        var llamadas = 0
        val t = Transmisor(s) { _, _ -> llamadas++; Respuesta(201, "{}") }
        val hilos = (1..4).map { Thread { t.vaciar() } }
        hilos.forEach { it.start() }; hilos.forEach { it.join() }
        assertEquals("la captura se transmitio $llamadas veces", 1, llamadas)
    }

    @Test
    fun `las rutas cubren todos los verbos que la cola acepta`() {
        // The selftest asserts RUTAS equals queue.js's map; this asserts the ten keys are the
        // ten the Transmisor names, so a typo in a key is caught here and not as a silent
        // `retirados++` that deletes the capture on the phone.
        //
        // Ten and not twelve since the 2026-08-27 split: "habito" and "sesion" left with La
        // Posada, and this repository can no longer reach the endpoints they posted to.
        assertEquals(10, Transmisor.RUTAS.size)
        assertEquals(
            listOf(
                "escaneo_disco", "escaneo_libro", "escaneo_peli", "paginas",
                "terminar_disco", "terminar_libro", "terminar_peli",
                "wishlist_disco", "wishlist_libro", "wishlist_peli",
            ),
            Transmisor.RUTAS.keys.sorted(),
        )
        assertTrue(
            "toda ruta empieza en / y termina en /",
            Transmisor.RUTAS.values.all { it.startsWith("/") && it.endsWith("/") },
        )
    }

    // A fake server that READS the request before it answers. Closing a socket while the request
    // body is still unread makes the kernel answer with an RST, and the client sees
    // `IOException: Error writing to server` — a defect in this helper, not in `postReal`.
    // Measured 2026-08-18: the first draft of the check below failed with that exception whether
    // redirects were on or off, which is the signature of a check that proves nothing.
    private val cabecerasVistas = mutableListOf<String>()

    private fun contestar(server: ServerSocket, respuesta: String) {
        server.accept().use { sock ->
            val entrada = sock.getInputStream()
            // Headers read a byte at a time rather than through a BufferedReader: a reader would
            // pull the body into its buffer as CHARACTERS, and `Content-Length` counts BYTES. With
            // an ASCII payload the two agree and the bug hides; with one accented character — and
            // this app's payloads carry titles — the drain under-reads and the response is written
            // with request bytes still unread, which is the RST this helper exists to avoid.
            var largo = 0
            while (true) {
                val linea = StringBuilder()
                var b = entrada.read()
                while (b != -1 && b != '\n'.code) {
                    if (b != '\r'.code) linea.append(b.toChar())
                    b = entrada.read()
                }
                if (linea.isEmpty() || b == -1) break
                cabecerasVistas.add(linea.toString())
                if (linea.startsWith("Content-Length:", ignoreCase = true)) {
                    largo = linea.substring(15).trim().toString().toInt()
                }
            }
            repeat(largo) { entrada.read() }
            sock.getOutputStream().apply { write(respuesta.toByteArray()); flush() }
        }
    }

    @Test
    fun `un 302 llega como 302 y no borra la captura`() {
        // The one check in this class that opens a real socket, because the property under test
        // belongs to HttpURLConnection and not to us: `postReal` turns `instanceFollowRedirects`
        // off so that a redirect in front of Django cannot come back a 2xx — and a 2xx is what
        // DELETES the capture. The fake server answers TWICE on purpose: with redirects left on,
        // the second answer's 200 is what arrives, so this fails saying the capture was deleted
        // rather than failing whichever way the runtime happens to break.
        //
        // Two things it does NOT prove, both worth saying out loud. That `disconnect()` reaches
        // the failure path: a leaked connection is not observable from a unit test. And that any
        // of this holds ON THE PHONE: Robolectric resolves `URL.openConnection()` through the
        // JVM's stack, the device through OkHttp's, and the manifest forbids cleartext so this
        // URL could never occur in production. Both repairs are read there, not measured.
        val server = ServerSocket(0, 0, InetAddress.getLoopbackAddress())
        thread {
            runCatching {
                contestar(server, "HTTP/1.1 302 Found\r\nLocation: /destino\r\nContent-Length: 0\r\n\r\n")
                contestar(server, "HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok")
            }
        }
        val s = store()
        s.encolar("paginas", """{"pages":12}""")
        server.use { srv ->
            // `postReal` for real, only the URL substituted: BuildConfig.BUNKER_URL points at the
            // tailnet and this check must not need one to exist.
            val r = Transmisor(s) { _, cuerpo ->
                Transmisor.postReal("http://127.0.0.1:${srv.localPort}/api/books/tracker/pages/", cuerpo)
            }.vaciar()
            assertEquals("un 302 se tomo por un envio bueno", 0, r.enviados)
            assertTrue("no vio al servidor cuando si lo alcanzo", r.alcanzoElServidor)
        }
        assertEquals("la captura se borro con un 302", 1, s.pendientes())
        // Reading a non-2xx body is the other half of what only a socket proves: `errorStream` is
        // null for a 3xx, and the `?: ""` is what stops that from throwing here.
        assertEquals("HTTP 302", s.items()[0].error)
    }

    @Test
    fun `cada POST lleva el token de la API`() {
        // Sobre un socket de verdad, porque lo que se prueba es lo que sale AL CABLE: una
        // aserción sobre `BuildConfig` sólo probaría que la constante existe.
        //
        // VACUIDAD PRIMERO, y aquí muerde de verdad: si `BUNKER_API_TOKEN` no está en el entorno
        // del build, `BuildConfig.BUNKER_TOKEN` es "" y `setRequestProperty` manda la cabecera
        // VACÍA — con lo que comparar la cabecera con la constante sería comparar "" con "" y
        // saldría verde con el token sin llegar nunca al teléfono. Es el mismo verde en las dos
        // direcciones que la Tarea 2 se comió. `cli/doctor.py` hereda la variable de `.env`
        // porque `_run` no toca el entorno; un `./gradlew` a mano sin ella falla aquí, y debe.
        assertTrue(
            "BUNKER_API_TOKEN no estaba en el entorno del build: BuildConfig.BUNKER_TOKEN esta " +
            "vacio, y entonces esta comprobacion no puede distinguir un token puesto de uno " +
            "ausente. Compila con BUNKER_API_TOKEN=... (cli/doctor.py lo hereda de .env).",
            BuildConfig.BUNKER_TOKEN.isNotEmpty())

        cabecerasVistas.clear()
        val server = ServerSocket(0, 0, InetAddress.getLoopbackAddress())
        thread { runCatching { contestar(server, "HTTP/1.1 201 Created\r\nContent-Length: 0\r\n\r\n") } }
        val s = store()
        s.encolar("paginas", """{"pages":12}""")
        server.use { srv ->
            Transmisor(s) { _, cuerpo ->
                Transmisor.postReal("http://127.0.0.1:${srv.localPort}/api/books/tracker/pages/", cuerpo)
            }.vaciar()
        }
        val token = cabecerasVistas
            .firstOrNull { it.startsWith("X-Bunker-Api-Token:", ignoreCase = true) }
            ?.substringAfter(':')?.trim()
        assertEquals("el POST del Transmisor salio sin el token de la API",
                     BuildConfig.BUNKER_TOKEN, token)
        // Y no a costa del Content-Type, que es lo que hace que Django lea el cuerpo como JSON.
        assertTrue("el POST perdio su Content-Type al ganar el token",
                   cabecerasVistas.any { it.startsWith("Content-Type: application/json", true) })
    }
}
