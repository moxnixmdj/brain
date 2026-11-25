"""Pytest plugin: run the law library around a repository's own green suite.

Loaded by `metamorphic_oracle_v1.violations_from_run` through a one-line shim on `PYTHONPATH`, so the
laws themselves live in `metamorphic_laws_v1` as ordinary, unit-testable Python.

Two instrumentation points, and no third:

* every public callable of the target modules is wrapped — module functions *and* class methods, so
  `click.core.Command.get_help_record` and `more_itertools.last` are covered as well as
  `PluginManager.unregister`;
* every instance created by the suite is retained (strongly: a test-local object is unreachable by
  teardown) and probed once at the end of the test that created it, which is how the lifecycle law
  manufactures the call the hidden test would have made.
"""

from __future__ import annotations

import importlib
import inspect
import json
import os
import sys
import traceback
from typing import Any

_STATE: dict[str, Any] = {
    "violations": [],
    "observed_calls": 0,
    "re_invocations": 0,
    "probes": 0,
    "skipped": 0,
    "wrapped": [],
    "laws_enabled": [],
}
_INSTANCES: list[Any] = []
_WRAPPED: list[tuple[Any, str]] = []
_IN_CHECK = [False]
_MAX_REINVOKE = 400
_MAX_PROBES = 4000


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


_TARGETS = [t for t in _env("META_TARGETS").split(",") if t]
_LAWS = {law for law in _env("META_LAWS").split(",") if law}
_REMOVE = tuple(v for v in _env("META_REMOVE").split(",") if v)
_GET = tuple(v for v in _env("META_GET").split(",") if v)
_OUT = _env("META_OUT")


def _laws():
    from canonical.swe_kernel import metamorphic_laws_v1 as laws

    return laws


def _want(law: str) -> bool:
    return law in _LAWS


def _record(violation: Any) -> None:
    if isinstance(violation, dict):
        _STATE["violations"].append(dict(violation))


def _budget(key: str, limit: int = 24) -> bool:
    if _STATE["re_invocations"] >= _MAX_REINVOKE:
        return False
    used = _STATE.setdefault("per_callable", {}).get(key, 0)
    if used >= limit:
        return False
    _STATE["per_callable"][key] = used + 1
    _STATE["re_invocations"] += 1
    return True


def _inverse_for(namespace: Any, name: str):
    laws = _laws()
    base = name.split(".")[-1]
    for forward, inverse in laws.PAIR_STEMS:
        if not (base == forward or base.startswith(forward + "_") or base.endswith("_" + forward)):
            continue
        for cand in (inverse, inverse + "s", inverse + "s_"):
            fn = getattr(namespace, cand, None)
            if callable(fn):
                return fn
        # a method pair on the same class: `to_json` / `from_json`
        for attr in dir(namespace):
            if attr == inverse or attr.endswith(inverse) or attr.startswith(inverse):
                fn = getattr(namespace, attr, None)
                if callable(fn) and attr != name:
                    return fn
    return None


def _check_call(namespace: Any, owner: str, name: str, fn: Any, args: tuple, kwargs: dict, result: Any,
                module_name: str) -> None:
    laws = _laws()
    qual = f"{owner}.{name}" if owner else name
    if _want("canonicality"):
        for violation in laws.check_canonicality(name, result):
            _record(violation)
    if _want("idempotence") and _budget("idem:" + qual):
        try:
            if result is not None:
                for violation in laws.check_idempotence(name, fn, args, result):
                    _record(violation)
        except Exception:
            pass
    if _want("round_trip") and args and _budget("rt:" + qual):
        inverse = _inverse_for(namespace, name)
        if inverse is not None:
            for violation in laws.check_round_trip(name, args, result, inverse):
                _record(violation)
    if _want("iterable_retyping") and _budget("it:" + qual, limit=12):
        try:
            for violation in laws.check_iterable_retyping(name, fn, args):
                _record(violation)
        except Exception:
            pass
    if _want("error_discipline") and args and _budget("err:" + qual, limit=12):
        errors = laws.package_error_classes(module_name, cache=_STATE.setdefault("errors", {}))
        if errors:
            outcomes: list[tuple[str, type | None]] = []
            for idx, label, mutated in laws.mutations_for(args):
                new_args = list(args)
                new_args[idx] = mutated
                try:
                    fn(*new_args, **kwargs)
                    outcomes.append((f"[{idx}]={label}", None))
                except BaseException as exc:  # noqa: BLE001 - the type *is* the observable
                    outcomes.append((f"[{idx}]={label}", type(exc)))
            for violation in laws.check_error_inconsistency(qual, module_name, outcomes, errors=errors):
                _record(violation)


