// swift-tools-version: 5.10
import Foundation
import PackageDescription

let packageDir = URL(fileURLWithPath: #filePath).deletingLastPathComponent().path
let nativeDir = packageDir + "/.native"

let package = Package(
    name: "Polylib",
    platforms: [
        .macOS(.v13),
        .iOS(.v16),
    ],
    products: [
        .library(
            name: "Polylib",
            targets: ["Polylib"]
        ),
    ],
    targets: [
        .target(
            name: "PolylibFFIInternal",
            path: "Sources/PolylibFFIInternal",
            publicHeadersPath: "include"
        ),
        .target(
            name: "PolylibFFI",
            dependencies: ["PolylibFFIInternal"],
            path: "Sources/PolylibFFI",
            linkerSettings: [
                .unsafeFlags(["-L", nativeDir, "-Xlinker", "-rpath", "-Xlinker", nativeDir]),
                .linkedLibrary("polylib_ffi"),
            ]
        ),
        .target(
            name: "Polylib",
            dependencies: ["PolylibFFI"],
            path: "Sources/Polylib"
        ),
        .testTarget(
            name: "PolylibTests",
            dependencies: ["Polylib"],
            path: "Tests/PolylibTests"
        ),
    ]
)
