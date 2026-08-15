package cl.alonso.bunker

import android.app.AlarmManager
import android.content.Context
import android.content.Intent
import android.provider.Settings
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.shadows.ShadowAlarmManager

/**
 * The rule the whole wake-up strategy rests on: an alarm exists exactly while the queue does.
 *
 * Robolectric here and not plain Kotlin — unlike `SyncWorkerTest` — because the thing worth
 * asserting is not the branch, it is that an alarm was actually handed to the platform. A test of
 * `if (pendientes > 0)` would pass against a `sincronizar` that scheduled nothing at all.
 */
@RunWith(RobolectricTestRunner::class)
class DespertadorTest {

    private val ctx: Context get() = ApplicationProvider.getApplicationContext()

    private fun alarmas() =
        shadowOf(ctx.getSystemService(AlarmManager::class.java)).scheduledAlarms

    private fun programada() = alarmas().firstOrNull()

    @Test
    fun `una cola con algo pendiente arma una alarma`() {
        Despertador.sincronizar(ctx, 1)
        assertNotNull("no programo ninguna alarma con la cola llena", programada())
    }

    @Test
    fun `una cola vacia no despierta el telefono`() {
        // The reason this is cheaper than the periodic it supplements: nothing to send costs no
        // wake-ups at all, where the 15-minute periodic woke up to find nothing.
        Despertador.sincronizar(ctx, 1)
        Despertador.sincronizar(ctx, 0)
        assertNull("dejo una alarma armada sin nada que enviar", programada())
    }

    @Test
    @Suppress("DEPRECATION")  // `type` is the only way Robolectric 4.13 exposes this field.
    fun `la alarma despierta el dispositivo y no solo lo aprovecha si esta despierto`() {
        // RTC_WAKEUP and not RTC: the whole point is a phone in a pocket with the screen off.
        Despertador.sincronizar(ctx, 3)
        assertEquals(AlarmManager.RTC_WAKEUP, programada()!!.type)
    }

    @Test
    fun `el receptor rearma antes de delegar el trabajo`() {
        // An exact alarm is one-shot: firing consumes it. `ahora` only enqueues work that carries
        // a network constraint, so a 03:00 firing with no link — the normal state of a phone whose
        // queue exists because there was no link — never reaches the re-arm inside `doWork`. If
        // the receiver does not arm first, the chain ends on its first miss.
        Despertador.cancelar(ctx)
        runCatching { DespertadorReceiver().onReceive(ctx, Intent()) }
        assertNotNull("la cadena muere en el primer disparo sin red", programada())
    }

    @Test
    fun `tras un reinicio la alarma vuelve si la cola tiene algo`() {
        // A reboot clears every alarm the platform holds. Without this receiver the only thing
        // left to re-arm is the periodic that this phone was measured never dispatching.
        Despertador.cancelar(ctx)
        ColaStore(ctx).encolar("paginas", """{"pages":7}""")
        ArranqueReceiver().onReceive(ctx, Intent(Intent.ACTION_BOOT_COMPLETED))
        assertNotNull("un reinicio dejo la cola sin despertador", programada())
    }

    @Test
    fun `sin el permiso ofrece la pantalla que lo concede, apuntada a esta app`() {
        ShadowAlarmManager.setCanScheduleExactAlarms(false)
        val intento = Despertador.intentoDePermiso(ctx)
        assertEquals(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM, intento?.action)
        // Without the package URI the screen is every app on the phone, which is where a grant
        // gets abandoned.
        assertEquals("package:cl.alonso.bunker", intento?.data.toString())
    }

    @Test
    fun `con el permiso concedido no manda a nadie a Ajustes`() {
        ShadowAlarmManager.setCanScheduleExactAlarms(true)
        assertNull(
            "mando al usuario a Ajustes con el permiso ya concedido",
            Despertador.intentoDePermiso(ctx),
        )
    }

    @Test
    fun `rearmar no acumula alarmas`() {
        // FLAG_UPDATE_CURRENT with a fixed request code, so a flush that leaves the queue full
        // replaces its own alarm instead of stacking one per attempt.
        repeat(5) { Despertador.sincronizar(ctx, 2) }
        assertEquals("acumulo una alarma por intento", 1, alarmas().size)
    }
}
