"""Metamorphic oracle: manufacture a failing test out of the repository's own API vocabulary.

WHY THIS EXISTS
---------------
Every repair in the current catalogue is handed its specification: the commit ships the test, the
test names the getter and the mutator, and `spec_contract_synthesis_v1` mines the postcondition out of
it. That is why the memory ablation is null (see the round doc, V10/V12): the store competes with a
specification that is already in the prompt. On SWE-bench Pro / Terminal-Bench style tasks the hidden
test is *not* given, the visible suite is green, and a synthesizer has no selection gradient at all —
"the oracle that cannot choose".

This module derives an oracle from the repository itself, with no model and no sight of the hidden
test. The only assumption is the one the code already makes about itself: **a method's name is a
promise about its effect on observable state.**

    remove-like  (unregister, remove, discard, delete, pop, deregister, ...) with argument `x`
                 => after the call, no zero-argument getter on the same object may still yield `x`.
    add-like     (register, add, insert, append, put, attach, ...) with argument `x`
                 => after the call, at least one zero-argument getter on the same object yields `x`.

Both halves are checked around *every real call the passing suite already makes*, so the suite is used
as a source of concrete arguments — never as an oracle. The oracle is the name/effect law, and it
fires on code the suite accepts (which is exactly the blind case).

Measured acceptance (see the round doc): on a commit whose defect is a stale container, the buggy
parent violates the remove-law and the human fix does not, with the hidden test file absent from both.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
from typing import Any, Iterable, Mapping, Sequence

__all__ = [
    "REMOVE_VERBS",
    "ADD_VERBS",
    "GETTER_PREFIXES",
    "PluginRun",
    "violations_from_run",
    "classify_method",
]

# The vocabulary is deliberately small and universal: these verbs mean the same thing in every
# object-oriented code base in every language, which is what makes the law transferable.
REMOVE_VERBS = (
    "unregister", "deregister", "remove", "discard", "delete", "destroy", "unset", "detach",
    "unsubscribe", "unlink", "revoke", "forget", "pop", "clear", "purge", "drop",
)
ADD_VERBS = (
    "register", "add", "insert", "append", "put", "set_", "attach", "subscribe", "install",
    "push", "store", "assign", "bind", "connect", "enable", "mount", "create",
)
# The laws the plugin is allowed to run. Each names an observable, not a heuristic.
LAWS = (
    "remove_argument_vanishes",   # lifecycle: a removal must be visible through the getters
    "canonicality",               # a presented header/token string must be whitespace-clean
    "round_trip",                 # decode(encode(x)) == x
    "idempotence",                # normalize(normalize(x)) == normalize(x)
    "iterable_retyping",          # a generator is a list; a list without __reversed__ is still a list
    "error_discipline",           # a malformed value raises through the library's own hierarchy
    "assert_validation",          # a public function must not validate arguments with `assert`
)

GETTER_PREFIXES = (
    "get", "list", "iter", "all", "names", "items", "values", "keys", "has", "is", "contains",
    "count", "len", "size", "find", "fetch", "query", "lookup", "dump", "snapshot", "export",
)


def classify_method(name: str) -> str | None:
    """`remove` / `add` / `None`, from the method's own name. No AST, no types, no model."""
    if name.startswith("__"):
        return None
    for verb in REMOVE_VERBS:
        if name == verb or name.startswith(verb + "_") or name.startswith(verb):
            return "remove"
    for verb in ADD_VERBS:
        if name == verb or name.startswith(verb + "_") or name.startswith(verb):
            return "add"
    return None


def is_getter_name(name: str) -> bool:
    if name.startswith("__"):
        return False
    return any(name == p or name.startswith(p) for p in GETTER_PREFIXES)


_PLUGIN_SHIM = "from canonical.swe_kernel.metamorphic_plugin_v1 import *  # noqa: F401,F403\n"


class PluginRun(dict):
    """Result of one instrumented suite run (a dict, so it serialises without ceremony)."""

    @property
    def violations(self) -> list[dict[str, Any]]:
        return list(self.get("violations") or [])


def violations_from_run(
    project_root: pathlib.Path | str,
    targets: Sequence[str],
    pytest_args: Sequence[str],
    *,
    timeout_s: float = 900.0,
    max_calls: int = 20000,
    python: str | None = None,
    hints: Sequence[str] | None = None,
) -> PluginRun:
    """Run `pytest` in `project_root` with the name/effect law instrumented; return what it saw.

    The suite supplies concrete arguments; the *law* supplies the assertion. A violation is therefore
    a failing test the repository never wrote.
    """
    root = pathlib.Path(project_root)
    python = python or sys.executable
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="meta_oracle_", dir="/dev/shm" if pathlib.Path("/dev/shm").is_dir() else None))
    (tmp / "meta_oracle_plugin.py").write_text(_PLUGIN_SHIM, encoding="utf-8")
    out = tmp / "violations.json"
    env = dict(os.environ)
    brain_root = str(pathlib.Path(__file__).resolve().parents[2])
    env["PYTHONPATH"] = os.pathsep.join(
        [str(tmp), brain_root, str(root), str(root / "src"), env.get("PYTHONPATH", "")])
    env["META_TARGETS"] = ",".join(targets)
    env["META_OUT"] = str(out)
    env["META_MAX_CALLS"] = str(max_calls)
    env["META_REMOVE"] = ",".join(REMOVE_VERBS)
    env["META_ADD"] = ",".join(ADD_VERBS)
    env["META_GET"] = ",".join(GETTER_PREFIXES)
    env["META_LAWS"] = ",".join(LAWS)
    # Hints are the issue's own words. They let the oracle *construct* the object the issue is about
    # (werkzeug: "bearer" -> WWWAuthenticate("bearer")) instead of waiting for the suite to build it.
    env["META_HINTS"] = ",".join(dict.fromkeys(h for h in (hints or []) if h))[:600]
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cmd = [python, "-m", "pytest", "-p", "meta_oracle_plugin", "-p", "no:cacheprovider", *pytest_args]
    try:
        proc = subprocess.run(cmd, cwd=str(root), env=env, capture_output=True, text=True, timeout=timeout_s)
        tail = (proc.stdout or "")[-2000:]
    except subprocess.TimeoutExpired:
        return PluginRun(violations=[], raw_count=0, mutator_calls=0, wrapped_classes=[], timeout=True, tail="")
    if not out.is_file():
        return PluginRun(violations=[], raw_count=0, mutator_calls=0, wrapped_classes=[], tail=tail, collected=False)
    data = json.loads(out.read_text(encoding="utf-8"))
    data["tail"] = tail
    data["collected"] = True
    return PluginRun(data)


def main(argv: Iterable[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if len(argv) < 3:
        print("usage: metamorphic_oracle_v1.py <repo> <module[,module...]> <pytest args...>", file=sys.stderr)
        return 2
    repo, targets = argv[0], argv[1].split(",")
    run = violations_from_run(repo, targets, argv[2:])
    print(json.dumps({k: v for k, v in run.items() if k != "tail"}, indent=1, sort_keys=True))
    return 0 if not run.violations else 1


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
