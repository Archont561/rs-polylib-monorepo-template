//! Conformance (`conformance/*.feature`) and BDD (`features/core.feature`) tests for `polylib-core`.

#![allow(clippy::expect_used, clippy::too_many_arguments)]

use std::cell::RefCell;

use polylib_core::{CoreError, ScoreSummary, VERSION, normalize_slug, summarize_scores};
use rstest::fixture;
use rstest_bdd_macros::{given, scenario, then, when};

#[derive(Default)]
struct CoreWorld {
    raw_input: RefCell<String>,
    slug_result: RefCell<Option<Result<String, CoreError>>>,
    scores: RefCell<Vec<f64>>,
    summary_result: RefCell<Option<Result<ScoreSummary, CoreError>>>,
}

#[fixture]
fn world() -> CoreWorld {
    CoreWorld::default()
}

#[given("the raw title {title:string}")]
fn given_title(world: &CoreWorld, title: String) {
    *world.raw_input.borrow_mut() = title;
}

#[given("the raw slug input {input:string}")]
fn given_slug_input(world: &CoreWorld, input: String) {
    *world.raw_input.borrow_mut() = input;
}

#[given("an empty slug input")]
fn given_empty_slug_input(world: &CoreWorld) {
    world.raw_input.borrow_mut().clear();
}

#[when("I normalize the slug")]
fn when_normalize(world: &CoreWorld) {
    let raw = world.raw_input.borrow().clone();
    *world.slug_result.borrow_mut() = Some(normalize_slug(&raw));
}

#[then("the resulting slug is {expected:string}")]
fn then_resulting_slug_is(world: &CoreWorld, expected: String) {
    let actual = world
        .slug_result
        .borrow()
        .as_ref()
        .expect("slug computed")
        .as_ref()
        .expect("valid slug")
        .clone();
    assert_eq!(actual, expected);
}

#[then("the normalized slug should be {expected:string}")]
fn then_normalized_slug_should_be(world: &CoreWorld, expected: String) {
    then_resulting_slug_is(world, expected);
}

#[then("slug normalization should fail with error code {error_code:string}")]
fn then_slug_fails_with(world: &CoreWorld, error_code: String) {
    let borrowed = world.slug_result.borrow();
    let err = borrowed
        .as_ref()
        .expect("slug computed")
        .as_ref()
        .expect_err("expected slug error");
    assert_eq!(err.code(), error_code);
}

#[given("the scores {raw:string}")]
fn given_scores(world: &CoreWorld, raw: String) {
    let parsed: Vec<f64> = raw
        .split(',')
        .map(|part| part.trim().parse::<f64>().expect("valid float"))
        .collect();
    *world.scores.borrow_mut() = parsed;
}

#[given("the score list {values:string}")]
fn given_score_list(world: &CoreWorld, values: String) {
    given_scores(world, values);
}

#[given("an empty score list")]
fn given_empty_score_list(world: &CoreWorld) {
    world.scores.borrow_mut().clear();
}

#[when("I summarize the scores")]
fn when_summarize(world: &CoreWorld) {
    let values = world.scores.borrow().clone();
    *world.summary_result.borrow_mut() = Some(summarize_scores(&values));
}

#[then("the summary mean is {mean:f64} and count is {count:usize}")]
fn then_summary_matches(world: &CoreWorld, mean: f64, count: usize) {
    let borrowed = world.summary_result.borrow();
    let summary = borrowed
        .as_ref()
        .expect("summary computed")
        .as_ref()
        .expect("valid summary");
    assert_eq!(summary.count, count);
    assert!((summary.mean - mean).abs() < 1e-12);
}

#[then("the summary should have count {count}, min {min}, max {max}, and mean {mean}")]
fn then_summary_stats_match(world: &CoreWorld, count: usize, min: f64, max: f64, mean: f64) {
    let borrowed = world.summary_result.borrow();
    let summary = borrowed
        .as_ref()
        .expect("summary computed")
        .as_ref()
        .expect("valid summary");
    assert_eq!(summary.count, count);
    assert!((summary.min - min).abs() < 1e-12);
    assert!((summary.max - max).abs() < 1e-12);
    assert!((summary.mean - mean).abs() < 1e-12);
}

#[then("score summarization should fail with error code {error_code:string}")]
fn then_score_fails_with(world: &CoreWorld, error_code: String) {
    let borrowed = world.summary_result.borrow();
    let err = borrowed
        .as_ref()
        .expect("summary computed")
        .as_ref()
        .expect_err("expected score error");
    assert_eq!(err.code(), error_code);
}

#[scenario(path = "features/core.feature", index = 0)]
fn bdd_normalize_slug(world: CoreWorld) {
    let _ = world;
}

#[scenario(path = "features/core.feature", index = 1)]
fn bdd_summarize_scores(world: CoreWorld) {
    let _ = world;
}

#[scenario(path = "../../conformance/slug.feature", index = 0)]
fn conformance_slug_valid(world: CoreWorld, input: String, expected: String) {
    let _ = (world, input, expected);
}

#[scenario(path = "../../conformance/slug.feature", index = 1)]
fn conformance_slug_punctuation(world: CoreWorld, input: String, error_code: String) {
    let _ = (world, input, error_code);
}

#[scenario(path = "../../conformance/slug.feature", index = 2)]
fn conformance_slug_empty(world: CoreWorld) {
    let _ = world;
}

#[allow(clippy::too_many_arguments)]
#[scenario(path = "../../conformance/scores.feature", index = 0)]
fn conformance_scores_valid(
    world: CoreWorld,
    values: String,
    count: usize,
    min: f64,
    max: f64,
    mean: f64,
) {
    let _ = (world, values, count, min, max, mean);
}

#[scenario(path = "../../conformance/scores.feature", index = 1)]
fn conformance_scores_empty(world: CoreWorld) {
    let _ = world;
}

#[test]
fn version_constant_is_non_empty() {
    assert_ne!(VERSION, "");
}
