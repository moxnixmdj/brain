"""Post-composition live frontier planner.

The R1-R12 binding wave and same-subject composition are already verified.
This adapter deliberately bypasses the obsolete sequential-root dynamic
refresh and reuses interval-robust frontier V2 directly on the bound current
frontier. All source bytes are still rehashed by V2 before any plan is emitted.
"""
from __future__ import annotations
from typing import Any, Mapping
from canonical.runtime import capability_parallel_frontier_v2 as core

SCHEMA="PROJECT_BRAIN_POST_COMPOSITION_PARALLEL_FRONTIER_V1"
PROF_WORK="PROFESSIONAL_QUALITY_V7_WHOLE_LEAF_DOMAIN_EVIDENCE"

class PostCompositionFrontierError(ValueError):
    pass

def _assert_post_composition(frontier: Mapping[str,Any]) -> None:
    candidates=frontier.get("candidates")
    if not isinstance(candidates,list):
        raise PostCompositionFrontierError("CANDIDATES_INVALID")
    rows=[x for x in candidates if isinstance(x,Mapping) and x.get("work_id")==PROF_WORK]
    if len(rows)!=1:
        raise PostCompositionFrontierError("POST_COMPOSITION_PROFESSIONAL_CANDIDATE_CARDINALITY")
    ev=rows[0].get("read_only_evidence")
    if not isinstance(ev,Mapping):
        raise PostCompositionFrontierError("PROFESSIONAL_EVIDENCE_MISSING")
    if ev.get("verified_root_subject_binding_count")!=12 or ev.get("required_root_count")!=12:
        raise PostCompositionFrontierError("PROFESSIONAL_ROOT_COUNT_NOT_12_OF_12")
    if ev.get("composition_admissible") is not True:
        raise PostCompositionFrontierError("PROFESSIONAL_COMPOSITION_NOT_ADMISSIBLE")
    if rows[0].get("evidence_acquisition_mode")!="READ_ONLY":
        raise PostCompositionFrontierError("PROFESSIONAL_POST_COMPOSITION_NOT_READ_ONLY")
    ledger_rel=ev.get("whole_leaf_residual_ledger_path")
    ledger_sha=ev.get("whole_leaf_residual_ledger_git_blob_sha")
    if not isinstance(ledger_rel,str) or not ledger_rel or not isinstance(ledger_sha,str) or not ledger_sha:
        raise PostCompositionFrontierError("PROFESSIONAL_WHOLE_LEAF_LEDGER_BINDING_MISSING")
    ledger_path=core.ROOT / ledger_rel
    if not ledger_path.is_file() or core._git_blob_sha(ledger_path)!=ledger_sha:
        raise PostCompositionFrontierError("PROFESSIONAL_WHOLE_LEAF_LEDGER_STALE")

def plan_current_post_composition_frontier() -> dict[str,Any]:
    frontier=core.load_current_frontier()
    _assert_post_composition(frontier)
    out=core.plan_parallel_frontier(frontier)
    return {
        **out,
        "adapter_schema":SCHEMA,
        "post_composition_phase_verified":True,
        "sequential_root_dynamic_refresh_bypassed":True,
        "execution_authority":False,
        "promotion_authority":False,
        "terminal_credit_delta":0,
    }
