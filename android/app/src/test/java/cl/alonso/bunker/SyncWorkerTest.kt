package cl.alonso.bunker

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Beyond the plan, which leaves these rules inside `doWork` where nothing but a device can reach
 * them. No Robolectric: with the decision split out, both rules are pure Kotlin over a data class.
 */
class SyncWorkerTest {

    private fun resultado(
        enviados: Int = 0,
        pendientes: Int = 0,
        retirados: Int = 0,
        alcanzo: Boolean = false,
        hechos: List<String> = emptyList(),
    ) = Resultado(enviados, pendientes, retirados, alcanzo, hechos)

    @Test
    fun `sin enlace y con cola pendiente, reintenta`() {
        assertTrue(SyncWorker.reintentar(resultado(pendientes = 3, alcanzo = false)))
    }

    @Test
    fun `una cola rechazada entera con 409 NO reintenta`() {
        // The battery rule. enviados == 0 looks like failure and is not: the link worked and the
        // server said no. A backoff chain here re-asks a question already answered.
        assertFalse(SyncWorker.reintentar(resultado(enviados = 0, pendientes = 3, alcanzo = true)))
    }

    @Test
    fun `un vaciado parcial NO reintenta y espera al periodico`() {
        // One 2xx, then the link dies. `alcanzoElServidor` is true because of the first item, so
        // this returns false ON PURPOSE — the periodic run picks the rest up inside 15 minutes.
        // Pinned as a decision rather than left as an accident of the boolean.
        assertFalse(SyncWorker.reintentar(resultado(enviados = 1, pendientes = 2, alcanzo = true)))
    }

    @Test
    fun `una cola vaciada del todo no reintenta`() {
        assertFalse(SyncWorker.reintentar(resultado(enviados = 3, pendientes = 0, alcanzo = true)))
    }

    @Test
    fun `sin enlace y sin nada pendiente no reintenta`() {
        // Everything in the queue was a retired verb: discarded locally, nothing to send, and no
        // reason to wake up again.
        assertFalse(SyncWorker.reintentar(resultado(retirados = 2, pendientes = 0, alcanzo = false)))
    }

    @Test
    fun `el titulo concuerda en numero`() {
        assertEquals("1 despacho archivado", SyncWorker.titulo(1))
        assertEquals("2 despachos archivados", SyncWorker.titulo(2))
    }
}
