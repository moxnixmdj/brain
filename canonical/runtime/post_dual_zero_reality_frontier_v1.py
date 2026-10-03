from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_POST_DUAL_ZERO_REALITY_FRONTIER_V1"
PATHS={
 "dominance":"canonical/governance/CURRENT_27_INFORMATION_DOMINANCE_V1.json",
 "frontier":"canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json",
 "activation":"canonical/governance/DUAL_JUDGMENT_SOURCE_GATE_ACTIVATION_V1.json",
 "verification":"canonical/verification/DUAL_JUDGMENT_SOURCE_GATE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
}
EXPECTED={
 PATHS["dominance"]:"fae786d6051277865ed6ecde69be5da98e2bf509",
 PATHS["frontier"]:"4b5517dbd12978f8ffe481fb775e85592c7790c8",
 PATHS["activation"]:"4211a0eee07c4758035d788c0be897d700c164cb",
 PATHS["verification"]:"6ec5f6d808c88bf9ea728fb7f259edc3b4ae5a51",
}

def blob(path):
    b=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def evaluate():
    errors=[]
    drift={p:{"expected":h,"actual":blob(p)} for p,h in EXPECTED.items() if blob(p)!=h}
    if drift:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED__SOURCE_BLOB_DRIFT","pass":False,"errors":["SOURCE_BLOB_DRIFT"],"drift":drift}

    dom,front,act,ver=(load(PATHS[k]) for k in ("dominance","frontier","activation","verification"))
    if not str(ver.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("DUAL_ACTIVATION_NOT_INDEPENDENT_PASS")
    discharged=set(act.get("discharged_requirements") or [])
    verified=set((ver.get("verified") or {}).get("discharged_requirements") or [])
    if discharged != verified or len(discharged)!=2:
        errors.append("DISCHARGED_REQUIREMENT_SET_INVALID")
    if (ver.get("verified") or {}).get("acceptance_predicate_delta") != 0:
        errors.append("ACCEPTANCE_DELTA_NONZERO")
    if (ver.get("verified") or {}).get("global_fresh_reality_authority") is not False:
        errors.append("GLOBAL_FRESH_REALITY_OVERCLAIM")

    active_ids=set(dom.get("nondominated_certificate_ids") or [])
    certs=[c for c in front.get("certificates",[]) if c.get("id") in active_ids]
    if len(certs)!=16:
        errors.append("BASE_CERTIFICATE_COUNT_DRIFT")

    satisfied=[]
    active=[]
    for c in certs:
        reqs=set(c.get("requires") or [])
        if not reqs:
            errors.append("EMPTY_BASE_CERT_REQUIREMENT:"+str(c.get("id")))
            continue
        rem=sorted(reqs-discharged)
        if not rem:
            satisfied.append({
                "certificate_id":c["id"],
                "target_predicates":list(c["target_predicates"]),
                "discharged_requirements":sorted(reqs),
                "state":"ZERO_REALITY_PRECONDITION_SATISFIED__TARGET_ACCEPTANCE_STILL_OPEN",
            })
        else:
            row=dict(c)
            row["requires_remaining"]=rem
            active.append(row)

    active_requirements=sorted({r for c in active for r in c["requires_remaining"]})
    satisfied_targets=sorted({p for c in satisfied for p in c["target_predicates"]})
    active_targets=sorted({p for c in active for p in c["target_predicates"] if p not in {
        "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR",
        "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
        "RECOVERY_TERMINAL_NONINFERIOR",
        "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
    }})

    if len(satisfied)!=2:
        errors.append("SATISFIED_CERTIFICATE_COUNT_NOT_TWO")
    if {x["certificate_id"] for x in satisfied} != {
        "FINANCE_JUDGMENT_SOURCE_CERTIFICATE","UNKNOWN_DOMAIN_JUDGMENT_SOURCE_CERTIFICATE"
    }:
        errors.append("SATISFIED_CERTIFICATE_ID_SET_DRIFT")
    if len(active)!=14: errors.append("ACTIVE_CERTIFICATE_COUNT_NOT_14")
    if len(active_requirements)!=17: errors.append("ACTIVE_ZERO_REALITY_REQUIREMENT_COUNT_NOT_17")
    if len(active_targets)!=25: errors.append("ACTIVE_ZERO_REALITY_TARGET_COUNT_NOT_25")
    if set(satisfied_targets)!={"FINANCE_UNCOVERED_SCOPE_AUDIT","UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"}:
        errors.append("REALITY_READY_TARGET_SET_DRIFT")

    ok=not errors
    return {
      "schema":SCHEMA,
      "status":"PASS__POST_DUAL_FRONTIER__27_ACCEPTANCE_OPEN_ATOMS__17_ZERO_REALITY_REQUIREMENTS__2_SOURCE_ADMITTED_REALITY_READY_TARGETS__ZERO_CREDIT" if ok else "FAIL_CLOSED",
      "pass":ok,
      "errors":sorted(set(errors)),
      "acceptance_frontier":{"proved":11,"unresolved":27,"total":38,"family_acceptance":"4/19_PASS__15/19_OPEN"},
      "zero_reality_frontier":{
        "active_certificate_count":len(active),
        "active_requirement_count":len(active_requirements),
        "active_target_count":len(active_targets),
        "required_propositions":active_requirements,
      },
      "precondition_satisfied_but_acceptance_open":satisfied,
      "fresh_reality_ready_but_globally_held_predicates":satisfied_targets,
      "global_fresh_reality_authority":False,
      "next":"CONTINUE_17_ZERO_REALITY_REQUIREMENTS_TO_VERIFIED_FIXED_POINT__DO_NOT_EXECUTE_FINANCE_OR_UNKNOWN_DIRECT_LEAVES_UNTIL_SEPARATE_GLOBAL_MINIMUM_REALITY_AUTHORITY",
      "new_reality_units_consumed":0,
      "acceptance_predicate_delta":0,
      "family_acceptance_delta":0,
      "ownership_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
    }

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
