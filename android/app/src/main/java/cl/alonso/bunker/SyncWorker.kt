package cl.alonso.bunker

import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.OutOfQuotaPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import java.util.concurrent.TimeUnit

/**
 * When a flush happens. Nothing here knows how to talk HTTP; that is Transmisor's job.
 *
 * WorkManager and not a plain thread because the app is closed when this matters: the whole
 * point of v2 is a flush that does not need the user to open anything.
 *
 * `Worker` and not `CoroutineWorker`, against the plan: everything below it blocks — an
 * HttpURLConnection and a SQLite read — and `CoroutineWorker.doWork` runs on `Dispatchers.Default`,
 * a CPU-bound pool that blocking calls starve. Getting that right needs a `withContext(IO)` that a
 * plain `Worker` does not need at all, because WorkManager already hands it a background executor.
 * Less code for the more correct behaviour.
 */
class SyncWorker(ctx: Context, params: WorkerParameters) : Worker(ctx, params) {

    override fun doWork(): Result {
        val store = ColaStore(applicationContext)
        val r = if (store.pendientes() > 0) Transmisor(store).vaciar() else null
        if (r != null && r.enviados > 0) notificar(r)

        // Deliberately NOT gated on the queue being non-empty, which is the common case: the whole
        // point of the snapshot is that it is fresh when there is nothing to send. And after the
        // flush rather than before it, so the snapshot it fetches already accounts for what was
        // just sent — otherwise the phone shows an inventory that contradicts its own capture.
        AssetStore(applicationContext).run { refrescarEstado(); revisarAssets() }

        // Re-armed from what the queue looks like AFTER the flush, and only here: this is the one
        // place that knows whether another wake-up is owed. `r.pendientes` is computed at the end
        // of `vaciar()`, so it is the remainder, not the starting count; a null `r` means the
        // queue was already empty. An empty queue arms nothing and the phone sleeps undisturbed.
        Despertador.sincronizar(applicationContext, r?.pendientes ?: 0)

        return if (r != null && reintentar(r)) Result.retry() else Result.success()
    }

    @SuppressLint("MissingPermission") // checked immediately below; lint cannot see through it
    private fun notificar(r: Resultado) {
        val ctx = applicationContext
        if (android.os.Build.VERSION.SDK_INT >= 33 &&
            ctx.checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) return  // Denied: the flush already happened. The permission never gates the work.

        val mgr = ctx.getSystemService(NotificationManager::class.java)
        mgr.createNotificationChannel(
            NotificationChannel(CANAL, "Despachos", NotificationManager.IMPORTANCE_DEFAULT)
        )

        // One notification per flush, not one per capture: with the app closed, seven
        // notifications in a row are noise, not information.
        val estilo = NotificationCompat.InboxStyle()
        r.hechos.take(6).forEach { estilo.addLine(it) }

        NotificationManagerCompat.from(ctx).notify(
            1,
            NotificationCompat.Builder(ctx, CANAL)
                .setSmallIcon(android.R.drawable.stat_sys_upload_done)
                .setContentTitle(titulo(r.enviados))
                .setContentText(r.hechos.firstOrNull() ?: "El Búnker recibió tus capturas.")
                .setStyle(estilo)
                .setAutoCancel(true)
                .build()
        )
    }

    companion object {
        private const val CANAL = "despachos"
        private const val PERIODICO = "transmisor-periodico"

        /**
         * Retry only when nothing reached the server. Split out of `doWork` and made pure,
         * against the plan, because it is a rule and rules are what get silently wrong — and
         * inside a Worker it cannot be exercised without a device.
         *
         * A queue rejected wholesale with 409s has `enviados == 0` while the link is perfectly
         * fine, and retrying that on a backoff would burn battery re-asking a question already
         * answered. A partial flush — one 2xx, then the link dies — also returns false on
         * purpose: `alcanzoElServidor` proves the link worked, and the periodic run picks the
         * rest up within 15 minutes without a backoff chain.
         */
        fun reintentar(r: Resultado): Boolean = !r.alcanzoElServidor && r.pendientes > 0

        /** Pure for the same reason, and because a plural is exactly the kind of off-by-one nobody checks. */
        fun titulo(enviados: Int): String =
            if (enviados == 1) "1 despacho archivado" else "$enviados despachos archivados"

        fun programar(context: Context) {
            val conRed = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED).build()

            // 15 minutes is WorkManager's floor for periodic work, not a chosen cadence. It runs
            // only when there is a network and returns immediately on an empty queue.
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                PERIODICO,
                ExistingPeriodicWorkPolicy.KEEP,
                PeriodicWorkRequestBuilder<SyncWorker>(15, TimeUnit.MINUTES)
                    .setConstraints(conRed)
                    .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
                    .build()
            )
            // No `ahora()` here, and the reason is measured, not stylistic. Registering the
            // periodic work happens in `onCreate`, and MIUI recreates the Activity invisibly
            // every time the system revives the process for a scheduled run — so an immediate
            // flush hung off this call fired a redundant one-shot two seconds ahead of the
            // periodic on every background wake (measured 2026-08-15, 13:45:51 vs 13:45:53).
            // Two flushes per wake, and no way to attribute an arrival to the periodic alone.
            // The immediate flush now hangs off the window actually taking focus instead.
        }

        fun ahora(context: Context) {
            val peticion = OneTimeWorkRequestBuilder<SyncWorker>()
                .setConstraints(
                    Constraints.Builder()
                        .setRequiredNetworkType(NetworkType.CONNECTED).build()
                )

            // Expedited, because the alarm that calls this exists precisely to escape deferrable
            // scheduling — enqueuing ordinary work from the receiver hands it straight back to
            // the scheduler that was sitting on it for seven minutes. RUN_AS_NON_EXPEDITED and
            // not DROP: when the quota is spent, late beats never, and the queue holds everything
            // until a 2xx regardless.
            //
            // Only from API 31. Below it WorkManager runs expedited work as a foreground service
            // and demands a `getForegroundInfoAsync` the worker would have to implement — which
            // needs `androidx.concurrent.futures` on the compile classpath, a dependency for a
            // code path no phone here will ever run. Below 31 this stays ordinary work, exactly
            // as it was before, so nothing regresses.
            if (android.os.Build.VERSION.SDK_INT >= 31) {
                peticion.setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
            }
            WorkManager.getInstance(context).enqueue(peticion.build())
        }
    }
}
