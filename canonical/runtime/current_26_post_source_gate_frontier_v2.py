from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_CURRENT_26_POST_SOURCE_GATE_FRONTIER_REDUCER_V2"

REG = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
EVID = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
OLD = "canonical/governance/CURRENT_27_ZERO_REALITY_FRONTIER_V2.json"
CERT = "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"
MATCHED = "canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json"
TDVER = "canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_PROMOTION_INTEGRATOR_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
SOURCE_ACT = "canonical/governance/DUAL_JUDGMENT_SOURCE_GATE_ACTIVATION_V1.json"
SOURCE_VER = "canonical/verification/DUAL_JUDGMENT_SOURCE_GATE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"

EXPECTED = {
    REG: "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
    EVID: "f99b00e6dca735ffa7a790a414155b4f69856cf0",
    OLD: "bab3876a1c4bd6a065d20d42b320df4b4b3fa519",
    CERT: "4b5517dbd12978f8ffe481fb775e85592c7790c8",
    MATCHED: "438e2775b64bee5ed6e792522ab35ebd0d6e1771",
    TDVER: "bed23f2e69d4bc8937d792b07b5812364cf26a85",
    SOURCE_ACT: "4211a0eee07c4758035d788c0be897d700c164cb",
    SOURCE_VER: "6ec5f6d808c88bf9ea728fb7f259edc3b4ae5a51",
}

MATCHED_PARENT_REQUIREMENTS = {
    "MATCHED_BRAIN_WITNESS_TARGET_ATOM_METRIC_BINDINGS_INDEPENDENT_PASS",
    "MATCHED_BRAIN_WITNESS_SCOPE_RELATIONS_INDEPENDENT_PASS",
}
DISCHARGED_SOURCE_REQUIREMENTS = {
    "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_FINANCE_JUDGMENT_SOURCE_GATE_PASS",
    "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_UNKNOWN_DOMAIN_JUDGMENT_SOURCE_GATE_PASS",
}
DIRECT_ELIGIBLE = {
    "FINANCE_UNCOVERED_SCOPE_AUDIT",
    "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
}

