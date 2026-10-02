"""Zero-terminal-evidence mutation preflight for the four frozen direct proof routes.

This module validates the *proof machinery*, not Brain capability.  Each route has
a hidden reference state, one known-good candidate, and predeclared mutations.
A preflight passes only when the independent oracle accepts the good candidate
and rejects every declared mutation.
"""
from __future__ import annotations
from copy import deepcopy


def _result(route, good_pass, mutation_rows):
    return {
        "route": route,
        "good_pass": bool(good_pass),
        "mutations": mutation_rows,
        "pass": bool(good_pass and mutation_rows and all(not x["accepted"] for x in mutation_rows)),
    }


def p0_oracle(hidden, candidate):
    req=set(hidden["requirements"])
    required_edges={tuple(x) for x in hidden["required_edges"]}
    edges={tuple(x) for x in candidate.get("edges",[])}
    exclusions=set(candidate.get("justified_exclusions",[]))
    typed=bool(candidate.get("types_consistent"))
    independent=bool(candidate.get("independent_acceptance"))
    traced={a for a,_ in edges}
    complete=all(r in traced or r in exclusions for r in req)
    return bool(complete and required_edges.issubset(edges) and typed and independent)


def p0_preflight():
    hidden={
        "requirements":["R_INPUT","R_FACTOR","R_OUTPUT"],
        "required_edges":[["R_INPUT","I_NORMALIZE"],["R_FACTOR","I_CALC"],["I_NORMALIZE","I_CALC"],["I_CALC","R_OUTPUT"]],
    }
    good={
        "edges":deepcopy(hidden["required_edges"]),
        "justified_exclusions":[],
        "types_consistent":True,
        "independent_acceptance":True,
    }
    mutations=[]
    variants={
        "DROP_REQUIRED_EDGE": lambda x: x["edges"].pop(1),
        "BYPASS_REQUIRED_INTERMEDIATE": lambda x: x["edges"].remove(["I_NORMALIZE","I_CALC"]),
        "DELETE_REQUIREMENT_TRACE": lambda x: x["edges"].remove(["R_FACTOR","I_CALC"]),
        "ADD_TYPE_INCONSISTENT_EDGE": lambda x: x.update(types_consistent=False),
        "REPLACE_INDEPENDENT_ACCEPTANCE_WITH_BUILDER_RECOMPUTATION": lambda x: x.update(independent_acceptance=False),
    }
    for name,fn in variants.items():
        bad=deepcopy(good); fn(bad)
        mutations.append({"id":name,"accepted":p0_oracle(hidden,bad)})
    return _result("P0_STRUCTURED_METHOD_GRAPH_DIRECT_PROOF",p0_oracle(hidden,good),mutations)


def p1_oracle(hidden, candidate):
    if hidden.get("nonidentifiable"):
        return bool(candidate.get("abstain") and candidate.get("request_discriminator"))
    return bool(
        candidate.get("critical_step")==hidden["cause_step"]
        and candidate.get("repair_target")==hidden["repair_target"]
        and candidate.get("repair_rescues") is True
        and candidate.get("symptom_only_repair_rescues") is False
    )


def p1_preflight():
    hidden={"cause_step":2,"repair_target":"AUTH_BINDING","nonidentifiable":False}
    good={
        "critical_step":2,"repair_target":"AUTH_BINDING",
        "repair_rescues":True,"symptom_only_repair_rescues":False,
        "abstain":False,"request_discriminator":False,
    }
    variants={
        "SHIFT_TO_DOWNSTREAM_SYMPTOM": lambda x: x.update(critical_step=4),
        "REMOVE_KEY_INVARIANT": lambda x: x.update(repair_target="UNKNOWN"),
        "SWAP_CAUSE_EFFECT": lambda x: x.update(critical_step=5,repair_target="TERMINAL_SYMPTOM"),
    }
    rows=[]
    for name,fn in variants.items():
        bad=deepcopy(good); fn(bad); rows.append({"id":name,"accepted":p1_oracle(hidden,bad)})
    amb_hidden={"nonidentifiable":True}
    amb_bad=deepcopy(good)
    rows.append({"id":"ADD_EQUIVALENT_CAUSES_WITHOUT_DISCRIMINATOR","accepted":p1_oracle(amb_hidden,amb_bad)})
    amb_good={"abstain":True,"request_discriminator":True}
    return {
        **_result("P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",p1_oracle(hidden,good),rows),
        "nonidentifiable_abstention_pass":p1_oracle(amb_hidden,amb_good),
    }


def p2_oracle(hidden, candidate):
    sections=set(candidate.get("sections",[]))
    claims=set(candidate.get("claims",[]))
    supported=set(hidden["supported_claims"])
    score=float(candidate.get("rubric_score",0))
    return bool(
        set(hidden["required_sections"]).issubset(sections)
        and claims.issubset(supported)
        and candidate.get("audience_priority")==hidden["audience_priority"]
        and candidate.get("native_structure_valid") is True
        and candidate.get("key_information_visible") is True
        and score>=float(hidden["minimum_score"])
    )


