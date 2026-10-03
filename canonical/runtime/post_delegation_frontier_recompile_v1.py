"""Fail-closed post-delegation terminal frontier recompiler.

Removes exactly the independently closed delegation atomic predicate, its
single-target certificate, and its single-target action, then recompiles the
canonical PA1 proof-atom basis using the already verified V2 compiler.
Grants zero terminal credit by itself.
"""
from __future__ import annotations
import copy
from typing import Any, Mapping
from canonical.runtime.canonical_proof_atom_basis_v2 import compile_basis

SCHEMA="PROJECT_BRAIN_POST_DELEGATION_FRONTIER_RECOMPILE_V1"
TARGET="DELEGATION_TERMINAL_SUCCESS_NONINFERIOR"
CERT_ID="DELEGATION_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE"
ACTION_ID="BUILD_DELEGATION_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE"
EXPECTED_REQUIREMENT="INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_DELEGATION_PROTOCOL"

def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema":SCHEMA,"status":"FAIL_CLOSED","errors":sorted(set(errors)),
        "execution_authority":False,"promotion_authority":False,
        "capability_credit_delta":0,"family_credit_delta":0,
        "new_reality_units_consumed":0,
    }

def compile_post_delegation(
    frontier: Mapping[str,Any],
    hypergraph: Mapping[str,Any],
    overlay: Mapping[str,Any],
) -> dict[str,Any]:
    if not isinstance(frontier,Mapping) or not isinstance(hypergraph,Mapping) or not isinstance(overlay,Mapping):
        return _fail("INPUT_NOT_OBJECT")
    unresolved=frontier.get("unresolved_predicates")
    certs=frontier.get("certificates")
    actions=hypergraph.get("actions")
    if not isinstance(unresolved,list) or unresolved.count(TARGET)!=1:
        return _fail("DELEGATION_TARGET_NOT_EXACTLY_ONCE")
    if not isinstance(certs,list) or not isinstance(actions,list):
        return _fail("CERTIFICATES_OR_ACTIONS_INVALID")

    matching_certs=[c for c in certs if isinstance(c,Mapping) and TARGET in c.get("target_predicates",[])]
    if len(matching_certs)!=1:
        return _fail("DELEGATION_CERTIFICATE_CARDINALITY_NOT_ONE")
    cert=matching_certs[0]
    if cert.get("id")!=CERT_ID or cert.get("target_predicates")!=[TARGET] or cert.get("requires")!=[EXPECTED_REQUIREMENT]:
        return _fail("DELEGATION_CERTIFICATE_NOT_EXACT_SINGLE_TARGET_LEAF")

    matching_actions=[a for a in actions if isinstance(a,Mapping) and TARGET in a.get("target_predicates",[])]
    if len(matching_actions)!=1:
        return _fail("DELEGATION_ACTION_CARDINALITY_NOT_ONE")
    action=matching_actions[0]
    if action.get("id")!=ACTION_ID or action.get("target_predicates")!=[TARGET]:
        return _fail("DELEGATION_ACTION_NOT_EXACT_SINGLE_TARGET_LEAF")

    new_frontier=copy.deepcopy(dict(frontier))
    new_frontier["unresolved_predicates"]=[x for x in unresolved if x!=TARGET]
    new_frontier["certificates"]=[copy.deepcopy(c) for c in certs if c.get("id")!=CERT_ID]

    new_hypergraph=copy.deepcopy(dict(hypergraph))
    new_hypergraph["actions"]=[copy.deepcopy(a) for a in actions if a.get("id")!=ACTION_ID]

    if any(TARGET in c.get("target_predicates",[]) for c in new_frontier["certificates"]):
        return _fail("DELEGATION_TARGET_SURVIVED_CERTIFICATES")
    if any(TARGET in a.get("target_predicates",[]) for a in new_hypergraph["actions"]):
        return _fail("DELEGATION_TARGET_SURVIVED_ACTIONS")

    basis=compile_basis(new_frontier,overlay)
    if not str(basis.get("status","")).startswith("PASS"):
        return _fail("RECOMPILED_BASIS_NOT_PASS", *basis.get("errors",[]))

    return {
        "schema":SCHEMA,
        "status":"PASS__EXACT_ONE_LEAF_DELEGATION_REMOVAL__POST_DELEGATION_PA1_RECOMPILED__ZERO_CREDIT",
        "errors":[],
        "removed":{
            "atomic_predicate":TARGET,
            "certificate_id":CERT_ID,
            "action_id":ACTION_ID,
            "primitive_requirement":EXPECTED_REQUIREMENT,
        },
        "before":{
            "unresolved_predicates":len(unresolved),
            "certificates":len(certs),
            "actions":len(actions),
        },
        "after":{
            "unresolved_predicates":len(new_frontier["unresolved_predicates"]),
            "certificates":len(new_frontier["certificates"]),
            "actions":len(new_hypergraph["actions"]),
            "leaf_requirement_occurrences":basis["leaf_requirement_occurrence_count"],
            "canonical_leaf_atoms":basis["leaf_atom_count"],
            "exact_duplicate_savings":basis["exact_duplicate_savings"],
        },
        "frontier_projection":{
            "unresolved_predicates":new_frontier["unresolved_predicates"],
            "certificates":new_frontier["certificates"],
        },
        "hypergraph_projection":{"actions":new_hypergraph["actions"]},
        "proof_atom_basis":basis,
        "rules":[
            "REMOVE_ONLY_INDEPENDENTLY_CLOSED_DELEGATION_LEAF",
            "NO_SHARED_CERTIFICATE_OR_ACTION_MUTATION",
            "PA1_IDS_RECOMPUTED_FROM_EXACT_PROPOSITION_LITERALS",
            "ZERO_ACCEPTANCE_CAPABILITY_FAMILY_EXECUTION_OR_PROMOTION_CREDIT_FROM_RECOMPILE",
        ],
        "new_reality_units_consumed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }
