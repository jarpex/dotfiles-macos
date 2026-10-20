#!/usr/bin/env python3
"""
End-to-end test of the complete aerospace-workspace-return daemon.

Runs the helper's real main() loop as a subprocess against a fake AeroSpace
server. The server plays the part of AeroSpace: it reports a window, moves it
to another workspace, then the app dies - and we assert the helper moves the
window back to the origin workspace before the server collects it.

The app is a real child process, because the helper watches the process with
kqueue. A fake pid would never exit, so the rescue would never fire.

Usage: python3 test_daemon_e2e.py
"""

import json
import os
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time

PROTOCOL = 1
SRC = os.path.expanduser("~/Documents/Repos/dotfiles/bin/aerospace-workspace-return")
BUNDLE = "ru.keepcoder.Telegram"


def check(name, condition, detail=""):
    if condition:
        print("  PASS  %s" % name)
    else:
        print("  FAIL  %s %s" % (name, detail))
        return 1
    return 0


class FakeServer(threading.Thread):
    def __init__(self, path):
        threading.Thread.__init__(self, daemon=True)
        self.path = path
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.listener.bind(path)
        self.listener.listen(8)
        self.windows = {}
        self.pid = 0
        self.focused = "2"
        self.switches = []
        self.commands = []
        self.subscriber = None
        self.lock = threading.Lock()

    def run(self):
        while True:
            try:
                conn, _ = self.listener.accept()
            except OSError:
                return
            threading.Thread(target=self.handle, args=(conn,), daemon=True).start()

    def handle(self, conn):
        try:
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
            return {"exitCode": 1, "stdout": "", "stderr": ""}
        name = args[0]
        with self.lock:
            self.commands.append(list(args))
            if name == "list-windows":
                out = ""
                if self.pid is not None:
                    out = "".join("%d %s %d %s\n" % (wid, BUNDLE, self.pid, ws)
                                  for wid, ws in self.windows.items())
            elif name == "move-node-to-workspace":
                target = args[-1]
                wid = None
                for index, arg in enumerate(args):
                    if arg == "--window-id":
                        wid = int(args[index + 1])
                if wid is None or wid not in self.windows:
                    # AeroSpace cannot move a window it has already collected.
                    return {"exitCode": 1, "stdout": "",
                            "stderr": "window not found"}
                self.windows[wid] = target
                out = ""
            elif name == "workspace":
                self.switches.append(args[1])
                self.focused = args[1]
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


def main():
    tmpdir = tempfile.mkdtemp()
    sock_path = os.path.join(tmpdir, "aerospace.sock")
    log_path = os.path.join(tmpdir, "helper.log")
    lock_path = os.path.join(tmpdir, "helper.lock")

    server = FakeServer(sock_path)
    server.start()
    time.sleep(0.2)

    # The helper hardcodes the socket path, so we patch it at import time by
    # running a small wrapper that overrides socket_path before main() runs.
    wrapper = os.path.join(tmpdir, "wrapper.py")
    with open(wrapper, "w") as handle:
        handle.write(
            "import sys, runpy\n"
            "src = open(%r).read().replace('if __name__ == \"__main__\":', 'if False:')\n"
            "mod = type(sys)('awr')\n"
            "exec(compile(src, 'awr', 'exec'), mod.__dict__)\n"
            "mod.socket_path = lambda: %r\n"
            "mod.main()\n" % (SRC, sock_path)
        )

    env = dict(os.environ)
    env["AEROSPACE_RETURN_LOG"] = log_path
    env["AEROSPACE_RETURN_LOCK"] = lock_path
    proc = subprocess.Popen([sys.executable, wrapper], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(1.5)

    failures = 0
    app = None
    try:
        if proc.poll() is not None:
            out, err = proc.communicate()
            print("  FAIL  helper exited early: %s %s" % (out.decode(), err.decode()))
            return 1
        print("  PASS  helper daemon started and stayed running")

        # 1. A Telegram window appears on workspace 2. The app is a real
        #    process, so the helper can watch it with kqueue.
        app = subprocess.Popen(["/bin/sh", "-c", "sleep 30"])
        server.pid = app.pid
        server.windows[5000] = "2"
        server.emit({"_event": "window-detected", "windowId": 5000, "workspace": "2",
                     "appBundleId": BUNDLE, "appName": "Telegram"})
        time.sleep(0.6)

        # 2. The auto-assign callback moves it to workspace 9.
        server.windows[5000] = "9"
        server.emit({"_event": "focus-changed", "windowId": 5000, "workspace": "9"})
        time.sleep(0.6)

        # 3. The app quits. AeroSpace has not collected the window yet - it
        #    is still in the tree - so the helper can rescue it by moving it
        #    back to its origin. That makes AeroSpace's own focus restore a
        #    no-op, so the bounce never happens.
        app.kill()
        app.wait()
        time.sleep(0.4)

        # 4. AeroSpace finally collects the window.
        del server.windows[5000]
        server.emit({"_event": "focus-changed", "windowId": 4999, "workspace": "2"})
        server.emit({"_event": "focused-workspace-changed", "prevWorkspace": "9", "workspace": "2"})
        time.sleep(0.6)

        failures += check("helper rescued the dying window back to its origin",
                          any(a[0] == "move-node-to-workspace" and a[-1] == "2"
                              for a in server.commands),
                          "commands=%r" % (server.commands,))
        failures += check("helper did not bounce the focus",
                          "9" not in server.switches,
                          "switches=%r" % (server.switches,))
        failures += check("focus stayed on the origin workspace",
                          server.focused == "2",
                          "focused=%r" % server.focused)

        # 5. A second instance must not start, or the load on AeroSpace
        #    doubles.
        second = subprocess.Popen([sys.executable, wrapper], env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(1.0)
        failures += check("a second instance refuses to run",
                          second.poll() is not None,
                          "second instance is still running")
        if second.poll() is None:
            second.kill()
    finally:
        if app is not None and app.poll() is None:
            app.kill()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    print()
    if failures:
        print("%d FAILURE(S)" % failures)
        return 1
    print("daemon end-to-end test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
