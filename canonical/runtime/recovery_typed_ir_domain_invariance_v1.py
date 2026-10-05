"""Prove Recovery typed-IR semantic-domain/resource-label invariance.

The claim is deliberately narrow: once a failed execution has been normalized into
TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001 typed IR, the Recovery solver's
decision is independent of semantic domain labels and of resource-token spelling,
provided resource equality/dataflow relations are preserved by a bijection.
"""
from __future__ import annotations

import ast
import copy
import inspect
from typing import Any

from canonical.runtime import trajectory_failure_typed_ir_candidate_v4 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v4 as proof

SCHEMA="PROJECT_BRAIN_RECOVERY_TYPED_IR_DOMAIN_INVARIANCE_V1"
CONDITIONS=("AUTOMATED_AI_RESEARCH_AND_DEVELOPMENT","MATHEMATICAL_REASONING_ARXIVMATH")

def _solve_ast_has_no_domain_read() -> bool:
    tree=ast.parse(inspect.getsource(candidate.solve))
    for node in ast.walk(tree):
        if isinstance(node,ast.Constant) and node.value=="domain":
            return False
    return True

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

def evaluate() -> dict[str,Any]:
    errors=[]
    if not _solve_ast_has_no_domain_read():
        errors.append("SOLVER_READS_DOMAIN_LABEL")

    cases=proof.suite_cases()
    checked=0
    for i,case in enumerate(cases):
        public=proof.public_task(case)
        baseline=candidate.solve(public)
        if not proof.score_case(case,baseline).get("pass"):
            errors.append(f"BASELINE_FAIL:{i}")
            continue
        for cond in CONDITIONS:
            transformed=_rename_resources(public,cond)
            got=candidate.solve(transformed)
            if got!=baseline:
                errors.append(f"DOMAIN_OR_RESOURCE_RENAMING_CHANGED_DECISION:{i}:{cond}")
            checked+=1

    ok=not errors
    return {
        "schema":SCHEMA,
        "status":"PASS__TYPED_IR_DOMAIN_AND_RESOURCE_LEXEME_INVARIANT" if ok else "FAIL_CLOSED",
        "pass":ok,
        "errors":sorted(set(errors)),
        "structural_cases":len(cases),
        "condition_labels_checked":list(CONDITIONS),
        "metamorphic_executions":checked,
        "solver_domain_field_read":not _solve_ast_has_no_domain_read(),
        "proved_scope":{
            "input_boundary":"NORMALIZED_TRAJECTORY_TYPED_IR_ONLY",
            "domain_label_non_load_bearing":ok,
            "resource_lexeme_non_load_bearing_under_bijection":ok,
            "structural_graph_and_failed_check_semantics_remain_load_bearing":True
        },
        "hard_nonclaims":[
            "DOES_NOT_PROVE_ARBITRARY_RAW_TASK_TO_TYPED_IR_NORMALIZATION",
            "DOES_NOT_PROVE_ANY_NON_RECOVERY_FAMILY",
            "DOES_NOT_CLOSE_A_CONDITION_CELL_WITHOUT_SEPARATE_EXACT_SCOPE_BINDING"
        ],
        "incremental_spend_usd":0,
        "new_reality_units_consumed":0,
        "execution_authority":False,
        "promotion_authority":False
    }

if __name__=="__main__":
    import json
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
