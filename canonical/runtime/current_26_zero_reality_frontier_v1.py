from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_CURRENT_26_ZERO_REALITY_FRONTIER_REDUCER_V1"

REG = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
EVID = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
OLD = "canonical/governance/CURRENT_27_ZERO_REALITY_FRONTIER_V2.json"
CERT = "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"
MATCHED = "canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json"
TDVER = "canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_PROMOTION_INTEGRATOR_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"

EXPECTED = {
    REG: "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
    EVID: "4000854d577f7ab5f0146d21d16e91d017458431",
    OLD: "bab3876a1c4bd6a065d20d42b320df4b4b3fa519",
    CERT: "4b5517dbd12978f8ffe481fb775e85592c7790c8",
    MATCHED: "438e2775b64bee5ed6e792522ab35ebd0d6e1771",
    TDVER: "bed23f2e69d4bc8937d792b07b5812364cf26a85",
}

MATCHED_PARENT_REQUIREMENTS = {
    "MATCHED_BRAIN_WITNESS_TARGET_ATOM_METRIC_BINDINGS_INDEPENDENT_PASS",
    "MATCHED_BRAIN_WITNESS_SCOPE_RELATIONS_INDEPENDENT_PASS",
}
DIRECT_BLOCKED = [
    "FINANCE_UNCOVERED_SCOPE_AUDIT",
    "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
]

def _blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def _load(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def evaluate() -> dict[str, Any]:
    drift = {p: {"expected": h, "actual": _blob(p)} for p,h in EXPECTED.items() if _blob(p) != h}
    if drift:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED__SOURCE_BLOB_DRIFT", "pass": False, "errors": ["SOURCE_BLOB_DRIFT"], "drift": drift,
                "execution_authority": False, "promotion_authority": False, "fresh_reality_authority": False}

    reg, evid, old, cert, matched, tdver = map(_load, [REG,EVID,OLD,CERT,MATCHED,TDVER])
    errors: list[str] = []

    claims = evid.get("claims") or []
    proved = {x.get("predicate_id") for x in claims if isinstance(x, Mapping) and x.get("state") == "PROVED"}
    predicates = [x.get("id") for x in (reg.get("predicates") or []) if isinstance(x, Mapping) and isinstance(x.get("id"), str)]
    unresolved = sorted(set(predicates) - proved)

    if len(predicates) != 38: errors.append("REGISTRY_COUNT_DRIFT")
    if len(proved) != 12: errors.append("PROVED_COUNT_NOT_12")
    if len(unresolved) != 26: errors.append("UNRESOLVED_COUNT_NOT_26")
    if "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR" not in proved: errors.append("TOOL_DISCOVERY_NOT_PROVED")
    if not str(tdver.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"): errors.append("TOOL_DISCOVERY_PROMOTION_NOT_INDEPENDENT_PASS")

    old_ids = set(old.get("active_nondominated_certificate_ids") or [])
    cert_rows = [x for x in (cert.get("certificates") or []) if isinstance(x, Mapping)]
    active = []
    for row in cert_rows:
        cid = row.get("id")
        targets = [t for t in (row.get("target_predicates") or []) if isinstance(t,str)]
        if cid in old_ids and any(t in unresolved for t in targets):
            active.append(row)
    active_ids = sorted(str(x.get("id")) for x in active)
    reqs = sorted({r for x in active for r in (x.get("requires") or []) if isinstance(r,str)})
    covered = sorted({t for x in active for t in (x.get("target_predicates") or []) if isinstance(t,str) and t in unresolved})

    if "TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE" in active_ids: errors.append("STALE_TOOL_DISCOVERY_CERTIFICATE_RETAINED")
    td_req = "INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_TOOL_DISCOVERY_PROTOCOL"
    if td_req in reqs: errors.append("STALE_TOOL_DISCOVERY_REQUIREMENT_RETAINED")
    if len(active_ids) != 13: errors.append("ACTIVE_CERTIFICATE_COUNT_NOT_13")
    if len(reqs) != 16: errors.append("REQUIREMENT_COUNT_NOT_16")
    if len(covered) != 24: errors.append("ZERO_REALITY_COVERED_COUNT_NOT_24")

    implications = [x for x in (matched.get("implications") or []) if isinstance(x, Mapping)]
    child_facts = sorted({
        f for edge in implications
        if edge.get("verified") is True and edge.get("independent") is True
        for f in (edge.get("if_all") or []) if isinstance(f,str)
    })
    matched_targets = sorted({t for edge in implications for t in (edge.get("then") or []) if isinstance(t,str)})
    if len(child_facts) != 16: errors.append("MATCHED_CHILD_FACT_COUNT_NOT_16")
    if len(matched_targets) != 8: errors.append("MATCHED_TARGET_COUNT_NOT_8")
    if not MATCHED_PARENT_REQUIREMENTS.issubset(set(reqs)): errors.append("MATCHED_PARENT_REQUIREMENTS_MISSING")

    primitive = len(reqs) - len(MATCHED_PARENT_REQUIREMENTS) + len(child_facts)
    if primitive != 30: errors.append("PRIMITIVE_WORK_UNIT_COUNT_NOT_30")

    if any(x not in unresolved for x in DIRECT_BLOCKED): errors.append("DIRECT_BLOCKED_PREDICATE_STATE_DRIFT")

    ok = not errors
    return {
        "schema": SCHEMA,
        "status": "PASS__CURRENT_26_ZERO_REALITY_FRONTIER__16_REQUIREMENTS__13_CERTIFICATES__30_PRIMITIVE_WORK_UNITS__ZERO_CREDIT" if ok else "FAIL_CLOSED",
        "pass": ok,
        "errors": sorted(set(errors)),
        "live_world": {
            "registry_predicates": 38,
            "proved_predicates": 12 if ok else len(proved),
            "unresolved_predicates": 26 if ok else len(unresolved),
            "opus55_acceptance": "5/19_PASS__14/19_OPEN",
            "active_zero_reality_requirements": 16 if ok else None,
            "active_nondominated_certificates": 13 if ok else None,
            "zero_reality_covered_predicates": 24 if ok else None,
            "primitive_zero_reality_work_units": 30 if ok else None,
            "matched_priority_child_facts": 16 if ok else None,
            "direct_reality_blocked_predicates": DIRECT_BLOCKED if ok else None,
        },
        "active_nondominated_certificate_ids": active_ids if ok else [],
        "active_required_propositions": reqs if ok else [],
        "zero_reality_covered_predicate_ids": covered if ok else [],
        "matched_child_fact_ids": child_facts if ok else [],
        "retired_due_to_tool_discovery_promotion": {
            "certificate": "TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE",
            "requirement": td_req,
            "predicate": "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        },
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
