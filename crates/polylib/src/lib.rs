#![forbid(unsafe_code)]
//! Public Rust metacrate facade for `polylib`.
//!
//! Consumers depend on `polylib` rather than internal subcrates directly. All
//! optional integrations (`serde`, `json`, `full`) are opt-in feature flags.
//!
//! # Examples
//!
//! ```
//! use polylib::prelude::*;
//!
//! let slug = normalize_slug("Hello, Metacrate!").unwrap();
//! assert_eq!(slug, "hello-metacrate");
//!
//! let summary = summarize_scores(&[2.0, 4.0, 6.0]).unwrap();
//! assert_eq!(summary.mean, 4.0);
//! ```

pub use polylib_core as core;
pub use polylib_core::{CoreError, ScoreSummary, VERSION, normalize_slug, summarize_scores};

/// Common imports for ergonomic use of `polylib`.
pub mod prelude {
    #[cfg(feature = "json")]
    pub use crate::summarize_scores_json;
    pub use crate::{CoreError, ScoreSummary, VERSION, normalize_slug, summarize_scores};
}

/// Summarize finite scores and serialize the [`ScoreSummary`] to compact JSON.
///
/// Requires the `json` feature flag.
///
/// # Examples
///
/// ```
/// # #[cfg(feature = "json")]
/// # {
/// let json = polylib::summarize_scores_json(&[10.0, 20.0]).unwrap();
/// assert!(json.contains("\"mean\":15.0"));
/// # }
/// ```
#[cfg(feature = "json")]
pub fn summarize_scores_json(values: &[f64]) -> Result<String, CoreError> {
    let summary = summarize_scores(values)?;
    serde_json::to_string(&summary).map_err(|_| CoreError::NonFiniteValue)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reexports_core_version() {
        assert_eq!(VERSION, polylib_core::VERSION);
    }

    #[cfg(feature = "json")]
    #[test]
    fn json_feature_serializes_summary() {
        let json = summarize_scores_json(&[10.0, 30.0]).expect("valid summary");
        assert!(json.contains("\"count\":2"));
        assert!(json.contains("\"mean\":20.0"));
    }
}
