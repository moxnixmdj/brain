#!/usr/bin/env python3
"""The seam the admitted confinement was built for: declared capabilities run confined.

WHY THIS EXISTS
---------------

`computer_execution_boundary_v1` refuses unconfined host execution with one status and
names its release condition: "until a reviewed, admitted confinement and
effect-verification path exists". `confinement_v1` (merged 2026-11-12, PR #6733) is that
path; this module is the wiring. Measured wall this seam attacks
(`canonical/tools/realistic_goal_reach_probe_v1.py`): 19 of 38 material-aware realistic
goals for the most advanced coding capabilities refuse with
`FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT` -- they compile, they
bind, and die for want of a carrier.

THE CONTRACT
------------

* A capability is routable ONLY if it is declared in
  `canonical/runtime/CONFINED_EFFECT_DECLARATIONS_V1.json` -- reviewed data: the effect
  argument names whose bound values must exist as files after the run, and the budget.
  No declaration, or a bound value that is not a string, or an absolute path pointing
  into the host -> `None` -> the caller's refusal stands exactly as before.
* The SAME adapter code runs, imported from the CONFINED CLONE (the worktree's own
  `canonical` package), with `root` set to the worktree. The host repository is never
  handed to the capability; after the run its `git status --porcelain` must be
  byte-identical (`confinement_v1` verifies, and the receipt records it).
* The result mirrors `run_adapter_locally`'s contract exactly -- `capability_id`, a
  `dependency` block whose `executor` names the confinement (honest provenance), and the
  caller's own expectation check (`_check_expectation`, imported lazily at call time, so
  a confined pass and a local pass are judged by the same ruler).
* Every result carries the confinement receipt: sha, host head, host_untouched, and the
  per-effect sha256 verification. A run that overruns its budget, exits nonzero without
  its declared effects, or loses its host guarantee is reported as what it is -- a
  fail-closed confinement outcome with the receipt attached -- never as a capability
  pass.

WHAT THIS IS NOT
----------------

Not a relaxation. The boundary module is untouched; undeclared capabilities keep the
refusal; a declaration that cannot be honored (unbound effect, escaping path) keeps the
refusal. The declarations file is the review surface: one JSON file, one capability per
row, each effect argument named.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import confinement_v1 as CF

SCHEMA = "PROJECT_BRAIN_CONFINED_DISPATCH_V1"

DECLARATIONS_PATH = Path(__file__).resolve().parent / "CONFINED_EFFECT_DECLARATIONS_V1.json"

EXECUTOR = "ADMITTED_CONFINEMENT_V1"
RESULT_FILE = "confinement_result.json"
MARKER = "@@CONFINED_RESULT@@"

# The runner executes inside the worktree with cwd = worktree, so `import canonical...`
# resolves to the CLONE's code and `root='.'` is the worktree. The adapter's own result
# dict goes to a file inside the worktree (stdout stays free for adapter prints), and the
# caller reads it before the worktree is released.
RUNNER = r"""
import importlib, json, sys
module_name, entrypoint, payload = sys.argv[1], sys.argv[2], sys.argv[3]
out = {"__confined_runner__": "started"}
try:
    mod = importlib.import_module("canonical.runtime.bound_capabilities." + module_name)
    fn = getattr(mod, entrypoint)
    res = fn(json.loads(payload), ".")
    out = res if isinstance(res, dict) else {"__confined_runner__": "non-dict result", "repr": repr(res)[:500]}
except BaseException as exc:
    out = {"__confined_runner__": "adapter_raised", "error_type": type(exc).__name__,
           "error": str(exc)[:500]}
with open(%r, "w") as fh:
    json.dump(out, fh)
