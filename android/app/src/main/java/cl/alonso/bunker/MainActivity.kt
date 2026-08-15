package cl.alonso.bunker

import android.content.pm.PackageManager
import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

// Still empty of features. The WebView arrives in Task 10, once there is a queue worth showing.
//
// AppCompatActivity and not android.app.Activity: the manifest declares
// `Theme.AppCompat.NoActionBar`, and an AppCompat theme belongs to an AppCompat activity.
class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(TextView(this).apply { text = "Transmisor" })

        // Asked only when it is not already granted, against the plan's unconditional call: on
        // API 33+ a second request after a denial does nothing at all, and an unconditional one
        // spends the single re-ask the system allows on a launch nobody was waiting for.
        // The flush never depends on the answer — SyncWorker checks the grant before notifying
        // and does the work regardless.
        if (android.os.Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), 1)
        }
        SyncWorker.programar(this)
    }

    // `onWindowFocusChanged` and not `onResume`: an invisible restore by MIUI runs the early
    // lifecycle callbacks but never takes window focus, and focus is the only signal that
    // separates "the user opened the app" from "the system revived the process".
    //
    // This fires more than once per visit — the permission dialog alone costs two, measured
    // 2026-08-15 as one-shots at 14:07:10 and 14:07:13 — and each one is NOT free: `doWork`
    // runs `refrescarEstado()` and `revisarAssets()` outside the `pendientes() > 0` guard, so
    // every fire is two blocking round trips to the tailnet. That is wanted here, because the
    // reason to return to the app is to read a fresh snapshot; it is not wanted from a
    // background wake, which is the whole point of hanging it off focus instead of `onCreate`.
    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (!hasFocus) return
        SyncWorker.ahora(this)
        pedirAlarmaExacta()
    }

    // Here and not in `onCreate` beside the notifications request, for the same property focus is
    // already being used for: window focus is gained only when no system dialog is on top of us,
    // so this cannot open Settings over the POST_NOTIFICATIONS dialog and spend the single ask
    // the system allows.
    //
    // Sent once and remembered, because nothing rate-limits reopening a Settings screen the way
    // the platform rate-limits a permission dialog: unconditional, this would throw the user out
    // of the app on every launch after a deliberate "no".
    //
    // ponytail: one shot and no way back — whoever declines keeps the inexact alarm for ever. The
    // upgrade is a banner in the WebView (Task 10), which is the first screen able to say why the
    // queue is slow and offer the intent again.
    private fun pedirAlarmaExacta() {
        val prefs = getSharedPreferences("transmisor", MODE_PRIVATE)
        if (prefs.getBoolean("alarma_pedida", false)) return
        val intento = Despertador.intentoDePermiso(this) ?: return
        // A phone whose OEM ships no such screen throws ActivityNotFoundException. Crashing on
        // launch would be a worse failure than the imprecision this exists to remove.
        if (runCatching { startActivity(intento) }.isSuccess) {
            prefs.edit().putBoolean("alarma_pedida", true).apply()
        }
    }
}
