package dev.polylib

import dev.polylib.ffi.PolylibFfiException
import dev.polylib.ffi.ffiVersion as nativeFfiVersion
import dev.polylib.ffi.normalizeSlug as nativeNormalizeSlug
import dev.polylib.ffi.summarizeScores as nativeSummarizeScores

/**
 * Typed domain error mirroring `polylib_core::CoreError` across Kotlin and the JVM.
 */
sealed class PolylibError(
    val code: String,
    val detail: String,
) : RuntimeException("$code: $detail") {
    class EmptyInput(detail: String) : PolylibError(code = "empty_input", detail = detail)

    class EmptyScores(detail: String) : PolylibError(code = "empty_scores", detail = detail)

    class NonFiniteValue(detail: String) : PolylibError(code = "non_finite_value", detail = detail)
}

/**
 * Deterministic summary statistics returned by [Polylib.summarizeScores].
 */
data class ScoreSummary(
    val count: Long,
    val min: Double,
    val max: Double,
    val mean: Double,
    val total: Double,
)

/**
 * Idiomatic Kotlin/JVM facade over the Rust `polylib-ffi` UniFFI bindings.
 */
object Polylib {
    const val VERSION: String = "0.1.0"

    /** Return the version compiled into the native `polylib-ffi` shared library. */
    fun ffiVersion(): String = nativeFfiVersion()

    /** Normalize free-form text into a lowercase hyphen-separated ASCII slug. */
    @Throws(PolylibError::class)
    fun normalizeSlug(input: String): String =
        mapErrors {
            nativeNormalizeSlug(input)
        }

    /** Summarize a non-empty list of finite floating-point scores. */
    @Throws(PolylibError::class)
    fun summarizeScores(values: List<Double>): ScoreSummary =
        mapErrors {
            val raw = nativeSummarizeScores(values)
            ScoreSummary(
                count = raw.count.toLong(),
                min = raw.min,
                max = raw.max,
                mean = raw.mean,
                total = raw.total,
            )
        }

    private inline fun <T> mapErrors(block: () -> T): T =
        try {
            block()
        } catch (err: PolylibFfiException) {
            throw when (err) {
                is PolylibFfiException.EmptyInput -> PolylibError.EmptyInput(err.detail)
                is PolylibFfiException.EmptyScores -> PolylibError.EmptyScores(err.detail)
                is PolylibFfiException.NonFiniteValue -> PolylibError.NonFiniteValue(err.detail)
            }
        }
}
