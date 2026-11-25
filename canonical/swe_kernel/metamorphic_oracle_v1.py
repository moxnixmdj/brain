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


_PLUGIN = textwrap.dedent(
    '''
    """Injected pytest plugin: manufacture the failing test the repository never wrote.

    Two sources of evidence, in increasing power:

    1. Observation — every mutator call the passing suite makes is checked against the name/effect law.
       Measured on pluggy: 332 mutator calls, and `unregister` is not among them, because the only
       caller of `unregister` in that repository is the very test that is hidden. Observation alone
       therefore cannot see the defect.
    2. Probing — at each test's teardown (objects alive, fixtures not yet torn down) the getters are
       read, one element is taken out of them, and the remove-verb is *called with that element*. The
       law then says it must vanish. This manufactures the missing call instead of waiting for it.
    """

    import inspect
    import json
    import os
    import weakref

    _STATE = {
        "violations": [], "probes": 0, "observed_calls": 0, "skipped": 0,
        "wrapped_classes": [], "remove_methods_seen": {}, "getters_seen": {},
    }
    _TARGETS = [t for t in os.environ.get("META_TARGETS", "").split(",") if t]
    _OUT = os.environ.get("META_OUT", "")
    _MAX_PROBES = int(os.environ.get("META_MAX_PROBES", "4000"))
    _REMOVE = tuple(v for v in os.environ.get("META_REMOVE", "").split(",") if v)
    _GET = tuple(v for v in os.environ.get("META_GET", "").split(",") if v)
    _INSTANCES = []
    _CLASSES = []

    def _kind(name):
        if name.startswith("__"):
            return None
        for v in _REMOVE:
            if name == v or name.startswith(v):
                return v
        return None

    def _is_getter(name):
        return not name.startswith("__") and any(name == g or name.startswith(g) for g in _GET)

    def _yields(container, needle):
        try:
            items = list(container)
        except TypeError:
            return container is needle
        for item in items:
            if item is needle:
                return True
            if isinstance(item, (tuple, list)):
                for inner in item:
                    if inner is needle:
                        return True
            if isinstance(item, dict):
                for key, val in item.items():
                    if key is needle or val is needle:
                        return True
        return False

    def _snapshot(obj, getters):
        snap = {}
        for g in getters:
            try:
                snap[g] = getattr(obj, g)()
            except Exception:
                snap[g] = None
        return snap

    def _candidates(val):
        """Elements of a getter result that are objects the mutator could plausibly take.

        A getter commonly hands back a mapping (`get_plugins() -> {name: plugin}`); iterating it yields
        the *keys*, which are strings and therefore invisible to the law. Values are the objects.
        """
        out = []
        if isinstance(val, dict):
            items = list(val.keys()) + list(val.values())
        else:
            try:
                items = list(val)
            except TypeError:
                return out
        for item in items:
            if isinstance(item, (tuple, list)) and item:
                head = item[0]
                if not isinstance(head, (str, bytes, int, float, bool, type(None))):
                    out.append(head)
            elif not isinstance(item, (str, bytes, int, float, bool, type(None))):
                out.append(item)
        return out

    def _probe(inst):
        cls = type(inst)
        getters = [n for n in dir(cls) if _is_getter(n) and callable(getattr(cls, n, None))]
        if not getters:
            return
        for name, verb in _remove_methods(cls).items():
            if _STATE["probes"] >= _MAX_PROBES:
                return
            before = _snapshot(inst, getters)
            for g, val in before.items():
                if val is None:
                    continue
                for cand in _candidates(val)[:3]:
                    if _STATE["probes"] >= _MAX_PROBES:
                        return
                    _STATE["probes"] += 1
                    try:
                        getattr(inst, name)(cand)
                    except Exception:
                        _STATE["skipped"] += 1
                        continue
                    after = _snapshot(inst, getters)
                    for g2, val2 in after.items():
                        if val2 is not None and _yields(val2, cand):
                            _STATE["violations"].append({
                                "law": "remove_argument_vanishes",
                                "method": cls.__name__ + "." + name,
                                "getter": g2,
                                "verb": verb,
                            })
                    return  # one manufactured call per method per object is enough to judge it

    def _remove_methods(cls):
        found = {}
        for name in dir(cls):
            verb = _kind(name)
            if verb is None:
                continue
            fn = getattr(cls, name, None)
            if not callable(fn):
                continue
            try:
                sig = inspect.signature(fn)
            except (TypeError, ValueError):
                continue
            params = [p for p in sig.parameters.values() if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
            # At least one positional parameter besides `self`. `unregister(self, plugin=None,
            # name=None)` in pluggy@50585e0^1 has two, both defaulted, and is still a one-argument
            # mutator when called as `unregister(plugin)`; requiring exactly one hid it completely.
            args = [p for p in params if p.name != "self"]
            if not args:
                continue
            found[name] = verb
        return found

    def _wrap_class(cls):
        if cls in _CLASSES:
            return False
        _CLASSES.append(cls)
        init = cls.__dict__.get("__init__")
        if init is not None and callable(init):
            def make_init(f):
                def wrapper(self, *a, **k):
                    f(self, *a, **k)
                    # A *strong* reference on purpose: a test-local registry is unreachable by the
                    # time teardown runs, and a weakref would silently drop exactly the objects the
                    # oracle exists to probe. Capped so a long suite cannot grow without bound.
                    if len(_INSTANCES) < 5000:
                        _INSTANCES.append(self)
                wrapper.__name__ = getattr(f, "__name__", "__init__")
                return wrapper
            try:
                cls.__init__ = make_init(init)
            except Exception:
                pass
        getters = [n for n in dir(cls) if _is_getter(n)]
        removers = _remove_methods(cls)
        if not getters or not removers:
            return False
        for name, verb in removers.items():
            _STATE["remove_methods_seen"][cls.__name__ + "." + name] = verb
            fn = getattr(cls, name)
            if not callable(fn):
                continue

            def make(f, name, verb, getters):
                def wrapper(self, *a, **k):
                    if _STATE["observed_calls"] >= 20000:
                        return f(self, *a, **k)
                    _STATE["observed_calls"] += 1
                    before = _snapshot(self, getters)
                    result = f(self, *a, **k)
                    after = _snapshot(self, getters)
                    if a:
                        target = a[0]
                        for g in getters:
                            b, af = before.get(g), after.get(g)
                            if b is None or af is None:
                                continue
                            if _yields(b, target) and _yields(af, target):
                                _STATE["violations"].append({
                                    "law": "remove_argument_vanishes",
                                    "method": type(self).__name__ + "." + name,
                                    "getter": g, "verb": verb,
                                })
                    return result
                wrapper.__name__ = getattr(f, "__name__", name)
                wrapper.__wrapped__ = f   # `inspect.signature` follows this; without it the probe
                return wrapper            # recomputes arity on the wrapper and sees (*a, **k)
            try:
                setattr(cls, name, make(vars(cls)[name] if name in vars(cls) else fn, name, verb, getters))
            except Exception:
                pass
        _STATE["getters_seen"][cls.__name__] = len(getters)
        _STATE["wrapped_classes"].append(cls.__module__ + "." + cls.__name__)
        return True

    def pytest_configure(config):
        import importlib
        for modname in _TARGETS:
            try:
                mod = importlib.import_module(modname)
            except Exception:
                continue
            for attr in list(vars(mod).values()):
                if inspect.isclass(attr) and getattr(attr, "__module__", None) == modname:
                    _wrap_class(attr)

    def pytest_runtest_teardown(item, nextitem):
        live = []
        prefixes = [t.split(".")[0] for t in _TARGETS]
        for obj in _INSTANCES:
            if type(obj).__module__.split(".")[0] in prefixes:
                live.append(obj)
        _INSTANCES[:] = []
        for obj in live:
            try:
                _probe(obj)
            except Exception:
                continue

    def pytest_sessionfinish(session, exitstatus):
        if not _OUT:
            return
        seen = set()
        unique = []
        for v in _STATE["violations"]:
            key = (v["law"], v["method"], v["getter"])
            if key in seen:
                continue
            seen.add(key)
            unique.append(v)
        with open(_OUT, "w", encoding="utf-8") as fh:
            json.dump({
                "violations": unique,
                "raw_count": len(_STATE["violations"]),
                "probes": _STATE["probes"],
                "skipped_calls": _STATE["skipped"],
                "observed_mutator_calls": _STATE["observed_calls"],
                "wrapped_classes": _STATE["wrapped_classes"],
                "remove_methods": _STATE["remove_methods_seen"],
                "exitstatus": int(exitstatus),
            }, fh, indent=1)
    '''
)


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
) -> PluginRun:
    """Run `pytest` in `project_root` with the name/effect law instrumented; return what it saw.

    The suite supplies concrete arguments; the *law* supplies the assertion. A violation is therefore
    a failing test the repository never wrote.
    """
    root = pathlib.Path(project_root)
    python = python or sys.executable
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="meta_oracle_", dir="/dev/shm" if pathlib.Path("/dev/shm").is_dir() else None))
    (tmp / "meta_oracle_plugin.py").write_text(_PLUGIN, encoding="utf-8")
    out = tmp / "violations.json"
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(tmp), str(root), str(root / "src"), env.get("PYTHONPATH", "")])
    env["META_TARGETS"] = ",".join(targets)
    env["META_OUT"] = str(out)
    env["META_MAX_CALLS"] = str(max_calls)
    env["META_REMOVE"] = ",".join(REMOVE_VERBS)
    env["META_ADD"] = ",".join(ADD_VERBS)
    env["META_GET"] = ",".join(GETTER_PREFIXES)
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
