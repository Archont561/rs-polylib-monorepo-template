// The suite loads the same source twice with a query string to get a module
// instance that has never been initialized: `core.ts` keeps its state at module
// scope, and Bun keys modules by specifier, so `core.ts?pristine=1` is a
// separate instance with its own `initialized` flag. TypeScript has no way to
// know about those specifiers, so they are declared here.
declare module "@/src/core.js?pristine=1" {
  export * from "@/src/core.js";
}

declare module "@/src/index.browser.ts?async" {
  export * from "@/src/index.browser.ts";
}

declare module "@/src/index.browser.ts?idem" {
  export * from "@/src/index.browser.ts";
}
