import { version } from "@/package.json" with { type: "json" };

export const VERSION: string = version;

export {
  getWasmVersion,
  initWasm,
  normalizeSlug,
  PolylibError,
  type ScoreSummary,
  summarizeScores,
} from "./wasm.js";
