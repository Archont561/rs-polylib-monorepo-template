//! Integration tests exercising `polylib` against shared Gherkin `conformance/*.feature` specs.

#![allow(clippy::expect_used, clippy::too_many_arguments)]

use std::cell::RefCell;

use polylib::prelude::*;
use rstest::fixture;
use rstest_bdd_macros::{given, scenario, then, when};

#[derive(Default)]
struct FacadeWorld {
    raw_input: RefCell<String>,
    slug_result: RefCell<Option<Result<String, CoreError>>>,
    scores: RefCell<Vec<f64>>,
    summary_result: RefCell<Option<Result<ScoreSummary, CoreError>>>,
}

#[fixture]
fn world() -> FacadeWorld {
    FacadeWorld::default()
}

#[given("the raw slug input {input:string}")]
fn given_slug_input(world: &FacadeWorld, input: String) {
    *world.raw_input.borrow_mut() = input;
}

#[given("an empty slug input")]
fn given_empty_slug_input(world: &FacadeWorld) {
    world.raw_input.borrow_mut().clear();
}

#[when("I normalize the slug")]
fn when_normalize(world: &FacadeWorld) {
    let raw = world.raw_input.borrow().clone();
    *world.slug_result.borrow_mut() = Some(normalize_slug(&raw));
}

#[then("the normalized slug should be {expected:string}")]
fn then_normalized_slug(world: &FacadeWorld, expected: String) {
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

#[then("slug normalization should fail with error code {error_code:string}")]
fn then_slug_fails(world: &FacadeWorld, error_code: String) {
    let borrowed = world.slug_result.borrow();
    let err = borrowed
        .as_ref()
        .expect("slug computed")
        .as_ref()
        .expect_err("expected slug error");
    assert_eq!(err.code(), error_code);
}

#[given("the score list {values:string}")]
fn given_score_list(world: &FacadeWorld, values: String) {
    let parsed: Vec<f64> = values
        .split(',')
        .map(|part| part.trim().parse::<f64>().expect("valid float"))
        .collect();
    *world.scores.borrow_mut() = parsed;
}

#[given("an empty score list")]
fn given_empty_score_list(world: &FacadeWorld) {
    world.scores.borrow_mut().clear();
}

#[when("I summarize the scores")]
fn when_summarize(world: &FacadeWorld) {
    let values = world.scores.borrow().clone();
    *world.summary_result.borrow_mut() = Some(summarize_scores(&values));
}

#[then("the summary should have count {count}, min {min}, max {max}, and mean {mean}")]
fn then_summary_stats(world: &FacadeWorld, count: usize, min: f64, max: f64, mean: f64) {
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
fn then_score_fails(world: &FacadeWorld, error_code: String) {
    let borrowed = world.summary_result.borrow();
    let err = borrowed
        .as_ref()
        .expect("summary computed")
        .as_ref()
        .expect_err("expected score error");
    assert_eq!(err.code(), error_code);
}

#[scenario(path = "../../conformance/slug.feature", index = 0)]
fn facade_conformance_slug_valid(world: FacadeWorld, input: String, expected: String) {
    let _ = (world, input, expected);
}

#[scenario(path = "../../conformance/slug.feature", index = 1)]
fn facade_conformance_slug_punctuation(world: FacadeWorld, input: String, error_code: String) {
    let _ = (world, input, error_code);
}

#[scenario(path = "../../conformance/slug.feature", index = 2)]
fn facade_conformance_slug_empty(world: FacadeWorld) {
    let _ = world;
}

#[allow(clippy::too_many_arguments)]
#[scenario(path = "../../conformance/scores.feature", index = 0)]
fn facade_conformance_scores_valid(
    world: FacadeWorld,
    values: String,
    count: usize,
    min: f64,
    max: f64,
    mean: f64,
) {
    let _ = (world, values, count, min, max, mean);
}

#[scenario(path = "../../conformance/scores.feature", index = 1)]
fn facade_conformance_scores_empty(world: FacadeWorld) {
    let _ = world;
}

#[test]
fn prelude_exports_version() {
    assert_ne!(VERSION, "");
}

#[cfg(feature = "json")]
#[test]
fn json_feature_round_trips_summary() {
    let encoded = summarize_scores_json(&[10.0, 20.0, 30.0]).expect("valid JSON");
    let decoded: ScoreSummary = serde_json::from_str(&encoded).expect("valid ScoreSummary JSON");
    assert_eq!(decoded.count, 3);
    assert!((decoded.mean - 20.0).abs() < 1e-12);
}
