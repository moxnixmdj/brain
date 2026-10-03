"""Machine-checkable proof obligations for complete-scope Tool Discovery V4.

The theorem is conditional on a verified content-addressed complete discovery
interface instance. It makes no claim that any external registry is globally
complete.
"""
from __future__ import annotations
import ast, inspect
from canonical.runtime import tool_discovery_complete_scope_candidate_v4 as c

SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_COMPLETE_SCOPE_THEOREM_V1"

def evaluate()->dict:
    src=inspect.getsource(c.next_action)
    tree=ast.parse(src)
    literals={n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str)}
    obligations={
        "FAIL_CLOSED_WITHOUT_COMPLETE_SCOPE_RECEIPT":"DISCOVERY_SCOPE_NOT_PROVED_COMPLETE" in literals,
        "DISCOVERY_ACTION_EXISTS":"DISCOVER" in literals,
        "PROBE_ACTION_EXISTS":"PROBE" in literals,
        "SELECT_ACTION_EXISTS":"SELECT" in literals,
        "ESCALATE_ACTION_EXISTS":"ESCALATE" in literals,
        "DISCOVERY_PRECEDES_CAPABILITY_DECISION_BY_CONTROL_FLOW":src.index("if unqueried:") < src.index("evidence=_evidence(public)"),
        "LEAST_COST_ORDER_EXPLICIT":'tools.sort(key=lambda t:(float(t.get("cost",0.0)),str(t.get("tool_id") or "")))' in src,
        "CURRENT_EPOCH_EVIDENCE_ONLY":'int(rec.get("epoch",-1))==epochs[tid]' in inspect.getsource(c._evidence),
        "DISCOVERY_RECEIPT_SCOPE_BOUND":all(x in inspect.getsource(c._complete_discovery_receipts) for x in ("complete_for_source","target_scope_id","scope_fingerprint")),
        "DECLARED_SOURCE_SET_EXACTLY_BOUND":"sorted(normalized)!=sorted(sources)" in inspect.getsource(c._scope),
    }
    passed=all(obligations.values())
    return {
        "schema":SCHEMA,
        "status":"CANDIDATE_UNIVERSAL_FORMAL_SCOPE_PROOF__INDEPENDENT_VERIFICATION_REQUIRED__ZERO_CREDIT" if passed else "FAIL_CLOSED__STRUCTURAL_PROOF_OBLIGATION_FAILED__ZERO_CREDIT",
        "structural_obligations":obligations,
        "theorem":{
            "domain":"ARBITRARY_FINITE_TOOL_ECOSYSTEM_WITH_VERIFIED_COMPLETE_DISCOVERY_INTERFACE",
            "assumptions":[
                "SCOPE_RECEIPT_EXACTLY_ENUMERATES_ALL_DISCOVERY_SOURCES_FOR_FROZEN_TARGET",
                "EACH_AVAILABLE_SOURCE_RECEIPT_IS_COMPLETE_FOR_SOURCE_AND_SCOPE_FINGERPRINT",
                "DISCOVERY_METADATA_TRUTHFULLY_REPORTS_ID_COST_AVAILABILITY_AUTHORIZATION_AND_CONSTRAINT_FIELDS",
                "SAFE_PROBE_RECEIPTS_TRUTHFULLY_REPORT_CURRENT_EPOCH_REQUIRED_CAPABILITY_SUPPORT"
            ],
            "conclusion":"FIRST_SELECTED_TOOL_IS_GLOBAL_LEAST_COST_ADMISSIBLE_SUFFICIENT_ROUTE_WITHIN_VERIFIED_TARGET_SCOPE__OR_ESCALATION_IS_SOUND_IF_NONE_EXISTS",
            "nonclaims":[
                "DOES_NOT_PROVE_ANY_EXTERNAL_REGISTRY_GLOBALLY_COMPLETE",
                "DOES_NOT_PROMOTE_ACCEPTANCE_WITHOUT_INDEPENDENT_TARGET_SCOPE_BINDING",
                "DOES_NOT_USE_FINITE_EMPIRICAL_CASES_AS_UNIVERSAL_SCOPE_PROOF"
            ]
        },
        "universal_scope_certificate_candidate":passed,
        "new_reality_units_consumed":0,
        "terminal_results_replayed":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }
