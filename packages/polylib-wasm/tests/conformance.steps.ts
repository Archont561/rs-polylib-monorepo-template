import { expect } from "bun:test";
import { withState } from "@aboviq/bun-test-cucumber";
import { normalizeSlug, PolylibError, type ScoreSummary, summarizeScores } from "@/src/index.node.js";

interface ConformanceState {
  rawInput?: string | undefined;
  slug?: string | undefined;
  slugError?: unknown;
  scores?: number[] | undefined;
  summary?: ScoreSummary | undefined;
  scoreError?: unknown;
}

const { Given, When, Then } = withState<ConformanceState>();

Given("the raw slug input {string}", (state, [input]) => ({
  ...state,
  rawInput: input,
}));

Given("an empty slug input", (state) => ({
  ...state,
  rawInput: "",
}));

When("I normalize the slug", (state) => {
  try {
    return {
      ...state,
      slug: normalizeSlug(state.rawInput ?? ""),
      slugError: undefined,
    };
  } catch (err) {
    return {
      ...state,
      slug: undefined,
      slugError: err,
    };
  }
});

Then("the normalized slug should be {string}", (state, [expected]) => {
  expect(state.slugError).toBeUndefined();
  expect(state.slug).toBe(expected);
  return state;
});

Then("slug normalization should fail with error code {string}", (state, [errorCode]) => {
  expect(state.slugError).toBeInstanceOf(PolylibError);
  expect((state.slugError as PolylibError).code).toBe(errorCode);
  return state;
});

Given("the score list {string}", (state, [values]) => ({
  ...state,
  scores: values.split(",").map((part) => Number(part.trim())),
}));

Given("an empty score list", (state) => ({
  ...state,
  scores: [],
}));

When("I summarize the scores", (state) => {
  try {
    return {
      ...state,
      summary: summarizeScores(state.scores ?? []),
      scoreError: undefined,
    };
  } catch (err) {
    return {
      ...state,
      summary: undefined,
      scoreError: err,
    };
  }
});

Then(
  "the summary should have count {int}, min {float}, max {float}, and mean {float}",
  (state, [count, min, max, mean]) => {
    expect(state.scoreError).toBeUndefined();
    expect(state.summary).toBeDefined();
    expect(state.summary?.count).toBe(count);
    expect(state.summary?.min).toBeCloseTo(min, 10);
    expect(state.summary?.max).toBeCloseTo(max, 10);
    expect(state.summary?.mean).toBeCloseTo(mean, 10);
    return state;
  },
);

Then("score summarization should fail with error code {string}", (state, [errorCode]) => {
  expect(state.scoreError).toBeInstanceOf(PolylibError);
  expect((state.scoreError as PolylibError).code).toBe(errorCode);
  return state;
});
