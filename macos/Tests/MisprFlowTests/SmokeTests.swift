import XCTest
@testable import MisprFlow

final class SmokeTests: XCTestCase {
    func testTheAppTargetLoads() {
        XCTAssertEqual(Page.allCases.map(\.rawValue), ["Home", "Voice Commands", "Notetaker", "Insights", "Prompts"])
    }
}
