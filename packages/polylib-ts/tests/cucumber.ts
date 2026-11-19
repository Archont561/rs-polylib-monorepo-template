import { bunTestCucumber } from "@aboviq/bun-test-cucumber";
import { plugin } from "bun";

// The facade imports the addon package statically, and the suite runs in-tree
// where no addon has been compiled. The generated loader's stand-in serves an
// inline binding only when this opt-in is set; a packed tarball carries the real
// loader, which always throws instead.
process.env.POLYLIB_ALLOW_INLINE_BINDING = "1";

await plugin(
  bunTestCucumber({
    stepDefinitionsPattern: "tests/**/*.steps.ts",
  }),
);
