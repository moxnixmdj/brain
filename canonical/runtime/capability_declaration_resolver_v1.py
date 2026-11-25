"""Resolve a capability by id and run it, without the front door importing it.

`CAPABILITY_REGISTRY_V1.json` says a capability exists and names the check that would
falsify it. This module is what makes that sentence have consequences:

  * `resolve(cap_id)` fails closed if the capability is not declared, if its module is
    missing, or if its verifier is missing. There is no "best effort" path -- an
    undeclared capability is UNRESOLVED, not a nice-to-have;
  * `invoke(cap_id, **kwargs)` imports the declared module *by path* and calls a named
    entry point. The import is done with `importlib.util.spec_from_file_location` under a
    private name so it cannot collide with a module already imported by the front door;
  * a capability whose declared entry point does not exist in its module is refused at
    resolve time, not at call time, so a typo cannot masquerade as a runtime failure.

The distinction this file is built around: a *declaration* is a claim; a *resolved
capability with a live entry point and a reachable verifier* is the smallest thing worth
routing to. Nothing here grants capability credit, and nothing here runs a benchmark.

Authority: NONE.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
from typing import Any, Callable, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_CAPABILITY_RESOLVER_V1"
DEFAULT_REGISTRY = "canonical/runtime/CAPABILITY_REGISTRY_V1.json"


class CapabilityError(RuntimeError):
    """A capability could not be resolved. Always fail closed."""


def _load_registry(repo_root: pathlib.Path, registry: str | pathlib.Path) -> dict[str, Any]:
    p = pathlib.Path(registry)
    if not p.is_absolute():
        p = repo_root / p
    if not p.is_file():
        return {}
    raw = json.loads(p.read_text(encoding="utf-8"))
    caps = raw.get("capabilities")
    if not isinstance(caps, dict):
        raise CapabilityError("REGISTRY_HAS_NO_CAPABILITIES_OBJECT")
    return caps


class Resolver:
    """Resolve + invoke declared capabilities for one repository root."""

    def __init__(self, repo_root: str | pathlib.Path, registry: str | pathlib.Path = DEFAULT_REGISTRY) -> None:
        self.root = pathlib.Path(repo_root).resolve()
        self._registry_path = registry
        self._caps = _load_registry(self.root, registry)
        self._loaded: dict[str, Any] = {}

    # ---- discovery -------------------------------------------------------
    def ids(self) -> list[str]:
        return sorted(self._caps)

    def describe(self, cap_id: str) -> dict[str, Any]:
        """What is declared about this capability, and whether it can actually be run."""
        entry = self._caps.get(cap_id)
        if entry is None:
            raise CapabilityError("CAPABILITY_NOT_DECLARED:" + cap_id)
        module = str(entry.get("module") or "")
        verifier = str(entry.get("verifier") or "")
        returns = str(entry.get("entry") or "run")
        module_path = self.root / module
        verifier_path = self.root / verifier
        return {
            "capability": cap_id,
            "module": module,
            "module_exists": module_path.is_file(),
            "verifier": verifier,
            "verifier_exists": verifier_path.is_file(),
            "entry": returns,
            "entry_exists": (
                module_path.is_file()
                and hasattr(self._import_module(module), returns)
            ) if module_path.is_file() else False,
            "preconditions": list(entry.get("preconditions") or []),
            "effects": list(entry.get("effects") or []),
        }

    def resolve(self, cap_id: str) -> Callable[..., Any]:
        """Return the callable entry point, or raise. No partial success."""
        info = self.describe(cap_id)
        if not info["module_exists"]:
            raise CapabilityError("CAPABILITY_MODULE_MISSING:" + info["module"])
        if not info["verifier_exists"]:
            raise CapabilityError("CAPABILITY_VERIFIER_MISSING:" + info["verifier"])
        if not info["entry_exists"]:
            raise CapabilityError("CAPABILITY_ENTRY_MISSING:" + info["entry"])
        fn = getattr(self._import_module(info["module"]), info["entry"])
        if not callable(fn):
            raise CapabilityError("CAPABILITY_ENTRY_NOT_CALLABLE:" + cap_id)
        return fn

    def invoke(self, cap_id: str, *args: Any, **kwargs: Any) -> Any:
        return self.resolve(cap_id)(*args, **kwargs)

    # ---- plumbing --------------------------------------------------------
    def _import_module(self, rel: str) -> Any:
        """Import a module by path under a private name, once."""
        if rel in self._loaded:
            return self._loaded[rel]
        path = self.root / rel
        if not path.is_file():
            raise CapabilityError("CAPABILITY_MODULE_MISSING:" + rel)
        private = "_brain_declared_" + rel.replace("/", "_").removesuffix(".py")
        if private in sys.modules:
            self._loaded[rel] = sys.modules[private]
            return sys.modules[private]
        spec = importlib.util.spec_from_file_location(private, path)
        if spec is None or spec.loader is None:
            raise CapabilityError("CAPABILITY_MODULE_UNLOADABLE:" + rel)
        module = importlib.util.module_from_spec(spec)
        sys.modules[private] = module
        # the repo root must be importable so the module's own `canonical.*` imports resolve
        if str(self.root) not in sys.path:
            sys.path.insert(0, str(self.root))
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(private, None)
            raise
        self._loaded[rel] = module
        return module


def resolve_all(repo_root: str | pathlib.Path, registry: str | pathlib.Path = DEFAULT_REGISTRY) -> dict[str, dict]:
    """Describe every declared capability. Never raises on a bad entry; reports it."""
    r = Resolver(repo_root, registry)
    out: dict[str, dict] = {}
    for cap_id in r.ids():
        try:
            out[cap_id] = r.describe(cap_id)
        except CapabilityError as exc:
            out[cap_id] = {"capability": cap_id, "error": str(exc), "entry_exists": False,
                           "module_exists": False, "verifier_exists": False}
    return out


def usable(repo_root: str | pathlib.Path, registry: str | pathlib.Path = DEFAULT_REGISTRY) -> dict[str, Callable[..., Any]]:
    """Only the capabilities that resolve to a real callable with a real verifier."""
    r = Resolver(repo_root, registry)
    out: dict[str, Callable[..., Any]] = {}
    for cap_id in r.ids():
        try:
            out[cap_id] = r.resolve(cap_id)
        except CapabilityError:
            continue
    return out


def main(argv: Iterable[str] | None = None) -> int:  # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser(description="Declared capability resolver")
    ap.add_argument("--root", default=".")
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    args = ap.parse_args(list(argv) if argv is not None else None)
    rows = resolve_all(args.root, args.registry)
    if not rows:
        print("no declared capabilities")
        return 0
    for cap_id, row in rows.items():
        mark = "OK  " if row.get("entry_exists") and row.get("verifier_exists") else "FAIL"
        print(f"{mark} {cap_id:32} module={row.get('module_exists')} verifier={row.get('verifier_exists')} entry={row.get('entry_exists')}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
