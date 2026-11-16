import Foundation
import PolylibFFI

/// Typed domain error mirroring `polylib_core::CoreError` across Swift.
public enum PolylibError: Error, Equatable, Hashable, LocalizedError, Sendable {
    case emptyInput(detail: String)
    case emptyScores(detail: String)
    case nonFiniteValue(detail: String)

    /// Stable cross-language error code matching `conformance/*.feature`.
    public var code: String {
        switch self {
        case .emptyInput:
            return "empty_input"
        case .emptyScores:
            return "empty_scores"
        case .nonFiniteValue:
            return "non_finite_value"
        }
    }

    /// Human-readable error detail returned from Rust.
    public var detail: String {
        switch self {
        case let .emptyInput(detail),
             let .emptyScores(detail),
             let .nonFiniteValue(detail):
            return detail
        }
    }

    public var errorDescription: String? {
        "\(code): \(detail)"
    }
}

/// Deterministic summary statistics returned by `Polylib.summarizeScores(_:)`.
public struct ScoreSummary: Equatable, Hashable, Sendable {
    public let count: Int
    public let min: Double
    public let max: Double
    public let mean: Double
    public let total: Double

    public init(count: Int, min: Double, max: Double, mean: Double, total: Double) {
        self.count = count
        self.min = min
        self.max = max
        self.mean = mean
        self.total = total
    }
}

/// Idiomatic Swift facade over the Rust `polylib-ffi` UniFFI bindings.
public enum Polylib {
    public static let version = "0.1.0"

    /// Return the version compiled into the native `polylib-ffi` library.
    public static func ffiVersion() -> String {
        PolylibFFI.ffiVersion()
    }

    /// Normalize free-form text into a lowercase hyphen-separated ASCII slug.
    public static func normalizeSlug(_ input: String) throws -> String {
        try mapErrors {
            try PolylibFFI.normalizeSlug(input: input)
        }
    }

    /// Summarize a non-empty array of finite floating-point scores.
    public static func summarizeScores(_ values: [Double]) throws -> ScoreSummary {
        try mapErrors {
            let raw = try PolylibFFI.summarizeScores(values: values)
            return ScoreSummary(
                count: Int(raw.count),
                min: raw.min,
                max: raw.max,
                mean: raw.mean,
                total: raw.total
            )
        }
    }

    private static func mapErrors<T>(_ body: () throws -> T) throws -> T {
        do {
            return try body()
        } catch let err as PolylibFFI.PolylibFfiError {
            switch err {
            case let .EmptyInput(_, detail):
                throw PolylibError.emptyInput(detail: detail)
            case let .EmptyScores(_, detail):
                throw PolylibError.emptyScores(detail: detail)
            case let .NonFiniteValue(_, detail):
                throw PolylibError.nonFiniteValue(detail: detail)
            }
        }
    }
}
