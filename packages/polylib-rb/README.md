# `polylib-rb` (Ruby Gem)

Idiomatic Ruby gem wrapping `crates/polylib-ffi` via `UniFFI` and Ruby `ffi`.

## Layout

- `polylib.gemspec`, `Gemfile`, `Rakefile`: Gem manifest, Bundler dependencies, and test tasks.
- `lib/polylib.rb`, `lib/polylib/{version,error,native_loader}.rb`: Idiomatic Ruby facade (`Polylib`, `Polylib::ScoreSummary`, `Polylib::Error`).
- `lib/polylib/generated/` & `lib/polylib/native/`: Generated `UniFFI` Ruby bindings and native shared library (built via `pixi run -e rb tools run ffi build --target ruby`, gitignored).
- `test/test_polylib.rb` & `conformance_steps/step_definitions.rb`: Minitest unit tests and Cucumber Ruby step definitions executing `conformance/*.feature`.

## Local Commands

```sh
pixi run -e rb tools run ffi build --target ruby
pixi run -e rb tools run ffi test --target ruby
pixi run -e rb tools run ffi compat --target ruby
```
