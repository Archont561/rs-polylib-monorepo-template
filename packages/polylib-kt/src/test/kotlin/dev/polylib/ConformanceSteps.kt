package dev.polylib

import io.cucumber.java.en.Given
import io.cucumber.java.en.Then
import io.cucumber.java.en.When
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull

class ConformanceSteps {
    private var slugInput: String = ""
    private var slugResult: String? = null
    private var slugError: PolylibError? = null

    private var scoreValues: List<Double> = emptyList()
    private var scoreSummary: ScoreSummary? = null
    private var scoreError: PolylibError? = null

    @Given("the raw slug input {string}")
    fun givenRawSlugInput(input: String) {
        slugInput = input
    }

    @Given("an empty slug input")
    fun givenEmptySlugInput() {
        slugInput = ""
    }

    @When("I normalize the slug")
    fun whenNormalizeSlug() {
        slugResult = null
        slugError = null
        try {
            slugResult = Polylib.normalizeSlug(slugInput)
        } catch (err: PolylibError) {
            slugError = err
        }
    }

    @Then("the normalized slug should be {string}")
    fun thenNormalizedSlugShouldBe(expected: String) {
        assertNull(slugError, "Expected success but got error: $slugError")
        assertEquals(expected, slugResult)
    }

    @Then("slug normalization should fail with error code {string}")
    fun thenSlugShouldFailWithCode(expectedCode: String) {
        assertNull(slugResult, "Expected error but got slug: $slugResult")
        val err = slugError
        assertNotNull(err, "Expected PolylibError but none was thrown")
        assertEquals(expectedCode, err!!.code)
    }

    @Given("the score list {string}")
    fun givenScoreList(rawValues: String) {
        scoreValues =
            rawValues
                .split(",")
                .map { it.trim() }
                .filter { it.isNotEmpty() }
                .map { it.toDouble() }
    }

    @Given("an empty score list")
    fun givenEmptyScoreList() {
        scoreValues = emptyList()
    }

    @When("I summarize the scores")
    fun whenSummarizeScores() {
        scoreSummary = null
        scoreError = null
        try {
            scoreSummary = Polylib.summarizeScores(scoreValues)
        } catch (err: PolylibError) {
            scoreError = err
        }
    }

    @Then("the summary should have count {long}, min {double}, max {double}, and mean {double}")
    fun thenSummaryShouldMatch(
        expectedCount: Long,
        expectedMin: Double,
        expectedMax: Double,
        expectedMean: Double,
    ) {
        assertNull(scoreError, "Expected success but got error: $scoreError")
        val summary = scoreSummary
        assertNotNull(summary, "Expected ScoreSummary but got null")
        assertEquals(expectedCount, summary!!.count)
        assertEquals(expectedMin, summary.min, 1e-12)
        assertEquals(expectedMax, summary.max, 1e-12)
        assertEquals(expectedMean, summary.mean, 1e-12)
    }

    @Then("score summarization should fail with error code {string}")
    fun thenScoreShouldFailWithCode(expectedCode: String) {
        assertNull(scoreSummary, "Expected error but got summary: $scoreSummary")
        val err = scoreError
        assertNotNull(err, "Expected PolylibError but none was thrown")
        assertEquals(expectedCode, err!!.code)
    }
}
