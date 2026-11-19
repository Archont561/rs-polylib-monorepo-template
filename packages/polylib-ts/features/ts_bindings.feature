Feature: Unified TypeScript facade for polylib-core

  The main entry is native-only. A missing native binding is an error that names
  the platform, never a silent switch to another backend.

  Scenario: The main entry uses native and keeps the version in step
    Given the unified @polylib/polylib facade package
    When a TypeScript caller invokes normalizeSlug and summarizeScores
    Then it delegates to @polylib/polylib-js and reports the native backend

  Scenario: A missing native binding reports the platform
    Given a platform with no @polylib/polylib-js native binding
    When a caller invokes normalizeSlug
    Then the error code is "missing_native_binding"
    And the message names the detected platform and the WebAssembly alternative

  Scenario: The browser condition resolves to an unsupported-runtime stub
    Given a bundler resolving the "default" export condition
    When it imports @polylib/polylib
    Then the import fails with error code "unsupported_runtime"
    And the message points at "@polylib/polylib/wasm"

  Scenario: The /wasm subpath requires the optional peer package
    Given the optional peer @polylib/polylib-wasm is not installed
    When a caller imports "@polylib/polylib/wasm"
    Then the import fails with a module-not-found error that names @polylib/polylib-wasm

  Scenario: Pin explicit native or WebAssembly backends
    Given the @polylib/polylib main entry and the @polylib/polylib/wasm subpath
    When a caller invokes both with identical inputs
    Then both backends return identical outputs and PolylibError codes