def p2_preflight():
    hidden={
        "required_sections":["EXEC_SUMMARY","ANALYSIS","RECOMMENDATION"],
        "supported_claims":["C1","C2","C3"],
        "audience_priority":"DECISION_FIRST",
        "minimum_score":0.80,
    }
    good={
        "sections":["EXEC_SUMMARY","ANALYSIS","RECOMMENDATION"],
        "claims":["C1","C2"],
        "audience_priority":"DECISION_FIRST",
        "native_structure_valid":True,
        "key_information_visible":True,
        "rubric_score":0.92,
    }
    variants={
        "REMOVE_REQUIRED_ANALYSIS": lambda x: x["sections"].remove("ANALYSIS"),
        "INSERT_UNSUPPORTED_POLISHED_CLAIM": lambda x: x["claims"].append("UNSUPPORTED"),
        "SWAP_AUDIENCE_PRIORITY": lambda x: x.update(audience_priority="DETAIL_FIRST"),
        "OBSCURE_KEY_INFORMATION": lambda x: x.update(key_information_visible=False),
        "BREAK_NATIVE_STRUCTURE": lambda x: x.update(native_structure_valid=False),
    }
    rows=[]
    for name,fn in variants.items():
        bad=deepcopy(good); fn(bad); rows.append({"id":name,"accepted":p2_oracle(hidden,bad)})
    return _result("P2_PROFESSIONAL_ARTIFACT_QUALITY_DIRECT_PROOF",p2_oracle(hidden,good),rows)


def p3_oracle(hidden, candidate):
    support=hidden["support"]
    out_claims=set(candidate.get("claims",[]))
    required=set(hidden["required_claims"])
    selected=set(candidate.get("selected_evidence",[]))
    uncertainty=set(candidate.get("uncertainty_markers",[]))
    unsupported=[c for c in out_claims if not (set(support.get(c,[])) & selected)]
    required_ok=required.issubset(out_claims)
    uncertainty_ok=set(hidden["required_uncertainty"]).issubset(uncertainty)
    relevant=set().union(*(set(support.get(c,[])) for c in out_claims)) if out_claims else set()
    budget_ok=len(selected)<=hidden["evidence_budget"]
    no_irrelevant=selected.issubset(relevant | set(hidden.get("required_conflict_evidence",[])))
    conflict_ok=set(hidden.get("required_conflict_evidence",[])).issubset(selected)
    return bool(not unsupported and required_ok and uncertainty_ok and budget_ok and no_irrelevant and conflict_ok)


def p3_preflight():
    hidden={
        "support":{"C1":["E1"],"C2":["E2","E3"]},
        "required_claims":["C1","C2"],
        "required_uncertainty":["C2_CONFLICT"],
        "required_conflict_evidence":["E2","E3"],
        "evidence_budget":3,
    }
    good={
        "claims":["C1","C2"],
        "selected_evidence":["E1","E2","E3"],
        "uncertainty_markers":["C2_CONFLICT"],
    }
    variants={
        "REMOVE_ONLY_SUPPORT": lambda x: x["selected_evidence"].remove("E1"),
        "INJECT_CONFLICT_WITHOUT_PRESERVATION": lambda x: x["selected_evidence"].remove("E3"),
        "DELETE_UNCERTAINTY": lambda x: x.update(uncertainty_markers=[]),
        "ADD_IRRELEVANT_VOLUME": lambda x: x["selected_evidence"].append("E_NOISE"),
        "TIGHTEN_BUDGET_BELOW_REQUIRED_SET": lambda x: None,
    }
    rows=[]
    for name,fn in variants.items():
        bad=deepcopy(good)
        local_hidden=deepcopy(hidden)
        if name=="TIGHTEN_BUDGET_BELOW_REQUIRED_SET":
            local_hidden["evidence_budget"]=2
        else:
            fn(bad)
        rows.append({"id":name,"accepted":p3_oracle(local_hidden,bad)})
    return _result("P3_EVIDENCE_AUDIENCE_SYNTHESIS_DIRECT_PROOF",p3_oracle(hidden,good),rows)


def run_all():
    rows=[p0_preflight(),p1_preflight(),p2_preflight(),p3_preflight()]
    passed=all(x["pass"] and x.get("nonidentifiable_abstention_pass",True) for x in rows)
    return {
        "schema":"PROJECT_BRAIN_FOUR_DIRECT_PROOF_MUTATION_PREFLIGHT_V1",
        "status":"PASS" if passed else "FAIL_CLOSED",
        "routes":rows,
        "fresh_terminal_evidence_consumed":0,
        "incremental_spend_usd":0,
    }


if __name__=="__main__":
    import json
    print(json.dumps(run_all(),sort_keys=True))
