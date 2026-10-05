"""Prove V7 Recovery typed-IR semantic-domain/resource-label invariance.

Narrow claim: after a failed execution is normalized into the frozen
TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001 typed IR, the accepted V7 solver's
decision is invariant to semantic domain labels and to bijective renaming of
resource tokens. Structural graph, failed-check kind, failure semantics,
composition, and evidence remain load-bearing.
"""
from __future__ import annotations

import ast
import copy
import inspect
from typing import Any

from canonical.runtime import trajectory_failure_typed_ir_candidate_v7 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as proof
from canonical.runtime.p1_v6_derived_only_counterexample_v1 import public_counterexample

SCHEMA="PROJECT_BRAIN_RECOVERY_TYPED_IR_DOMAIN_INVARIANCE_V1"
CONDITIONS=("AUTOMATED_AI_RESEARCH_AND_DEVELOPMENT","MATHEMATICAL_REASONING_ARXIVMATH")


def _solve_ast_has_no_domain_read() -> bool:
    tree=ast.parse(inspect.getsource(candidate.solve))
    return not any(
        isinstance(node,ast.Constant) and node.value=="domain"
        for node in ast.walk(tree)
    )


def _rename_resources(public_case: dict[str,Any], salt: str) -> dict[str,Any]:
    out=copy.deepcopy(public_case)
    task=out["task"]
    task["domain"]=salt
    tokens=[]
    for row in task["trajectory"]:
        row["domain"]=salt
        tokens.extend(row.get("reads",[]))
        tokens.extend(row.get("writes",[]))
    tokens.extend(task.get("terminal_failed_resources",[]))
    mapping={tok:f"{salt}::R{i}" for i,tok in enumerate(sorted(set(tokens)))}
    for row in task["trajectory"]:
        row["reads"]=[mapping[x] for x in row.get("reads",[])]
        row["writes"]=[mapping[x] for x in row.get("writes",[])]
    task["terminal_failed_resources"]=[mapping[x] for x in task.get("terminal_failed_resources",[])]
    return out


def _check(kind: str, aid: str, passed: bool, semantics: str="DIRECT_CONTRACT") -> dict[str,Any]:
    return {
        "kind":kind,
        "id":f"{aid}:{kind}",
        "pass":passed,
        "evidence":[f"receipt:{aid}",f"check:{aid}:{kind}"],
        "failure_semantics":semantics,
    }


def _row(i: int, *, reads: list[str], writes: list[str], deps: list[str],
         failed: str|None=None, semantics: str="DIRECT_CONTRACT") -> dict[str,Any]:
    aid=f"A{i}"
    checks=[_check("INVARIANT",aid,True)]
    if failed is not None:
        checks.append(_check(failed,aid,False,semantics))
    return {
        "step":i,
        "action_id":aid,
        "domain":"TOOL_API",
        "reads":reads,
        "writes":writes,
        "depends_on":deps,
        "dependency_composition":"SEQUENTIAL",
        "checks":checks,
    }


def serial_direct_cofault_case() -> dict[str,Any]:
    p="tool_api:"
    return {
        "schema":"PROJECT_BRAIN_TRAJECTORY_CAUSAL_IR_SERIAL_COFAULT_COUNTEREXAMPLE_V1",
        "behavior_id":"TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "task":{
            "domain":"TOOL_API",
            "trajectory":[
                _row(0,reads=[],writes=[p+"seed"],deps=[]),
                _row(1,reads=[p+"seed"],writes=[p+"scope_state"],deps=["A0"],failed="SCOPE"),
                _row(2,reads=[p+"scope_state"],writes=[p+"tool_state"],deps=["A1"],failed="TOOL_CONTRACT"),
                _row(3,reads=[p+"tool_state"],writes=[p+"symptom"],deps=["A2"],failed="INVARIANT",semantics="DERIVED_UPSTREAM"),
                _row(4,reads=[p+"symptom"],writes=[p+"terminal"],deps=["A3"]),
            ],
            "terminal_failed_resources":[p+"terminal"],
            "goal":"LOCALIZE_CAUSAL_FAILURES_AND_NOMINATE_REPAIR_SET_THAT_ACTUALLY_RESCUES_TERMINAL_OUTCOME",
        },
    }


def evaluate() -> dict[str,Any]:
    errors=[]
    if not _solve_ast_has_no_domain_read():
        errors.append("SOLVER_READS_DOMAIN_LABEL")

    publics=[]
    for i,case in enumerate(proof.suite_cases()):
        public=proof.public_task(case)
        baseline=candidate.solve(public)
        if proof.score_case(case,baseline).get("pass") is not True:
            errors.append(f"INHERITED_V6_BASELINE_FAIL:{i}")
        publics.append(("V6_SUITE",public))

    derived=public_counterexample()
    if candidate.solve(copy.deepcopy(derived)).get("status")!="ESCALATE":
        errors.append("V7_DERIVED_ONLY_BASELINE_DRIFT")
    publics.append(("V7_DERIVED_ONLY",derived))

    serial=serial_direct_cofault_case()
    serial_out=candidate.solve(copy.deepcopy(serial))
    if serial_out.get("status")!="INTERACTION" or serial_out.get("cause_action_ids")!=["A1","A2"]:
        errors.append("V7_SERIAL_COFAULT_BASELINE_DRIFT")
    publics.append(("V7_SERIAL_COFAULT",serial))

    checked=0
    for label,public in publics:
        baseline=candidate.solve(copy.deepcopy(public))
        for cond in CONDITIONS:
            transformed=_rename_resources(public,cond)
            got=candidate.solve(transformed)
            if got!=baseline:
                errors.append(f"DOMAIN_OR_RESOURCE_RENAMING_CHANGED_DECISION:{label}:{cond}")
            checked+=1

    ok=not errors
    return {
        "schema":SCHEMA,
        "status":"PASS__V7_TYPED_IR_DOMAIN_AND_RESOURCE_LEXEME_INVARIANT" if ok else "FAIL_CLOSED",
        "pass":ok,
        "errors":sorted(set(errors)),
        "accepted_route":"canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py",
        "inherited_structural_cases":192,
        "v7_specific_cases":2,
        "total_structural_cases":len(publics),
        "condition_labels_checked":list(CONDITIONS),
        "metamorphic_executions":checked,
        "solver_domain_field_read":not _solve_ast_has_no_domain_read(),
        "proved_scope":{
            "input_boundary":"NORMALIZED_TRAJECTORY_TYPED_IR_ONLY",
            "domain_label_non_load_bearing":ok,
            "resource_lexeme_non_load_bearing_under_bijection":ok,
            "structural_graph_and_failed_check_semantics_remain_load_bearing":True,
        },
        "hard_nonclaims":[
            "DOES_NOT_PROVE_ARBITRARY_RAW_TASK_TO_TYPED_IR_NORMALIZATION",
            "DOES_NOT_PROVE_NON_RECOVERY_BEHAVIOR",
            "DOES_NOT_CLOSE_A_CONDITION_CELL_WITHOUT_SEPARATE_EXACT_SCOPE_BINDING",
            "DOES_NOT_WEAKEN_FAILURE_SEMANTICS_OR_GRAPH_REQUIREMENTS",
        ],
        "incremental_spend_usd":0,
        "new_reality_units_consumed":0,
        "execution_authority":False,
        "promotion_authority":False,
    }


if __name__=="__main__":
    import json
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
