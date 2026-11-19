Feature: TypeScript NAPI-RS native bindings for polylib-core

  The addon ships as one package per platform. Missing the one for the current
  host is reported as `missing_native_binding`, naming the platform.

  Scenario: Normalize a title through the native NAPI-RS addon
    Given a raw title "Hello, Polyglot World!"
    When native TypeScript normalizes the title
    Then the native TypeScript slug is "hello-polyglot-world"

  Scenario: Summarize scores through the native NAPI-RS addon
    Given numeric scores "10.0, 20.0, 30.0, 40.0"
    When native TypeScript summarizes the scores
    Then the native TypeScript summary has count 4 and mean 25.0

  Scenario: A platform without an installed addon reports it explicitly
    Given a host with no per-platform @polylib/polylib-js package installed
    When native TypeScript loads the binding
    Then the error code is "missing_native_binding"
    And the message names the detected platform and the supported targets
    And the error carries the loader failure as its cause

  Scenario: Only the matching platform package is installed
    Given the published @polylib/polylib-js manifest
    When a consumer installs @polylib/polylib-js
    Then it declares one optional dependency per napi target at an exact version
    And the main tarball ships no compiled .node addon
