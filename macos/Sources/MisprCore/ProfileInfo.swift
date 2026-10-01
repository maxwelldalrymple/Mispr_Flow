import Foundation

/// Who you are, for the greeting and your avatar. Stored on this Mac only.
public struct ProfileInfo: Equatable {
    public var name: String
    public var nickname: String
    public var role: String

    public init(name: String = "", nickname: String = "", role: String = "") {
        self.name = name
        self.nickname = nickname
        self.role = role
    }

    /// The greeting's name: the nickname, else the first word of the name, else the Mac
    /// account's name, capitalized ("cyb" -> "Cyb").
    public func greetingName(account: String) -> String {
        let nick = nickname.trimmingCharacters(in: .whitespaces)
        if !nick.isEmpty { return nick }
        if let first = name.split(separator: " ").first { return String(first) }
        let fallback = account.split(separator: " ").first.map(String.init) ?? account
        return fallback.prefix(1).uppercased() + fallback.dropFirst()
    }

    /// Up to two initials for the avatar ("Max Dalrymple" -> "MD").
    public func initials(account: String) -> String {
        let source = name.trimmingCharacters(in: .whitespaces).isEmpty ? greetingName(account: account) : name
        let letters = source.split(separator: " ").prefix(2).compactMap(\.first).map { String($0).uppercased() }
        return letters.isEmpty ? "?" : letters.joined()
    }
}
