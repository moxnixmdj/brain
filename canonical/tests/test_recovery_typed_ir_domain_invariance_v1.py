from __future__ import annotations
from canonical.runtime.recovery_typed_ir_domain_invariance_v1 import (
    CONDITIONS,_rename_resources,_solve_ast_has_no_domain_read,evaluate,
)
from canonical.runtime import trajectory_failure_typed_ir_candidate_v4 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v4 as proof

def test_solver_does_not_read_domain_label():
    assert _solve_ast_has_no_domain_read()

def test_full_168_by_2_metamorphic_matrix():
    cases=proof.suite_cases()
    assert len(cases)==168
    checked=0
    for case in cases:
        public=proof.public_task(case)
        baseline=candidate.solve(public)
        assert proof.score_case(case,baseline)["pass"]
        for cond in CONDITIONS:
            transformed=_rename_resources(public,cond)
            assert candidate.solve(transformed)==baseline
            checked+=1
    assert checked==336

def test_nonbijective_resource_change_is_not_claimed_safe():
    case=proof.generate_case(1001,pattern="SINGLE",domain="RESEARCH",kind="DEPENDENCY")
    public=proof.public_task(case)
    baseline=candidate.solve(public)
    transformed=_rename_resources(public,CONDITIONS[0])
    # Destroy resource equality/dataflow instead of merely renaming it.
    transformed["task"]["terminal_failed_resources"]=["missing-resource"]
    assert candidate.solve(transformed)!=baseline

def test_evaluate_is_narrow_zero_credit_pass():
    out=evaluate()
    assert out["pass"],out
    assert out["metamorphic_executions"]==336
    assert out["proved_scope"]["domain_label_non_load_bearing"] is True
    assert out["proved_scope"]["resource_lexeme_non_load_bearing_under_bijection"] is True
    assert "DOES_NOT_PROVE_ARBITRARY_RAW_TASK_TO_TYPED_IR_NORMALIZATION" in out["hard_nonclaims"]
    assert out["incremental_spend_usd"]==0
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
