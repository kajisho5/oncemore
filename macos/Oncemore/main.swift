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

final class AppDelegate: NSObject, NSApplicationDelegate, WKUIDelegate, WKNavigationDelegate {
    var window: NSWindow!
    var webView: WKWebView!
    var server: ServerProcess?
    var projectDir: URL?
    let smokeResult = ProcessInfo.processInfo.environment["ONCEMORE_SMOKE_RESULT"]
    let lastProjectKey = "lastProjectFolder"

    func applicationDidFinishLaunching(_ notification: Notification) {
        buildMenu()
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()
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
        projectDir = url
        UserDefaults.standard.set(url.path, forKey: lastProjectKey)
        NSDocumentController.shared.noteNewRecentDocumentURL(url)
        window.title = url.lastPathComponent
        window.representedURL = url
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
        guard let id = sender.representedObject as? String, id.allSatisfy({ $0.isLetter || $0 == "_" }) else { return }
        webView?.evaluateJavaScript("window.oncemoreCommand && window.oncemoreCommand('\(id)')", completionHandler: nil)
    }

    // Undo / Redo: text editing inside a field, otherwise the project's history
    @objc func webUndo(_ sender: Any?) { webEdit("undo") }
    @objc func webRedo(_ sender: Any?) { webEdit("redo") }
    func webEdit(_ what: String) {
        let js = """
        (function () { var a = document.activeElement;
          if (a && (a.tagName === 'INPUT' || a.tagName === 'TEXTAREA' || a.isContentEditable)) document.execCommand('\(what)');
          else if (window.oncemoreCommand) window.oncemoreCommand('\(what)'); })()
        """
        webView?.evaluateJavaScript(js, completionHandler: nil)
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
                let text = (result as? String) ?? "{\"jsError\": \"\(error.map { "\($0)" } ?? "none")\"}"
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

    func buildMenu() {
        let main = NSMenu()
        func add(_ title: String, _ items: [NSMenuItem]) -> NSMenu {
            let item = NSMenuItem()
            let menu = NSMenu(title: title)
            items.forEach { menu.addItem($0) }
            item.submenu = menu
            main.addItem(item)
            return menu
        }
        func mi(_ title: String, _ action: Selector?, _ key: String, _ mods: NSEvent.ModifierFlags = .command) -> NSMenuItem {
            let item = NSMenuItem(title: title, action: action, keyEquivalent: key)
            item.keyEquivalentModifierMask = mods
            return item
        }
        _ = add("oncemore", [
            mi("About oncemore", #selector(NSApplication.orderFrontStandardAboutPanel(_:)), ""),
            .separator(),
            mi("Hide oncemore", #selector(NSApplication.hide(_:)), "h"),
            mi("Hide Others", #selector(NSApplication.hideOtherApplications(_:)), "h", [.command, .option]),
            mi("Show All", #selector(NSApplication.unhideAllApplications(_:)), ""),
            .separator(),
            mi("Quit oncemore", #selector(NSApplication.terminate(_:)), "q"),
        ])
        func cmd(_ title: String, _ id: String, _ key: String = "", _ mods: NSEvent.ModifierFlags = .command) -> NSMenuItem {
            let item = mi(title, #selector(runWebCommand(_:)), key, mods)
            item.representedObject = id
            item.target = self
            return item
        }
        func own(_ item: NSMenuItem) -> NSMenuItem { item.target = self; return item }
        // the order disc authoring people know: File, Edit, Object, Menu, Timeline, View, Window, Help
        _ = add("File", [
            own(mi("New Project…", #selector(newProject(_:)), "n")),
            own(mi("Open Project…", #selector(openProject(_:)), "o")),
            .separator(),
            cmd("Import Files…", "import_files", "i"),
            cmd("Import Photoshop Design…", "import_psd"),
            cmd("Replace Asset…", "replace_asset"),
            .separator(),
            cmd("Project Settings…", "project_settings"),
            .separator(),
            cmd("Transcode This Title Now", "transcode_title"),
            cmd("Transcode All Titles Now", "transcode_all"),
            .separator(),
            cmd("Preview", "preview"),        // (⇧Space in the page; not here, it would take the key from text fields)
            cmd("Check Project", "check"),
            cmd("Build Disc…", "build", "b"),
            .separator(),
            own(mi("Show Project Folder in Finder", #selector(revealProject(_:)), "r", [.command, .shift])),
            .separator(),
            mi("Close Window", #selector(NSWindow.performClose(_:)), "w"),
        ])
        // Cut / Copy / Paste / Select All stay the standard ones for text fields
        _ = add("Edit", [
            own(mi("Undo", #selector(webUndo(_:)), "z")),
            own(mi("Redo", #selector(webRedo(_:)), "z", [.command, .shift])),
            .separator(),
            mi("Cut", #selector(NSText.cut(_:)), "x"),
            mi("Copy", #selector(NSText.copy(_:)), "c"),
            mi("Paste", #selector(NSText.paste(_:)), "v"),
            mi("Select All", #selector(NSText.selectAll(_:)), "a"),
            .separator(),
            cmd("Duplicate", "duplicate", "d"),
            cmd("Delete", "delete"),
            .separator(),
            cmd("Edit Menu in Photoshop", "edit_psd"),
            .separator(),
            cmd("Preferences…", "preferences", ","),
        ])
        _ = add("Object", [
            cmd("Align Left Edges", "align_left"),
            cmd("Align Horizontal Centres", "align_hcenter"),
            cmd("Align Right Edges", "align_right"),
            cmd("Align Top Edges", "align_top"),
            cmd("Align Vertical Centres", "align_vcenter"),
            cmd("Align Bottom Edges", "align_bottom"),
            .separator(),
            cmd("Distribute Horizontally", "distribute_h"),
            cmd("Distribute Vertically", "distribute_v"),
            .separator(),
            cmd("Bring to Front", "bring_front", "]", [.command, .shift]),
            cmd("Send to Back", "send_back", "[", [.command, .shift]),
            .separator(),
            cmd("Convert Text ⇄ Button", "convert"),
        ])
        _ = add("Menu", [
            cmd("New Menu…", "new_menu"),
            .separator(),
            cmd("Set Link…", "set_link", "l"),
            .separator(),
            cmd("Selection Tool", "tool_select"),
            cmd("Text Tool", "tool_text"),
            cmd("Zoom Tool", "tool_zoom"),
        ])
        _ = add("Timeline", [
            cmd("New Title from a Video…", "new_timeline"),
            cmd("New Slideshow", "new_slideshow"),
            cmd("New Playlist", "new_playlist"),
            .separator(),
            cmd("Add Chapter at Playhead", "add_chapter"),
            cmd("Add Chapter Points at Intervals…", "chapters_interval"),
            cmd("Previous Chapter", "prev_chapter"),
            cmd("Next Chapter", "next_chapter"),
            cmd("Play / Pause", "play"),
        ])
        _ = add("View", [
            cmd("Zoom In", "zoom_in", "="),
            cmd("Zoom Out", "zoom_out", "-"),
            .separator(),
            cmd("Show Safe Area", "safe_area"),
            cmd("Show Button Routing", "routing"),
        ])
        let windowMenu = add("Window", [
            cmd("Workspace: Default", "ws_author", "1", [.option, .shift]),
            cmd("Workspace: Flowchart", "ws_flow", "2", [.option, .shift]),
            cmd("Project Preview", "ws_sim", "3", [.option, .shift]),
            cmd("Build", "ws_build", "4", [.option, .shift]),
            .separator(),
            cmd("Project", "win_project"),
            cmd("Menus", "win_menus"),
            cmd("Timelines", "win_timelines"),
            cmd("Build Panel", "win_build"),
            cmd("Monitor", "win_monitor"),
            cmd("Flowchart Panel", "win_flowchart"),
            cmd("Properties", "win_properties"),
            cmd("Layers", "win_layers"),
            cmd("Library", "win_library"),
            .separator(),
            cmd("Light / Dark Theme", "theme"),
            cmd("English / 日本語", "language"),
            own(mi("Reload", #selector(reloadPage(_:)), "r")),
            mi("Enter Full Screen", #selector(NSWindow.toggleFullScreen(_:)), "f", [.command, .control]),
            .separator(),
            mi("Minimize", #selector(NSWindow.performMiniaturize(_:)), "m"),
            mi("Zoom", #selector(NSWindow.performZoom(_:)), ""),
        ])
        NSApp.windowsMenu = windowMenu
        NSApp.helpMenu = add("Help", [
            cmd("Keyboard Shortcuts", "shortcuts", "/"),
        ])
        NSApp.mainMenu = main
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
