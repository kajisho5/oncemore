// Oncemore.app — a native macOS window around `oncemore gui`.
//
// The app starts the bundled Python running `-m oncemore gui <project>
// --no-browser`, reads the URL (with its per-launch token) the server prints,
// and shows it in a WKWebView. Everything else — editing, building ISOs — is
// the same web UI as in the browser.
//
// Build: see macos/build_app.sh (swiftc, no Xcode project needed).

import Cocoa
import WebKit

// MARK: - Server process

final class ServerProcess {
    let process = Process()
    private let errPipe = Pipe()
    private var buffer = ""
    private(set) var log = ""
    var onURL: ((URL) -> Void)?
    var onExit: ((Int32, String) -> Void)?

    init(projectDir: URL) {
        let res = Bundle.main.resourceURL!
        let bundledPython = res.appendingPathComponent("python/bin/python3")
        let appDir = res.appendingPathComponent("app")
        var env = ProcessInfo.processInfo.environment
        // Apps started from Finder get a minimal PATH; Homebrew's tools
        // (ffmpeg-full, dvdauthor, xorriso, mkisofs) live here.
        let extra = ["/opt/homebrew/bin", "/opt/homebrew/sbin", "/usr/local/bin", "/usr/local/sbin"]
        let current = (env["PATH"] ?? "/usr/bin:/bin:/usr/sbin:/sbin").split(separator: ":").map(String.init)
        env["PATH"] = (extra.filter { !current.contains($0) } + current).joined(separator: ":")
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONUNBUFFERED"] = "1"
        if FileManager.default.fileExists(atPath: appDir.path) {
            env["PYTHONPATH"] = appDir.path
        }
        if FileManager.default.isExecutableFile(atPath: bundledPython.path) {
            process.executableURL = bundledPython
            process.arguments = ["-s", "-m", "oncemore", "gui", projectDir.path, "--no-browser"]
        } else {
            // development build without a bundled interpreter
            process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
            process.arguments = ["python3", "-m", "oncemore", "gui", projectDir.path, "--no-browser"]
        }
        process.environment = env
        process.standardError = errPipe
        process.standardOutput = errPipe
    }

    func start() throws {
        errPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard let self = self, !data.isEmpty, let text = String(data: data, encoding: .utf8) else { return }
            DispatchQueue.main.async { self.consume(text) }
        }
        process.terminationHandler = { [weak self] p in
            DispatchQueue.main.async {
                guard let self = self else { return }
                self.onExit?(p.terminationStatus, self.log)
            }
        }
        try process.run()
    }

    private func consume(_ text: String) {
        log += text
        buffer += text
        guard onURL != nil else { return }
        let pattern = "http://127\\.0\\.0\\.1:[0-9]+/#token=[A-Za-z0-9_-]+"
        if let range = buffer.range(of: pattern, options: .regularExpression),
           let url = URL(string: String(buffer[range])) {
            let callback = onURL
            onURL = nil
            callback?(url)
        }
    }

    func stop() {
        errPipe.fileHandleForReading.readabilityHandler = nil
        if process.isRunning {
            process.terminate()
        }
    }
}

// MARK: - App

final class AppDelegate: NSObject, NSApplicationDelegate, WKUIDelegate, WKNavigationDelegate, WKScriptMessageHandler {
    var window: NSWindow!
    var webView: WKWebView!
    var server: ServerProcess?
    var projectDir: URL?
    let smokeResult = ProcessInfo.processInfo.environment["ONCEMORE_SMOKE_RESULT"]
    let lastProjectKey = "lastProjectFolder"

