"""Wave 1 Spine — Self-Forging Capability Growth, Implied-World Binding & Macro Chunking (`K3 = 0`).

Composes existing dormant/unwired runtime organs into one fast, zero-LLM spine:
  1. `canonical/runtime/world_binding_v1.py`: *"Bind first, then rank"* — promotes
     stated files to parent `source_root`s, deterministically synthesizes omitted
     `output_path`s, and leaves unjustifiable inputs unbound.
  2. `canonical/runtime/grounded_action_v1.py`: Perception -> Bindability ->
     Equivalence -> Specificity -> `DECISIVE_MARGIN_RATIO = 1.25` -> Independent
     Artifact Byte Re-Read.
  3. `canonical/runtime/capability_forge_v1.py` + `bound_capabilities/forged_invoker.py`:
     Discovers unbound adapter modules, AST-infers `args.get(...)` contracts,
     demands >= 2 distinct deterministic non-vacuous runs, re-hashes output bytes,
     and **requires corrupted inputs to be killed (`require_kill=True`)** before
     admitting any forged capability.
  4. `canonical/runtime/macro_v1.py`: DreamCoder-style plan chunking keyed on
     `(clause_verbs, file_kinds)` so repeated multi-step jobs recall their
     verified capability sequence in `< 1 ms` while re-verifying every step and
     applying e-process `failures > successes` eviction.
"""
from __future__ import annotations

import pathlib
import time
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_FORGED_BINDING_AND_MACRO_SPINE_V1"
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def bind_implied_capability_inputs(
    goal: str,
    capability_id: str,
    entry: Mapping[str, Any],
    *,
    root: str | pathlib.Path | None = None,
) -> dict[str, Any]:
    """Complete implied inputs (`source_root` from file, deterministic `output_path`) via `world_binding_v1`."""
    from canonical.runtime import goal_compiler, world_binding_v1 as wb

    work_root = pathlib.Path(root or REPO_ROOT).resolve()
    entry_with_id = dict(entry)
    entry_with_id.setdefault("capability_id", capability_id)
    comp = wb.complete_inputs(goal, work_root, entry_with_id, compiler=goal_compiler)
    rendered: dict[str, Any] | None = None
    if comp.get("complete") or not comp.get("missing"):
        try:
            rendered = wb.render_args(entry_with_id, dict(comp.get("inputs") or {}))
        except KeyError:
            rendered = None
    return {
        "schema": SCHEMA + "/world_binding",
        "capability_id": capability_id,
        "complete": bool(comp.get("complete") or (rendered is not None and not comp.get("missing"))),
        "inputs": dict(comp.get("inputs") or {}),
        "rendered_args": rendered,
        "missing": list(comp.get("missing") or []),
        "k3_external_llm_calls": 0,
    }


