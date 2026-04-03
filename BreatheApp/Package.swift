// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "BreatheApp",
    platforms: [.iOS(.v17)],
    products: [
        .library(name: "BreatheApp", targets: ["BreatheApp"]),
    ],
    targets: [
        .target(
            name: "BreatheApp",
            path: "BreatheApp"
        ),
    ]
)
