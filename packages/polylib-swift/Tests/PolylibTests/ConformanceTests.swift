import Foundation
import XCTest
@testable import Polylib

/// Executes shared cross-language Gherkin specs from `conformance/{slug,scores}.feature`.
final class ConformanceTests: XCTestCase {
    private func repoRoot() -> URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent() // PolylibTests
            .deletingLastPathComponent() // Tests
            .deletingLastPathComponent() // polylib-swift
            .deletingLastPathComponent() // packages
            .deletingLastPathComponent() // repo root
    }

    private func parseExamplesTables(at path: URL) throws -> [[[String: String]]] {
        let content = try String(contentsOf: path, encoding: .utf8)
        var tables: [[[String: String]]] = []
        var headers: [String]?
        var currentRows: [[String: String]] = []

        for rawLine in content.components(separatedBy: .newlines) {
            let line = rawLine.trimmingCharacters(in: .whitespaces)
            if line.hasPrefix("|") && line.hasSuffix("|") {
                let cells = line.dropFirst().dropLast()
                    .split(separator: "|", omittingEmptySubsequences: false)
                    .map { $0.trimmingCharacters(in: .whitespaces) }
                if headers == nil {
                    headers = cells
                } else if let headerCells = headers {
                    var row: [String: String] = [:]
                    for (key, value) in zip(headerCells, cells) {
                        row[key] = value
                    }
                    currentRows.append(row)
                }
            } else if headers != nil {
                tables.append(currentRows)
                headers = nil
                currentRows = []
            }
        }
        if headers != nil {
            tables.append(currentRows)
        }
        return tables
    }

    func testSlugConformanceFeature() throws {
        let featureURL = repoRoot().appendingPathComponent("conformance/slug.feature")
        let tables = try parseExamplesTables(at: featureURL)
        XCTAssertEqual(tables.count, 2, "Expected 2 Examples tables in conformance/slug.feature")

        for row in tables[0] {
            let input = try XCTUnwrap(row["input"])
            let expected = try XCTUnwrap(row["expected"])
            XCTAssertEqual(try Polylib.normalizeSlug(input), expected)
        }

        for row in tables[1] {
            let input = try XCTUnwrap(row["input"])
            let expectedCode = try XCTUnwrap(row["error_code"])
            XCTAssertThrowsError(try Polylib.normalizeSlug(input)) { err in
                XCTAssertEqual((err as? PolylibError)?.code, expectedCode)
            }
        }

        // Scenario: Reject an empty slug input
        XCTAssertThrowsError(try Polylib.normalizeSlug("")) { err in
            XCTAssertEqual((err as? PolylibError)?.code, "empty_input")
        }
    }

    func testScoresConformanceFeature() throws {
        let featureURL = repoRoot().appendingPathComponent("conformance/scores.feature")
        let tables = try parseExamplesTables(at: featureURL)
        XCTAssertEqual(tables.count, 1, "Expected 1 Examples table in conformance/scores.feature")

        for row in tables[0] {
            let rawValues = try XCTUnwrap(row["values"])
            let values = rawValues
                .split(separator: ",")
                .compactMap { Double($0.trimmingCharacters(in: .whitespaces)) }
            let expectedCount = try XCTUnwrap(Int(row["count"] ?? ""))
            let expectedMin = try XCTUnwrap(Double(row["min"] ?? ""))
            let expectedMax = try XCTUnwrap(Double(row["max"] ?? ""))
            let expectedMean = try XCTUnwrap(Double(row["mean"] ?? ""))

            let summary = try Polylib.summarizeScores(values)
            XCTAssertEqual(summary.count, expectedCount)
            XCTAssertEqual(summary.min, expectedMin, accuracy: 1e-12)
            XCTAssertEqual(summary.max, expectedMax, accuracy: 1e-12)
            XCTAssertEqual(summary.mean, expectedMean, accuracy: 1e-12)
        }

        // Scenario: Reject an empty score list
        XCTAssertThrowsError(try Polylib.summarizeScores([])) { err in
            XCTAssertEqual((err as? PolylibError)?.code, "empty_scores")
        }
    }
}
