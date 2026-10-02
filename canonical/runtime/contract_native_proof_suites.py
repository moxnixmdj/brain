"""Contract-native zero-cost terminal proof suites for four private-surface gaps.

These generators/oracles are *evaluation infrastructure*, not capability
implementations.  They provide deterministic, independently machine-checkable
cases for the frozen behavioral contracts that otherwise depended on
inaccessible/private benchmark surfaces.

No terminal cases are frozen here.  Cases are derived from a seed only after the
Brain candidate package is frozen.  The seed source is supplied by the caller
and must satisfy the canonical unpredictable-post-freeze selection policy.

Covered contracts
-----------------
1. STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001
2. TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001
3. EVIDENCE_TO_AUDIENCE_SYNTHESIS_001
4. PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001

The suites intentionally operate on the typed/explicit information boundary in
the contracts.  Arbitrary upstream natural-language interpretation is tested
elsewhere (M0).
"""
from __future__ import annotations

import itertools
import random
from typing import Any, Mapping

SCHEMA = "BRAIN_CONTRACT_NATIVE_PROOF_SUITES_V1"
CONTRACTS = {
    "STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001",
    "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
    "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001",
    "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001",
}


class ProofSuiteError(ValueError):
    pass


def _rng(seed: int) -> random.Random:
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ProofSuiteError("SEED_MUST_BE_INTEGER")
    return random.Random(seed)


def _structured_method_case(seed: int, difficulty: int) -> dict[str, Any]:
    r = _rng(seed)
    n = max(3, min(8, 3 + difficulty))
    factors = []
    for i in range(n):
        factors.append({
            "id": f"F{i}",
            "coefficient": r.choice([-5, -3, -2, -1, 1, 2, 3, 5]),
            "required": True,
            "units": "u",
        })
    # Public task input contains normalized applicable rules. Hidden probes are
    # oracle-only so output-equivalent shortcuts that omit factors are killed.
    visible_inputs = {f["id"]: r.randint(-7, 9) for f in factors}
    hidden_probes = [
        {f["id"]: r.randint(-11, 13) for f in factors}
        for _ in range(max(4, n))
    ]
    return {
        "schema": SCHEMA,
        "contract": "STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001",
        "seed": seed,
        "task": {
            "requirements": factors,
            "visible_inputs": visible_inputs,
            "required_output": "Y",
            "allowed_ops": ["weighted_sum"],
        },
        "_oracle": {"hidden_probes": hidden_probes},
    }


def _eval_candidate_graph(candidate: Mapping[str, Any], inputs: Mapping[str, int]) -> int:
    graph = candidate.get("graph")
    if not isinstance(graph, list):
        raise ProofSuiteError("CANDIDATE_GRAPH_NOT_LIST")
    total = 0
    seen: set[str] = set()
    for row in graph:
        if not isinstance(row, Mapping):
            raise ProofSuiteError("CANDIDATE_GRAPH_ROW_INVALID")
        fid = row.get("factor")
        coeff = row.get("coefficient")
        if not isinstance(fid, str) or fid in seen or fid not in inputs:
            raise ProofSuiteError("CANDIDATE_FACTOR_INVALID_OR_DUPLICATE")
        if not isinstance(coeff, int) or isinstance(coeff, bool):
            raise ProofSuiteError("CANDIDATE_COEFFICIENT_INVALID")
        seen.add(fid)
        total += coeff * int(inputs[fid])
    return total


