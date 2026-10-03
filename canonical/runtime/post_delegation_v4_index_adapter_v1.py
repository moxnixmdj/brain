"""Verified-mechanism composition for the current post-delegation V4 corpus index.

This adapter does not alter V4 scan semantics. It first executes the independently
verified post-delegation one-leaf recompiler, then passes that exact 30-predicate
frontier projection to the independently verified V4 content-addressed indexer.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.post_delegation_frontier_recompile_v1 import compile_post_delegation
from canonical.runtime.proof_atom_receipt_index_v4 import build_index as build_v4_index

SCHEMA="PROJECT_BRAIN_POST_DELEGATION_V4_INDEX_ADAPTER_V1"
ROOT=Path(__file__).resolve().parents[2]


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema":SCHEMA,
        "status":"FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "canonical_atom_count":0,
        "new_reality_units_consumed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }


def current_frontier_projection(
    frontier: Mapping[str,Any],
    hypergraph: Mapping[str,Any],
    overlay: Mapping[str,Any],
) -> dict[str,Any]:
    rec=compile_post_delegation(frontier,hypergraph,overlay)
    if not str(rec.get("status","")).startswith("PASS"):
        return _fail("POST_DELEGATION_RECOMPILE_NOT_PASS",*rec.get("errors",[]))
    basis=rec.get("proof_atom_basis",{})
    if basis.get("leaf_atom_count")!=39 or rec.get("after",{}).get("unresolved_predicates")!=30:
        return _fail("POST_DELEGATION_PROJECTION_NOT_30_PREDICATES_39_ATOMS")
    return {
        "schema":SCHEMA,
        "status":"PASS__POST_DELEGATION_FRONTIER_READY__ZERO_CREDIT",
        "frontier_projection":rec["frontier_projection"],
        "proof_atom_basis":basis,
        "removed":rec["removed"],
        "new_reality_units_consumed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }


def build_current_index(
    frontier: Mapping[str,Any],
    hypergraph: Mapping[str,Any],
    overlay: Mapping[str,Any],
    *,
    root: Path=ROOT,
) -> dict[str,Any]:
    cur=current_frontier_projection(frontier,hypergraph,overlay)
    if not str(cur.get("status","")).startswith("PASS"):
        return cur
    out=build_v4_index(cur["frontier_projection"],overlay,root=root)
    if not str(out.get("status","")).startswith("PASS"):
        return _fail("V4_INDEX_NOT_PASS",*out.get("errors",[]))
    if out.get("canonical_atom_count")!=39:
        return _fail("V4_INDEX_DID_NOT_USE_39_ATOM_POST_DELEGATION_BASIS")
    return {
        "schema":SCHEMA,
        "status":"PASS__POST_DELEGATION_39_ATOM_V4_CORPUS_INDEX__ZERO_CREDIT",
        "errors":[],
        "source_recompile":{
            "removed":cur["removed"],
            "unresolved_predicates":30,
            "canonical_leaf_atoms":39,
        },
        "v4_index":out,
        "new_reality_units_consumed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }


def main() -> int:
    frontier=json.loads((ROOT/"canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text(encoding="utf-8"))
    hypergraph=json.loads((ROOT/"canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json").read_text(encoding="utf-8"))
    overlay=json.loads((ROOT/"canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json").read_text(encoding="utf-8"))
    out=build_current_index(frontier,hypergraph,overlay)
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if str(out.get("status","")).startswith("PASS") else 1


if __name__=="__main__":
    raise SystemExit(main())
