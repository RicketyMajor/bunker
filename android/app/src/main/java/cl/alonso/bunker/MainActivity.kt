package cl.alonso.bunker

import android.content.pm.PackageManager
import android.os.Bundle
import android.webkit.WebResourceRequest
import android.webkit.WebView
import androidx.appcompat.app.AppCompatActivity
import androidx.webkit.WebViewAssetLoader
import androidx.webkit.WebViewClientCompat

// AppCompatActivity and not android.app.Activity: the manifest declares
// `Theme.AppCompat.NoActionBar`, and an AppCompat theme belongs to an AppCompat activity.
class MainActivity : AppCompatActivity() {

    private lateinit var vista: WebView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        vista = montarWebView()
        setContentView(vista)

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

    /**
     * The interface. Every byte it shows comes from the device; it makes no network request of
     * its own, which is what lets the whole thing work with the laptop off and is why there is no
     * CORS anywhere in this project.
     */
    private fun montarWebView(): WebView {
        // `handler()` sweeps superseded generations, so it is called ONCE and shared. Twice would
        // resolve the directory twice, and the second resolution could disagree with the first.
        val servidor = AssetStore(this).handler()
        val loader = WebViewAssetLoader.Builder()
            // Both prefixes, and the second is not optional. `app.html` is a Django template and
            // its rendered script tag reads `/static/movil/dist/main.js` — that is what Django
            // emits and what the APK downloads. Registering only `/movil/` leaves that request
            // unintercepted: the page renders, no script loads, and nothing reports an error.
            //
            // The extra `dist/` segment costs nothing: `AssetStore.handler` resolves a request
            // by `substringAfterLast('/')`, so depth under this prefix is irrelevant — which is
            // also why `copiarAssets` must stage the bundle FLAT in `assets/movil/`.
            .addPathHandler("/movil/", servidor)
            .addPathHandler("/static/movil/", servidor)
            .build()

        return WebView(this).apply {
            settings.javaScriptEnabled = true
            // app.js still writes the snapshot to localStorage on the optimistic-update paths.
            // Native storage is the source of truth here, but turning this off would throw on
            // every one of those writes.
            settings.domStorageEnabled = true
            // Nothing here is a browser. No file access, no content providers, no zoom controls.
            settings.allowFileAccess = false
            settings.allowContentAccess = false

            webViewClient = object : WebViewClientCompat() {
                override fun shouldInterceptRequest(view: WebView, req: WebResourceRequest) =
                    loader.shouldInterceptRequest(req.url)

                // The bridge is exposed to whatever document this WebView holds, so what it is
                // allowed to hold is a security boundary, not a nicety. A link to anywhere else
                // would hand `Bunker` to that page. Refused outright rather than opened in a
                // browser: nothing in this app has any business navigating.
                override fun shouldOverrideUrlLoading(view: WebView, req: WebResourceRequest) =
                    req.url.host != "appassets.androidplatform.net"
            }

            addJavascriptInterface(Puente(this@MainActivity, ColaStore(this@MainActivity)), "Bunker")
            loadUrl("https://appassets.androidplatform.net/movil/app.html")
        }
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
        // The banner's own `visibilitychange` listener cannot be relied on: nothing here calls
        // `WebView.onPause()/onResume()`, so the document's visibility may never flip when the
        // user returns from the Settings screen that banner sent them to — leaving it nagging for
        // a permission already granted. Window focus is the signal this app has already proven
        // reliable for "the user is here", and it dispatches the event the page ALREADY listens
        // for rather than calling a function of its own, so the page keeps one contract.
        vista.evaluateJavascript("document.dispatchEvent(new Event('visibilitychange'))", null)
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
    // One shot, and there IS a way back now: the WebView paints a banner when the grant is
    // missing and `Puente.pedirAlarmaExacta` re-offers this same intent from a tap (2026-08-18,
    // discharging the marker that stood here). This stays pref-guarded and stays automatic; the
    // two paths are deliberately independent, so the banner cannot un-spend the single automatic
    // ask and the automatic ask cannot silence the banner.
    private fun pedirAlarmaExacta() {
        val prefs = getSharedPreferences("transmisor", MODE_PRIVATE)
        if (prefs.getBoolean("alarma_pedida", false)) return
        if (Despertador.abrirAjustes(this)) prefs.edit().putBoolean("alarma_pedida", true).apply()
    }
}