def execute_grounded_world_action(
    goal: str,
    *,
    root: str | pathlib.Path | None = None,
    registry: Mapping[str, Any] | None = None,
    prefer: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Execute a plain goal via `grounded_action_v1.act` (bind-first + decisive margin + independent byte re-read)."""
    from canonical.runtime import grounded_action_v1 as ga

    work_root = pathlib.Path(root or REPO_ROOT).resolve()
    res = ga.act(
        goal,
        root=work_root,
        registry=dict(registry) if registry is not None else None,
        prefer=list(prefer) if prefer is not None else None,
    )
    out = dict(res)
    out["k3_external_llm_calls"] = 0
    return out


# ---------------------------------------------------------------------------
# Self-Forging Dormant Module Admission (`capability_forge_v1` + `forged_invoker`)
# ---------------------------------------------------------------------------


def discover_unbound_adapters(registry: Mapping[str, Any] | None = None) -> list[str]:
    """Return adapter modules in `canonical/runtime/bound_capabilities/` not yet bound in `registry`."""
    from canonical.runtime import capability_forge_v1 as forge_mod

    return list(forge_mod.unbound_modules(dict(registry) if registry is not None else None))


def forge_dormant_adapter(
    module_name: str,
    seed_cases: Sequence[Mapping[str, Any]],
    *,
    root: str | pathlib.Path | None = None,
    state_path: str | pathlib.Path | None = None,
    register_on_admit: bool = True,
) -> dict[str, Any]:
    """Run the 5-gate `capability_forge_v1.forge` kill-test on `module_name` and optionally register."""
    from canonical.runtime import capability_forge_v1 as forge_mod

    t0 = time.perf_counter_ns()
    work_root = pathlib.Path(root or REPO_ROOT).resolve()
    cases = [dict(c) for c in seed_cases]

    orig_state = forge_mod.STATE
    try:
        if state_path is not None:
            forge_mod.STATE = pathlib.Path(state_path).resolve()
        report = forge_mod.forge(module_name, cases, root=work_root, require_kill=True)
        registered_cid: str | None = None
        if report.get("admitted") is True and register_on_admit:
            reg_out = forge_mod.register(module_name, report.get("contract") or {}, cases)
            registered_cid = reg_out.get("capability_id") if isinstance(reg_out, Mapping) else f"forged.{module_name}"
        return {
            "schema": SCHEMA + "/forge_report",
            "module": module_name,
            "admitted": bool(report.get("admitted")),
            "capability_id": registered_cid,
            "contract": report.get("contract"),
            "checks": report.get("checks"),
            "reasons": list(report.get("reasons") or []),
            "elapsed_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
            "k3_external_llm_calls": 0,
        }
    finally:
        forge_mod.STATE = orig_state


def invoke_forged_capability(
    capability_id: str,
    call_args: Mapping[str, Any],
    *,
    root: str | pathlib.Path | None = None,
    state_path: str | pathlib.Path | None = None,
) -> dict[str, Any]:
    """Invoke an already-forged capability through `forged_invoker` / `capability_forge_v1` allowlist (refuses unforged IDs!)."""
    from canonical.runtime import capability_forge_v1 as forge_mod
    from canonical.runtime.bound_capabilities import forged_invoker

    work_root = pathlib.Path(root or REPO_ROOT).resolve()
    orig_state = forge_mod.STATE
    try:
        if state_path is not None:
            forge_mod.STATE = pathlib.Path(state_path).resolve()
        forged_map = forge_mod._state().get("forged") or {}
        rec = forged_map.get(capability_id)
        if not rec:
            raise RuntimeError(f"NOT_FORGED:{capability_id}")
        # Bound-adapter forged entry (`forged.<adapter_module>`) vs general-module forged entry (`module` + `function`)
        entry = rec.get("entry") if isinstance(rec.get("entry"), Mapping) else {}
        adapter_mod = rec.get("module") if not rec.get("function") else None
        if not adapter_mod and isinstance(entry, Mapping):
            adapter_mod = entry.get("adapter_module")
        if adapter_mod and not rec.get("function"):
            ok, out = forge_mod._call(str(adapter_mod), dict(call_args), work_root)
            if not ok:
                raise RuntimeError(f"FORGED_EXECUTION_FAILED:{out}")
            res = dict(out) if isinstance(out, Mapping) else {"result": out}
            res["ok"] = True
            res["forged_from"] = str(adapter_mod)
            res["capability_id"] = capability_id
            return res
        payload = dict(call_args)
        payload["capability_id"] = capability_id
        out_inv = dict(forged_invoker.run(payload, work_root))
        if out_inv.get("ok") is False:
            raise RuntimeError(str(out_inv.get("error") or "FORGED_INVOKER_REFUSED"))
        return out_inv
    finally:
        forge_mod.STATE = orig_state


# ---------------------------------------------------------------------------
# DreamCoder Plan Chunking (`macro_v1`)
# ---------------------------------------------------------------------------


def lookup_verified_chain_macro(
    clauses: Sequence[str],
    *,
    state_path: str | pathlib.Path | None = None,
) -> dict[str, Any] | None:
    """Lookup a previously verified multi-clause capability macro in `< 0.5 ms`."""
    from canonical.runtime import macro_v1

    orig = macro_v1.STATE
    try:
        if state_path is not None:
            macro_v1.STATE = pathlib.Path(state_path).resolve()
        return macro_v1.lookup(list(clauses))
    finally:
        macro_v1.STATE = orig


def record_verified_chain_macro(
    clauses: Sequence[str],
    steps: Sequence[Mapping[str, Any]],
    *,
    state_path: str | pathlib.Path | None = None,
) -> bool:
    """Record a multi-clause plan where every step has `verified: True`."""
    from canonical.runtime import macro_v1

    orig = macro_v1.STATE
    try:
        if state_path is not None:
            macro_v1.STATE = pathlib.Path(state_path).resolve()
        return bool(macro_v1.record(list(clauses), [dict(s) for s in steps]))
    finally:
        macro_v1.STATE = orig


def execute_or_learn_clause_macro(
    clauses: Sequence[str],
    *,
    clause_executor: Callable[[str, str | None], Mapping[str, Any]],
    state_path: str | pathlib.Path | None = None,
) -> dict[str, Any]:
    """Execute `clauses` preferring a remembered `macro_v1` plan (`< 1 ms` lookup) while re-verifying every step."""
    from canonical.runtime import macro_v1

    t0 = time.perf_counter_ns()
    clause_list = [str(c).strip() for c in clauses if str(c).strip()]
    if len(clause_list) < 2:
        return {"pass": False, "status": "NEEDS_AT_LEAST_TWO_CLAUSES"}

    hit = lookup_verified_chain_macro(clause_list, state_path=state_path)
    if hit is not None:
        plan = list(hit.get("plan") or [])
        step_results: list[dict[str, Any]] = []
        all_ok = True
        for idx, clause in enumerate(clause_list):
            pref_cid = str(plan[idx].get("capability_id") or "") if idx < len(plan) else None
            r = dict(clause_executor(clause, pref_cid or None))
            step_results.append(r)
            if not (r.get("pass") is True or r.get("ok") is True or r.get("verified") is True):
                all_ok = False
                break
        if all_ok:
            record_verified_chain_macro(
                clause_list,
                [{"capability_id": s.get("capability_id") or s.get("compiled_capability_id"), "verified": True} for s in step_results],
                state_path=state_path,
            )
            return {
                "schema": SCHEMA + "/macro_execution",
                "pass": True,
                "from_macro": True,
                "macro_key": hit["key"],
                "steps": step_results,
                "elapsed_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
            }
        # Instance failure: apply `macro_v1`'s e-process `failures > successes` rule
        orig = macro_v1.STATE
        try:
            if state_path is not None:
                macro_v1.STATE = pathlib.Path(state_path).resolve()
            macro_v1.note_failure(str(hit["key"]))
        finally:
            macro_v1.STATE = orig

    # Cold path: solve each clause without macro hint, then chunk if all steps verified!
    cold_steps: list[dict[str, Any]] = []
    for clause in clause_list:
        r = dict(clause_executor(clause, None))
        cold_steps.append(r)
        if not (r.get("pass") is True or r.get("ok") is True or r.get("verified") is True):
            return {
                "schema": SCHEMA + "/macro_execution",
                "pass": False,
                "from_macro": False,
                "steps": cold_steps,
                "elapsed_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
            }

    recorded = record_verified_chain_macro(
        clause_list,
        [
            {
                "capability_id": s.get("capability_id") or s.get("compiled_capability_id") or "step",
                "verified": True,
            }
            for s in cold_steps
        ],
        state_path=state_path,
    )
    return {
        "schema": SCHEMA + "/macro_execution",
        "pass": True,
        "from_macro": False,
        "macro_recorded": recorded,
        "macro_key": macro_v1.signature(clause_list),
        "steps": cold_steps,
        "elapsed_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
    }
