import copy
from canonical.runtime.astra_behavioral_calibration_001_evaluator_v3 import evaluate
from canonical.tests.test_astra_behavioral_calibration_001_evaluator import GOOD

def test_good():
    assert evaluate(GOOD)["all_passed"]

def test_weak_case3_test_strings_fail():
    x=copy.deepcopy(GOOD)
    x["case3"]["tests"]=["1 0 invalid","x","y","z"]
    assert not evaluate(x)["checks"]["case3_four_structured_tests"]

def test_wrong_503_window_fails():
    x=copy.deepcopy(GOOD)
    x["case4"]["bullets"][0]="Service returned 503 errors from 10:03 to 10:11."
    assert not evaluate(x)["checks"]["case4_fact_consistency"]

def test_vague_gpu_invariant_fails():
    x=copy.deepcopy(GOOD)
    x["case5"]["invariant"]="One GPU is available."
    assert not evaluate(x)["checks"]["case5_invariant"]
