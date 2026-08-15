package cl.alonso.bunker

import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class ColaStoreTest {

    private fun store() = ColaStore(ApplicationProvider.getApplicationContext())

    @Test
    fun `una captura sobrevive a reabrir el almacen`() {
        store().encolar("paginas", """{"pages":12}""")
        // A second instance is what a process restart looks like from here: nothing is held
        // in memory, everything is read back from disk.
        assertEquals(1, store().pendientes())
        assertEquals("paginas", store().items()[0].verbo)
    }

    @Test
    fun `descartar borra solo el senalado`() {
        val s = store()
        s.encolar("paginas", """{"pages":1}""")
        s.encolar("habito", """{"habit_id":3}""")
        s.descartar(s.items()[0].id)
        assertEquals(1, s.pendientes())
        assertEquals("habito", s.items()[0].verbo)
    }

    @Test
    fun `marcar un error conserva la captura`() {
        val s = store()
        s.encolar("habito", """{"habit_id":3}""")
        s.marcarError(s.items()[0].id, "HTTP 409")
        assertEquals(1, s.pendientes())
        assertEquals("HTTP 409", s.items()[0].error)
    }

    @Test
    fun `dos capturas nunca comparten id`() {
        val s = store()
        repeat(500) { s.encolar("paginas", """{"pages":$it}""") }
        assertEquals(500, s.items().map { it.id }.toSet().size)
    }

    @Test
    fun `el respaldo contiene la captura`() {
        // The assertion the plan asks for, against the half that can be wrong by logic.
        // `leerRespaldo()` is NOT asserted here: Robolectric's ContentResolver accepts the
        // MediaStore write (respaldar() returns true) and then returns an empty read, so a
        // round-trip assertion would be testing the shadow, not ColaStore. Measured:
        // `respaldar=true leido.length=0`.
        val s = store()
        s.encolar("paginas", """{"pages":7}""")
        assertTrue(s.respaldar())
        val json = s.serializar()
        assertTrue("el respaldo no contiene la captura", json.contains("\"pages\":7"))
        assertTrue("el respaldo pierde el verbo", json.contains("\"verbo\":\"paginas\""))
    }

    @Test
    fun `el respaldo anida el payload en vez de escaparlo`() {
        // A double-encoded payload is the failure this format invites: the queue stores the
        // payload as TEXT, so putting the string straight in gives "{\"pages\":7}" — valid
        // JSON that no reader can use without a second parse.
        val s = store()
        s.encolar("paginas", """{"pages":7}""")
        assertTrue("el payload viaja escapado como string", !s.serializar().contains("\\\""))
    }
}
