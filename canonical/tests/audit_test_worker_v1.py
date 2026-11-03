"""Isolate no-execution tests without replacing standard-library functions.

CPython audit hooks are permanent, so each observed test runs in a real child
interpreter. A hook records and rejects audited process operations; callers can
also reject dynamic execution. A separate negative control exercises real APIs
and checks their audit events are rejected before they perform work.

This observes Python audit events, not arbitrary native calls: the adapter tests
also independently inspect their source for native/process imports and calls.
"""
from __future__ import annotations

import builtins
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

PROCESS_EVENTS = frozenset({
    "subprocess.Popen", "os.system", "os.fork", "os.forkpty", "os.exec",
    "os.spawn", "os.posix_spawn",
})


def run_isolated(path: str, name: str, *, block_exec: bool = False) -> None:
    command = [sys.executable, "-B", str(Path(path).resolve()), "--audit-worker", name]
    if block_exec:
        command.append("--block-exec")
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise AssertionError("isolated audit test failed: %s\n%s\n%s" %
                             (name, result.stdout, result.stderr))


def dispatch(namespace: dict, arguments: list[str]) -> bool:
    """Run an audited worker or control, returning False for normal execution."""
    if len(arguments) < 3 or arguments[1] != "--audit-worker":
        return False
    name = arguments[2]
    # tempfile lazily imports its random-name machinery. Load it before arming
    # the optional dynamic-code hook, so import startup is not mistaken for work.
    tempfile.gettempdir()
    next(tempfile._get_candidate_names())
    control_code = compile("pass", "<audit-control>", "exec")
    events = []
    blocked = PROCESS_EVENTS | ({"exec"} if "--block-exec" in arguments else set())

    def audit(event: str, _args: tuple) -> None:
        if event in blocked:
            events.append(event)
            raise AssertionError("FORBIDDEN_AUDIT_EVENT:" + event)

    sys.addaudithook(audit)
    if name == "--control":
        controls: list[tuple[str, Callable[[], object]]] = [
            ("subprocess.Popen", lambda: subprocess.run([sys.executable, "-c", "pass"])),
            ("os.system", lambda: os.system("true")),
            ("os.exec", lambda: os.execv(sys.executable, [sys.executable])),
        ]
        if hasattr(os, "fork"):
            controls.append(("os.fork", lambda: os.fork()))
        if hasattr(os, "posix_spawn"):
            controls.append(("os.posix_spawn", lambda: os.posix_spawn(sys.executable, [sys.executable], {})))
        if "exec" in blocked:
            controls.append(("exec", lambda: builtins.exec(control_code, {})))
        for expected, call in controls:
            try:
                call()
            except AssertionError as exc:
                if str(exc) != "FORBIDDEN_AUDIT_EVENT:" + expected:
                    raise
            else:
                raise AssertionError("AUDIT_CONTROL_DID_NOT_BLOCK:" + expected)
        if events != [name for name, _call in controls]:
            raise AssertionError("AUDIT_CONTROL_EVENTS:" + repr(events))
    else:
        namespace[name]()
        if events:
            raise AssertionError("FORBIDDEN_AUDIT_EVENTS:" + repr(events))
    return True
