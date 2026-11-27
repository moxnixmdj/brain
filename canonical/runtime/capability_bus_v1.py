#!/usr/bin/env python3
"""A capability bus that admits a plugin only when the plugin can prove itself by running.

WHY THIS EXISTS
---------------
The tree has 6,508 Python files under `canonical/` and two front doors
(`brain_unified_model_v1.py`, `unified_hidden_capability_federation_v1.py`) that reference almost none
of them: an imported-and-never-called module is indistinguishable from a working one until something
executes it. Hand-wiring organs into a 7,653-line model file is the opposite of a solution -- every
addition is permanent, and nothing checks that the new organ does anything.

This bus inverts that. A capability declares *how to prove it*, and the bus runs the proof before it
will dispatch a single call. Three outcomes, and only the first dispenses:

  ADMITTED      the module imported and its `self_check()` returned a passing verdict in <= 5 s;
  UNVERIFIED    it imported but cannot prove itself: it is kept in the inventory and never dispatched;
  IMPORT_FAILED the module did not import (missing dependency, syntax, or a timeout).

The point is the middle row. "23 organs are unwired" and "23 organs are ready to wire" are different
claims, and only execution separates them.

WHAT THIS IS NOT
----------------
It is not a registry, an index or a framework. It adds no knowledge, no parameters and no runtime
dependency; it is 200 lines of importlib plus a manifest the caller supplies. It does not decide
whether a plugin is *useful* -- that is what the receipt's measurement is for.
"""
from __future__ import annotations

import argparse
import importlib
import json
import pathlib
import signal
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

SCHEMA = "BRAIN_CAPABILITY_BUS_V1"
PROTOCOL = 1

ADMITTED = "ADMITTED"
UNVERIFIED = "UNVERIFIED"
IMPORT_FAILED = "IMPORT_FAILED"
SELF_CHECK_FAILED = "SELF_CHECK_FAILED"
ENTRY_MISSING = "ENTRY_MISSING"

DEFAULT_TIMEOUT_S = 5.0


@dataclass
class PluginSpec:
    """One declared capability: where it lives, what it exposes, and how it proves itself."""

    plugin_id: str
    module: str
    entry: str = ""
    triggers: List[str] = field(default_factory=list)
    rung: int = 1
    note: str = ""

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "PluginSpec":
        return cls(
            plugin_id=str(payload["plugin_id"]),
            module=str(payload["module"]),
            entry=str(payload.get("entry") or ""),
            triggers=[str(t) for t in payload.get("triggers") or []],
            rung=int(payload.get("rung") or 1),
            note=str(payload.get("note") or ""),
        )


@dataclass
class Loaded:
    spec: PluginSpec
    state: str
    detail: str = ""
    import_ms: float = 0.0
    self_check_ms: float = 0.0
    module: Any = None
    self_check_result: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.spec.plugin_id,
            "module": self.spec.module,
            "entry": self.spec.entry,
            "rung": self.spec.rung,
            "triggers": list(self.spec.triggers),
            "state": self.state,
            "detail": self.detail,
            "import_ms": round(self.import_ms, 2),
            "self_check_ms": round(self.self_check_ms, 2),
        }


class _Timeout(Exception):
    pass


def _alarm(signum, frame):  # pragma: no cover - signal handler
    raise _Timeout("self_check exceeded its budget")


def _passing(result: Any) -> bool:
    """A self-check passes only by saying so. Silence is not a pass."""
    if not isinstance(result, dict):
        return False
    verdict = str(result.get("verdict") or "")
    if verdict:
        return verdict.endswith("_PASS") or verdict == "PASS"
    return result.get("ok") is True or result.get("pass") is True


