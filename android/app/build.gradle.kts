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
