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
        if (hasFocus) SyncWorker.ahora(this)
    }
}