class CapabilityBus:
    """Loads a manifest, proves what it can, and dispatches only to the proven."""

    def __init__(self, specs: Sequence[PluginSpec], *, timeout_s: float = DEFAULT_TIMEOUT_S) -> None:
        self.specs = list(specs)
        self.timeout_s = timeout_s
        self.loaded: Dict[str, Loaded] = {}

    @classmethod
    def from_manifest(cls, manifest: Dict[str, Any], **kwargs: Any) -> "CapabilityBus":
        return cls([PluginSpec.from_dict(item) for item in manifest.get("plugins") or []], **kwargs)

    def load(self) -> Dict[str, Loaded]:
        self.loaded = {}
        for spec in self.specs:
            self.loaded[spec.plugin_id] = self._load_one(spec)
        return self.loaded

    def _load_one(self, spec: PluginSpec) -> Loaded:
        started = time.perf_counter()
        try:
            module = importlib.import_module(spec.module)
        except BaseException as exc:  # a plugin may raise anything at import time
            return Loaded(spec=spec, state=IMPORT_FAILED, detail=f"{type(exc).__name__}: {str(exc)[:120]}",
                          import_ms=(time.perf_counter() - started) * 1000.0)
        imported = Loaded(spec=spec, state=UNVERIFIED, module=module,
                          import_ms=(time.perf_counter() - started) * 1000.0)
        checker = getattr(module, "self_check", None)
        if not callable(checker):
            imported.detail = "no self_check(): cannot prove itself, never dispatched"
            return imported
        begun = time.perf_counter()
        previous = signal.getsignal(signal.SIGALRM)
        try:
            signal.signal(signal.SIGALRM, _alarm)
            signal.setitimer(signal.ITIMER_REAL, self.timeout_s)
            result = checker()
        except BaseException as exc:
            imported.state = SELF_CHECK_FAILED
            imported.detail = f"{type(exc).__name__}: {str(exc)[:120]}"
            return imported
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous)
            imported.self_check_ms = (time.perf_counter() - begun) * 1000.0
        imported.self_check_result = result if isinstance(result, dict) else {"raw": repr(result)}
        if _passing(result):
            imported.state = ADMITTED
            imported.detail = "self_check passed"
            if spec.entry and not callable(getattr(module, spec.entry, None)):
                imported.state = ENTRY_MISSING
                imported.detail = f"declared entry {spec.entry!r} is not callable"
        else:
            imported.state = SELF_CHECK_FAILED
            imported.detail = f"self_check returned {result!r}"[:160]
        return imported

    def dispatch(self, trigger: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call the admitted plugin that declares this trigger; never an unproven one."""
        for loaded in sorted(self.loaded.values(), key=lambda item: (item.spec.rung, item.spec.plugin_id)):
            if loaded.state != ADMITTED or trigger not in loaded.spec.triggers:
                continue
            entry = getattr(loaded.module, loaded.spec.entry or "", None)
            if not callable(entry):
                continue
            try:
                value = entry(**payload)
            except BaseException as exc:
                return {"plugin_id": loaded.spec.plugin_id, "ok": False,
                        "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
            return {"plugin_id": loaded.spec.plugin_id, "ok": True, "value": value}
        return {"plugin_id": None, "ok": False, "error": f"NO_ADMITTED_PLUGIN_FOR_TRIGGER:{trigger}"}

    def audit(self) -> Dict[str, Any]:
        states: Dict[str, int] = {}
        for loaded in self.loaded.values():
            states[loaded.state] = states.get(loaded.state, 0) + 1
        return {
            "schema": f"{SCHEMA}_AUDIT",
            "declared": len(self.specs),
            "states": dict(sorted(states.items())),
            "admitted": [loaded.spec.plugin_id for loaded in self.loaded.values() if loaded.state == ADMITTED],
            "unverified": [loaded.spec.plugin_id for loaded in self.loaded.values() if loaded.state == UNVERIFIED],
            "failed": [loaded.spec.plugin_id for loaded in self.loaded.values()
                       if loaded.state in (IMPORT_FAILED, SELF_CHECK_FAILED, ENTRY_MISSING)],
            "import_ms_total": round(sum(item.import_ms for item in self.loaded.values()), 2),
            "self_check_ms_total": round(sum(item.self_check_ms for item in self.loaded.values()), 2),
            "plugins": [item.to_dict() for item in self.loaded.values()],
        }


def scan(specs: Sequence[PluginSpec], *, timeout_s: float = DEFAULT_TIMEOUT_S) -> Dict[str, Any]:
    """Load and audit a manifest without dispatching anything."""
    bus = CapabilityBus(specs, timeout_s=timeout_s)
    bus.load()
    return bus.audit()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", default="canonical/runtime/plugins/capability_bus_manifest_v1.json")
    parser.add_argument("--json", default="")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)
    args = parser.parse_args(argv)

    root = pathlib.Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    path = pathlib.Path(args.manifest) if pathlib.Path(args.manifest).is_absolute() else root / args.manifest
    manifest = json.loads(path.read_text(encoding="utf-8"))
    report = scan([PluginSpec.from_dict(item) for item in manifest.get("plugins") or []],
                  timeout_s=args.timeout)
    if args.json:
        out = pathlib.Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "plugins"}, indent=1, sort_keys=True))
    return 0 if report["admitted"] else 1


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
