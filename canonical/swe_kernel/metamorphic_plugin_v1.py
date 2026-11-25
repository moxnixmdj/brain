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
import copy
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
    "law_errors": [],
}
_INSTANCES: list[Any] = []
_WRAPPED: list[tuple[Any, str]] = []
_IN_CHECK = [False]
_MAX_REINVOKE = 1500  # per law, not global
_MAX_PROBES = 4000
_TRACE = bool(__import__("os").environ.get("META_TRACE"))


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


_TARGETS = [t for t in _env("META_TARGETS").split(",") if t]
_LAWS = {law for law in _env("META_LAWS").split(",") if law}
_REMOVE = tuple(v for v in _env("META_REMOVE").split(",") if v)
_GET = tuple(v for v in _env("META_GET").split(",") if v)
_OUT = _env("META_OUT")
_HINTS = [h for h in _env("META_HINTS").split(",") if h]


def _laws():
    from canonical.swe_kernel import metamorphic_laws_v1 as laws

    return laws


def _want(law: str) -> bool:
    return law in _LAWS


def _record(violation: Any) -> None:
    if isinstance(violation, dict):
        _STATE["violations"].append(dict(violation))


def _replay(args: tuple) -> tuple | None:
    """Deep-copied arguments for any law that calls the function again, or None if not replayable.

    Two refusals, both measured:

    1. Re-invoking with the suite's own objects is not observation, it is mutation. more-itertools'
       tests hand live buffers to `prepend`-shaped methods, and building the mutated call from the live
       args let `prepend("not-a-number")` land on the suite's instance and broke 14 tests.
    2. A live iterator cannot be replayed *even after copying*, because the copy captures what is
       **left** of the stream. `all_unique(prepend(3, count()))` is answered at the duplicate `3`; the
       copy then holds `4, 5, 6, ...` with no duplicate in it, so the re-invocation never terminates and
       the run is OOM-killed (exit -9). Deepcopy of an `itertools.chain` succeeds, which is exactly why
       "copy it and hope" is not enough: the danger is the unbounded remainder, not the copy.
    """
    for value in args:
        if hasattr(value, "__next__") and not hasattr(value, "__len__"):
            return None
    try:
        copies = copy.deepcopy(list(args))
    except Exception:
        return None
    return tuple(copies)


def _quiet(thunk):
    """Run a law's re-invocations with their own warning machinery.

    Re-invoking a function is observation of its *value*, not of its warnings, but Python's warning
    registry is one-shot per location: pyjwt's `test_decode_complete_warns_on_...` failed because an
    earlier re-invocation had already consumed the emission the test was waiting for. A private
    `catch_warnings` block gives the law its own recorder and leaves the suite's warnings untouched.
    """
    import warnings

    with warnings.catch_warnings(record=True):
        # `record=True` is the part that matters: without it the nested block only changes *filters*, the
        # outer handler still receives the emission, and pyjwt's `assert len(deprecation_warnings) == 1`
        # saw 3 because the law's re-invocations were being recorded by the test's own `pytest.warns`.
        warnings.simplefilter("always")
        return thunk()


def _arg_sig(args: tuple) -> str:
    """A cheap structural signature of a call's arguments.

    Budgeting by function name alone starves a law on the informative call: more-itertools' suite calls
    `last()` more than twelve times, nearly all on an empty list (asserting `ValueError`), and the one
    call carrying a real element was never examined. Budgeting by shape keeps one bucket per shape.
    """
    parts: list[str] = []
    for value in args[:2]:
        if isinstance(value, (list, tuple, set, frozenset, dict, str, bytes)):
            parts.append(f"{type(value).__name__}[{len(value)}]")
        else:
            parts.append(type(value).__name__)
    return "|".join(parts)


def _budget(key: str, limit: int = 24) -> bool:
    """Charge one re-invocation to `key`, capped per key and per law.

    Per *law* because the pool is finite and shared: with one global cap, `canonicality` and
    `idempotence` spending it on the first few hundred hot calls starved `iterable_retyping` entirely,
    and the more-itertools defect was invisible even though the law fires on a direct call.
    """
    pool = key.split(":", 1)[0]
    pools = _STATE.setdefault("per_law", {})
    if pools.get(pool, 0) >= _MAX_REINVOKE:
        return False
    used = _STATE.setdefault("per_callable", {}).get(key, 0)
    if used >= limit:
        return False
    _STATE["per_callable"][key] = used + 1
    pools[pool] = pools.get(pool, 0) + 1
    _STATE["re_invocations"] += 1
    return True


