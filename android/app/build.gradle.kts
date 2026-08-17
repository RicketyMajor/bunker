plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "cl.alonso.bunker"
    compileSdk = 34

    defaultConfig {
        applicationId = "cl.alonso.bunker"
        // 29 is not a preference: the permissionless MediaStore write into Documents/ — the
        // whole mechanism behind a backup that survives uninstalling — starts at API 29.
        minSdk = 29
        targetSdk = 34
        versionCode = 1
        versionName = "2.0"
        // The tailnet host the queue transmits to. Read at build time so the URL lives in one
        // place; a phone talking to the wrong host fails silently for days.
        buildConfigField("String", "BUNKER_URL",
            "\"https://alonso-inspiron-5570.tail834684.ts.net\"")
    }

    buildFeatures { buildConfig = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    // Robolectric reads the manifest from the merged resources; without this every test in
    // Tasks 6, 7 and 9 fails before its first assertion.
    testOptions { unitTests { isIncludeAndroidResources = true } }
}

// One source of truth: the assets belong to the repository and the APK carries a copy, never a
// fork. A second, separately edited copy of the frontend is the failure mode this whole task is
// shaped around.
//
// Correction to the plan, found before writing any of it: `app.html` is a Django TEMPLATE, not a
// static file. A plain Copy ships `{% load static %}` and `{% static 'movil/queue.js' %}`
// verbatim, and the WebView then loads a page whose two script tags point at a literal `{% … %}`.
// The page renders, nothing runs, and nothing reports an error. The three substitutions below are
// exactly what Django's renderer emits — minus the CSRF value, which the APK never uses, because
// `Cola.vaciar` is dead code there and `Transmisor` owns the flush.
//
// ponytail: the render is reproduced here rather than invoked, because invoking it would make the
// Android build depend on a running Django. Ceiling: a fourth template tag added to `app.html`
// ships raw and breaks the BUNDLED copy. It is self-healing — the first successful contact with
// the server replaces the bundle with Django's own render — so the upgrade is worth it only if a
// phone ever has to live on bundled assets for long.
val copiarAssets by tasks.registering(Copy::class) {
    val repo = rootDir.parentFile
    from(repo.resolve("bunker_core/static/movil")) { include("app.js", "queue.js") }
    from(repo.resolve("bunker_core/templates/movil")) {
        include("app.html")
        filter { linea: String ->
            linea.replace("{% load static %}", "")
                .replace(Regex("\\{% static '([^']+)' %}"), "/static/$1")
                .replace("{{ csrf_token }}", "")
        }
    }
    into(layout.projectDirectory.dir("src/main/assets/movil"))
}
tasks.named("preBuild") { dependsOn(copiarAssets) }

dependencies {
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.work:work-runtime-ktx:2.9.1")
    implementation("androidx.webkit:webkit:1.11.0")
    implementation("androidx.core:core-ktx:1.13.1")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.robolectric:robolectric:4.13")
    // ApplicationProvider lives here, not in Robolectric. Without it every test class in
    // Tasks 6 and 7 fails to compile on its first line.
    testImplementation("androidx.test:core:1.6.1")
}
