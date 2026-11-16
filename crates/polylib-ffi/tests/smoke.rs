//! Smoke tests for the `polylib-ffi` `UniFFI` boundary.

use polylib_ffi::{PolylibFfiError, VERSION, ffi_version, normalize_slug, summarize_scores};

#[test]
fn ffi_version_matches_core() {
    assert_eq!(VERSION, polylib_core::VERSION);
    assert_eq!(ffi_version(), polylib_core::VERSION);
}

#[test]
fn ffi_delegates_slug_and_scores_and_preserves_error_codes() {
    assert_eq!(
        normalize_slug("Hello, UniFFI!".to_owned()).ok().as_deref(),
        Some("hello-uniffi"),
    );
    assert!(matches!(
        normalize_slug("!!!".to_owned()),
        Err(PolylibFfiError::EmptyInput { ref code, .. }) if code == "empty_input"
    ));

    let summary = summarize_scores(vec![10.0, 20.0, 30.0]).ok();
    assert!(summary.is_some());
    if let Some(summary) = summary {
        assert_eq!(summary.count, 3);
        assert!((summary.mean - 20.0).abs() < 1e-12);
    }

    assert!(matches!(
        summarize_scores(Vec::new()),
        Err(PolylibFfiError::EmptyScores { ref code, .. }) if code == "empty_scores"
    ));
    assert!(matches!(
        summarize_scores(vec![f64::NAN]),
        Err(PolylibFfiError::NonFiniteValue { ref code, .. }) if code == "non_finite_value"
    ));
}