def _inverse_for(namespace: Any, name: str):
    laws = _laws()
    base = name.split(".")[-1]
    # Both directions: a parser is as often the *inverse* of a serializer (`decode` next to `encode`),
    # and the content law needs the encoder to re-sign what it mutated.
    both = tuple(laws.PAIR_STEMS) + tuple((b, a) for a, b in laws.PAIR_STEMS)
    for forward, inverse in both:
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
    replay = _replay(args)
    if _want("canonicality"):
        for violation in laws.check_canonicality(name, result):
            _record(violation)
    if _want("idempotence") and _budget("idem:" + qual):
        try:
            if result is not None and replay is not None:
                for violation in _quiet(lambda: laws.check_idempotence(name, fn, replay, result)):
                    _record(violation)
        except Exception as exc:
            _STATE["law_errors"].append(f"idempotence:{name}:{type(exc).__name__}")
    if _want("round_trip") and args and _budget("rt:" + qual):
        inverse = _inverse_for(namespace, name)
        if inverse is not None and replay is not None:
            for violation in _quiet(lambda: laws.check_round_trip(name, replay, result, inverse)):
                _record(violation)
    # Retyping arguments is a statement about *data*, not about a receiver: substituting `self` with a
    # retyped shell made `__repr__` "raise" on the healthy tree (AttributeError on the shell). The law
    # therefore applies to module-level functions, where every argument is data.
    if _want("iterable_retyping") and not owner and _budget(f"it:{qual}:{_arg_sig(args)}", limit=3):
        try:
            for violation in _quiet(lambda: laws.check_iterable_retyping(name, fn, replay if replay is not None else ())):
                _record(violation)
        except Exception as exc:
            _STATE["law_errors"].append(f"iterable_retyping:{name}:{type(exc).__name__}")
    if _want("content_retyping") and args and result is not None and _budget("cr:" + qual, limit=40):
        # The mutation goes inside the parsed content, so the parser's own inverse has to put it back into
        # a document the parser will accept; without that the signature check answers first and the claim
        # is never read (measured: mutating the payload text alone raises InvalidSignatureError).
        inverse = _inverse_for(namespace, name)
        errors = laws.package_error_classes(module_name, cache=_STATE.setdefault("errors", {}))
        offset = 1 if owner else 0
        if inverse is not None and errors and len(args) > offset and isinstance(args[offset], str):
            head, tail = tuple(args)[:offset], tuple(args)[offset + 1:]
            recall = lambda document: fn(*head, document, *tail, **kwargs)  # noqa: E731
            encode = lambda mutated: inverse(*head, mutated, *tail[:1])  # noqa: E731
            try:
                for violation in _quiet(lambda: laws.check_content_retyping(
                        name, recall, encode, result, errors,
                        package=module_name.split(".")[0])):
                    violation["where"] = qual
                    _record(violation)
            except Exception as exc:
                _STATE["law_errors"].append(f"content_retyping:{name}:{type(exc).__name__}")
    if _want("error_discipline") and args and _budget("err:" + qual, limit=12):
        errors = laws.package_error_classes(module_name, cache=_STATE.setdefault("errors", {}))
        if errors:
            outcomes: list[tuple[str, type | None]] = []
            for idx, label, mutated in laws.mutations_for(replay or ()):
                # Must be the *copies*: building new_args from the live args let
                # `prepend("not-a-number")` land on the suite's own instance and broke 14 tests.
                new_args = list(replay or ())
                new_args[idx] = mutated
                try:
                    _quiet(lambda: fn(*new_args, **kwargs))
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


# Re-export aliases: `more_itertools/__init__.py` does `from .more import *`, so `mi.last` is the same
# function object as `more_itertools.more.last` but a *different* module attribute. Patching only the
# defining module left the name the suite actually calls unwrapped: measured on more-itertools, the
# law saw zero calls and could not fire at all. Wrapping a definition is not enough; every alias of it
# has to move with it.
_ALIAS: dict[int, tuple[Any, Any]] = {}


def _sweep_aliases() -> None:
    """Point every module attribute that still holds an unwrapped original at its wrapper."""
    if not _ALIAS:
        return
    for mod in list(sys.modules.values()):
        try:
            items = list(vars(mod).items())
        except Exception:
            continue
        for name, value in items:
            entry = _ALIAS.get(id(value))
            if entry is None or entry[0] is not value or entry[1] is value:
                continue
            try:
                setattr(mod, name, entry[1])
            except Exception:
                pass


