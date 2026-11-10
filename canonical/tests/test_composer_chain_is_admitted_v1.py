"""A chain the composer picked must pass the admission gate before it runs.

Your own project already had the safeguard. `capability_selection_retrieval_v1.admit()`
returns DEFINITION_COUNT_REQUIRES_CODE_SYMBOL_SUBJECT for a source-code symbol counter
asked a question about a text file. `composer_route_v1.route()` never called it -- grep
count: 0.

Measured 2026-11-09: "how many unique lines in data.txt" routed to
['python.source.definition_count.v1'], which counts Python definitions, and then ran.

ToolGate (ACL 2026) names the rule: each tool is a Hoare contract, and the precondition
gates invocation. This is that gate, at the one place execution actually starts.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_composer_v1 as comp
from canonical.runtime import capability_selection_retrieval_v1 as csr
from canonical.swe_kernel import closed_loop_autonomous_controller_v1 as ctrl


def test_the_composer_alone_still_picks_the_wrong_tool():
    """Record the defect the gate exists for. If this ever passes, delete the gate."""
    from canonical.runtime import composer_route_v1 as croute
    routed = croute.route("how many unique lines in data.txt")
    assert routed.get("chain") == ["python.source.definition_count.v1"], routed


def test_admission_rejects_that_choice_and_the_gate_now_uses_it():
    reg = comp.load_registry()
    verdict = csr.admit("how many unique lines in data.txt",
                        "python.source.definition_count.v1",
                        reg["python.source.definition_count.v1"], ROOT)
    assert verdict["admitted"] is False
    assert verdict["reason"] == "DEFINITION_COUNT_REQUIRES_CODE_SYMBOL_SUBJECT"


def test_the_controller_refuses_the_unadmitted_chain_before_executing():
    """TWO independent gates, measured: the door refuses earlier, the chain gate names why."""
    learning = ctrl.solve_or_learn({"goal": "how many unique lines in data.txt",
                                    "task_id": "gate"}, learn=True)
    assert learning.get("pass") is False
    assert learning.get("status") == "FAIL_CLOSED__COMPOSER_ROUTE_NOT_ADMITTED", learning
    assert learning.get("executed") is False
    assert learning.get("side_effects_may_exist") is False
    assert learning["refused_steps"][0]["reason"] == "DEFINITION_COUNT_REQUIRES_CODE_SYMBOL_SUBJECT"

    read_only = ctrl.solve_or_learn({"goal": "how many unique lines in data.txt",
                                     "task_id": "gate"}, learn=False)
    assert read_only.get("pass") is False
    assert read_only.get("executed") is False
    assert read_only.get("status") == "FAIL_CLOSED__ROUTE_ADMISSION_REJECTED", read_only


def test_the_gate_does_not_refuse_a_capability_that_is_the_right_subject():
    """A definition_count question about CODE must still be admitted."""
    reg = comp.load_registry()
    verdict = csr.admit("how many functions are defined in calc.py",
                        "python.source.definition_count.v1",
                        reg["python.source.definition_count.v1"], ROOT)
    assert verdict.get("reason") != "DEFINITION_COUNT_REQUIRES_CODE_SYMBOL_SUBJECT"


def test_a_binding_refusal_is_NOT_treated_as_a_semantic_refusal():
    """The first version of the gate did this and broke a passing test.

    BINDING_REFUSED:target_path:0_type_compatible_existing_files_named is a fact about
    files that existed when the registry was built, not about this call -- the door
    binds its own output path. Gating on it cost a working route.
    """
    from canonical.runtime import composer_route_v1 as croute
    out = ctrl.solve_or_learn({"goal": "transform calc.py and synthesize a report",
                               "task_id": "bind"}, learn=False)
    # Whatever this returns, it must not be a semantic-subject refusal.
    for step in (out.get("refused_steps") or []):
        assert not str(step.get("reason") or "").startswith("BINDING_REFUSED")
