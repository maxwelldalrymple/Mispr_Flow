import AppKit

// A plain AppKit entry point (rather than SwiftUI's App) so the window, Dock behavior,
// menus, and engine lifetime are all explicit.
let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