def _wrap_module(mod: Any) -> None:
    for attr_name in list(vars(mod)):
        attr = vars(mod)[attr_name]
        if inspect.isfunction(attr) and getattr(attr, "__module__", None) == mod.__name__:
            if attr_name.startswith("_"):
                continue
            try:
                wrapper = _make_wrapper(mod, "", attr_name, attr, mod.__name__)
                setattr(mod, attr_name, wrapper)
                _ALIAS[id(attr)] = (attr, wrapper)
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
                wrapper = _make_wrapper(cls, cls_name, meth_name, meth, mod.__name__)
                setattr(cls, meth_name, wrapper)
                _ALIAS[id(meth)] = (meth, wrapper)
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
    # Presentation probing: a header/token string is usually produced by `__str__`/`to_header`, and
    # the suite may never call it on an object it constructed. Measured need: werkzeug@051fd663's
    # trailing space never appeared because nothing in the passing suite presented the header.
    laws = _laws()
    for pname in dir(cls):
        low = pname.lower()
        if not any(tok in low for tok in laws.HEADER_TOKENS):
            continue
        fn = getattr(cls, pname, None)
        if not callable(fn):
            continue
        try:
            import inspect as _inspect
            sig = _inspect.signature(fn)
        except Exception:
            continue
        required = [p for p in sig.parameters.values()
                    if p.name != "self" and p.default is p.empty
                    and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
        if required:
            continue
        try:
            produced = getattr(inst, pname)()
        except Exception:
            continue
        for violation in laws.check_canonicality(pname, produced):
            violation["where"] = f"{cls.__name__}.{pname}"
            _record(violation)

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
        if _want("assert_validation"):
            path = getattr(mod, "__file__", None)
            if path and path.endswith(".py"):
                try:
                    from canonical.swe_kernel import metamorphic_laws_v1 as laws_mod
                    source = open(path, "r", encoding="utf-8", errors="replace").read()
                    for violation in laws_mod.static_assert_validation(source, modname):
                        violation["where"] = f"{modname}.{violation['where']}"
                        _record(violation)
                except Exception:
                    _STATE["skipped"] += 1
        _wrap_module(mod)
    _sweep_aliases()


def pytest_collection_finish(session) -> None:
    # The package `__init__` runs `from .more import *` while the test modules are imported, i.e.
    # *after* `pytest_configure` wrapped the definitions. Sweep once more here, when every test module
    # (and therefore every re-export) exists, or the suite calls the unwrapped alias and observes nothing.
    _sweep_aliases()


def pytest_runtest_teardown(item, nextitem) -> None:
    prefixes = [t.split(".")[0] for t in _TARGETS]
    live = [obj for obj in _INSTANCES if type(obj).__module__.split(".")[0] in prefixes]
    _INSTANCES[:] = []
    for obj in live:
        try:
            _probe(obj)
        except Exception:
            _STATE["skipped"] += 1


def _hinted_constructions() -> None:
    """Build the object the issue names, from the issue's own words, and present it.

    Measured need: werkzeug's trailing space appears for `WWWAuthenticate("bearer")`, a construction
    the passing suite never performs. Without this the canonicality law has no trigger at all.
    """
    if not _HINTS:
        return
    laws = _laws()
    for modname in _TARGETS:
        try:
            mod = importlib.import_module(modname)
        except Exception:
            continue
        for cls_name, cls in list(vars(mod).items()):
            if not inspect.isclass(cls) or getattr(cls, "__module__", None) != modname:
                continue
            presenters = [n for n in dir(cls)
                          if any(tok in n.lower() for tok in laws.HEADER_TOKENS)
                          and callable(getattr(cls, n, None))]
            if not presenters:
                continue
            try:
                ctor = inspect.signature(cls.__init__)
            except (TypeError, ValueError):
                continue
            positional = [p for p in ctor.parameters.values()
                          if p.name != "self" and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
            if not positional:
                continue
            for hint in _HINTS[:12]:
                try:
                    inst = cls(hint)
                except Exception:
                    continue
                for pname in presenters:
                    try:
                        produced = getattr(inst, pname)()
                    except Exception:
                        continue
                    for violation in laws.check_canonicality(pname, produced):
                        violation["where"] = f'{cls_name}("{hint}").{pname}'
                        _record(violation)


def pytest_sessionfinish(session, exitstatus) -> None:
    try:
        _hinted_constructions()
    except Exception:
        _STATE["skipped"] += 1
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
        "per_law": dict(_STATE.get("per_law", {})),
        "probes": _STATE["probes"],
        "skipped": _STATE["skipped"],
        "law_errors": sorted(set(_STATE.get("law_errors", [])))[:20],
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
