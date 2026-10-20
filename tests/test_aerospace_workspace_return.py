#!/usr/bin/env python3
"""Unit tests for the Tracker logic in aerospace-workspace-return."""

import importlib.util
import os
import sys
import time

SRC = os.path.expanduser("~/Documents/Repos/dotfiles/bin/aerospace-workspace-return")

# A pid that is alive (this very process) and one that is guaranteed to be
# gone, so the liveness check can be tested both ways.
PID_ALIVE = os.getpid()
PID_DEAD = 999999
source = open(SRC).read().replace('if __name__ == "__main__":', "if False:")
awr = type(sys)("awr")
exec(compile(source, SRC, "exec"), awr.__dict__)

failures = []


def check(name, condition, detail=""):
    if condition:
        print("  PASS  %s" % name)
    else:
        print("  FAIL  %s %s" % (name, detail))
        failures.append(name)


print("test 1: auto-moved window closing schedules a return to origin")
t = awr.Tracker()
t.window_detected(100, "2")
t.sync_windows({100: ("app", 4242, "2")})
time.sleep(0.01)
t.sync_windows({100: ("app", 4242, "9")})          # auto-move to 9
check("auto-move recorded", t.auto_moved.get(100) is True)
t.sync_windows({})                    # window closed
check("return scheduled", t.pending_return is not None)
origin, moved_to, _deadline, _created = t.pending_return
check("origin is 2", origin == "2", "got %r" % origin)
check("moved_to is 9", moved_to == "9", "got %r" % moved_to)
check("returns 2 when on 9 (bounce)", t.evaluate_return("9") == "2")
check("pending cleared after return", t.pending_return is None)

print("test 2: window that never moved produces no return")
t = awr.Tracker()
t.window_detected(200, "3")
t.sync_windows({200: ("app", 4242, "3")})
t.sync_windows({})
check("no pending return", t.pending_return is None)
check("evaluate returns None", t.evaluate_return("3") is None)

print("test 3: manual move later is treated as a new origin, no return")
t = awr.Tracker()
t.window_detected(300, "2")
t.sync_windows({300: ("app", 4242, "2")})
t.detected_at[300] = time.monotonic() - 60   # simulate an old window
t.sync_windows({300: ("app", 4242, "5")})                    # moved by hand much later
check("not marked auto-moved", t.auto_moved.get(300) is False)
check("origin updated to 5", t.origin.get(300) == "5")
t.sync_windows({})
check("no pending return for manual move", t.pending_return is None)

print("test 4: user moved elsewhere on purpose -> return is dropped")
t = awr.Tracker()
t.window_detected(400, "2")
t.sync_windows({400: ("app", 4242, "2")})
t.sync_windows({400: ("app", 4242, "9")})
t.sync_windows({})
check("return scheduled", t.pending_return is not None)
check("no switch when user is on 7", t.evaluate_return("7") is None)
check("pending dropped", t.pending_return is None)

print("test 5: already on origin, pending return survives for the bounce")
t = awr.Tracker()
t.window_detected(500, "2")
t.sync_windows({500: ("app", 4242, "2")})
t.sync_windows({500: ("app", 4242, "9")})
t.sync_windows({})
check("return scheduled", t.pending_return is not None)
check("no switch while on origin 2", t.evaluate_return("2") is None)
check("pending still alive for the bounce", t.pending_return is not None)
check("switch back after bounce to 9", t.evaluate_return("9") == "2")

print("test 6: pending return expires if the bounce never comes")
t = awr.Tracker()
t.window_detected(600, "2")
t.sync_windows({600: ("app", 4242, "2")})
t.sync_windows({600: ("app", 4242, "9")})
t.sync_windows({})
t.pending_return = (t.pending_return[0], t.pending_return[1], time.monotonic() - 1, t.pending_return[3])
check("expired, no switch", t.evaluate_return("2") is None)
check("pending cleared on expiry", t.pending_return is None)

print("test 7: parse_windows handles the CLI output format")
parsed = awr.parse_windows(
    "24395 com.apple.finder 501 1\n"
    "22165 com.nousresearch.hermes 502 8\n"
    "24471 app.zen-browser.zen 503 2\n")
check("parsed 3 windows", len(parsed) == 3, "got %s" % (parsed,))
check("ids are ints", all(isinstance(k, int) for k in parsed), "got %s" % (parsed,))
check("bundle, pid and workspace kept",
      parsed[24471] == ("app.zen-browser.zen", 503, "2"), "got %s" % (parsed,))

print("test 8: poll sees the move BEFORE the detection event arrives")
t = awr.Tracker()
# The poll loop can observe the already-moved window before the
# window-detected event is drained from the queue.
t.sync_windows({700: ("app", 4242, "9")})          # poll first: window already on 9
t.window_detected(700, "2")         # then the event arrives, saying it started on 2
check("auto-move detected despite event ordering", t.auto_moved.get(700) is True,
      "auto_moved=%r" % t.auto_moved.get(700))
