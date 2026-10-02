import CryptoKit
import Foundation

/// A newer Mispr Flow on GitHub Releases: its DMG and the DMG's signature.
public struct Release: Equatable {
    public let version: String
    public let dmg: URL
    public let signature: URL
    public let page: URL?
}

/// The pieces of automatic updates that don't touch the system: reading GitHub's answer,
/// comparing versions, and checking a download's signature.
///
/// Every release DMG is signed (Ed25519, over its SHA-256) with a private key that never leaves
/// the maintainer's Mac (tools/build_dmg.sh). The app only installs a DMG whose signature checks
/// out against the public key below, so a swapped file on GitHub, or anywhere in between, is refused.
public enum Update {
    public static let latestURL = URL(string: "https://api.github.com/repos/maxwelldalrymple/Mispr_Flow/releases/latest")!
    /// The public half of ~/.config/mispr-flow/update-signing-key.pem.
    public static let publicKey = "8pAbV5YsCHSk4CduRDIR3etCMbgAHGlolm8jwA0c5fY="
    /// How often to look for a new version (about 5 times a day), and how soon after launch.
    public static let checkEvery: TimeInterval = 5 * 3600
    public static let firstCheckAfter: TimeInterval = 60
    /// Where downloads may come from (GitHub and its file servers), always HTTPS.
    static let allowedHosts: Set<String> = ["github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"]

    /// The release in GitHub's "latest release" JSON, if it has a signed DMG.
    public static func parse(_ data: Data) -> Release? {
        guard let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let tag = object["tag_name"] as? String,
              object["draft"] as? Bool != true, object["prerelease"] as? Bool != true,
              let assets = object["assets"] as? [[String: Any]] else { return nil }
        let version = tag.hasPrefix("v") ? String(tag.dropFirst()) : tag
        func asset(_ name: String) -> URL? {
            guard let found = assets.first(where: { $0["name"] as? String == name }),
                  let link = found["browser_download_url"] as? String, let url = URL(string: link),
                  isAllowed(url) else { return nil }
            return url
        }
        let name = "Mispr-Flow-\(version).dmg"
        guard let dmg = asset(name), let signature = asset(name + ".sig") else { return nil }
        return Release(version: version, dmg: dmg, signature: signature,
                       page: (object["html_url"] as? String).flatMap(URL.init(string:)))
    }

    public static func isAllowed(_ url: URL) -> Bool {
        url.scheme == "https" && allowedHosts.contains(url.host ?? "")
    }

    /// "1.10.0" is newer than "1.9.2"; missing parts count as 0.
    public static func isNewer(_ candidate: String, than current: String) -> Bool {
        func parts(_ v: String) -> [Int] { v.split(separator: ".").map { Int($0.prefix { $0.isNumber }) ?? 0 } }
        let a = parts(candidate), b = parts(current)
        for i in 0..<max(a.count, b.count) {
            let x = i < a.count ? a[i] : 0, y = i < b.count ? b[i] : 0
            if x != y { return x > y }
        }
        return false
    }

    /// True if `signature` (base64 text, as in the .sig file) is the maintainer's signature of
    /// this file's SHA-256.
    public static func verify(file: URL, signature: String, publicKey: String = publicKey) -> Bool {
        guard let sig = Data(base64Encoded: signature.trimmingCharacters(in: .whitespacesAndNewlines)),
              let raw = Data(base64Encoded: publicKey),
              let key = try? Curve25519.Signing.PublicKey(rawRepresentation: raw),
              let digest = try? sha256(of: file) else { return false }
        return key.isValidSignature(sig, for: digest)
    }

    /// SHA-256 of a file, read in pieces (DMGs are ~90 MB).
    public static func sha256(of file: URL) throws -> Data {
        let handle = try FileHandle(forReadingFrom: file)
        defer { try? handle.close() }
        var hasher = SHA256()
        while let chunk = try handle.read(upToCount: 1 << 20), !chunk.isEmpty {
            hasher.update(data: chunk)
        }
        return Data(hasher.finalize())
    }
}
