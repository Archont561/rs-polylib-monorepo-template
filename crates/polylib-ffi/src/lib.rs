//! Thin `uniffi` FFI boundary exposing `polylib-core` to Kotlin, Swift, and Ruby.
//!
//! Domain logic lives exclusively in `polylib-core`. This crate converts core
//! records and typed `CoreError` variants into UniFFI-generated foreign types.

#![allow(unsafe_code)]

use polylib_core::{CoreError, ScoreSummary as CoreScoreSummary};

uniffi::setup_scaffolding!();

/// Crate version synchronized with the workspace manifest.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Typed `UniFFI` error mirroring `polylib_core::CoreError` across Kotlin, Swift, and Ruby.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error, uniffi::Error)]
pub enum PolylibFfiError {
    /// Input contained no ASCII alphanumeric characters.
    #[error("{code}: {detail}")]
    EmptyInput {
        /// Stable cross-language error code (`empty_input`).
        code: String,
        /// Human-readable error explanation.
        detail: String,
    },
    /// Score list contained zero elements.
    #[error("{code}: {detail}")]
    EmptyScores {
        /// Stable cross-language error code (`empty_scores`).
        code: String,
        /// Human-readable error explanation.
        detail: String,
    },
    /// Score list contained `NaN` or `Infinity`.
    #[error("{code}: {detail}")]
    NonFiniteValue {
        /// Stable cross-language error code (`non_finite_value`).
        code: String,
        /// Human-readable error explanation.
        detail: String,
    },
}

impl From<CoreError> for PolylibFfiError {
    fn from(error: CoreError) -> Self {
        let code = error.code().to_owned();
        let detail = error.to_string();
        match error {
            CoreError::EmptyInput => Self::EmptyInput { code, detail },
            CoreError::EmptyScores => Self::EmptyScores { code, detail },
            CoreError::NonFiniteValue => Self::NonFiniteValue { code, detail },
        }
    }
}

/// Foreign-visible summary statistics returned by [`summarize_scores`].
#[derive(Debug, Clone, Copy, PartialEq, uniffi::Record)]
pub struct ScoreSummary {
    /// Number of observations.
    pub count: u64,
    /// Minimum observed value.
    pub min: f64,
    /// Maximum observed value.
    pub max: f64,
    /// Arithmetic mean of all observations.
    pub mean: f64,
    /// Sum of all observations.
    pub total: f64,
}

impl From<CoreScoreSummary> for ScoreSummary {
    fn from(summary: CoreScoreSummary) -> Self {
        Self {
            count: summary.count as u64,
            min: summary.min,
            max: summary.max,
            mean: summary.mean,
            total: summary.total,
        }
    }
}

/// Return the compiled `polylib-ffi` library version.
#[must_use]
#[uniffi::export]
pub fn ffi_version() -> String {
    VERSION.to_owned()
}

/// Normalize free-form text into a lowercase hyphen-separated ASCII slug.
#[uniffi::export]
#[allow(clippy::needless_pass_by_value)]
pub fn normalize_slug(input: String) -> Result<String, PolylibFfiError> {
    polylib_core::normalize_slug(&input).map_err(PolylibFfiError::from)
}

/// Summarize a non-empty list of finite floating-point scores.
#[uniffi::export]
#[allow(clippy::needless_pass_by_value)]
pub fn summarize_scores(values: Vec<f64>) -> Result<ScoreSummary, PolylibFfiError> {
    polylib_core::summarize_scores(&values)
        .map(ScoreSummary::from)
        .map_err(PolylibFfiError::from)
}
