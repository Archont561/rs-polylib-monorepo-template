# `polylib-kt` (Kotlin / JVM)

Idiomatic Kotlin/JVM library wrapping `crates/polylib-ffi` via `UniFFI` and JNA.

## Layout

- `src/main/kotlin/dev/polylib/Polylib.kt`: Idiomatic Kotlin facade (`Polylib`, `ScoreSummary`, `PolylibError`).
- `src/generated/kotlin/` & `src/generated/resources/`: Generated `UniFFI` Kotlin bindings and native shared library (built via `pixi run -e kt tools run ffi build --target kotlin`, gitignored).
- `src/test/kotlin/dev/polylib/`: JUnit 5 unit tests and Cucumber-JVM step definitions executing `conformance/*.feature`.

## Local Commands

```sh
pixi run -e kt tools run ffi build --target kotlin
pixi run -e kt tools run ffi test --target kotlin
pixi run -e kt tools run ffi compat --target kotlin
```
