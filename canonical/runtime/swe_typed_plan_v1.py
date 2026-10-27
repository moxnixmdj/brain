"""Scoped typed-SWE execution plan for the live front door (hidden-tool wiring).

Measured 2026-10-27.  ``capability_selection_retrieval_v1.select`` already
shortlists, admits and (for a stated effect) disambiguates a software-engineering
capability from a human sentence, and ``declared_input_derivation_v1`` already
proves the missing declared inputs from stated evidence.  But ``select()`` is a
*proposal* surface: the live door ``live_brain_route_admission_v1.solve`` still
routes primarily through the pinned lexical compiler, which sends ordinary SWE
sentences to PDF/document converters.  This module is the missing wire: it turns
a DECISIVE typed selection into a fully-bound, executable ``compiled`` plan that
re-enters the SAME ``solve`` gate chain (route admission, execution, tool truth,
promised artifact, source change, observed effect).  Nothing runs here directly.

Route order (why this is REUSE/ADAPT, not a new primitive): the selector, the
derivation, the type surface, the binder and the whole observation gate chain
already exist.  This module only composes them and fixes two shape mismatches the
probes measured:

  * the derived/ adapter-defaulted slots must be removed from the EXECUTABLE
    template (else ``_render_template`` raises GOAL_INPUT_BINDING_REQUIRED on a
    slot the adapter defaults), but DERIVED slots must KEEP their bound values
    (else the adapter gets TEST_PATHS_REQUIRED).  ``binding_view``'s shadow is
    built for BINDING; this builds a second, execution-only template.
  * an ``output_path`` bound onto a stated SOURCE file would be overwritten by a
    report, corrupting the module.  It is moved to a fresh, deterministic report
    path in the stated source directory.  A stated report path is never touched.

Authority: NONE. Credit: 0. Model dependency: 0. Incremental spend: $0.
"""
from __future__ import annotations

import pathlib
from typing import Any, Mapping

from canonical.runtime import capability_selection_retrieval_v1 as selection
from canonical.runtime import declared_input_derivation_v1 as derivation
from canonical.runtime import goal_compiler
from canonical.runtime import live_integrated_brain_v1 as live_brain

SCHEMA = "PROJECT_BRAIN_SWE_TYPED_PLAN_V1"


def is_swe_request(goal: str) -> bool:
    """True only for an explicit software-engineering request (not a module call)."""
    return derivation.is_swe_request(goal)


def _execution_template(entry: Mapping[str, Any], removed: set[str]) -> dict[str, Any]:
    """Copy the adapter's declared template, dropping ONLY adapter-defaulted
    ``${input.*}`` placeholders.  Slots with a bound value (including derived
    ones) are kept so the adapter still receives them at run time."""
    template = dict(entry.get("action_template") or {})
    args = dict(template.get("args") or {})
    for key in list(args):
        value = args[key]
        if key in removed and isinstance(value, str) and "${input." in value:
            args.pop(key, None)
    template["args"] = args
    return template


def _fresh_output_path(goal: str, root: pathlib.Path, inputs: Mapping[str, Any]) -> str | None:
    """If ``output_path`` was bound onto a stated source file, relocate it to a
    fresh report path in the stated source directory.  Never overwrite a source.

    Evidence: the stated source directory (or the parent of the single stated
    source file).  Deterministic name; the promised-artifact gate independently
    checks that the file is non-empty, so inventing a passing path proves nothing.
    """
    stated = set(derivation.stated_existing_files(goal, root))
    current = inputs.get("output_path")
    if not isinstance(current, str) or current not in stated:
        return None
    # Only a file the sentence treats as code is a dangerous output target.
    if not current.endswith((".py", ".js", ".ts", ".rs", ".go", ".java", ".cpp", ".c", ".rb")):
        return None
    source_root = inputs.get("source_root")
    if isinstance(source_root, str) and source_root and (root / source_root).is_dir():
        parent = source_root
    else:
        parent = str(pathlib.PurePosixPath(current).parent)
    if not parent or not (root / parent).is_dir():
        return None
    return str(pathlib.PurePosixPath(parent) / "typed_swe_report.json")


def build_plan(goal: str, root: Any) -> tuple[dict, dict, dict] | None:
    """Return ``(registry, admissible, compiled)`` for a DECISIVE typed SWE
    selection, or ``None``.  ``None`` means: not a SWE request, ambiguous, no
    bindable proposal, or any fault — the caller keeps its original fail-closed
    verdict.  Ambiguity is never silently resolved (``select`` refuses it)."""
    root = pathlib.Path(root)
    if not is_swe_request(goal):
        return None
    try:
        registry = dict(live_brain.load_verified_registry())
        decision = selection.select(goal, registry, root, 8)
        if decision.get("status") != "SELECTED":
            return None  # ambiguity / no admitted proposal -> refuse
        cid = str(decision.get("selected_capability") or "")
        if not cid:
            return None
        admissible = goal_compiler._platform_admissible_registry(dict(registry))
        entry = dict(admissible.get(cid) or registry.get(cid) or {})
        if not entry:
            return None

        inputs = dict(decision.get("inputs") or {})
        shadow, values, report = derivation.binding_view(goal, entry, root)
        inputs = {**inputs, **values}
        removed = set((report.get("adapter_defaulted") or {}).keys())

        relocated = _fresh_output_path(goal, root, inputs)
        if relocated:
            inputs["output_path"] = relocated

        exec_entry = dict(entry)
        exec_entry["action_template"] = _execution_template(entry, removed)
        admissible[cid] = exec_entry

        # Prefer the real compiled shape when the lexical compiler can produce
        # one (it carries target_effects / finish_summary / match_evidence the
        # lossless raw-task contract reads); fall back to a synthetic single-
        # capability plan when the compiler raised (the short-sentence case).
        try:
            _, _, real = live_brain.compile_against_live_registry(goal, root)
            compiled = dict(real)
        except Exception:
            compiled = {
                "schema": SCHEMA, "capabilities": [cid], "compiled_parts": [],
                "score": 0, "match_evidence": {}, "initial_facts": {},
                "finish_summary": "RAW_GOAL_COMPLETE",
            }
        compiled["selected_capability"] = cid
        compiled["inputs"] = inputs
        compiled["compiler_mode"] = "SWE_TYPED_PLAN_V1"
        compiled.setdefault("target_effects", list(entry.get("provides") or []) or [cid])
        compiled.pop("capability_dag", None)
        compiled.pop("controller_actions", None)
        return (registry, admissible, compiled)
    except Exception:
        return None


def plan_report(goal: str, root: Any) -> dict[str, Any]:
    """Measurement surface: what a decisive typed plan would select, without
    executing anything.  Independent of any claim of success."""
    plan = build_plan(goal, root)
    if plan is None:
        return {"schema": SCHEMA, "status": "NO_DECISIVE_TYPED_PLAN"}
    _, _, compiled = plan
    return {
        "schema": SCHEMA, "status": "DECISIVE_TYPED_PLAN",
        "selected_capability": compiled.get("selected_capability"),
        "inputs": {k: (v if isinstance(v, (str, int, float, bool, list, dict)) else str(v))
                   for k, v in (compiled.get("inputs") or {}).items()},
        "model_dependency_count": 0, "incremental_spend_usd": 0,
    }
