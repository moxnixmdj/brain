"""P1 typed causal proof V7.

V7 preserves the independently verified V6 forward-causal intervention engine
and 192-case envelope, then adds a 48-case derived-only matrix. A visible
DERIVED_UPSTREAM check is a symptom witness, not a direct causal root. When no
DIRECT_CONTRACT failure is visible on the terminal causal slice, the correct
result is abstention/escalation rather than a fabricated repair.
"""
from __future__ import annotations
from typing import Any, Mapping
from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as v6

SCHEMA="PROJECT_BRAIN_TRAJECTORY_CAUSAL_IR_PROOF_V7"
DOMAINS=v6.DOMAINS
KINDS=v6.KINDS
PATTERNS=v6.PATTERNS


def generate_case(seed:int, *, pattern:str|None=None, domain:str|None=None, kind:str|None=None)->dict[str,Any]:
    return v6.generate_case(seed,pattern=pattern,domain=domain,kind=kind)


def public_task(case:Mapping[str,Any])->dict[str,Any]:
    return v6.public_task(case)


def execute_intervention(public_case:Mapping[str,Any], candidate:Mapping[str,Any])->dict[str,Any]:
    return v6.execute_intervention(public_case,candidate)


def derived_only_case(seed:int, *, domain:str, kind:str)->dict[str,Any]:
    if domain not in DOMAINS or kind not in KINDS:
        raise ValueError("DOMAIN_OR_KIND_INVALID")
    p=f"{domain.lower()}:"
    rows=[
        v6._row(0,domain,reads=[],writes=[p+"upstream"],depends_on=[]),
        v6._row(
            1,domain,reads=[p+"upstream"],writes=[p+"symptom"],
            depends_on=["A0"],failed_kind=kind,derived_failure=True,
        ),
        v6._row(
            2,domain,reads=[p+"symptom"],writes=[p+"terminal"],
            depends_on=["A1"],
        ),
    ]
    return {
        "schema":SCHEMA,
        "behavior_id":"TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "seed":seed,
        "task":{
            "domain":domain,
            "trajectory":rows,
            "terminal_failed_resources":[p+"terminal"],
            "goal":"LOCALIZE_CAUSAL_ROOT_OR_ABSTAIN_WHEN_ONLY_DERIVED_FAILURE_IS_VISIBLE",
        },
        "_oracle":{
            "status":"ESCALATE_DERIVED_ONLY",
            "derived_failure_action_ids":["A1"],
            "mechanism":kind,
        },
    }


def score_case(case:Mapping[str,Any], candidate:Mapping[str,Any])->dict[str,Any]:
    oracle=case.get("_oracle")
    if isinstance(oracle,Mapping) and oracle.get("status")=="ESCALATE_DERIVED_ONLY":
        if not isinstance(candidate,Mapping):
            return {"pass":False,"reason":"CANDIDATE_NOT_OBJECT"}
        expected_keys={
            "status","reason","derived_failure_action_ids",
            "supporting_receipts","information_request",
        }
        if set(candidate.keys())!=expected_keys:
            return {"pass":False,"reason":"DERIVED_ONLY_OUTPUT_SCHEMA_NOT_EXACT"}
        if candidate.get("status")!="ESCALATE":
            return {"pass":False,"reason":"DERIVED_ONLY_MUST_ESCALATE"}
        if candidate.get("reason")!="ONLY_DERIVED_UPSTREAM_FAILURES_VISIBLE":
            return {"pass":False,"reason":"DERIVED_ONLY_REASON_WRONG"}
        if candidate.get("derived_failure_action_ids")!=oracle["derived_failure_action_ids"]:
            return {"pass":False,"reason":"DERIVED_ONLY_ACTION_SET_WRONG"}
        if not candidate.get("supporting_receipts"):
            return {"pass":False,"reason":"DERIVED_ONLY_SUPPORTING_RECEIPTS_REQUIRED"}
        if not candidate.get("information_request"):
            return {"pass":False,"reason":"DERIVED_ONLY_INFORMATION_REQUEST_REQUIRED"}
        if "repair_targets" in candidate or "cause_action_id" in candidate:
            return {"pass":False,"reason":"DERIVED_ONLY_MUST_NOT_NOMINATE_CAUSE_OR_REPAIR"}
        iv=execute_intervention(public_task(case),candidate)
        if iv.get("terminal_rescued") is True:
            return {"pass":False,"reason":"DERIVED_ONLY_ABSTENTION_FALSE_RESCUE"}
        return {
            "pass":True,
            "reason":"PASS__DERIVED_ONLY_ABSTENTION",
            "intervention_rescue_verified":False,
            "intervention":iv,
        }
    return v6.score_case(case,candidate)


def baseline_cases()->list[dict[str,Any]]:
    return v6.suite_cases()


def derived_only_cases()->list[dict[str,Any]]:
    out=[]
    seed=30000
    for domain in DOMAINS:
        for kind in KINDS:
            out.append(derived_only_case(seed,domain=domain,kind=kind))
            seed+=1
    return out


def suite_cases()->list[dict[str,Any]]:
    return baseline_cases()+derived_only_cases()


def anti_shortcut_mutations()->list[dict[str,str]]:
    return v6.anti_shortcut_mutations()+[
        {
            "id":"DERIVED_ONLY_ROOT_OVERCLAIM",
            "property":"ONLY_DERIVED_UPSTREAM_FAILURES_VISIBLE_MUST_ABSTAIN_WITHOUT_CAUSE_OR_REPAIR",
        },
        {
            "id":"FAILURE_SEMANTICS_ERASURE",
            "property":"DERIVED_UPSTREAM_AND_DIRECT_CONTRACT_MUST_BE_CAUSALLY_DISTINCT",
        },
    ]
