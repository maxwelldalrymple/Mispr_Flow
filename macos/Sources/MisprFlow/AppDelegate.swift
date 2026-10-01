import AppKit
import MisprCore
import SwiftUI

final class AppDelegate: NSObject, NSApplicationDelegate {
    let model = AppModel()
    private var window: NSWindow?
    private lazy var noteWindow = NoteWindowController(model: model)

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.mainMenu = makeMainMenu()
        model.engine.onCleanExit = { NSApp.terminate(nil) }
        model.openNote = { [weak self] in self?.noteWindow.show() }
        model.start()
        showMainWindow()
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows: Bool) -> Bool {
        showMainWindow()  // clicking the Dock icon
        return true
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        false  // dictation keeps working with the window closed, like Wispr Flow
    }

    func applicationWillTerminate(_ notification: Notification) {
        model.engine.stop()
    }

    // MARK: - Window

    @objc func showMainWindow() {
        if window == nil {
            let window = NSWindow(
                contentRect: NSRect(x: 0, y: 0, width: 1180, height: 760),
                styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
                backing: .buffered, defer: false)
            window.title = "Mispr Flow"
            window.titleVisibility = .hidden
            window.titlebarAppearsTransparent = true
            window.isMovableByWindowBackground = true
            window.minSize = NSSize(width: 900, height: 600)
            window.isReleasedWhenClosed = false
            window.contentView = NSHostingView(rootView: RootView().environmentObject(model))
            window.center()
            window.setFrameAutosaveName("MainWindow")
            self.window = window
        }
        window?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        model.reloadRecordings()
    }

    @objc func showSettings() {
        showMainWindow()
        model.showSettings = true
    }

    @objc func openSetupGuide() {
        model.engine.send(.openSetup)
    }

    // MARK: - Menus

    private func makeMainMenu() -> NSMenu {
        let main = NSMenu()

        let appMenu = NSMenu(title: "Mispr Flow")
        appMenu.addItem(withTitle: "About Mispr Flow", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(item("Settings…", #selector(showSettings), ","))
        appMenu.addItem(item("Setup Guide…", #selector(openSetupGuide), ""))
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Hide Mispr Flow", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        let others = appMenu.addItem(withTitle: "Hide Others", action: #selector(NSApplication.hideOtherApplications(_:)), keyEquivalent: "h")
        others.keyEquivalentModifierMask = [.command, .option]
        appMenu.addItem(withTitle: "Show All", action: #selector(NSApplication.unhideAllApplications(_:)), keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Quit Mispr Flow", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        main.addItem(submenu(appMenu))

        let edit = NSMenu(title: "Edit")  // so ⌘C / ⌘V / ⌘A work in text fields
        edit.addItem(withTitle: "Undo", action: Selector(("undo:")), keyEquivalent: "z")
        edit.addItem(withTitle: "Redo", action: Selector(("redo:")), keyEquivalent: "Z")
        edit.addItem(.separator())
        edit.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        edit.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        edit.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        edit.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        main.addItem(submenu(edit))

        let windowMenu = NSMenu(title: "Window")
        windowMenu.addItem(withTitle: "Minimize", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        windowMenu.addItem(withTitle: "Close", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w")
        windowMenu.addItem(.separator())
        windowMenu.addItem(item("Mispr Flow", #selector(showMainWindow), "0"))
        main.addItem(submenu(windowMenu))
        NSApp.windowsMenu = windowMenu
        return main
    }

    private func item(_ title: String, _ action: Selector, _ key: String) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: action, keyEquivalent: key)
        item.target = self
        return item
    }

    private func submenu(_ menu: NSMenu) -> NSMenuItem {
        let item = NSMenuItem()
        item.submenu = menu
        return item
    }
}
