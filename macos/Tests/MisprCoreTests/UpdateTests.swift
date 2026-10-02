import CryptoKit
import XCTest
@testable import MisprCore

/// Automatic updates: reading GitHub's answer, comparing versions, checking signatures.
final class UpdateTests: XCTestCase {
    func release(_ tag: String = "v1.2.0", host: String = "github.com", sig: Bool = true, draft: Bool = false) -> Data {
        var assets: [[String: Any]] = [["name": "Mispr-Flow-1.2.0.dmg",
                                        "browser_download_url": "https://\(host)/maxwelldalrymple/Mispr_Flow/releases/download/v1.2.0/Mispr-Flow-1.2.0.dmg"]]
        if sig {
            assets.append(["name": "Mispr-Flow-1.2.0.dmg.sig",
                           "browser_download_url": "https://\(host)/maxwelldalrymple/Mispr_Flow/releases/download/v1.2.0/Mispr-Flow-1.2.0.dmg.sig"])
        }
        let object: [String: Any] = ["tag_name": tag, "draft": draft, "prerelease": false, "assets": assets,
                                     "html_url": "https://github.com/maxwelldalrymple/Mispr_Flow/releases/tag/v1.2.0"]
        return try! JSONSerialization.data(withJSONObject: object)
    }

    func testParsesASignedRelease() throws {
        let r = try XCTUnwrap(Update.parse(release()))
        XCTAssertEqual(r.version, "1.2.0")
        XCTAssertEqual(r.dmg.lastPathComponent, "Mispr-Flow-1.2.0.dmg")
        XCTAssertEqual(r.signature.lastPathComponent, "Mispr-Flow-1.2.0.dmg.sig")
    }

    func testRefusesUnsignedDraftsAndOtherHosts() {
        XCTAssertNil(Update.parse(release(sig: false)))  // no signature: never installed
        XCTAssertNil(Update.parse(release(draft: true)))
        XCTAssertNil(Update.parse(release(host: "evil.example.com")))
        XCTAssertNil(Update.parse(Data("not json".utf8)))
        XCTAssertFalse(Update.isAllowed(URL(string: "http://github.com/x")!))  // never plain HTTP
    }

    func testVersionOrder() {
        XCTAssertTrue(Update.isNewer("1.1.0", than: "1.0.0"))
        XCTAssertTrue(Update.isNewer("1.10.0", than: "1.9.2"))
        XCTAssertTrue(Update.isNewer("2", than: "1.9.9"))
        XCTAssertFalse(Update.isNewer("1.0.0", than: "1.0"))
        XCTAssertFalse(Update.isNewer("1.0.0", than: "1.1.0"))
    }

    func testSignatureCheck() throws {
        let key = Curve25519.Signing.PrivateKey()
        let file = FileManager.default.temporaryDirectory.appendingPathComponent("\(UUID()).dmg")
        try Data("the real dmg".utf8).write(to: file)
        defer { try? FileManager.default.removeItem(at: file) }
        let signature = try key.signature(for: Update.sha256(of: file)).base64EncodedString()
        let publicKey = key.publicKey.rawRepresentation.base64EncodedString()
        XCTAssertTrue(Update.verify(file: file, signature: signature + "\n", publicKey: publicKey))
        try Data("a swapped dmg".utf8).write(to: file)
        XCTAssertFalse(Update.verify(file: file, signature: signature, publicKey: publicKey))  // changed file
        XCTAssertFalse(Update.verify(file: file, signature: "not base64", publicKey: publicKey))
        let other = Curve25519.Signing.PrivateKey().publicKey.rawRepresentation.base64EncodedString()
        try Data("the real dmg".utf8).write(to: file)
        XCTAssertFalse(Update.verify(file: file, signature: signature, publicKey: other))  // someone else's key
    }

    func testTheBuiltInKeyIsAValidEd25519Key() throws {
        let raw = try XCTUnwrap(Data(base64Encoded: Update.publicKey))
        XCTAssertNoThrow(try Curve25519.Signing.PublicKey(rawRepresentation: raw))
    }

    func testChecksAboutFiveTimesADay() {
        XCTAssertEqual(86_400 / Update.checkEvery, 4.8, accuracy: 0.01)
    }

    func testBusyEventAndAutoEnterKeySetting() throws {
        XCTAssertEqual(EngineEvent.parse(EngineEvent.prefix + #"{"event": "busy", "busy": true}"#), .busy(true))
        let file = SettingsFile(url: FileManager.default.temporaryDirectory.appendingPathComponent("\(UUID()).json"))
        XCTAssertEqual(file.autoEnterKey, SettingsFile.defaultAutoEnterKey)  // ⌃⌥↩ until changed
        XCTAssertEqual(SettingsFile.defaultAutoEnterKey.json["keycode"] as? Int, 36)
        try file.setAutoEnterKey(nil)
        XCTAssertNil(file.autoEnterKey)
        XCTAssertTrue(file.bool("auto_update"))  // on by default
    }

    func list(_ entries: [(String, Bool)]) -> Data {
        let objects: [[String: Any]] = entries.map { tag, pre in
            let v = String(tag.dropFirst())
            return ["tag_name": tag, "prerelease": pre, "draft": false,
                    "assets": [["name": "Mispr-Flow-\(v).dmg", "browser_download_url": "https://github.com/x/releases/download/\(tag)/Mispr-Flow-\(v).dmg"],
                               ["name": "Mispr-Flow-\(v).dmg.sig", "browser_download_url": "https://github.com/x/releases/download/\(tag)/Mispr-Flow-\(v).dmg.sig"]]]
        }
        return try! JSONSerialization.data(withJSONObject: objects)
    }

    func testBetaVersionsOrder() {
        XCTAssertTrue(Update.isNewer("1.3.0-beta.1", than: "1.2.0"))
        XCTAssertTrue(Update.isNewer("1.3.0", than: "1.3.0-beta.2"))  // the release beats its betas
        XCTAssertTrue(Update.isNewer("1.3.0-beta.2", than: "1.3.0-beta.1"))
        XCTAssertFalse(Update.isNewer("1.3.0-beta.9", than: "1.3.0"))
    }

    func testStableInstallsBetaIsOnlyOffered() {
        let found = Update.choose(list([("v1.2.0", false), ("v1.3.0-beta.1", true), ("v1.1.1", false)]), current: "1.1.1")
        XCTAssertEqual(found.stable?.version, "1.2.0")
        XCTAssertEqual(found.beta?.version, "1.3.0-beta.1")
        XCTAssertEqual(found.beta?.beta, true)
    }

    func testABetaOlderThanTheNewestStableIsNeverShown() {
        let found = Update.choose(list([("v1.3.0", false), ("v1.3.0-beta.2", true)]), current: "1.2.0")
        XCTAssertEqual(found.stable?.version, "1.3.0")
        XCTAssertNil(found.beta)
    }

    func testOnTheNewestStableOnlyANewerBetaIsOffered() {
        let found = Update.choose(list([("v1.2.0", false), ("v1.3.0-beta.1", true)]), current: "1.2.0")
        XCTAssertNil(found.stable)
        XCTAssertEqual(found.beta?.version, "1.3.0-beta.1")
        XCTAssertNil(Update.choose(list([("v1.2.0", false)]), current: "1.3.0-beta.1").beta)  // already past it
    }

    func testLatestEndpointParseSkipsBetas() {
        XCTAssertNil(Update.parse(release("v1.3.0-beta.1")))
    }
}
