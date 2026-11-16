import { resolve } from "node:path";
import { loadFeatures } from "@aboviq/bun-test-cucumber";

await loadFeatures("*.feature", resolve(import.meta.dir, "../../../conformance"));
