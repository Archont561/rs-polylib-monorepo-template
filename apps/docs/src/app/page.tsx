export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-6 px-6 py-16">
      <p className="text-sm font-medium uppercase tracking-wide opacity-70">polylib v0.1.0</p>
      <h1 className="text-4xl font-bold tracking-tight">Polyglot Library Template</h1>
      <p className="text-lg opacity-80">
        One pure Rust core library shipped to Rust (crates.io metacrate), Python (PyO3 / maturin
        abi3 wheels), TypeScript (NAPI-RS + wasm-bindgen / bunup unified ESM facade), and Kotlin,
        Swift, and Ruby (UniFFI) with shared Gherkin conformance specifications.
      </p>
    </main>
  );
}
