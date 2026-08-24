# Android build report — GATE-001

- Date: 2026-08-24
- Build scope: development debug only
- Result: **PASS**

## Environment

| Component | Value |
|---|---|
| Server default Java | OpenJDK 11.0.24 (restored; production services unaffected) |
| Build-only `JAVA_HOME` | `/usr/lib/jvm/java-17-openjdk-amd64` |
| Build Java | OpenJDK 17.0.19 |
| Gradle wrapper | 8.14.3 |
| Android Gradle Plugin | 8.13.0 |
| Android SDK | `/home/erpnext/Android/Sdk` |
| compile/target SDK | 36 / 36 |
| Build tools | 36.0.0 (Gradle also resolved 35.0.0 for compatibility) |
| Node | 24.16.0 |
| Capacitor | 6.2.1 core/native line; plugins 6.x |

The initial Capacitor 8 dependency line explicitly requested Java 21 toolchains in its Android plugins and failed under Java 17. Because Java 17 is a binding gate requirement, all Capacitor packages were pinned to the supported 6.x major line, whose Android sources target Java 17. No application feature or screen was changed.

## Commands and evidence

```bash
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export ANDROID_HOME=/home/erpnext/Android/Sdk
export ANDROID_SDK_ROOT=/home/erpnext/Android/Sdk
export PATH=/home/erpnext/.nvm/versions/node/v24.16.0/bin:$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$PATH
yarn build
npx cap sync android
cd android
./gradlew --version
./gradlew assembleDebug
```

`Capacitor sync` found and synchronized 11 Android plugins. Gradle reported launcher and daemon JVM 17.0.19. `assembleDebug` completed `BUILD SUCCESSFUL` with 423 actionable tasks.

| Artifact | Evidence |
|---|---|
| APK path | `frontend/mobile/android/app/build/outputs/apk/debug/app-debug.apk` |
| Size | 8,557,123 bytes |
| SHA256 | `3f038163a9f0ade133b7673fe92e2e8242da2788431f5ba4f49c6cb18cb0b7aa` |

The debug APK is a generated local artifact and is not committed. Remaining warnings are the upstream `flatDir` metadata warning, deprecated Gradle features before Gradle 9, and the existing Vite chunk-size warning; none blocked the debug artifact.