t.sync_windows({})                  # window closed
check("return scheduled", t.pending_return is not None)
if t.pending_return:
    check("origin is 2", t.pending_return[0] == "2")
    check("moved_to is 9", t.pending_return[1] == "9")
check("returns 2 when on 9", t.evaluate_return("9") == "2")

print("test 9: focus-changed event reports the new workspace")
t = awr.Tracker()
t.window_detected(800, "2")
t.window_focused(800, "9")          # focus event carries the moved workspace
check("auto-move recorded from focus event", t.auto_moved.get(800) is True)
t.sync_windows({})                  # closed
check("return scheduled", t.pending_return is not None)
check("returns 2 when on 9", t.evaluate_return("9") == "2")

print("test 10: focus event on an unrelated window does not disturb tracking")
t = awr.Tracker()
t.window_detected(900, "2")
t.window_focused(901, "5")          # some other window
check("origin of 900 untouched", t.origin.get(900) == "2")
check("not auto-moved", t.auto_moved.get(900) is False)

print("test 11: the bounce is detected from the empty-workspace focus event")
t = awr.Tracker()
t.window_detected(1000, "2")
t.sync_windows({1000: ("app", 4242, "2")})
t.sync_windows({1000: ("app", 4242, "9")})          # auto-move to 9
t.sync_windows({})                   # closed -> return to 2 scheduled
check("return scheduled", t.pending_return is not None)
check("bounce to 9 returns 2", t.bounce_target("9") == "2")
check("second bounce is a no-op", t.bounce_target("9") is None)

print("test 12: a switch to a different workspace is not a bounce")
t = awr.Tracker()
t.window_detected(1100, "2")
t.sync_windows({1100: ("app", 4242, "2")})
t.sync_windows({1100: ("app", 4242, "9")})
t.sync_windows({})
check("return scheduled", t.pending_return is not None)
check("switch to 5 is not a bounce", t.bounce_target("5") is None)
check("bounce to 9 still detected", t.bounce_target("9") == "2")

print("test 13: the bounce is caught before the poll notices the close")
# This is the fast path: the focus-changed event arrives with no window id
# (focus landed on an empty desk) before the 120ms poll has run, so the
# decision has to be made from the event alone.
t = awr.Tracker()
t.window_detected(1200, "2")
t.sync_windows({1200: ("app", 4242, "2")})
t.sync_windows({1200: ("app", 4242, "9")})          # auto-move to 9, poll noticed
check("poll has not seen the close yet", t.pending_return is None)
check("bounce to 9 returns 2 without waiting for the poll",
      t.bounce_target("9") == "2")

print("test 14: a workspace we never auto-moved to is not a bounce")
t = awr.Tracker()
t.window_detected(1300, "2")
t.sync_windows({1300: ("app", 4242, "2")})
check("bounce to 9 is not ours", t.bounce_target("9") is None)

print("test 15: a hand-moved window does not trigger a return")
t = awr.Tracker()
t.window_detected(1400, "2")
t.sync_windows({1400: ("app", 4242, "2")})
# Pretend it was detected long ago, so the move counts as manual.
t.detected_at[1400] = t.detected_at[1400] - 100
t.sync_windows({1400: ("app", 4242, "5")})
t.sync_windows({})
check("no return scheduled", t.pending_return is None)
check("bounce to 5 is not ours", t.bounce_target("5") is None)

print("test 16: a dying auto-moved window is rescued back to its origin")
# The rescue happens in the window where the app has quit but AeroSpace has
# not yet collected the window. Moving it back makes the bounce impossible.
t = awr.Tracker()
t.window_detected(1500, "2", "ru.keepcoder.Telegram")
t.sync_windows({1500: ("ru.keepcoder.Telegram", PID_ALIVE, "2")})
t.sync_windows({1500: ("ru.keepcoder.Telegram", PID_ALIVE, "9")})   # auto-moved to 9
check("the window is tracked", t.has_live_windows())
check("nothing to rescue while the app runs", t.dead_pids() == [],
      "got %s" % (t.dead_pids(),))
# The app quit (its pid is gone), but the window is still in AeroSpace's tree.
t.pid[1500] = PID_DEAD
check("the dying window is found", t.dead_pids() == [(1500, "2")],
      "got %s" % (t.dead_pids(),))
# Once rescued, it is not offered again.
t.mark_rescued(1500)
check("a rescued window is not offered again", t.dead_pids() == [],
      "got %s" % (t.dead_pids(),))

print("test 17: the focused workspace is tracked from the event stream")
t = awr.Tracker()
t.workspace_focused("3")
check("the focused workspace is known", t.focused_workspace_now() == "3",
      "got %r" % t.focused_workspace_now())

print("test 18: a window that was never auto-moved is not reported as dying")
t = awr.Tracker()
t.window_detected(1700, "2", "com.apple.finder")
t.sync_windows({1700: ("com.apple.finder", PID_ALIVE, "2")})
check("plain window has no auto move", t.dead_pids() == [],
      "got %s" % (t.dead_pids(),))

