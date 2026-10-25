plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.vgp.markengine"
    compileSdk = 37

    defaultConfig {
        minSdk = 26
        consumerProguardFiles("consumer-rules.pro")
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlin {
        compilerOptions {
            jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
        }
    }
}

// No dependencies on purpose: the engine is plain Kotlin plus android.graphics. Keep it that way.
dependencies {
    testImplementation("junit:junit:4.13.2")
}
