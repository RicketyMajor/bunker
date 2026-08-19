package cl.alonso.bunker

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings

/**
 * What wakes the process. This exists because the thing it replaces does not work on this phone.
 *
 * `WorkManager`'s periodic work is *deferrable* by definition and the OS is allowed to sit on it.
 * Measured on the Redmi 22041219NY, 2026-08-15: the job reported `Ready: true`, overdue by 7m21s,
 * `Unsatisfied constraints:` empty and `Restricted due to: none`, in standby bucket RARE — and was
 * never dispatched. MIUI forces the app back to RARE about three minutes after it leaves the
 * foreground, with Autostart granted and battery restrictions already removed, so the bucket is
 * not something a setting fixes. `setExpedited` is no answer either: it exists only for one-shot
 * requests, never for periodic ones.
 *
 * An exact alarm is the one self-hosted primitive the platform still promises to fire under Doze
 * and app standby. It may yet be throttled by the same power manager — that is measured, not
 * assumed — but it is the only mechanism left that does not mean adding Firebase to a project that
 * deliberately talks to nothing but its own tailnet.
 *
 * Armed only while the queue holds something, so an empty queue costs zero wake-ups. That is
 * strictly cheaper than the periodic it supplements, which woke every fifteen minutes to find
 * nothing at all.
 */
object Despertador {

    // Matches what the periodic promised. Nothing shorter is worth writing: the platform throttles
    // `setExactAndAllowWhileIdle` to roughly one firing every nine minutes while the device dozes,
    // so a smaller number here is a number the OS quietly ignores.
    private const val CADA_MS = 15 * 60 * 1000L

    private fun intento(context: Context) = PendingIntent.getBroadcast(
        context,
        0,
        Intent(context, DespertadorReceiver::class.java),
        // IMMUTABLE is required from API 31 and correct everywhere: nothing about this intent is
        // meant to be rewritten by whoever holds it.
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
    )

    /**
     * Arms when there is something to send and cancels when there is not.
     *
     * Takes the count rather than reading the queue, so the decision is one comparison a caller
     * can make wrongly in only one way, and so nothing here needs a database to be tested.
     */
    fun sincronizar(context: Context, pendientes: Int) {
        if (pendientes > 0) armar(context) else cancelar(context)
    }

    fun armar(context: Context) {
        val am = context.getSystemService(AlarmManager::class.java)
        val cuando = System.currentTimeMillis() + CADA_MS
        // Not a nicety: from API 31 `setExactAndAllowWhileIdle` throws SecurityException without
        // the grant, and every caller of this runs from a worker or a receiver with nobody
        // watching, where an exception is a queue that stops draining and says nothing. The
        // inexact variant still survives Doze; it is only less punctual, which for a queue that
        // has already waited is an acceptable second best.
        if (Build.VERSION.SDK_INT < 31 || am.canScheduleExactAlarms()) {
            am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, cuando, intento(context))
        } else {
            am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, cuando, intento(context))
        }
    }

    fun cancelar(context: Context) {
        context.getSystemService(AlarmManager::class.java).cancel(intento(context))
    }

    /**
     * The Settings screen that grants what [armar] needs, or `null` when there is nothing to ask.
     *
     * From API 31 `SCHEDULE_EXACT_ALARM` is denied by default, and MIUI files it under *Permisos
     * especiales → Alarmas y recordatorios* rather than in the app's own permission list — where
     * it was looked for on 2026-08-15 and not found. Nothing fails loudly without the grant:
     * [armar] degrades to the inexact variant, so the only symptom is a queue that seems slow.
     *
     * Returned rather than launched, so the decision is testable without an Activity and the
     * caller owns the policy of how often a user may be thrown into Settings.
     */
    fun intentoDePermiso(context: Context): Intent? {
        if (Build.VERSION.SDK_INT < 31) return null
        if (context.getSystemService(AlarmManager::class.java).canScheduleExactAlarms()) return null
        // The package URI opens this app's own toggle; without it the screen is the list of every
        // app on the phone, which is where a grant gets abandoned.
        return Intent(
            Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM,
            Uri.fromParts("package", context.packageName, null),
        )
    }

    /**
     * Opens that screen. `false` means there was nothing to ask, or no screen to open it on.
     *
     * The launch belongs here, beside the policy, because TWO callers need it — the Activity's
     * one-shot ask on focus, and the WebView banner's button — and two copies of "start the intent,
     * tolerate ActivityNotFoundException" drift. The first draft of the banner was exactly that
     * copy, and it had already drifted: it added `FLAG_ACTIVITY_NEW_TASK` on one path only, which
     * puts Settings in its own task and makes Back leave the app instead of returning to the
     * banner that sent you there.
     */
    fun abrirAjustes(context: Context): Boolean {
        val intento = intentoDePermiso(context) ?: return false
        // A phone whose OEM ships no such screen throws ActivityNotFoundException. Crashing on
        // launch would be a worse failure than the imprecision this exists to remove.
        return runCatching { context.startActivity(intento) }.isSuccess
    }
}

class DespertadorReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        // Nothing is flushed here. A manifest receiver gets about ten seconds before it is an ANR,
        // and a flush over a link that has just come back can legitimately take longer than that.
        // The alarm's job was to get this process running at all; the work goes to WorkManager as
        // an expedited request, which is a class the OS does dispatch promptly.
        //
        // Re-armed BEFORE delegating, and the ordering is the whole point: an exact alarm is
        // one-shot, so firing consumes it. `ahora` only enqueues, and its work carries a network
        // constraint — at 03:00 with no link, which is the normal state of a phone whose queue
        // exists *because* there was no link, `doWork` never runs, the re-arm inside it never runs
        // either, and the chain ends on its first miss. Arming first costs one PendingIntent
        // update and makes a miss cost fifteen minutes instead of everything.
        //
        // `doWork` still owns the cancel: it re-reads the queue after the flush and is the only
        // place that knows the wake-up is no longer owed.
        Despertador.armar(context)
        SyncWorker.ahora(context, expedito = true)
    }
}

/**
 * A reboot clears every alarm the platform holds, and the queue does not care that the phone was
 * restarted. Without this the only thing left to re-arm is WorkManager's periodic — the mechanism
 * measured on this phone as sitting `Ready: true` and overdue without ever being dispatched — so a
 * capture made before a restart would wait for a human to open the app, which is the exact failure
 * v2 exists to remove.
 *
 * Exported, unlike [DespertadorReceiver], because BOOT_COMPLETED arrives from outside the app.
 * That is safe here where it would not be there: this arms an alarm from our own queue and touches
 * nothing else, so the worst that a forged broadcast could buy — and BOOT_COMPLETED is a protected
 * broadcast only the system may send — is a wake-up we already owed.
 */
class ArranqueReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        Despertador.sincronizar(context, ColaStore(context).pendientes())
    }
}
