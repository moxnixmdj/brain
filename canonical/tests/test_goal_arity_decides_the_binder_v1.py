"""r86 -- three consecutive improvements to the instrument and the planner produced ZERO gain.

  r84  fixed the coverage bug (93 tasks never attempted)          -> 9/130, unchanged
  r85  fixed typing fidelity + made refusal honest (NOT_LOOKED)   -> 9/130, unchanged
  r86  reversed the loop to SEARCH-THEN-PLAN                      -> 9/130, unchanged

That constancy is the evidence. The planner was never the bottleneck: it produced a plan
for 9 tasks this round (up from 1) and only 2 of those won. Looking at WHY those 9 lost:

    enter-password : "Enter the password "0xMq" into BOTH text fields"
    login-user     : "username "dolores" AND password "xGta""
    enter-text-2   : "Type "leonie" in ALL UPPER CASE letters"

The binder writes ONE literal into ONE control. Every one of those needs two literals, two
fields, or a transform. The executor's model covers 32 of 130 goals (25%).
"""
import pathlib

import pytest

from canonical.runtime.goal_arity_v1 import goal_shape


def test_two_literals_are_two_writes():
    s = goal_shape('Login with the username "dolores" and password "xGta"')
    assert s["arity"] == 2
    assert not s["single_binding_suffices"]
    assert "needs 2 literals" in s["why_not"]


def test_one_literal_across_several_fields_is_not_one_write():
    s = goal_shape('Enter the password "0xMq" into both text fields and press submit.')
    assert s["arity"] == 1
    assert s["spreads_across_fields"]
    assert not s["single_binding_suffices"]


def test_a_transform_is_not_a_binding():
    s = goal_shape('Type "leonie" in all upper case letters in the text input')
    assert s["transform"] == ["upper"]
    assert not s["single_binding_suffices"]


def test_a_plain_single_value_is_the_only_case_the_executor_can_handle():
    s = goal_shape('Enter the item "Annis" in the text field and press Submit.')
    assert s["single_binding_suffices"]
    assert s["why_not"] == []


@pytest.mark.skipif(not pathlib.Path(
    "canonical/evaluation/bench/result_planned_v1.json").exists(), reason="no run recorded")
def test_the_executors_model_covers_only_a_quarter_of_the_suite():
    import json
    d = json.loads(pathlib.Path("canonical/evaluation/bench/result_planned_v1.json").read_text())
    single = [t for t in d["tasks"] if goal_shape(t.get("goal", ""))["single_binding_suffices"]]
    assert len(single) <= 40, f"expected about a quarter, got {len(single)}/130"
