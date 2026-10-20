#!/usr/bin/env python3
"""
Integration test for aerospace-workspace-return.

Drives the helper's real AeroSpace socket client against a fake AeroSpace
server that speaks the same Unix-socket protocol (version 1). This exercises
the event subscription, the polling loop and the workspace switch - the same
code paths the live helper uses - without needing a real window manager or an
unlocked screen.

The fake server:
  - answers the version handshake
  - answers one-shot commands (list-windows, list-workspaces, workspace)
  - streams window-detected / focus-changed events for a subscribe request

The script then:
  1. tells the server a window appeared on workspace "2"
  2. moves it to workspace "9" (simulating the auto-assign callback)
  3. removes it (simulating the app closing)
  4. asserts the helper asked the server to switch back to workspace "2"
"""

import json
import os
import socket
import struct
import sys
import tempfile
import threading
import time

SRC = os.path.expanduser("~/Documents/Repos/dotfiles/bin/aerospace-workspace-return")
source = open(SRC).read().replace('if __name__ == "__main__":', "if False:")
awr = type(sys)("awr")
exec(compile(source, SRC, "exec"), awr.__dict__)

PROTOCOL = 1
BUNDLE = "ru.keepcoder.Telegram"
PID = 4242
failures = []


def check(name, condition, detail=""):
    if condition:
        print("  PASS  %s" % name)
    else:
        print("  FAIL  %s %s" % (name, detail))
        failures.append(name)


class FakeServer(threading.Thread):
    """A minimal AeroSpace server over a Unix socket."""

    def __init__(self, path):
        threading.Thread.__init__(self, daemon=True)
        self.path = path
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.listener.bind(path)
        self.listener.listen(5)
        self.windows = {}          # window id -> workspace
        self.apps = {BUNDLE}
        self.focused = "2"
        self.switches = []         # workspaces the client asked to focus
        self.subscriber = None     # connection to push events to
        self.lock = threading.Lock()

    def run(self):
        while True:
            conn, _ = self.listener.accept()
            threading.Thread(target=self.handle, args=(conn,), daemon=True).start()

    def handle(self, conn):
        try:
            # Handshake: read client version, send ours.
            raw = conn.recv(4)
            if len(raw) < 4:
                return
            conn.sendall(struct.pack("<I", PROTOCOL))

            while True:
                header = conn.recv(4)
                if len(header) < 4:
                    return
                (length,) = struct.unpack("<I", header)
                body = b""
                while len(body) < length:
                    body += conn.recv(length - len(body))
                request = json.loads(body)
                args = request.get("args", [])

                if args and args[0] == "subscribe":
                    with self.lock:
                        self.subscriber = conn
                    continue

                answer = self.handle_command(args)
                payload = json.dumps(answer).encode("utf-8")
                conn.sendall(struct.pack("<I", len(payload)) + payload)
        except OSError:
            pass

    def handle_command(self, args):
        if not args:
            return {"exitCode": 1, "stdout": "", "stderr": "no args"}
        name = args[0]
        with self.lock:
            if name == "list-windows":
                out = "".join("%d %s %d %s\n" % (wid, BUNDLE, PID, ws)
                              for wid, ws in self.windows.items())
            elif name == "list-apps":
                out = "".join("%s\n" % bundle for bundle in self.apps)
            elif name == "move-node-to-workspace":
                target = args[-1]
                wid = None
                for index, arg in enumerate(args):
                    if arg == "--window-id":
                        wid = int(args[index + 1])
                if wid is not None and wid in self.windows:
                    self.windows[wid] = target
                out = ""
            elif name == "list-workspaces":
                out = self.focused + "\n"
            elif name == "workspace":
                target = args[1]
                self.switches.append(target)
                self.focused = target
                out = ""
            else:
                out = ""
        return {"exitCode": 0, "stdout": out, "stderr": "", "serverVersionAndHash": "test 0"}

    def emit(self, event):
        with self.lock:
            conn = self.subscriber
        if conn is None:
            return
        payload = json.dumps(event).encode("utf-8")
        try:
            conn.sendall(struct.pack("<I", len(payload)) + payload)
        except OSError:
            pass


