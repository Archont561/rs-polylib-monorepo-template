#![forbid(unsafe_code)]
//! Pure Rust core for `polylib`.
//!
//! This crate has zero I/O or FFI dependencies and compiles cleanly for native
//! targets as well as `wasm32-unknown-unknown`.

use thiserror::Error;

/// Crate version synchronized with the workspace manifest.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Typed errors returned by core domain functions.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
#[cfg_attr(feature = "serde", derive(serde::Serialize, serde::Deserialize))]
pub enum CoreError {
    /// Input contained no ASCII alphanumeric characters after normalization.
    #[error("input must contain at least one ASCII alphanumeric character")]
    EmptyInput,
    /// Score slice contained zero observations.
    #[error("scores must not be empty")]
    EmptyScores,
    /// Score slice contained a `NaN` or infinite value.
    #[error("scores must only contain finite floating-point numbers")]
    NonFiniteValue,
}

impl CoreError {
    /// Stable cross-language error code matched by `conformance/*.feature`.
    #[must_use]
    pub const fn code(&self) -> &'static str {
        match self {
            Self::EmptyInput => "empty_input",
            Self::EmptyScores => "empty_scores",
            Self::NonFiniteValue => "non_finite_value",
        }
    }
}

/// Summary statistics computed over a non-empty slice of finite scores.
#[derive(Debug, Clone, Copy, PartialEq)]
#[cfg_attr(feature = "serde", derive(serde::Serialize, serde::Deserialize))]
pub struct ScoreSummary {
    /// Number of observations.
    pub count: usize,
    /// Minimum observed value.
    pub min: f64,
    /// Maximum observed value.
    pub max: f64,
    /// Arithmetic mean of all observations.
    pub mean: f64,
    /// Sum of all observations.
    pub total: f64,
}

/// Normalize free-form text into a lowercase hyphen-separated ASCII slug.
///
/// # Examples
///
/// ```
/// use polylib_core::normalize_slug;
///
/// assert_eq!(normalize_slug("Hello, Polyglot World!"), Ok("hello-polyglot-world".to_owned()));
/// ```
pub fn normalize_slug(input: &str) -> Result<String, CoreError> {
    let mut out = String::with_capacity(input.len());
    let mut last_was_sep = true;

    for ch in input.chars() {
        if ch.is_ascii_alphanumeric() {
            out.push(ch.to_ascii_lowercase());
            last_was_sep = false;
        } else if !last_was_sep {
            out.push('-');
            last_was_sep = true;
        }
    }

    while out.ends_with('-') {
        out.pop();
    }

    if out.is_empty() {
        return Err(CoreError::EmptyInput);
    }

    Ok(out)
}

/// Compute count, minimum, maximum, mean, and total for a non-empty slice of finite scores.
///
/// # Examples
///
/// ```
/// use polylib_core::summarize_scores;
///
/// let summary = summarize_scores(&[10.0, 20.0, 30.0]).unwrap();
/// assert_eq!(summary.count, 3);
/// assert_eq!(summary.mean, 20.0);
/// ```
pub fn summarize_scores(values: &[f64]) -> Result<ScoreSummary, CoreError> {
    let Some(&first) = values.first() else {
        return Err(CoreError::EmptyScores);
    };
    if !first.is_finite() {
        return Err(CoreError::NonFiniteValue);
    }

    let mut min = first;
    let mut max = first;
    let mut total = 0.0_f64;

    for &value in values {
        if !value.is_finite() {
            return Err(CoreError::NonFiniteValue);
        }
        if value < min {
            min = value;
        }
        if value > max {
            max = value;
        }
        total += value;
    }

    #[allow(clippy::cast_precision_loss)]
    let mean = total / (values.len() as f64);

    Ok(ScoreSummary {
        count: values.len(),
        min,
        max,
        mean,
        total,
    })
}

#[cfg(test)]
mod tests {
    use proptest::prelude::*;
    use rstest::rstest;

    use super::*;

    #[rstest]
    #[case("Hello World", "hello-world")]
    #[case("  a___b---c  ", "a-b-c")]
    #[case("V1.2.3", "v1-2-3")]
    fn slug_normalization_cases(#[case] raw: &str, #[case] expected: &str) {
        assert_eq!(normalize_slug(raw).as_deref(), Ok(expected));
    }

    #[test]
    fn summarize_rejects_non_finite_values() {
        assert_eq!(
            summarize_scores(&[1.0, f64::NAN]),
            Err(CoreError::NonFiniteValue)
        );
        assert_eq!(
            summarize_scores(&[f64::INFINITY]),
            Err(CoreError::NonFiniteValue)
        );
    }

    proptest! {
        #[test]
        fn slug_is_idempotent(input in "[A-Za-z0-9 _.-]{1,64}") {
            if let Ok(slug) = normalize_slug(&input) {
                prop_assert_eq!(normalize_slug(&slug), Ok(slug.clone()));
                prop_assert!(!slug.starts_with('-'));
                prop_assert!(!slug.ends_with('-'));
                prop_assert!(!slug.contains("--"));
            }
        }

        #[test]
        fn summary_bounds_hold(values in prop::collection::vec(-1_000.0_f64..1_000.0_f64, 1..64)) {
            let summary = summarize_scores(&values).expect("finite non-empty values");
            prop_assert_eq!(summary.count, values.len());
            prop_assert!(summary.min <= summary.mean + 1e-9);
            prop_assert!(summary.mean <= summary.max + 1e-9);
        }
    }
}
