import copy, json
from pathlib import Path
from canonical.runtime.instruction_scope_shared_semantic_residual_verifier_v1 import ROOT, GOV, evaluate, load, verify

def _inputs():
    return (
        load(ROOT,"canonical/governance/TERMINAL_NOW_V16_RESIDUAL_NORMALIZATION_20261007_V1.json"),
        load(ROOT,"canonical/governance/PSTAR_INSTRUCTION_FOLLOWING_SCOPE_FIRST_APPLICATION_20261007_V1.json"),
        load(ROOT,"canonical/governance/FIVE_PRIMITIVE_ROLE_SINGLE_SEMANTIC_FRONTIER_20261007_V1.json"),
        load(ROOT,"canonical/governance/M0_GLOBAL_SEMANTIC_DECOMPOSITION_NECESSITY_FALSIFIER_20261007_V1.json"),
        load(ROOT,GOV),
    )

def test_current_reduction_passes_fail_closed_verifier():
    x=verify()
    assert x["pass"] is True,x
    assert x["instruction_family_closed"] is False
    assert x["terminal"] is False
    assert x["terminal_credit_delta"]==0

def test_positive_p_forced_reopens_distinct_mechanism_question():
    vals=[copy.deepcopy(x) for x in _inputs()]
    vals[1]["pstar_routes"]["P"]="FORCED"
    assert "PSTAR_POSITIVE_P_NO_LONGER_NOT_FORCED" in evaluate(*vals)

def test_shared_frontier_generic_generator_reversal_fails():
    vals=[copy.deepcopy(x) for x in _inputs()]
    vals[2]["shared_frontier"]["generic_new_implementation_generator_required"]=True
    assert "SHARED_FRONTIER_NOW_REQUIRES_GENERIC_GENERATOR" in evaluate(*vals)

def test_false_terminal_closure_fails():
    vals=[copy.deepcopy(x) for x in _inputs()]
    vals[4]["terminal_effect"]["terminal"]=True
    assert "FALSE_CLOSURE_OR_TERMINAL_PROMOTION" in evaluate(*vals)

def test_credit_leak_fails():
    vals=[copy.deepcopy(x) for x in _inputs()]
    vals[4]["accounting"]["acceptance_credit_delta"]=1
    assert "CREDIT_LEAK" in evaluate(*vals)
