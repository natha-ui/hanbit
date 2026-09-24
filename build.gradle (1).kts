plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.hanbit.hakdang"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.hanbit.hakdang"
        minSdk = 26
        targetSdk = 35
        versionCode = 3
        versionName = "0.3"
    }
    // One fixed key for every build (GitHub Actions or Android Studio), so a new
    // APK installs over the old one and keeps your progress.
    signingConfigs {
        create("hanbit") {
            storeFile = rootProject.file("keystore/hanbit.jks")
            storePassword = "hanbit-study"
            keyAlias = "hanbit"
            keyPassword = "hanbit-study"
        }
    }
    buildTypes {
        debug { signingConfig = signingConfigs.getByName("hanbit") }
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("hanbit")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.work:work-runtime-ktx:2.9.1")
}
