import { RootProvider } from "fumadocs-ui/provider/next";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./global.css";

export const metadata: Metadata = {
  title: {
    default: "Polyglot Library Template",
    template: "%s | Polyglot Library Template",
  },
  description:
    "One pure Rust core library shipped to Rust, Python, TypeScript, Kotlin, Swift, and Ruby.",
};

export default function RootLayout({ children }: { readonly children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <RootProvider>{children}</RootProvider>
      </body>
    </html>
  );
}
