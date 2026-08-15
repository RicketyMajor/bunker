package cl.alonso.bunker

import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

// Deliberately empty of features. This task's deliverable is "an APK exists, installs and
// opens"; the WebView arrives in Task 10, once there is a queue worth showing.
//
// AppCompatActivity and not android.app.Activity: the manifest declares
// `Theme.AppCompat.NoActionBar`, and an AppCompat theme belongs to an AppCompat activity.
class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(TextView(this).apply { text = "Transmisor" })
    }
}
