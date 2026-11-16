import { createMDX } from "fumadocs-mdx/next";

const withMDX = createMDX();

/**
 * GitHub Pages serves a project site from `<user>.github.io/<repository>`, so every
 * asset and route URL needs that prefix. Without it the exported site links to
 * `/_next/...` and `/docs`, which resolve to the apex domain instead of the
 * project path.
 *
 * `GITHUB_REPOSITORY` is `<owner>/<repository>`, and only the repository name is
 * part of the path. The fallback keeps a local build working.
 */
const repository = (process.env.GITHUB_REPOSITORY ?? "rs-polylib-monorepo-template")
  .split("/")
  .pop();
const basePath = `/${repository}`;

/** @type {import('next').NextConfig} */
const config = {
  basePath,
  output: "export",
  reactStrictMode: true,
};

export default withMDX(config);
