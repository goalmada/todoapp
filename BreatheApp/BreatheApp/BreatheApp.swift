import SwiftUI

@main
struct BreatheApp: App {
    @StateObject private var tracker = SessionTracker()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(tracker)
        }
    }
}