    func applicationDidFinishLaunching(_ notification: Notification) {
        buildMenu(from: AppDelegate.startMenus)
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()
        // the page posts its menu bar (and the project it switched to) here
        config.userContentController.add(self, name: "oncemoreMenu")
        config.userContentController.add(self, name: "oncemoreProject")
        // the page hides its own menu bar inside the app (this one has a real one)
        config.applicationNameForUserAgent = "OncemoreApp"
        webView = WKWebView(frame: NSRect(x: 0, y: 0, width: 1400, height: 880), configuration: config)
        webView.uiDelegate = self
        webView.navigationDelegate = self
        webView.allowsMagnification = true
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1400, height: 880),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable],
                          backing: .buffered, defer: false)
        window.title = "oncemore"
        window.minSize = NSSize(width: 960, height: 600)
        window.contentView = webView
        window.center()
        window.setFrameAutosaveName("OncemoreMain")
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        showMessage("oncemore", "Starting…")

        let env = ProcessInfo.processInfo.environment
        if let p = env["ONCEMORE_PROJECT"] {
            open(project: URL(fileURLWithPath: p))
        } else if let last = UserDefaults.standard.string(forKey: lastProjectKey),
                  FileManager.default.fileExists(atPath: last) {
            open(project: URL(fileURLWithPath: last))
        } else {
            DispatchQueue.main.async { self.newProject(nil) }
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }

    func applicationWillTerminate(_ notification: Notification) {
        server?.stop()
    }

    // MARK: projects

    func open(project url: URL) {
        server?.onExit = nil
        server?.stop()
        try? FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        noteProject(url)
        showMessage(url.lastPathComponent, "Starting the oncemore engine…")
        let s = ServerProcess(projectDir: url)
        s.onURL = { [weak self] link in
            self?.webView.load(URLRequest(url: link))
        }
        s.onExit = { [weak self] status, log in
            self?.showError("The oncemore engine stopped (exit \(status)).", log)
        }
        server = s
        do {
            try s.start()
        } catch {
            showError("Could not start the oncemore engine.", "\(error)")
        }
    }

    // the project being worked on (also after the page's Open recent / Save as)
    func noteProject(_ url: URL) {
        projectDir = url
        UserDefaults.standard.set(url.path, forKey: lastProjectKey)
        NSDocumentController.shared.noteNewRecentDocumentURL(url)
        window.title = url.lastPathComponent
        window.representedURL = url
    }

    @objc func openProject(_ sender: Any?) {
        let panel = NSOpenPanel()
        panel.message = "Choose a project folder (a folder with project.oncemore.json, or an empty one)"
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.canCreateDirectories = true
        panel.allowsMultipleSelection = false
        panel.beginSheetModal(for: window) { [weak self] resp in
            if resp == .OK, let url = panel.url { self?.open(project: url) }
        }
    }

    @objc func newProject(_ sender: Any?) {
        let panel = NSSavePanel()
        panel.message = "Name the new DVD project folder"
        panel.nameFieldStringValue = "My DVD"
        panel.canCreateDirectories = true
        panel.beginSheetModal(for: window) { [weak self] resp in
            if resp == .OK, let url = panel.url { self?.open(project: url) }
        }
    }

    @objc func revealProject(_ sender: Any?) {
        if let dir = projectDir { NSWorkspace.shared.activateFileViewerSelecting([dir]) }
    }

    @objc func reloadPage(_ sender: Any?) { webView.reload() }

    // Menu items that act on the project run the page's own commands (the
    // same ones as its menu bar, right-click menus and shortcuts).
    @objc func runWebCommand(_ sender: NSMenuItem) {
        guard let id = sender.representedObject as? String, id.allSatisfy({ $0.isASCII && ($0.isLetter || $0.isNumber || $0 == "_") }) else { return }
        webView?.evaluateJavaScript("window.oncemoreCommand && window.oncemoreCommand('\(id)')", completionHandler: nil)
    }

    // Undo / Redo: text editing inside a field, otherwise the project's history
    @objc func webUndo(_ sender: Any?) { webEdit("undo", "undo") }
    @objc func webRedo(_ sender: Any?) { webEdit("redo", "redo") }
    // Select All: the text in a field, otherwise every object of the menu being edited
    @objc func webSelectAll(_ sender: Any?) { webEdit("selectAll", "select_all") }
    func webEdit(_ what: String, _ command: String) {
        let js = """
        (function () { var a = document.activeElement;
          if (a && (a.tagName === 'INPUT' || a.tagName === 'TEXTAREA' || a.isContentEditable)) document.execCommand('\(what)');
          else if (window.oncemoreCommand) window.oncemoreCommand('\(command)'); })()
        """
        webView?.evaluateJavaScript(js, completionHandler: nil)
    }

    // MARK: WKScriptMessageHandler

    func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
        if message.name == "oncemoreMenu", let text = message.body as? String,
           let data = text.data(using: .utf8),
           let spec = (try? JSONSerialization.jsonObject(with: data)) as? [[String: Any]] {
            buildMenu(from: spec)
        } else if message.name == "oncemoreProject", let path = message.body as? String, path.hasPrefix("/") {
            noteProject(URL(fileURLWithPath: path))
        }
    }

    // MARK: messages

    func showMessage(_ title: String, _ body: String) {
        let html = """
        <html><body style="background:#15171c;color:#e6e8ee;font-family:-apple-system,sans-serif;
        display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
        <div style="text-align:center"><div style="font-size:22px;font-weight:600">
        <span style="color:#ffd400">◉</span> \(escape(title))</div>
        <p style="color:#98a0b3">\(escape(body))</p></div></body></html>
        """
        webView.loadHTMLString(html, baseURL: nil)
    }

    func showError(_ message: String, _ detail: String) {
        let html = """
        <html><body style="background:#15171c;color:#e6e8ee;font-family:-apple-system,sans-serif;padding:40px">
        <h2 style="color:#ff5f6d">\(escape(message))</h2>
        <p>oncemore needs ffmpeg (with drawtext) and dvdauthor. Install them with Homebrew:</p>
        <pre style="background:#000;padding:12px;border-radius:6px">brew install ffmpeg-full dvdauthor</pre>
        <p>Then choose File › Open Project… again.</p>
        <pre style="white-space:pre-wrap;color:#98a0b3;font-size:11px">\(escape(String(detail.suffix(4000))))</pre>
        </body></html>
        """
        webView.loadHTMLString(html, baseURL: nil)
        if let path = smokeResult {
            try? "{\"error\": true}".write(toFile: path, atomically: true, encoding: .utf8)
            NSApp.terminate(nil)
        }
    }

    func escape(_ s: String) -> String {
        s.replacingOccurrences(of: "&", with: "&amp;").replacingOccurrences(of: "<", with: "&lt;")
            .replacingOccurrences(of: ">", with: "&gt;")
    }

    // MARK: WKNavigationDelegate

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url else { return decisionHandler(.cancel) }
        if url.scheme == "about" || (url.host == "127.0.0.1" && url.scheme == "http") {
            return decisionHandler(.allow)
        }
        if url.scheme == "https" || url.scheme == "http" {
            NSWorkspace.shared.open(url)   // links to the outside world open in the browser
        }
        decisionHandler(.cancel)
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        guard let path = smokeResult, webView.url?.host == "127.0.0.1" else { return }
        // smoke test: wait for the app to render, report what it shows, quit
        DispatchQueue.main.asyncAfter(deadline: .now() + 4) {
            let js = """
            JSON.stringify({disc: document.querySelector('#disc-name') ? document.querySelector('#disc-name').textContent : null,
              navItems: document.querySelectorAll('.nav-item').length,
              stage: !!document.querySelector('.stage'),
              status: document.querySelector('#statusbar') ? document.querySelector('#statusbar').textContent : null})
            """
            webView.evaluateJavaScript(js) { result, error in
                var text = (result as? String) ?? "{\"jsError\": \"\(error.map { "\($0)" } ?? "none")\"}"
                // and the menu bar the page made
                let menus = (NSApp.mainMenu?.items ?? []).compactMap { $0.submenu?.title }
                if let data = try? JSONSerialization.data(withJSONObject: menus), let list = String(data: data, encoding: .utf8),
                   text.hasSuffix("}") {
                    text = String(text.dropLast()) + ", \"menus\": \(list)}"
                }
                try? text.write(toFile: path, atomically: true, encoding: .utf8)
                NSApp.terminate(nil)
            }
        }
    }

    // MARK: WKUIDelegate (file picker, alert, confirm)

    func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping ([URL]?) -> Void) {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = parameters.allowsMultipleSelection
        panel.canChooseDirectories = false
        panel.canChooseFiles = true
        panel.beginSheetModal(for: window) { resp in
            completionHandler(resp == .OK ? panel.urls : nil)
        }
    }

    func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
        let alert = NSAlert()
        alert.messageText = message
        alert.beginSheetModal(for: window) { _ in completionHandler() }
    }

    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        let alert = NSAlert()
        alert.messageText = message
        alert.addButton(withTitle: "OK")
        alert.addButton(withTitle: "Cancel")
        alert.beginSheetModal(for: window) { resp in completionHandler(resp == .alertFirstButtonReturn) }
    }

    // MARK: menu

    // The menu bar is the page's own (window.oncemoreMenuSpec): it posts the
    // menus, in the language it shows, whenever what they can do changes, and
    // they are made again here. Until the page is there: the few items that
    // need no page.
    static let startMenus: [[String: Any]] = [
        ["title": "File", "role": "file", "items": [
            ["id": "new_project", "label": "New Project…", "key": "mod+n"],
            ["id": "open_project", "label": "Open Project…", "key": "mod+o"], "-",
            ["id": "close_window", "label": "Close Window", "key": "mod+w"]] as [Any]],
        ["title": "Edit", "role": "edit", "items": [
            ["id": "undo", "label": "Undo", "key": "mod+z"], ["id": "redo", "label": "Redo", "key": "mod+shift+z"], "-",
            ["id": "cut", "label": "Cut", "key": "mod+x"], ["id": "copy", "label": "Copy", "key": "mod+c"],
            ["id": "paste", "label": "Paste", "key": "mod+v"], ["id": "select_all", "label": "Select All", "key": "mod+a"]] as [Any]],
        ["title": "Window", "role": "window", "items": [
            ["id": "reload", "label": "Reload", "key": "mod+r"], ["id": "full_screen", "label": "Enter Full Screen", "key": "mod+ctrl+f"], "-",
            ["id": "minimize", "label": "Minimize", "key": "mod+m"], ["id": "zoom_window", "label": "Zoom"]] as [Any]],
    ]

    // items the app does itself (the rest run the page's commands); the
    // text-editing ones also work in the page's text fields, so stay enabled
    struct Native { let action: Selector; let own: Bool; let text: Bool }
    lazy var natives: [String: Native] = [
        "new_project": Native(action: #selector(AppDelegate.newProject(_:)), own: true, text: false),
        "open_project": Native(action: #selector(AppDelegate.openProject(_:)), own: true, text: false),
        "reveal": Native(action: #selector(AppDelegate.revealProject(_:)), own: true, text: false),
        "close_window": Native(action: #selector(NSWindow.performClose(_:)), own: false, text: true),
        "undo": Native(action: #selector(AppDelegate.webUndo(_:)), own: true, text: true),
        "redo": Native(action: #selector(AppDelegate.webRedo(_:)), own: true, text: true),
        "cut": Native(action: #selector(NSText.cut(_:)), own: false, text: true),
        "copy": Native(action: #selector(NSText.copy(_:)), own: false, text: true),
        "paste": Native(action: #selector(NSText.paste(_:)), own: false, text: true),
        "select_all": Native(action: #selector(AppDelegate.webSelectAll(_:)), own: true, text: true),
        "reload": Native(action: #selector(AppDelegate.reloadPage(_:)), own: true, text: true),
        "full_screen": Native(action: #selector(NSWindow.toggleFullScreen(_:)), own: false, text: true),
        "minimize": Native(action: #selector(NSWindow.performMiniaturize(_:)), own: false, text: true),
        "zoom_window": Native(action: #selector(NSWindow.performZoom(_:)), own: false, text: true),
    ]

    // "mod+shift+z" -> ("z", ⌘⇧); keys without ⌘ or ⌥ (Space, Delete, V…) stay
    // the page's, so typing in its fields is never taken by a menu
    func keyEquivalent(_ spec: String) -> (String, NSEvent.ModifierFlags) {
        let parts = spec == "+" ? ["+"] : spec.components(separatedBy: "+")
        guard parts.count > 1, let key = parts.last, key.count == 1 else { return ("", []) }
        var mods: NSEvent.ModifierFlags = []
        if parts.contains("mod") { mods.insert(.command) }
        if parts.contains("shift") { mods.insert(.shift) }
        if parts.contains("alt") { mods.insert(.option) }
        if parts.contains("ctrl") { mods.insert(.control) }
        guard mods.contains(.command) || mods.contains(.option) else { return ("", []) }
        return (key, mods)
    }

    func menuItem(_ entry: Any) -> NSMenuItem {
        guard let d = entry as? [String: Any] else { return .separator() }
        let label = d["label"] as? String ?? ""
        let id = d["id"] as? String ?? ""
        let disabled = d["disabled"] as? Bool ?? false
        if let sub = d["sub"] as? [Any] {
            let item = NSMenuItem(title: label, action: nil, keyEquivalent: "")
            let menu = NSMenu(title: label)
            menu.autoenablesItems = false
            sub.forEach { menu.addItem(menuItem($0)) }
            item.submenu = menu
            item.isEnabled = !disabled
            return item
        }
        let (key, mods) = keyEquivalent(d["key"] as? String ?? "")
        let item: NSMenuItem
        if let n = natives[id] {
            item = NSMenuItem(title: label, action: n.action, keyEquivalent: key)
            item.target = n.own ? self : nil
            item.isEnabled = n.text || !disabled
        } else {
            item = NSMenuItem(title: label, action: #selector(runWebCommand(_:)), keyEquivalent: key)
            item.target = self
            item.representedObject = id
            item.isEnabled = !disabled
        }
        item.keyEquivalentModifierMask = mods
        item.state = (d["checked"] as? Bool ?? false) ? .on : .off
        return item
    }

    func buildMenu(from spec: [[String: Any]]) {
        let main = NSMenu()
        func mi(_ title: String, _ action: Selector?, _ key: String, _ mods: NSEvent.ModifierFlags = .command) -> NSMenuItem {
            let item = NSMenuItem(title: title, action: action, keyEquivalent: key)
            item.keyEquivalentModifierMask = mods
            return item
        }
        let appMenu = NSMenu(title: "oncemore")
        let appItems: [NSMenuItem] = [mi("About oncemore", #selector(NSApplication.orderFrontStandardAboutPanel(_:)), ""),
         .separator(),
         mi("Hide oncemore", #selector(NSApplication.hide(_:)), "h"),
         mi("Hide Others", #selector(NSApplication.hideOtherApplications(_:)), "h", [.command, .option]),
         mi("Show All", #selector(NSApplication.unhideAllApplications(_:)), ""),
         .separator(),
         mi("Quit oncemore", #selector(NSApplication.terminate(_:)), "q")]
        appItems.forEach { appMenu.addItem($0) }
        let appItem = NSMenuItem()
        appItem.submenu = appMenu
        main.addItem(appItem)
        for entry in spec {
            guard let title = entry["title"] as? String, let items = entry["items"] as? [Any] else { continue }
            let menu = NSMenu(title: title)
            menu.autoenablesItems = false
            items.forEach { menu.addItem(menuItem($0)) }
            let top = NSMenuItem()
            top.submenu = menu
            main.addItem(top)
            switch entry["role"] as? String ?? "" {
            case "window": NSApp.windowsMenu = menu
            case "help": NSApp.helpMenu = menu
            default: break
            }
        }
        NSApp.mainMenu = main
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
