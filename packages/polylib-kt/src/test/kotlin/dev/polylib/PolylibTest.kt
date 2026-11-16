package dev.polylib

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class PolylibTest {
    @Test
    fun versionMatchesNativeLibrary() {
        assertEquals(Polylib.VERSION, Polylib.ffiVersion())
    }

    @Test
    fun normalizeSlugIsIdempotentOnValidInputs() {
        val samples =
            listOf(
                "Hello, Polyglot World!",
                "Rust + Kotlin & JVM",
                "Already-Clean_123",
                "---Leading___Trailing---",
                "Cafe 2026 -- v1.2.3",
                "A1 b2 C3",
            )
        for (sample in samples) {
            val once = Polylib.normalizeSlug(sample)
            val twice = Polylib.normalizeSlug(once)
            assertEquals(once, twice)
            assertTrue(once.isNotEmpty())
            assertFalse(once.startsWith("-"))
            assertFalse(once.endsWith("-"))
            assertFalse(once.contains("--"))
            assertTrue(once.all { it in 'a'..'z' || it in '0'..'9' || it == '-' })
        }
    }

    @Test
    fun summarizeScoresPreservesNumericInvariants() {
        val summary = Polylib.summarizeScores(listOf(10.0, 20.0, 30.0))
        assertEquals(3L, summary.count)
        assertEquals(10.0, summary.min, 1e-12)
        assertEquals(30.0, summary.max, 1e-12)
        assertEquals(20.0, summary.mean, 1e-12)
        assertEquals(60.0, summary.total, 1e-12)
    }

    @Test
    fun rejectsNonFiniteValues() {
        val nanErr = assertThrows(PolylibError.NonFiniteValue::class.java) {
            Polylib.summarizeScores(listOf(1.0, Double.NaN, 3.0))
        }
        assertEquals("non_finite_value", nanErr.code)

        val infErr = assertThrows(PolylibError.NonFiniteValue::class.java) {
            Polylib.summarizeScores(listOf(Double.POSITIVE_INFINITY))
        }
        assertEquals("non_finite_value", infErr.code)
    }

    @Test
    fun rejectsEmptyInputsWithTypedErrors() {
        val slugErr = assertThrows(PolylibError.EmptyInput::class.java) {
            Polylib.normalizeSlug("   !!!   ")
        }
        assertEquals("empty_input", slugErr.code)

        val scoreErr = assertThrows(PolylibError.EmptyScores::class.java) {
            Polylib.summarizeScores(emptyList())
        }
        assertEquals("empty_scores", scoreErr.code)
    }
}
