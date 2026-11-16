import defaultMdxComponents from "fumadocs-ui/mdx";
import type { MDXComponents } from "mdx/types";

/**
 * Components available inside every MDX page.
 *
 * Fumadocs provides the defaults (headings, links, code blocks, callouts, tabs);
 * this map is the place to add project-specific ones.
 */
export function useMDXComponents(components?: MDXComponents): MDXComponents {
  return {
    ...defaultMdxComponents,
    ...components,
  };
}
