//! Thin `napi-rs` FFI boundary exposing `polylib-core` as a native Node-API addon.
//!
//! Business logic stays strictly inside `polylib-core`. This crate marshals
//! UTF-8 strings, float slices, and typed `CoreError` codes across Node-API.

#![allow(unsafe_code)]

use napi::{Error, Result, Status};
use napi_derive::napi;
use polylib_core::{CoreError, ScoreSummary as CoreScoreSummary};

/// Crate version synchronized with the workspace manifest.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

fn to_napi_err(error: &CoreError) -> Error {
    Error::new(Status::InvalidArg, format!("{}: {error}", error.code()))
}

/// JavaScript-visible summary statistics returned by [`summarize_scores`].
#[napi(object)]
#[derive(Debug, Clone, Copy)]
pub struct ScoreSummary {
    /// Number of observations.
    pub count: u32,
    /// Minimum observed value.
    pub min: f64,
    /// Maximum observed value.
    pub max: f64,
    /// Arithmetic mean of all observations.
    pub mean: f64,
    /// Sum of all observations.
    pub total: f64,
}

impl TryFrom<CoreScoreSummary> for ScoreSummary {
    type Error = Error;

    fn try_from(summary: CoreScoreSummary) -> Result<Self> {
        let count = u32::try_from(summary.count).map_err(|_| {
            Error::new(
                Status::InvalidArg,
                "count_overflow: score count exceeds 32-bit unsigned integer range",
            )
        })?;
        Ok(Self {
            count,
            min: summary.min,
            max: summary.max,
            mean: summary.mean,
            total: summary.total,
        })
    }
}

/// Return the compiled native `polylib-js` addon version.
#[must_use]
#[napi]
pub fn native_version() -> String {
    VERSION.to_owned()
}

/// Normalize free-form text into a lowercase hyphen-separated ASCII slug.
#[napi]
#[allow(clippy::needless_pass_by_value)]
pub fn normalize_slug(input: String) -> Result<String> {
    polylib_core::normalize_slug(&input).map_err(|err| to_napi_err(&err))
}

/// Summarize a non-empty array of finite floating-point scores.
#[napi]
#[allow(clippy::needless_pass_by_value)]
pub fn summarize_scores(values: Vec<f64>) -> Result<ScoreSummary> {
    let summary = polylib_core::summarize_scores(&values).map_err(|err| to_napi_err(&err))?;
    ScoreSummary::try_from(summary)
}