def _make_wrapper(namespace: Any, owner: str, name: str, fn: Any, module_name: str):
    if getattr(fn, "__meta_wrapped__", False):
        return fn

    def wrapper(*a: Any, **k: Any) -> Any:
        if _IN_CHECK[0]:
            return fn(*a, **k)
        _IN_CHECK[0] = True
        try:
            _STATE["observed_calls"] += 1
            result = fn(*a, **k)
        finally:
            _IN_CHECK[0] = False
        try:
            _check_call(namespace, owner, name, fn, a, k, result, module_name)
        except Exception:
            _STATE["skipped"] += 1
        return result

    wrapper.__name__ = getattr(fn, "__name__", name)
    wrapper.__doc__ = getattr(fn, "__doc__", None)
    wrapper.__wrapped__ = fn
    wrapper.__meta_wrapped__ = True  # type: ignore[attr-defined]
    return wrapper


def _wrap_module(mod: Any) -> None:
    for attr_name in list(vars(mod)):
        attr = vars(mod)[attr_name]
        if inspect.isfunction(attr) and getattr(attr, "__module__", None) == mod.__name__:
            if attr_name.startswith("_"):
                continue
            try:
                setattr(mod, attr_name, _make_wrapper(mod, "", attr_name, attr, mod.__name__))
                _WRAPPED.append((mod, attr_name))
            except Exception:
                pass
    for cls_name in list(vars(mod)):
        cls = vars(mod)[cls_name]
        if not inspect.isclass(cls) or getattr(cls, "__module__", None) != mod.__name__:
            continue
        for meth_name in list(vars(cls)):
            meth = vars(cls)[meth_name]
            if not callable(meth) or isinstance(meth, (staticmethod, classmethod)):
                continue
            # `__str__` is where a header value is actually produced; skipping every dunder made the
            # canonicality law blind to exactly the objects it was written for.
            if meth_name.startswith("__") and meth_name not in {"__str__", "__repr__", "__bytes__"}:
                continue
            try:
                setattr(cls, meth_name, _make_wrapper(cls, cls_name, meth_name, meth, mod.__name__))
                _WRAPPED.append((cls, meth_name))
            except Exception:
                pass
        init = cls.__dict__.get("__init__")
        if callable(init) and not getattr(init, "__meta_wrapped__", False):
            def make_init(f):
                def wrapper(self, *a, **k):
                    f(self, *a, **k)
                    if len(_INSTANCES) < 5000:
                        _INSTANCES.append(self)
                wrapper.__wrapped__ = f
                wrapper.__meta_wrapped__ = True  # type: ignore[attr-defined]
                return wrapper
            try:
                cls.__init__ = make_init(init)
            except Exception:
                pass
    _STATE["wrapped"].append(mod.__name__)


# ---------------------------------------------------------------- lifecycle probing (teardown) -- #


def _is_getter(name: str) -> bool:
    return not name.startswith("__") and any(name == g or name.startswith(g) for g in _GET if g)


def _yields(container: Any, needle: Any) -> bool:
    if isinstance(container, dict):
        items = list(container.keys()) + list(container.values())
    else:
        try:
            items = list(container)
        except TypeError:
            return container is needle
    for item in items:
        if item is needle:
            return True
        if isinstance(item, (tuple, list)):
            if any(inner is needle for inner in item):
                return True
        if isinstance(item, dict):
            if any(key is needle or val is needle for key, val in item.items()):
                return True
    return False