def live(server):
    """The window list in the shape the helper parses it."""
    return {wid: (BUNDLE, PID, ws) for wid, ws in server.windows.items()}


def main():
    tmpdir = tempfile.mkdtemp()
    sock_path = os.path.join(tmpdir, "aerospace.sock")

    # Point the helper at the fake server.
    awr.socket_path = lambda: sock_path

    server = FakeServer(sock_path)
    server.start()
    time.sleep(0.2)

    events = []
    awr.log = lambda message: events.append(message)

    tracker = awr.Tracker()
    print("test A: full flow through the real Tracker + client code")

    # 1. A window appears on workspace 2.
    server.windows[1000] = "2"
    server.emit({"_event": "window-detected", "windowId": 1000, "workspace": "2",
                 "appBundleId": "ru.keepcoder.Telegram", "appName": "Telegram"})
    time.sleep(0.2)
    tracker.window_detected(1000, "2")
    tracker.sync_windows(live(server))
    check("window tracked with origin 2", tracker.origin.get(1000) == "2")

    # 2. The auto-assign callback moves it to workspace 9.
    server.windows[1000] = "9"
    tracker.sync_windows(live(server))
    check("auto-move detected", tracker.auto_moved.get(1000) is True)

    # 3. The app is closed: the window disappears and macOS focuses the other app.
    del server.windows[1000]
    server.focused = "2"          # macOS focus went to the app on workspace 2
    tracker.sync_windows(live(server))
    check("return scheduled", tracker.pending_return is not None)
    if tracker.pending_return:
        check("origin is 2", tracker.pending_return[0] == "2")
        check("moved_to is 9", tracker.pending_return[1] == "9")

    # 4. AeroSpace bounces us back to the empty workspace 9.
    server.focused = "9"
    target = tracker.evaluate_return("9")
    check("helper switches back to 2 after the bounce", target == "2", "got %r" % target)

    print("test B: the client actually issues the workspace command")
    client = awr.AeroSpaceClient()
    client.command("workspace", "2")
    time.sleep(0.2)
    check("server received a workspace switch to 2", "2" in server.switches,
          "switches=%r" % server.switches)

    print("test C: helper does not switch when the user moved on purpose")
    server.switches = []
    server.windows[2000] = "2"
    server.emit({"_event": "window-detected", "windowId": 2000, "workspace": "2"})
    time.sleep(0.2)
    tracker.window_detected(2000, "2")
    server.windows[2000] = "9"
    tracker.sync_windows(live(server))
    del server.windows[2000]
    tracker.sync_windows(live(server))
    check("return scheduled", tracker.pending_return is not None)
    server.focused = "5"          # user deliberately went to workspace 5
    check("no switch when user is on 5", tracker.evaluate_return("5") is None)
    check("no switch command issued", server.switches == [], "switches=%r" % server.switches)

    print("test D: helper waits for the bounce when already home")
    server.switches = []
    server.windows[3000] = "2"
    server.emit({"_event": "window-detected", "windowId": 3000, "workspace": "2"})
    time.sleep(0.2)
    tracker.window_detected(3000, "2")
    server.windows[3000] = "9"
    tracker.sync_windows(live(server))
    del server.windows[3000]
    tracker.sync_windows(live(server))
    server.focused = "2"          # we are already home
    check("no immediate switch", tracker.evaluate_return("2") is None)
    server.focused = "9"          # now the bounce lands
    check("switch after the bounce", tracker.evaluate_return("9") == "2")

    print()
    if failures:
        print("%d FAILURE(S): %s" % (len(failures), ", ".join(failures)))
        return 1
    print("all integration tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