""" % (RESULT_FILE,)

_ADAPTER_OK = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")

_DECLS: dict[str, Any] | None = None


def declarations(path: Path = DECLARATIONS_PATH) -> dict[str, Any]:
    """Load and validate the reviewed effect declarations (cached)."""
    global _DECLS
    if _DECLS is not None:
        return _DECLS
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema") != "PROJECT_BRAIN_CONFINED_EFFECT_DECLARATIONS_V1":
        raise ValueError("CONFINED_EFFECT_DECLARATIONS_SCHEMA_MISMATCH")
    caps = raw.get("capabilities")
    if not isinstance(caps, dict):
        raise ValueError("CONFINED_EFFECT_DECLARATIONS_INVALID")
    _DECLS = caps
    return _DECLS


def reset_cache() -> None:
    global _DECLS
    _DECLS = None


def _args_of(entry: Mapping[str, Any], action: Mapping[str, Any]) -> dict[str, Any]:
    args = dict(action.get("args") or {})
    args.pop("capability_id", None)
    return args


def _host_escaping(host_root: Path, value: str) -> bool:
    """True when a bound string value is an absolute path into the host."""
    if not isinstance(value, str) or not value.startswith("/"):
        return False
    stripped = value[len(str(host_root)):] if value.startswith(str(host_root)) else value
    candidate = (host_root / stripped.lstrip("/")).resolve()
    try:
        return host_root.resolve() in candidate.parents or candidate == host_root.resolve()
    except (OSError, RuntimeError, ValueError):
        return False


def run_confined_capability(
    cid: str,
    entry: Mapping[str, Any],
    action: Mapping[str, Any],
    *,
    host_root: str | Path,
) -> dict[str, Any] | None:
    """Run one declared capability on the disposable clone; `None` means "not routable".

    `None` is the fail-closed answer: the caller then refuses exactly as before. A dict
    return is the adapter's own result, stamped with the confinement receipt and judged
    by the caller's expectation check.
    """
    host = Path(host_root).resolve()
    decl = declarations().get(str(cid))
    if not isinstance(decl, Mapping):
        return None
    effect_args = decl.get("effect_args")
    if not isinstance(effect_args, list) or not effect_args:
        return None
    args = _args_of(entry, action)
    effects: list[str] = []
    for name in effect_args:
        value = args.get(str(name))
        if not isinstance(value, str) or not value.strip():
            return None  # the door did not bind the declared effect -> refuse as before
        if _host_escaping(host, value):
            return None  # a bound absolute path into the host is not a confined effect
        effects.append(value)

    module_name = str(entry.get("adapter_module") or "")
    if not module_name or any(ch not in _ADAPTER_OK for ch in module_name):
        return None
    entrypoint = str(entry.get("entrypoint") or "run")

    budget = float(decl.get("budget_s") or 600.0)
    argv = ["python3", "-c", RUNNER, module_name, entrypoint, json.dumps(args)]
    conf = CF.admit(host, argv, budget_s=budget, declared_effects=effects)
    if not isinstance(conf, CF.Confinement):
        return None  # the confinement refused the declared shape -> refuse as before
    try:
        executed = CF.execute(conf)
        outcome = executed.get("outcome")
        host_untouched = bool(executed.get("host_untouched"))
        observed = executed.get("declared_effects") or {}
        effects_ok = bool(observed) and all(o.get("exists") for o in observed.values())
        receipt = {
            "receipt_sha256": executed.get("receipt_sha256"),
            "host_head": executed.get("host_head"),
            "host_untouched": host_untouched,
            "outcome": outcome,
            "elapsed_s": executed.get("elapsed_s"),
            "declared_effects": observed,
        }
        adapter_result: dict[str, Any] | None = None
        result_path = conf.worktree / RESULT_FILE
        if result_path.is_file():
            try:
                loaded = json.loads(result_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict) and "__confined_runner__" not in loaded:
                    adapter_result = loaded
            except (ValueError, OSError):
                adapter_result = None

        if adapter_result is None:
            return {
                "pass": False,
                "status": CF.STATUS if hasattr(CF, "STATUS") else "FAIL_CLOSED__CONFINED_EXECUTION",
                "reason": "CONFINED_RUN_DID_NOT_PRODUCE_A_RESULT",
                "confinement": receipt,
                "capability_id": str(cid),
                "dependency": {"type": "confinement", "modules": [], "executor": EXECUTOR},
                "terminal_authority": False,
            }

        adapter_result.setdefault("capability_id", str(cid))
        adapter_result["confinement"] = receipt
        adapter_result["dependency"] = {
            "type": "confinement", "modules": [], "executor": EXECUTOR,
        }
        adapter_result["terminal_authority"] = False
        # The same ruler the local path uses, applied to the confined result.
        from canonical.runtime import live_brain_route_admission_v1 as _door

        _door._check_expectation(action.get("expect"), adapter_result, args)
        return adapter_result
    finally:
        CF.release(conf)
