import { version } from "@/package.json" with { type: "json" };

export const VERSION: string = version;

export {
  getNativeVersion,
  normalizeSlug,
  PolylibError,
  type ScoreSummary,
  summarizeScores,
} from "./native.js";
