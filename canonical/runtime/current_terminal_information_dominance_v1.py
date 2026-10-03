"""Recompute exact structural information dominance on the live receipt-derived terminal world.

Scheduling only. Zero acceptance/execution/promotion credit.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from canonical.runtime.current_terminal_scheduling_world_v1 import evaluate as compile_world
from canonical.runtime.terminal_information_dominance_v1 import evaluate as information_dominance

SCHEMA="PROJECT_BRAIN_CURRENT_TERMINAL_INFORMATION_DOMINANCE_V1"

def evaluate(
    registry:dict[str,Any],
    evidence:dict[str,Any],
    frontier:dict[str,Any],
    hypergraph:dict[str,Any],
    scheduling_v6:dict[str,Any],
    authority:dict[str,Any],
)->dict[str,Any]:
    live=compile_world(registry,evidence,frontier,hypergraph,scheduling_v6,authority)
    if live.get("pass") is not True:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED__LIVE_WORLD_INVALID",
            "live_world":live,"execution_authority":False,"promotion_authority":False,
            "fresh_reality_authority":False,"capability_credit_delta":0,"family_credit_delta":0,
        }
    doc={
        "unresolved_predicates":live["unresolved_predicates"],
        "certificates":live["live_certificates"],
    }
    dominance=information_dominance(doc)
    ok=dominance.get("status")=="EXACT_INFORMATION_DOMINANCE_COMPUTED"
    return {
        "schema":SCHEMA,
        "status":"PASS__EXACT_LIVE_30_INFORMATION_DOMINANCE__ZERO_REALITY__ZERO_CREDIT" if ok else "FAIL_CLOSED__DOMINANCE_NOT_COMPUTED",
        "pass":ok,
        "live_world_summary":{
            "frozen_predicates":live["registry_predicate_count"],
            "proved_predicates":live["proved_predicate_count"],
            "unresolved_predicates":live["unresolved_predicate_count"],
            "live_certificate_count":live["live_certificate_count"],
            "live_action_coverage_count":live["live_action_coverage_count"],
        },
        "dominance":dominance,
        "next_rule":"WORK_ONLY_NONDOMINATED_ZERO_REALITY_CERTIFICATES__RUN_FIXED_POINT_AFTER_EACH_VERIFIED_CERTIFICATE__FRESH_REALITY_ONLY_AFTER_ZERO_REALITY_FRONTIER_SATURATES",
        "new_reality_units_consumed":0,
        "incremental_spend_usd":0,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }

def main()->int:
    root=Path(__file__).resolve().parents[2]
    def load(rel:str):
        return json.loads((root/rel).read_text(encoding="utf-8"))
    out=evaluate(
        load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
        load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
        load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
        load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"),
        load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json"),
        load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
    )
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out.get("pass") else 1

if __name__=="__main__":
    raise SystemExit(main())