def _blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def _load(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def evaluate() -> dict[str, Any]:
    drift = {p: {"expected": h, "actual": _blob(p)} for p,h in EXPECTED.items() if _blob(p) != h}
    if drift:
        return {
            "schema": SCHEMA, "status": "FAIL_CLOSED__SOURCE_BLOB_DRIFT", "pass": False,
            "errors": ["SOURCE_BLOB_DRIFT"], "drift": drift,
            "execution_authority": False, "promotion_authority": False, "fresh_reality_authority": False,
        }

    reg, evid, old, cert, matched, tdver, source_act, source_ver = map(
        _load, [REG,EVID,OLD,CERT,MATCHED,TDVER,SOURCE_ACT,SOURCE_VER]
    )
    errors: list[str] = []

    claims = evid.get("claims") or []
    proved = {x.get("predicate_id") for x in claims if isinstance(x, Mapping) and x.get("state") == "PROVED"}
    predicates = [x.get("id") for x in (reg.get("predicates") or []) if isinstance(x, Mapping) and isinstance(x.get("id"), str)]
    unresolved = sorted(set(predicates) - proved)

    if len(predicates) != 38: errors.append("REGISTRY_COUNT_DRIFT")
    if len(proved) != 12: errors.append("PROVED_COUNT_NOT_12")
    if len(unresolved) != 26: errors.append("UNRESOLVED_COUNT_NOT_26")
    if "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR" not in proved: errors.append("TOOL_DISCOVERY_NOT_PROVED")
    if not str(tdver.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("TOOL_DISCOVERY_PROMOTION_NOT_INDEPENDENT_PASS")

    if not str(source_ver.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("DUAL_SOURCE_GATE_VERIFICATION_NOT_INDEPENDENT_PASS")
    verified_source = source_ver.get("verified") or {}
    if set(verified_source.get("discharged_requirements") or []) != DISCHARGED_SOURCE_REQUIREMENTS:
        errors.append("DUAL_SOURCE_GATE_VERIFIED_REQUIREMENT_SET_DRIFT")
    if verified_source.get("finance_source_admitted") is not True:
        errors.append("FINANCE_SOURCE_NOT_ADMITTED")
    if verified_source.get("unknown_domain_source_admitted") is not True:
        errors.append("UNKNOWN_DOMAIN_SOURCE_NOT_ADMITTED")
    if verified_source.get("direct_oracle_leaves_executed") is not False:
        errors.append("DIRECT_ORACLE_EXECUTION_STATE_DRIFT")
    if verified_source.get("global_fresh_reality_authority") is not False:
        errors.append("GLOBAL_FRESH_REALITY_OVERCLAIM")

    if set(source_act.get("discharged_requirements") or []) != DISCHARGED_SOURCE_REQUIREMENTS:
        errors.append("DUAL_SOURCE_ACTIVATION_REQUIREMENT_SET_DRIFT")
    direct_state = source_act.get("resulting_direct_protocol_state") or {}
    if direct_state.get("clean_direct_case_execution_eligible") is not True:
        errors.append("CLEAN_DIRECT_CASE_NOT_ELIGIBLE")
    if direct_state.get("global_fresh_reality_authority") is not False:
        errors.append("SOURCE_ACTIVATION_FRESH_REALITY_OVERCLAIM")

    old_ids = set(old.get("active_nondominated_certificate_ids") or [])
    cert_rows = [x for x in (cert.get("certificates") or []) if isinstance(x, Mapping)]
    candidate_rows = []
    for row in cert_rows:
        cid = row.get("id")
        targets = [t for t in (row.get("target_predicates") or []) if isinstance(t,str)]
        if cid in old_ids and any(t in unresolved for t in targets):
            candidate_rows.append(row)

    td_req = "INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_TOOL_DISCOVERY_PROTOCOL"
    if any(x.get("id") == "TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE" for x in candidate_rows):
        errors.append("STALE_TOOL_DISCOVERY_CERTIFICATE_RETAINED")

    raw_requirements = {
        r for row in candidate_rows for r in (row.get("requires") or []) if isinstance(r,str)
    }
    if td_req in raw_requirements:
        errors.append("STALE_TOOL_DISCOVERY_REQUIREMENT_RETAINED")
    if not DISCHARGED_SOURCE_REQUIREMENTS.issubset(raw_requirements):
        errors.append("SOURCE_GATE_REQUIREMENTS_NOT_PRESENT_IN_PRIOR_FRONTIER")

    zero_rows = []
    direct_ready_rows = []
    for row in candidate_rows:
        reqs = {r for r in (row.get("requires") or []) if isinstance(r,str)}
        remaining = reqs - DISCHARGED_SOURCE_REQUIREMENTS
        targets = {t for t in (row.get("target_predicates") or []) if isinstance(t,str) and t in unresolved}
        if remaining:
            zero_rows.append((row, remaining, targets))
        elif targets and targets.issubset(DIRECT_ELIGIBLE):
            direct_ready_rows.append((row, targets))
        elif targets:
            errors.append("CERTIFICATE_LOST_ALL_REQUIREMENTS_WITHOUT_DIRECT_ELIGIBILITY:" + str(row.get("id")))

    active_zero_ids = sorted(str(row.get("id")) for row,_,_ in zero_rows)
    active_requirements = sorted({r for _,reqs,_ in zero_rows for r in reqs})
    zero_covered = sorted({t for _,_,targets in zero_rows for t in targets})
    direct_ready = sorted({t for _,targets in direct_ready_rows for t in targets})

    if len(active_zero_ids) != 11: errors.append("ACTIVE_ZERO_CERTIFICATE_COUNT_NOT_11")
    if len(active_requirements) != 14: errors.append("ACTIVE_ZERO_REQUIREMENT_COUNT_NOT_14")
    if len(zero_covered) != 22: errors.append("ZERO_REALITY_COVERED_COUNT_NOT_22")
    if set(direct_ready) != DIRECT_ELIGIBLE: errors.append("DIRECT_ELIGIBLE_PREDICATE_SET_DRIFT")
    if len(direct_ready_rows) != 2: errors.append("DIRECT_READY_CERTIFICATE_COUNT_NOT_2")

    implications = [x for x in (matched.get("implications") or []) if isinstance(x, Mapping)]
    child_facts = sorted({
        f for edge in implications
        if edge.get("verified") is True and edge.get("independent") is True
        for f in (edge.get("if_all") or []) if isinstance(f,str)
    })
    matched_targets = sorted({t for edge in implications for t in (edge.get("then") or []) if isinstance(t,str)})
    if len(child_facts) != 16: errors.append("MATCHED_CHILD_FACT_COUNT_NOT_16")
    if len(matched_targets) != 8: errors.append("MATCHED_TARGET_COUNT_NOT_8")
    if not MATCHED_PARENT_REQUIREMENTS.issubset(set(active_requirements)):
        errors.append("MATCHED_PARENT_REQUIREMENTS_MISSING")

    primitive_zero = len(active_requirements) - len(MATCHED_PARENT_REQUIREMENTS) + len(child_facts)
    if primitive_zero != 28: errors.append("PRIMITIVE_ZERO_REALITY_WORK_UNIT_COUNT_NOT_28")

    ok = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__CURRENT_26_POST_SOURCE_GATE_FRONTIER__14_ZERO_REQUIREMENTS__11_ZERO_CERTIFICATES__"
            "28_PRIMITIVE_ZERO_REALITY_UNITS__2_DIRECT_PREDICATES_ELIGIBLE_BUT_FRESH_REALITY_UNAUTHORIZED__ZERO_CREDIT"
            if ok else "FAIL_CLOSED"
        ),
        "pass": ok,
        "errors": sorted(set(errors)),
        "live_world": {
            "registry_predicates": 38,
            "proved_predicates": 12 if ok else len(proved),
            "unresolved_predicates": 26 if ok else len(unresolved),
            "opus55_acceptance": "5/19_PASS__14/19_OPEN",
            "active_zero_reality_requirements": 14 if ok else None,
            "active_zero_reality_certificates": 11 if ok else None,
            "zero_reality_covered_predicates": 22 if ok else None,
            "primitive_zero_reality_work_units": 28 if ok else None,
            "matched_priority_child_facts": 16 if ok else None,
            "direct_reality_eligible_predicates": direct_ready if ok else [],
            "global_fresh_reality_authority": False,
        },
        "active_zero_reality_certificate_ids": active_zero_ids if ok else [],
        "active_zero_reality_required_propositions": active_requirements if ok else [],
        "zero_reality_covered_predicate_ids": zero_covered if ok else [],
        "matched_child_fact_ids": child_facts if ok else [],
        "discharged_zero_reality_requirements": sorted(DISCHARGED_SOURCE_REQUIREMENTS) if ok else [],
        "direct_reality_eligible_predicate_ids": direct_ready if ok else [],
        "direct_reality_execution_eligible": bool(ok and len(direct_ready) == 2),
        "direct_reality_execution_authorized_now": False,
        "next": (
            "DISCHARGE_28_PRIMITIVE_ZERO_REALITY_UNITS__PRIORITIZE_16_MATCHED_CHILD_FACTS__"
            "RECOMPUTE_FIXED_POINT_AFTER_EACH_VERIFIED_DELTA__DO_NOT_EXECUTE_DIRECT_REALITY_UNTIL_SEPARATELY_AUTHORIZED"
            if ok else "FAIL_CLOSED"
        ),
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }

if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
