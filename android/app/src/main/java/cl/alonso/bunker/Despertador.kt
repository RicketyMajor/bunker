package cl.alonso.bunker

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build

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
}

class DespertadorReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        // Nothing is flushed here. A manifest receiver gets about ten seconds before it is an ANR,
        // and a flush over a link that has just come back can legitimately take longer than that.
        // The alarm's job was to get this process running at all; the work goes to WorkManager as
        // an expedited request, which is a class the OS does dispatch promptly.
        //
        // Re-arming is deliberately not done here either. `SyncWorker` re-arms from what the queue
        // looks like AFTER the flush, which is the only place that knows whether another wake-up
        // is owed.
        SyncWorker.ahora(context)
    }
}
