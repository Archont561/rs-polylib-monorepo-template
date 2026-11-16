/*
 * Intentionally empty translation unit.
 *
 * `PolylibFFIInternal` is a header-only C module: the UniFFI-generated
 * `include/PolylibFFIInternal.h` and `include/module.modulemap` declare the
 * FFI surface, and the implementation lives in the `polylib_ffi` shared
 * library that is linked at build time.
 *
 * SwiftPM compiles every C target into an object file and links that object
 * into the target's static library. A target with no source files produces no
 * object file, and the link step then fails with
 *
 *     Build input file cannot be found: '.../PolylibFFIInternal.o'.
 *
 * This empty translation unit gives SwiftPM the object file it expects.
 */
