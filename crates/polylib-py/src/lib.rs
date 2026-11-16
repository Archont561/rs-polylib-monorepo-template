//! Thin `PyO3` FFI boundary exposing `polylib-core` as `polylib._native`.
//!
//! Business logic stays strictly inside `polylib-core`. This crate converts
//! Rust types and `CoreError` into Python values and exceptions.

#![allow(unsafe_code, clippy::useless_conversion)]

use polylib_core::{CoreError, ScoreSummary};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

/// Crate version synchronized with the workspace manifest.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

fn to_py_err(error: &CoreError) -> PyErr {
    PyValueError::new_err(format!("{}: {error}", error.code()))
}

/// Python-visible summary statistics returned by [`summarize_scores`].
#[pyclass(name = "ScoreSummary", frozen, from_py_object)]
#[derive(Debug, Clone, Copy)]
pub struct PyScoreSummary {
    inner: ScoreSummary,
}

#[pymethods]
impl PyScoreSummary {
    /// Number of observations.
    #[getter]
    const fn count(&self) -> usize {
        self.inner.count
    }

    /// Minimum observed value.
    #[getter]
    const fn min(&self) -> f64 {
        self.inner.min
    }

    /// Maximum observed value.
    #[getter]
    const fn max(&self) -> f64 {
        self.inner.max
    }

    /// Arithmetic mean of all observations.
    #[getter]
    const fn mean(&self) -> f64 {
        self.inner.mean
    }

    /// Sum of all observations.
    #[getter]
    const fn total(&self) -> f64 {
        self.inner.total
    }

    fn __repr__(&self) -> String {
        format!(
            "ScoreSummary(count={}, min={}, max={}, mean={}, total={})",
            self.inner.count, self.inner.min, self.inner.max, self.inner.mean, self.inner.total
        )
    }
}

/// Normalize free-form text into a lowercase hyphen-separated ASCII slug.
#[pyfunction]
fn normalize_slug(input: &str) -> PyResult<String> {
    polylib_core::normalize_slug(input).map_err(|err| to_py_err(&err))
}

/// Summarize a non-empty sequence of finite floating-point scores.
#[pyfunction]
#[allow(clippy::needless_pass_by_value)]
fn summarize_scores(values: Vec<f64>) -> PyResult<PyScoreSummary> {
    polylib_core::summarize_scores(&values)
        .map(|inner| PyScoreSummary { inner })
        .map_err(|err| to_py_err(&err))
}

/// Native `PyO3` module loaded as `polylib._native`.
#[pymodule(name = "_native")]
fn native_module(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add("VERSION", VERSION)?;
    module.add_class::<PyScoreSummary>()?;
    module.add_function(wrap_pyfunction!(normalize_slug, module)?)?;
    module.add_function(wrap_pyfunction!(summarize_scores, module)?)?;
    Ok(())
}