def _score_structured_method(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    reqs = case["task"]["requirements"]
    expected = {x["id"]: x["coefficient"] for x in reqs if x["required"]}
    graph = candidate.get("graph")
    if not isinstance(graph, list):
        return {"pass": False, "reasons": ["GRAPH_NOT_LIST"]}
    actual: dict[str, int] = {}
    reasons: list[str] = []
    for row in graph:
        if not isinstance(row, Mapping):
            reasons.append("GRAPH_ROW_INVALID")
            continue
        fid=row.get("factor"); coeff=row.get("coefficient")
        if not isinstance(fid,str) or not isinstance(coeff,int) or isinstance(coeff,bool):
            reasons.append("GRAPH_ROW_FIELDS_INVALID")
            continue
        if fid in actual:
            reasons.append("DUPLICATE_FACTOR:" + fid)
        actual[fid]=coeff
    missing=sorted(set(expected)-set(actual))
    extra=sorted(set(actual)-set(expected))
    wrong=sorted(fid for fid in set(expected)&set(actual) if actual[fid]!=expected[fid])
    reasons += ["MISSING_FACTOR:"+x for x in missing]
    reasons += ["EXTRA_FACTOR:"+x for x in extra]
    reasons += ["WRONG_COEFFICIENT:"+x for x in wrong]

    if not reasons:
        probes=[case["task"]["visible_inputs"], *case["_oracle"]["hidden_probes"]]
        for i,inputs in enumerate(probes):
            gold=sum(expected[fid]*int(inputs[fid]) for fid in expected)
            try:
                got=_eval_candidate_graph(candidate, inputs)
            except ProofSuiteError as exc:
                reasons.append("GRAPH_EXECUTION:"+str(exc)); break
            if got != gold:
                reasons.append(f"PROBE_MISMATCH:{i}")
                break
    return {"pass": not reasons, "reasons": reasons}


def _trajectory_case(seed: int, difficulty: int) -> dict[str, Any]:
    r=_rng(seed)
    n=max(5,min(14,6+difficulty))
    cause=r.randint(1,n-3)
    steps=[]
    for i in range(n):
        if i < cause:
            state="OK"; invariant=True; symptom=False
        elif i == cause:
            state="FAULT_INJECTED"; invariant=False; symptom=False
        else:
            state="DOWNSTREAM_DEGRADED"; invariant=False; symptom=True
        steps.append({
            "step":i,
            "action":f"A{i}",
            "state":state,
            "invariant_pass":invariant,
            "terminal_symptom":symptom,
        })
    # Distractor downstream repair names are visible; only the causal repair
    # restores the injected fault and therefore the terminal state.
    repairs=[{"id":f"repair_{i}","targets_step":i} for i in range(cause,n-1)]
    r.shuffle(repairs)
    return {
        "schema":SCHEMA,
        "contract":"TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "seed":seed,
        "task":{"trajectory":steps,"repair_candidates":repairs},
        "_oracle":{"cause_step":cause,"repair_id":f"repair_{cause}"},
    }


def _score_trajectory(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    reasons=[]
    if candidate.get("cause_step") != case["_oracle"]["cause_step"]:
        reasons.append("CAUSE_STEP_WRONG")
    if candidate.get("repair_id") != case["_oracle"]["repair_id"]:
        reasons.append("REPAIR_TARGET_WRONG")
    evidence=candidate.get("evidence_steps")
    if not isinstance(evidence,list) or case["_oracle"]["cause_step"] not in evidence:
        reasons.append("CAUSAL_EVIDENCE_MISSING")
    # Rescue is exact in this generated transition system: only repair of the
    # injected cause restores all later invariants.
    rescued=(candidate.get("repair_id")==case["_oracle"]["repair_id"])
    if not rescued:
        reasons.append("RESCUE_FAILED")
    return {"pass":not reasons,"reasons":reasons,"rescue_pass":rescued}


def _synthesis_case(seed: int, difficulty: int) -> dict[str, Any]:
    r=_rng(seed)
    n=max(5,min(12,5+difficulty))
    evidence=[]
    required=[]
    optional=[]
    forbidden=[]
    uncertainty=[]
    audience=r.choice(["executive","engineer","auditor","operator"])
    for i in range(n):
        cid=f"C{i}"
        role=r.choice(["required","required","optional","forbidden"])
        if role=="required": required.append(cid)
        elif role=="optional": optional.append(cid)
        else: forbidden.append(cid)
        support=r.choice(["supported","supported","conflicted"]) if role!="forbidden" else "unsupported"
        if support=="conflicted":
            uncertainty.append(cid)
        evidence.append({
            "claim_id":cid,
            "role":role,
            "support":support,
            "provenance":[f"SRC-{i}-A", f"SRC-{i}-B"] if support=="conflicted" else [f"SRC-{i}-A"],
            "audience":audience,
        })
    # Guarantee at least one required claim so omission is meaningful.
    if not required:
        evidence[0]["role"]="required"; required.append("C0")
        if "C0" in optional: optional.remove("C0")
        if "C0" in forbidden: forbidden.remove("C0")
    return {
        "schema":SCHEMA,
        "contract":"EVIDENCE_TO_AUDIENCE_SYNTHESIS_001",
        "seed":seed,
        "task":{
            "audience":audience,
            "evidence":evidence,
            "format_constraints":{"max_claims":len(required)+len(optional),"ordered_required_first":True},
        },
        "_oracle":{
            "required":sorted(required),
            "allowed_optional":sorted(optional),
            "forbidden":sorted(forbidden),
            "uncertainty":sorted(uncertainty),
        },
    }


def _score_synthesis(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    selected=candidate.get("selected_claims")
    uncertainty=candidate.get("uncertainty_claims")
    if not isinstance(selected,list) or not isinstance(uncertainty,list):
        return {"pass":False,"reasons":["OUTPUT_SCHEMA_INVALID"]}
    selected=[str(x) for x in selected]
    uncertainty=[str(x) for x in uncertainty]
    o=case["_oracle"]; reasons=[]
    missing=sorted(set(o["required"])-set(selected))
    forbidden=sorted(set(o["forbidden"])&set(selected))
    unknown=sorted(set(selected)-set(o["required"])-set(o["allowed_optional"]))
    missing_uncertainty=sorted(set(o["uncertainty"])&set(selected)-set(uncertainty))
    extra_uncertainty=sorted(set(uncertainty)-set(selected))
    if missing: reasons.append("REQUIRED_CLAIMS_MISSING:"+",".join(missing))
    if forbidden: reasons.append("UNSUPPORTED_CLAIMS_SELECTED:"+",".join(forbidden))
    if unknown: reasons.append("UNKNOWN_CLAIMS:"+",".join(unknown))
    if missing_uncertainty: reasons.append("UNCERTAINTY_DROPPED:"+",".join(missing_uncertainty))
    if extra_uncertainty: reasons.append("UNCERTAINTY_WITHOUT_CLAIM:"+",".join(extra_uncertainty))
    max_claims=case["task"]["format_constraints"]["max_claims"]
    if len(selected)>max_claims: reasons.append("FORMAT_MAX_CLAIMS_EXCEEDED")
    if case["task"]["format_constraints"]["ordered_required_first"]:
        req_positions=[selected.index(x) for x in o["required"] if x in selected]
        opt_positions=[selected.index(x) for x in selected if x in o["allowed_optional"]]
        if req_positions and opt_positions and max(req_positions)>min(opt_positions):
            reasons.append("AUDIENCE_ORDER_CONSTRAINT_FAILED")
    return {"pass":not reasons,"reasons":reasons}


def _professional_plan_case(seed: int, difficulty: int) -> dict[str, Any]:
    r=_rng(seed)
    dims=["analysis","clarity","layout","audience_fit"]
    weights={d:r.randint(1,5) for d in dims}
    n=max(4,min(9,4+difficulty))
    actions=[]
    for i in range(n):
        actions.append({
            "id":f"E{i}",
            "scores":{d:r.randint(-2,4) for d in dims},
            "cost":r.randint(1,4),
            "supported":r.random()>0.15,
            "hard_violation":r.random()<0.10,
        })
    budget=max(3,min(9,2+difficulty))
    # Ensure at least one admissible action.
    actions[0]["supported"]=True; actions[0]["hard_violation"]=False
    return {
        "schema":SCHEMA,
        "contract":"PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001",
        "seed":seed,
        "task":{
            "rubric_weights":weights,
            "edit_candidates":actions,
            "edit_budget":budget,
            "objective":"maximize_explicit_rubric_gain_without_unsupported_or_hard_constraint_edits",
        },
        "_oracle":{},
    }


def _plan_gold(case: Mapping[str, Any]) -> tuple[tuple[str,...], int, int]:
    task=case["task"]; acts=task["edit_candidates"]; w=task["rubric_weights"]; budget=task["edit_budget"]
    best=None
    for mask in range(1<<len(acts)):
        chosen=[acts[i] for i in range(len(acts)) if mask&(1<<i)]
        if any((not a["supported"]) or a["hard_violation"] for a in chosen):
            continue
        cost=sum(a["cost"] for a in chosen)
        if cost>budget: continue
        score=sum(sum(w[d]*a["scores"][d] for d in w) for a in chosen)
        ids=tuple(sorted(a["id"] for a in chosen))
        # Max score, then min cost, then lexical IDs.
        key=(-score,cost,ids)
        if best is None or key<best[0]:
            best=(key,ids,score,cost)
    assert best is not None
    return best[1],best[2],best[3]


def _score_professional_plan(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    selected=candidate.get("selected_edits")
    if not isinstance(selected,list):
        return {"pass":False,"reasons":["OUTPUT_SCHEMA_INVALID"]}
    selected_tuple=tuple(sorted(str(x) for x in selected))
    gold,score,cost=_plan_gold(case)
    reasons=[]
    if len(selected_tuple)!=len(set(selected_tuple)):
        reasons.append("DUPLICATE_EDIT")
    known={a["id"]:a for a in case["task"]["edit_candidates"]}
    if any(x not in known for x in selected_tuple):
        reasons.append("UNKNOWN_EDIT")
    if not reasons:
        chosen=[known[x] for x in selected_tuple]
        if any(not a["supported"] for a in chosen): reasons.append("UNSUPPORTED_EDIT")
        if any(a["hard_violation"] for a in chosen): reasons.append("HARD_CONSTRAINT_VIOLATION")
        if sum(a["cost"] for a in chosen)>case["task"]["edit_budget"]: reasons.append("BUDGET_EXCEEDED")
    if selected_tuple!=gold:
        reasons.append("NOT_OPTIMAL_EXPLICIT_RUBRIC_PLAN")
    return {"pass":not reasons,"reasons":reasons,"gold_score":score,"gold_cost":cost}


def generate_case(contract: str, seed: int, difficulty: int = 3) -> dict[str, Any]:
    if contract not in CONTRACTS:
        raise ProofSuiteError("UNKNOWN_CONTRACT")
    if not isinstance(difficulty,int) or isinstance(difficulty,bool) or difficulty<1 or difficulty>5:
        raise ProofSuiteError("DIFFICULTY_MUST_BE_1_TO_5")
    if contract=="STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001":
        return _structured_method_case(seed,difficulty)
    if contract=="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001":
        return _trajectory_case(seed,difficulty)
    if contract=="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001":
        return _synthesis_case(seed,difficulty)
    return _professional_plan_case(seed,difficulty)


def public_task(case: Mapping[str, Any]) -> dict[str, Any]:
    """Return candidate-visible case with oracle data removed."""
    return {k:v for k,v in case.items() if k!="_oracle"}


def score_case(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    contract=case.get("contract")
    if contract=="STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001":
        return _score_structured_method(case,candidate)
    if contract=="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001":
        return _score_trajectory(case,candidate)
    if contract=="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001":
        return _score_synthesis(case,candidate)
    if contract=="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001":
        return _score_professional_plan(case,candidate)
    raise ProofSuiteError("UNKNOWN_CONTRACT")


def oracle_candidate(case: Mapping[str, Any]) -> dict[str, Any]:
    """Reference candidate used only to test the evaluation harness itself."""
    contract=case["contract"]
    if contract=="STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001":
        return {"graph":[{"factor":x["id"],"coefficient":x["coefficient"]} for x in case["task"]["requirements"]]}
    if contract=="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001":
        c=case["_oracle"]["cause_step"]
        return {"cause_step":c,"repair_id":case["_oracle"]["repair_id"],"evidence_steps":[c]}
    if contract=="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001":
        req=list(case["_oracle"]["required"])
        opts=list(case["_oracle"]["allowed_optional"])
        selected=req+opts
        return {"selected_claims":selected,"uncertainty_claims":[x for x in case["_oracle"]["uncertainty"] if x in selected]}
    if contract=="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001":
        gold,_,_=_plan_gold(case)
        return {"selected_edits":list(gold)}
    raise ProofSuiteError("UNKNOWN_CONTRACT")
