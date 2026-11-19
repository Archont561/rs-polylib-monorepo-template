import { bunTestCucumber } from "@aboviq/bun-test-cucumber";
import { plugin } from "bun";

// The suite runs in-tree, where no addon has been compiled, so the generated
// loader's stand-in (`src/native/binding.cjs`) serves an inline binding. The
// stand-in throws by default, because a packed tarball must never fall back
// silently; the opt-in is here rather than in the stand-in so the production
// behaviour is the default one. A missing-binding test opts back out.
process.env.POLYLIB_ALLOW_INLINE_BINDING = "1";

await plugin(
  bunTestCucumber({
    stepDefinitionsPattern: "tests/**/*.steps.ts",
  }),
);
