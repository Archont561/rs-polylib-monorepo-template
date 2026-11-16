import { DocsLayout } from "fumadocs-ui/layouts/docs";
import type { ReactNode } from "react";
import { source } from "@/lib/source";

/**
 * Chrome for every documentation page: sidebar, header and table of contents.
 *
 * The tree comes from the Fumadocs source, so the navigation reflects whatever is
 * under `content/docs` — adding a page there is enough to make it reachable.
 */
export default function Layout({ children }: { readonly children: ReactNode }) {
  return <DocsLayout tree={source.pageTree}>{children}</DocsLayout>;
}
