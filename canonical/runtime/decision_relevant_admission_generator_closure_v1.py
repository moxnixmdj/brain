from __future__ import annotations
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_DECISION_RELEVANT_ADMISSION_GENERATOR_CLOSURE_V1"
COVER_MODES = {"POSITIVE_COVER", "COMPLETE_OBJECTIVE", "DIRECT_DOMINANCE"}

def _sha1(v: Any) -> bool:
    return isinstance(v, str) and len(v) == 40 and all(c in "0123456789abcdef" for c in v)

def _binding(v: Any) -> bool:
    return (
        isinstance(v, Mapping)
        and isinstance(v.get("path"), str)
        and bool(v["path"].strip())
        and _sha1(v.get("git_blob_sha"))
    )

def _receipts(v: Any) -> bool:
    return (
        isinstance(v, Sequence)
        and not isinstance(v, (str, bytes))
        and bool(v)
        and all(_binding(x) for x in v)
    )

def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "abc_closed": False,
        "u_empty": False,
        "terminal": False,
        "d_finality_required": True,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out

def evaluate(problem: Mapping[str, Any]) -> dict[str, Any]:
    """Compose already-proved closure ingredients into one fail-closed ABC rule.

    This verifier does not discover generators or prove receipts. It checks the
    exact logical seam needed for U-empty promotion:
      * useful target scope is already represented by the observable-trace superset;
      * every primitive generator region is scope-complete and covered by a sound
        Brain-owned positive cover, complete-objective optimizer, or direct dominance proof;
      * every primitive transform preserves admission and every load-bearing terminal
        property used by ABC;
      * the generator closure reaches every useful context in the trace scope.

    Under those premises, structural induction proves every useful context covered,
    hence U is empty. D finality remains separate.
    """
    if not isinstance(problem, Mapping):
        return _fail("PROBLEM_REQUIRED")

    trace = problem.get("trace_scope")
    if not isinstance(trace, Mapping):
        return _fail("TRACE_SCOPE_REQUIRED")
    if trace.get("proved") is not True or not _receipts(trace.get("proof_receipts")):
        return _fail("TRACE_SCOPE_SUPERSET_UNPROVED")

    generators = problem.get("generators")
    if (
        not isinstance(generators, Sequence)
        or isinstance(generators, (str, bytes))
        or not generators
    ):
        return _fail("GENERATORS_REQUIRED")

    gids: set[str] = set()
    modes: dict[str, str] = {}
    for i, row in enumerate(generators):
        if not isinstance(row, Mapping):
            return _fail(f"GENERATOR_INVALID:{i}")
        gid = row.get("generator_id")
        if not isinstance(gid, str) or not gid or gid in gids:
            return _fail(f"GENERATOR_ID_INVALID:{i}")
        gids.add(gid)

        mode = row.get("coverage_mode")
        if mode not in COVER_MODES:
            return _fail(f"GENERATOR_COVERAGE_MODE_INVALID:{gid}")
        if row.get("scope_complete") is not True:
            return _fail(f"GENERATOR_SCOPE_COMPLETENESS_UNPROVED:{gid}")
        if row.get("covered") is not True:
            return _fail(f"GENERATOR_COVERAGE_UNPROVED:{gid}")
        if not _receipts(row.get("proof_receipts")):
            return _fail(f"GENERATOR_PROOF_RECEIPTS_INVALID:{gid}")
        modes[gid] = mode

    transforms = problem.get("transforms", [])
    if not isinstance(transforms, Sequence) or isinstance(transforms, (str, bytes)):
        return _fail("TRANSFORMS_INVALID")

    tids: set[str] = set()
    for i, row in enumerate(transforms):
        if not isinstance(row, Mapping):
            return _fail(f"TRANSFORM_INVALID:{i}")
        tid = row.get("transform_id")
        if not isinstance(tid, str) or not tid or tid in tids:
            return _fail(f"TRANSFORM_ID_INVALID:{i}")
        tids.add(tid)

        for field in (
            "admission_preserving",
            "load_bearing_order_preserving",
            "hard_constraint_preserving",
            "resource_safety_preserving",
            "authority_preserving",
        ):
            if row.get(field) is not True:
                return _fail(f"TRANSFORM_{field.upper()}_UNPROVED:{tid}")
        if not _receipts(row.get("proof_receipts")):
            return _fail(f"TRANSFORM_PROOF_RECEIPTS_INVALID:{tid}")

    closure = problem.get("generator_closure")
    if not isinstance(closure, Mapping):
        return _fail("GENERATOR_CLOSURE_REQUIRED")
    if closure.get("complete") is not True:
        return _fail("GENERATOR_COMPLETENESS_UNPROVED")
    if closure.get("all_useful_contexts_reachable") is not True:
        return _fail("USEFUL_CONTEXT_REACHABILITY_UNPROVED")
    if not _receipts(closure.get("proof_receipts")):
        return _fail("GENERATOR_CLOSURE_PROOF_RECEIPTS_INVALID")

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__ABC_CLOSED_BY_DECISION_RELEVANT_GENERATOR_INDUCTION",
        "trace_scope_superset_proved": True,
        "generator_count": len(gids),
        "transform_count": len(tids),
        "coverage_modes": {k: modes[k] for k in sorted(modes)},
        "generator_basis_complete": True,
        "all_declared_generators_covered": True,
        "all_declared_transforms_abc_preserving": True,
        "all_useful_contexts_reachable": True,
        "proof_rule": (
            "BASE_GENERATORS_COVERED__ABC_PRESERVED_BY_EVERY_PRIMITIVE_TRANSFORM__"
            "GENERATOR_CLOSURE_EXHAUSTS_USEFUL_TRACE_SCOPE__THEREFORE_ALL_USEFUL_CONTEXTS_COVERED"
        ),
        "abc_closed": True,
        "u_empty": True,
        "d_finality_required": True,
        "terminal": False,
        "terminal_credit_delta": 0,
        "hard_boundary": (
            "NO_CREDIT_UNLESS_EVERY_PREMISE_HAS_SOUND_CONTENT_ADDRESSED_PROOF_RECEIPTS__"
            "D_OWNERSHIP_EFFECT_AND_DONOR_INDEPENDENCE_FINALITY_REMAIN_SEPARATE"
        ),
    }
