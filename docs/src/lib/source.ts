import { loader } from "fumadocs-core/source";
import { docs } from "@/.source/server";

/**
 * The documentation source.
 *
 * `fumadocs-mdx` compiles `content/docs` into `.source/server.ts`, which exposes the
 * collection as virtual files. `fumadocs-core`'s `loader` turns those files into a
 * queryable source: `getPage`, `getPageTree` and `generateParams`.
 *
 * Slugs come from the file path relative to the content root, so `content/docs/index.mdx`
 * is served at `/docs` and `content/docs/guides/setup.mdx` at `/docs/guides/setup`.
 * `baseUrl` keeps the generated links and the page tree in sync with that prefix.
 */
export const source = loader(docs.toFumadocsSource(), {
  baseUrl: "/docs",
});
