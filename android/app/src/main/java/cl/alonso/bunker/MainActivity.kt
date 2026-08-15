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
}
