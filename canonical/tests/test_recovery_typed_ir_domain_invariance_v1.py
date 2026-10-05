from __future__ import annotations
import copy

from canonical.runtime.recovery_typed_ir_domain_invariance_v1 import (
    CONDITIONS,_rename_resources,_solve_ast_has_no_domain_read,evaluate,
    serial_direct_cofault_case,
)
from canonical.runtime import trajectory_failure_typed_ir_candidate_v7 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as proof
from canonical.runtime.p1_v6_derived_only_counterexample_v1 import public_counterexample


def test_solver_does_not_read_domain_label():
    assert _solve_ast_has_no_domain_read()


def test_full_192_by_2_metamorphic_matrix():
    cases=proof.suite_cases()
    assert len(cases)==192
    checked=0
    for case in cases:
        public=proof.public_task(case)
        baseline=candidate.solve(copy.deepcopy(public))
        assert proof.score_case(case,baseline)["pass"]
        for cond in CONDITIONS:
            transformed=_rename_resources(public,cond)
            assert candidate.solve(transformed)==baseline
            checked+=1
    assert checked==384


def test_v7_derived_only_case_is_domain_invariant():
    public=public_counterexample()
    baseline=candidate.solve(copy.deepcopy(public))
    assert baseline["status"]=="ESCALATE"
    for cond in CONDITIONS:
        assert candidate.solve(_rename_resources(public,cond))==baseline


def test_v7_serial_cofault_is_domain_invariant():
    public=serial_direct_cofault_case()
    baseline=candidate.solve(copy.deepcopy(public))
    assert baseline["status"]=="INTERACTION"
    assert baseline["cause_action_ids"]==["A1","A2"]
    for cond in CONDITIONS:
        assert candidate.solve(_rename_resources(public,cond))==baseline


def test_nonbijective_resource_change_is_not_claimed_safe():
    case=proof.generate_case(2001,pattern="SINGLE",domain="RESEARCH",kind="DEPENDENCY")
    public=proof.public_task(case)
    baseline=candidate.solve(copy.deepcopy(public))
    transformed=_rename_resources(public,CONDITIONS[0])
    transformed["task"]["terminal_failed_resources"]=["missing-resource"]
    assert candidate.solve(transformed)!=baseline


def test_failure_semantics_remains_load_bearing():
    public=serial_direct_cofault_case()
    direct=candidate.solve(copy.deepcopy(public))
    mutated=copy.deepcopy(public)
    for row in mutated["task"]["trajectory"]:
        for item in row["checks"]:
            if item["pass"] is False:
                item["failure_semantics"]="DERIVED_UPSTREAM"
    assert candidate.solve(mutated)!=direct


def test_evaluate_is_narrow_zero_credit_pass():
    out=evaluate()
    assert out["pass"],out
    assert out["accepted_route"]=="canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py"
    assert out["inherited_structural_cases"]==192
    assert out["v7_specific_cases"]==2
    assert out["metamorphic_executions"]==388
    assert out["proved_scope"]["domain_label_non_load_bearing"] is True
    assert out["proved_scope"]["resource_lexeme_non_load_bearing_under_bijection"] is True
    assert "DOES_NOT_PROVE_ARBITRARY_RAW_TASK_TO_TYPED_IR_NORMALIZATION" in out["hard_nonclaims"]
    assert out["incremental_spend_usd"]==0
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
