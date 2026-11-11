"""r85 -- a READ-ONLY state channel, and two input defects it exposed.

The r84 conclusion ("129/130 have no code-readable terminal state") was WRONG, and the
error was mine. MiniWob's own scorer reads `WOB_DONE_GLOBAL` through `Runtime.evaluate`.
The state was always readable as code; what made it unreadable was the r82 decision to
forbid `Runtime.evaluate` in the vision channel.

That decision is right for ACT and wrong for VERIFY. Reading cannot cause an effect, so
the capabilities are split: ACT stays pixels-and-input-only, VERIFY may ask typed,
read-only questions whose selector is DATA and never code.

Two input defects fell out of using it:
  * `type_text` sent `type: "char"` alone -- no keyDown, so no `input` event, so
    listener-bound fields never saw the text.
  * adding keyDown with a `text` field inserted each character TWICE: "abc" -> "aabbcc".
"""
import json
import pathlib

import pytest

from canonical.runtime import state_read_v1 as S


# --- the channel cannot act ------------------------------------------------- #
def test_the_channel_cannot_dispatch_input_or_navigate():
    for forbidden in ("Input.dispatchKeyEvent", "Input.dispatchMouseEvent",
                      "Page.navigate", "Runtime.callFunctionOn", "Debugger.enable"):
        assert forbidden not in S.ALLOWED_METHODS


def test_a_selector_that_could_be_code_is_refused():
    for good in ("#h", "tr.r", "input,textarea", "[id]"):
        assert S._selector_is_data(good), good
    for bad in ("h1){alert(1)}", "a;b", "x=>y", "`t`", "eval(x)", "a=b"):
        assert not S._selector_is_data(bad), bad


def test_an_unknown_question_is_refused_rather_than_evaluated():
    class Fake:
        ws = None
    ch = S.StateReadChannel.__new__(S.StateReadChannel)
    ch.ws = None; ch.i = 0; ch.reads = []
    with pytest.raises(RuntimeError, match="STATE_READ_UNKNOWN_QUESTION"):
        ch.ask("write_to_disk", "#x")


# --- the two typing defects -------------------------------------------------- #
def test_type_text_sends_a_full_key_press_and_never_double_inserts():
    src = pathlib.Path("canonical/runtime/bench_miniwob_v1.py").read_text()
    start = src.index("def type_text")
    body = src[start:src.index("def goal", start)]
    assert '"type": "keyDown"' in body and '"type": "keyUp"' in body
    assert '"type": "char"' in body
    # keyDown must NOT carry the character as well: that is what produced "aabbcc"
    assert '"type": "keyDown", "text"' not in body
    assert '{"type": "keyDown"}' in body


def test_list_of_hides_a_typed_value_and_value_of_does_not():
    """list_of reports innerText||value, which reads "" for a filled <input>."""
    q = S.QUESTIONS
    assert "innerText" in q["list_of"]
    assert "e.value" in q["value_of"]


# --- the planner's refusal is not a default ---------------------------------- #
def test_an_empty_capability_library_is_not_looked_not_no_route():
    from canonical.runtime import bench_capability_graph_v1 as G
    r = G.plan_to_reveal(frozenset({"name:a"}), "target", [])
    assert r["status"] == "NOT_LOOKED"


def test_the_planner_solves_once_it_is_given_a_real_capability():
    """My own r85 check used the wrong dict shape and read NO_ROUTE from a fine planner."""
    from canonical.runtime import bench_capability_graph_v1 as G
    cap = G.capability_for("Tab #2", {"the answer"}, "tab")
    r = G.plan_to_reveal(frozenset({"name:tab #1"}), "the answer", [cap])
    assert r["status"] == "SOLVED"
    assert len(r["plan"]) == 1


# --- the honest instrument --------------------------------------------------- #
def test_the_runner_records_why_a_task_was_not_attempted():
    src = pathlib.Path("canonical/evaluation/bench/run_planned_v1.py").read_text()
    assert "not_attempted_no_literal" in src
    assert 'r["plan_status"] = pr["status"]' in src
