package cl.alonso.bunker

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
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
    fun `el respaldo escribe siempre en el mismo archivo`() {
        // The 2026-08-17 defect, and the only part of it a check off the device can reach:
        // respaldar() found its file by DISPLAY_NAME, the probe stopped matching after an
        // uninstall, and every capture inserted one more `bunker-cola (N).json`. Robolectric
        // hands back a DIFFERENT Uri per insert (measured: file/1, then file/2), so a second
        // insert is visible right here — the remembered Uri would change.
        val ctx = ApplicationProvider.getApplicationContext<Context>()
        val prefs = ctx.getSharedPreferences("transmisor", Context.MODE_PRIVATE)
        val s = ColaStore(ctx)

        s.encolar("paginas", """{"pages":1}""")
        val primero = prefs.getString(ColaStore.URI_RESPALDO, null)
        assertNotNull("el respaldo no recordo su Uri", primero)

        s.encolar("paginas", """{"pages":2}""")
        s.descartar(s.items()[0].id)
        assertEquals("el respaldo creo un archivo nuevo", primero,
            prefs.getString(ColaStore.URI_RESPALDO, null))
    }

    @Test
    fun `el respaldo contiene la captura`() {
        // The assertion the plan asks for, against the half that can be wrong by logic.
        // Neither `respaldar()`'s return value nor `leerRespaldo()` is asserted here, and both
        // exclusions are measured, not assumed: Robolectric's ContentResolver refuses the
        // truncating mode the rewrite path needs (`openOutputStream(uri, "wt")` →
        // `FileNotFoundException: No content provider`) and refuses to read back what it accepted
        // (`UnsupportedOperationException: You must use ShadowContentResolver.registerInputStream`).
        // Asserting either would be asserting the shadow. What the file must CONTAIN is right here.
        val s = store()
        s.encolar("paginas", """{"pages":7}""")
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
