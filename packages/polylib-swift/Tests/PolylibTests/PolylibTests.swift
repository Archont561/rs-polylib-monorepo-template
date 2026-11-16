import XCTest
@testable import Polylib

final class PolylibTests: XCTestCase {
    func testVersionMatchesNativeLibrary() {
        XCTAssertEqual(Polylib.ffiVersion(), Polylib.version)
    }

    func testNormalizeSlugIsIdempotentOnValidInputs() throws {
        let samples = [
            "Hello, Polyglot World!",
            "Rust + Swift & Apple",
            "Already-Clean_123",
            "---Leading___Trailing---",
            "Cafe 2026 -- v1.2.3",
        ]
        for sample in samples {
            let once = try Polylib.normalizeSlug(sample)
            let twice = try Polylib.normalizeSlug(once)
            XCTAssertEqual(once, twice)
            XCTAssertFalse(once.isEmpty)
            XCTAssertFalse(once.hasPrefix("-"))
            XCTAssertFalse(once.hasSuffix("-"))
            XCTAssertFalse(once.contains("--"))
        }
    }

    func testSummarizeScoresPreservesInvariants() throws {
        let summary = try Polylib.summarizeScores([10.0, 20.0, 30.0])
        XCTAssertEqual(summary.count, 3)
        XCTAssertEqual(summary.min, 10.0, accuracy: 1e-12)
        XCTAssertEqual(summary.max, 30.0, accuracy: 1e-12)
        XCTAssertEqual(summary.mean, 20.0, accuracy: 1e-12)
        XCTAssertEqual(summary.total, 60.0, accuracy: 1e-12)
    }

    func testRejectsNonFiniteScores() {
        XCTAssertThrowsError(try Polylib.summarizeScores([1.0, .nan, 3.0])) { err in
            guard let polyErr = err as? PolylibError else {
                return XCTFail("Expected PolylibError, got \(err)")
            }
            XCTAssertEqual(polyErr.code, "non_finite_value")
            XCTAssertFalse(polyErr.detail.isEmpty)
            XCTAssertTrue(polyErr.localizedDescription.contains("non_finite_value"))
        }
        XCTAssertThrowsError(try Polylib.summarizeScores([.infinity])) { err in
            guard let polyErr = err as? PolylibError else {
                return XCTFail("Expected PolylibError, got \(err)")
            }
            XCTAssertEqual(polyErr.code, "non_finite_value")
            XCTAssertFalse(polyErr.detail.isEmpty)
        }
    }
}
