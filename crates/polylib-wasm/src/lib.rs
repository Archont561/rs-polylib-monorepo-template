//! Thin `wasm-bindgen` FFI boundary exposing `polylib-core` to TypeScript.
//!
//! Business logic stays strictly inside `polylib-core`. This crate marshals
//! strings, float slices, and `CoreError` codes across the WASM ABI.

#![allow(unsafe_code)]

use polylib_core::CoreError;
use wasm_bindgen::prelude::*;

/// Crate version synchronized with the workspace manifest.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

fn format_error(error: &CoreError) -> JsValue {
    JsValue::from_str(&format!("{}: {error}", error.code()))
}

/// Return the compiled WASM module version.
#[must_use]
#[wasm_bindgen(js_name = "wasmVersion")]
pub fn wasm_version() -> String {
    VERSION.to_owned()
}

/// Normalize free-form text into a lowercase hyphen-separated ASCII slug.
#[wasm_bindgen(js_name = "wasmNormalizeSlug")]
pub fn wasm_normalize_slug(input: &str) -> Result<String, JsValue> {
    polylib_core::normalize_slug(input).map_err(|err| format_error(&err))
}

/// Summarize a non-empty slice of finite floating-point scores.
#[wasm_bindgen(js_name = "wasmSummarizeScores")]
pub fn wasm_summarize_scores(values: &[f64]) -> Result<JsValue, JsValue> {
    let summary = polylib_core::summarize_scores(values).map_err(|err| format_error(&err))?;
    serde_wasm_bindgen::to_value(&summary).map_err(|err| JsValue::from_str(&err.to_string()))
}