def _candidates(val: Any) -> list[Any]:
    if isinstance(val, dict):
        items = list(val.keys()) + list(val.values())
    else:
        try:
            items = list(val)
        except TypeError:
            return []
    out: list[Any] = []
    for item in items:
        head = item[0] if isinstance(item, (tuple, list)) and item else item
        if not isinstance(head, (str, bytes, int, float, bool, type(None))):
            out.append(head)
    return out


def _remove_methods(cls: type) -> dict[str, str]:
    found: dict[str, str] = {}
    for name in dir(cls):
        if name.startswith("__"):
            continue
        verb = next((v for v in _REMOVE if name == v or name.startswith(v)), None)
        if verb is None:
            continue
        fn = getattr(cls, name, None)
        if not callable(fn):
            continue
        try:
            sig = inspect.signature(fn)
        except (TypeError, ValueError):
            continue
        params = [p for p in sig.parameters.values()
                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) and p.name != "self"]
        if not params:
            continue
        found[name] = verb
    return found


def _snapshot(obj: Any, getters: list[str]) -> dict[str, Any]:
    snap: dict[str, Any] = {}
    for g in getters:
        try:
            snap[g] = getattr(obj, g)()
        except Exception:
            snap[g] = None
    return snap


def _probe(inst: Any) -> None:
    cls = type(inst)
    getters = [n for n in dir(cls) if _is_getter(n) and callable(getattr(cls, n, None))]
    if not getters:
        return
    for name in _remove_methods(cls):
        if _STATE["probes"] >= _MAX_PROBES:
            return
        before = _snapshot(inst, getters)
        for gate, val in before.items():
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
                for gate2, val2 in after.items():
                    if val2 is not None and _yields(val2, cand):
                        _record({
                            "law": "remove_argument_vanishes",
                            "where": f"{cls.__name__}.{name}",
                            "detail": f"{cand!r} still yielded by {gate2}",
                            "getter": gate2,
                        })
                return


# ---------------------------------------------------------------------------- pytest hooks -- #


def pytest_configure(config) -> None:
    _STATE["laws_enabled"] = sorted(_LAWS)
    for modname in _TARGETS:
        try:
            mod = importlib.import_module(modname)
        except Exception:
            _STATE.setdefault("import_errors", []).append(modname)
            continue
        _wrap_module(mod)


def pytest_runtest_teardown(item, nextitem) -> None:
    prefixes = [t.split(".")[0] for t in _TARGETS]
    live = [obj for obj in _INSTANCES if type(obj).__module__.split(".")[0] in prefixes]
    _INSTANCES[:] = []
    for obj in live:
        try:
            _probe(obj)
        except Exception:
            _STATE["skipped"] += 1


def pytest_sessionfinish(session, exitstatus) -> None:
    if not _OUT:
        return
    seen: set[tuple] = set()
    unique: list[dict] = []
    for v in _STATE["violations"]:
        key = (v.get("law"), v.get("where"), v.get("detail"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(v)
    payload = {
        "violations": unique,
        "raw_count": len(_STATE["violations"]),
        "observed_calls": _STATE["observed_calls"],
        "re_invocations": _STATE["re_invocations"],
        "probes": _STATE["probes"],
        "skipped": _STATE["skipped"],
        "wrapped": _STATE["wrapped"],
        "laws_enabled": _STATE["laws_enabled"],
        "import_errors": _STATE.get("import_errors", []),
        "exitstatus": int(exitstatus),
        "laws": sorted({v.get("law", "?") for v in unique}),
    }
    with open(_OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, default=repr)


def pytest_exception_interact(node, call, report) -> None:  # pragma: no cover - diagnostics only
    if os.environ.get("META_TRACE"):
        sys.stderr.write("".join(traceback.format_exception(call.excinfo.type, call.excinfo.value, call.excinfo.tb))[:2000])
