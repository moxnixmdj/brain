"""Post-composition live frontier planner.

The R1-R12 binding wave and same-subject composition are already verified.
This adapter deliberately bypasses the obsolete sequential-root dynamic
refresh and reuses interval-robust frontier V2 directly on the bound current
frontier. All source bytes are still rehashed by V2 before any plan is emitted.
"""
from __future__ import annotations
import json
from typing import Any, Mapping
from canonical.runtime import capability_parallel_frontier_v2 as core

SCHEMA="PROJECT_BRAIN_POST_COMPOSITION_PARALLEL_FRONTIER_V1"
PROF_WORK="PROFESSIONAL_QUALITY_V7_WHOLE_LEAF_DOMAIN_EVIDENCE"
WHOLE_LEAF_LEDGER_REL="canonical/governance/PROFESSIONAL_QUALITY_WHOLE_LEAF_RESIDUAL_LEDGER_20261010_V1.json"
WHOLE_LEAF_LEDGER_SHA="ae5503829ad340cccef287f37ff70e4ab9288d33"

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
    ledger_path=core.ROOT / WHOLE_LEAF_LEDGER_REL
    if not ledger_path.is_file() or core._git_blob_sha(ledger_path)!=WHOLE_LEAF_LEDGER_SHA:
        raise PostCompositionFrontierError("PROFESSIONAL_WHOLE_LEAF_LEDGER_STALE")
    ledger=json.loads(ledger_path.read_text(encoding="utf-8"))
    subject=ledger.get("subject")
    if not isinstance(subject,Mapping):
        raise PostCompositionFrontierError("PROFESSIONAL_WHOLE_LEAF_LEDGER_SUBJECT_INVALID")
    for path_key,sha_key in (
        ("professional_current_path","professional_current_git_blob_sha"),
        ("scoped_registry_path","scoped_registry_git_blob_sha"),
    ):
        rel=subject.get(path_key)
        sha=subject.get(sha_key)
        if not isinstance(rel,str) or not rel or not isinstance(sha,str) or not sha:
            raise PostCompositionFrontierError("PROFESSIONAL_WHOLE_LEAF_LEDGER_SOURCE_BINDING_INVALID")
        live=core.ROOT / rel
        if not live.is_file() or core._git_blob_sha(live)!=sha:
            raise PostCompositionFrontierError("PROFESSIONAL_WHOLE_LEAF_LEDGER_SOURCE_STALE")

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