print("test 19: a rescued window does not schedule a return")
# The rescue moved the window back to its origin before AeroSpace collected
# it. The window therefore died on its origin desk, so there is no bounce
# and nothing to return to.
t = awr.Tracker()
t.window_detected(1800, "2", "ru.keepcoder.Telegram")
t.sync_windows({1800: ("ru.keepcoder.Telegram", PID_ALIVE, "2")})
t.sync_windows({1800: ("ru.keepcoder.Telegram", PID_ALIVE, "9")})   # auto-moved to 9
t.pid[1800] = PID_DEAD
t.mark_rescued(1800)
t.sync_windows({})                                                # the window is gone
check("no return is scheduled", t.pending_return is None,
      "got %s" % (t.pending_return,))

print("test 20: a window whose rescue failed still schedules the return")
t = awr.Tracker()
t.window_detected(1900, "2", "ru.keepcoder.Telegram")
t.sync_windows({1900: ("ru.keepcoder.Telegram", PID_ALIVE, "2")})
t.sync_windows({1900: ("ru.keepcoder.Telegram", PID_ALIVE, "9")})   # auto-moved to 9
t.pid[1900] = PID_DEAD
t.mark_rescue_failed(1900)
t.sync_windows({})                                                # the window is gone
check("the return is scheduled", t.pending_return is not None
      and t.pending_return[0] == "2",
      "got %s" % (t.pending_return,))

print("test 21: a failed rescue still leaves the bounce to be undone")
# If the rescue loses the race with AeroSpace's collection, the window is
# gone from the tree - but the bounce is still coming, so the return has to
# be scheduled for the event-driven correction to undo it.
t = awr.Tracker()
t.window_detected(1900, "2", "ru.keepcoder.Telegram")
t.sync_windows({1900: ("ru.keepcoder.Telegram", PID_ALIVE, "2")})
t.sync_windows({1900: ("ru.keepcoder.Telegram", PID_ALIVE, "9")})   # auto-moved to 9
t.pid[1900] = PID_DEAD
t.mark_rescued(1900)
t.mark_rescue_failed(1900)      # the move command failed
t.sync_windows({})              # AeroSpace collects the window
check("a return is scheduled", t.pending_return is not None)
check("the bounce can still be undone", t.bounce_target("9") == "2")

print("test 22: kqueue reports the exit of a process")
# The exit watcher is what makes the rescue timely: it fires the moment
# the app's process exits, without polling.
import subprocess
watcher = awr.ExitWatcher()
child = subprocess.Popen(["/bin/sh", "-c", "exit 0"])
watcher.watch(child.pid)
child.wait()
exited, _changed = watcher.wait(2.0)
check("the exit was reported", child.pid in exited,
      "got %s for pid %d" % (exited, child.pid))

print("test 23: a live process is not reported as exited")
watcher = awr.ExitWatcher()
watcher.watch(PID_ALIVE)
exited, _changed = watcher.wait(0.1)
check("nothing exited", exited == [],
      "got %s" % (exited,))
watcher.unwatch(PID_ALIVE)

print("test 24: a rescued window does not trigger a bounce correction")
# The window was moved home before AeroSpace collected it, so it died on its
# origin desk. Focus landing on the old desk later is not a bounce.
t = awr.Tracker()
t.window_detected(2000, "2", "ru.keepcoder.Telegram")
t.sync_windows({2000: ("ru.keepcoder.Telegram", PID_ALIVE, "2")})
t.sync_windows({2000: ("ru.keepcoder.Telegram", PID_ALIVE, "9")})
t.pid[2000] = PID_DEAD
t.mark_rescued(2000)
t.sync_windows({})
check("no bounce correction for a rescued window", t.bounce_target("9") is None,
      "got %r" % t.bounce_target("9"))

print("test 25: a closed window keeps its desk claimed only briefly")
# A desk that a window died on may receive focus once more, as the bounce.
# After that it must not hijack a deliberate switch.
t = awr.Tracker()
t.window_detected(2100, "2", "ru.keepcoder.Telegram")
t.sync_windows({2100: ("ru.keepcoder.Telegram", PID_ALIVE, "2")})
t.sync_windows({2100: ("ru.keepcoder.Telegram", PID_ALIVE, "9")})
t.sync_windows({})
check("the bounce is corrected", t.bounce_target("9") == "2")
t.window_detected(2200, "2", "ru.keepcoder.Telegram")
t.sync_windows({2200: ("ru.keepcoder.Telegram", PID_ALIVE, "2")})
t.sync_windows({2200: ("ru.keepcoder.Telegram", PID_ALIVE, "9")})
t.sync_windows({})
t.dead_auto_moves["9"] = ("2", time.monotonic() - 1)
check("a stale desk does not hijack a deliberate switch",
      t.bounce_target("9") is None, "got %r" % t.bounce_target("9"))

print()
if failures:
    print("%d FAILURE(S): %s" % (len(failures), ", ".join(failures)))
    sys.exit(1)
print("all tests passed")
