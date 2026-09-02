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
        // El token de la API, cocido en el build igual que la URL. NO va en el repositorio: sale
        // del entorno, y vacio si no esta — con lo que el APK habla sin credencial y el servidor
        // le responde 403 en voz alta, en vez de llevar un token de relleno que si funcionaria.
        // `cli/doctor.py` lo hereda de `.env` sin hacer nada: `_run` no toca el entorno.
        // Esto es lo que hace que el APK NO sea distribuible: cada instalacion tiene el suyo.
        buildConfigField("String", "BUNKER_TOKEN",
            "\"${System.getenv("BUNKER_API_TOKEN") ?: ""}\"")
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
// Node, and therefore a dependency the Android build did not have before. Accepted 2026-08-21:
// in exchange `copiarAssets` cannot stage a stale bundle, because this runs first by dependency.
// A machine without Node fails HERE, by name, instead of shipping last week's front-end.
val construirBundle by tasks.registering(Exec::class) {
    workingDir = rootDir.parentFile
    commandLine("npm", "run", "build")
    // `dist/` is this task's OUTPUT. Declaring the whole directory as the input — as the plan
    // first did — makes the task never up-to-date, which is the opposite of the guarantee wanted.
    inputs.files(fileTree(rootDir.parentFile.resolve("bunker_core/static/movil")) {
        exclude("dist/**")
    })
    outputs.dir(rootDir.parentFile.resolve("bunker_core/static/movil/dist"))
}

// `Sync`, not `Copy`: the destination is a MIRROR of what the APK must carry. A plain Copy leaves
// whatever it staged on an earlier run — `app.js` and `queue.js` sat there after the bundle moved
// to `dist/`, and would have been packaged into the APK for ever. Gradle only sweeps stale outputs
// under the build directory, and this destination is not one.
val copiarAssets by tasks.registering(Sync::class) {
    dependsOn(construirBundle)
    val repo = rootDir.parentFile
    // FLAT, no `into("dist")`: `AssetStore.handler` resolves a request with
    // `substringAfterLast('/')`, so a nested directory in the packaged assets is never found.
    // The three names that land here are exactly `AssetStore.REQUERIDOS`.
    from(repo.resolve("bunker_core/static/movil/dist"))
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
