import Link from "fumadocs-core/link";
import { buttonVariants } from "fumadocs-ui/components/ui/button";
import { HomeLayout } from "fumadocs-ui/layouts/home";

/**
 * The landing page.
 *
 * `HomeLayout` supplies the Fumadocs chrome (navbar, theme switch, search) so the
 * landing page looks like the rest of the site instead of a bare document.
 *
 * The call-to-action buttons point at the documentation routes. They use
 * `fumadocs-core/link`, which routes through the framework provider to Next.js's
 * `Link`. Next.js prepends `basePath` to internal hrefs, so these resolve to
 * `/<repository>/docs` on GitHub Pages — a raw `<a href="/docs">` would point at
 * the apex domain and 404.
 */
export default function HomePage() {
  return (
    <HomeLayout>
      <main className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-3xl flex-col justify-center gap-6 px-6 py-16">
        <p className="text-sm font-medium uppercase tracking-wide opacity-70">polylib v0.1.0</p>
        <h1 className="text-4xl font-bold tracking-tight">Polyglot Library Template</h1>
        <p className="text-lg opacity-80">
          One pure Rust core library shipped to Rust (crates.io metacrate), Python (PyO3 / maturin
          abi3 wheels), TypeScript (NAPI-RS + wasm-bindgen / bunup unified ESM facade), and Kotlin,
          Swift, and Ruby (UniFFI) with shared Gherkin conformance specifications.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link href="/docs" className={`${buttonVariants({ variant: "primary" })} px-4 py-2`}>
            Read the docs
          </Link>
          <Link
            href="/docs/getting-started"
            className={`${buttonVariants({ variant: "outline" })} px-4 py-2`}
          >
            Get started
          </Link>
          <Link
            href="/docs/api-reference"
            className={`${buttonVariants({ variant: "outline" })} px-4 py-2`}
          >
            API reference
          </Link>
        </div>
      </main>
    </HomeLayout>
  );
}
