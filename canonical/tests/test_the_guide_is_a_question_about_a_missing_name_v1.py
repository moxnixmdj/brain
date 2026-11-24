"""The right question is the missing name; the guide supplies the answer.

Regressions held here:

  1. a refusal names exactly one missing name and no question is invented from prose;
  2. a binding is admitted only when the guide's OWN printed output comes back AND a
     machine-made wrong binding does not;
  3. two bindings that both reproduce it are AMBIGUOUS and refused (one shot cannot identify);
  4. a foreign-memory pool and an obviously wrong binding never resolve;
  5. resolution transfers to a guide that was not used to design the mechanism;
  6. resolved facts live in an external JSON receipt, never in a weight;
  7. the agent's document->plan path uses the mechanism: a document that binds a name in one
     example and uses it in a later one now yields a plan for both.
"""
from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO / "canonical" / "tools"), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.runtime import guide_precondition_v1 as gp  # noqa: E402
from canonical.swe_kernel.perfect_algorithm_v1 import _plan_from_document  # noqa: E402
from canonical.tools import (  # noqa: E402
    the_guide_is_a_question_about_a_missing_name_v1 as subject,
)


def _job(statement: str, expected: list[str]) -> dict:
    return {"guide": "g", "block_line": 10, "kind": "python", "module": None,
            "_session": [statement], "expected": expected,
            "_statement": statement, "command": statement}


# 1 --------------------------------------------------------------------------- #

def test_the_question_is_read_from_the_refusal_not_invented():
    assert gp.missing_name(["NameError: name 's' is not defined"]) == "s"
    assert gp.missing_name("NameError: name 'Color' is not defined. Did you mean: 'id'?") == "Color"
    assert gp.missing_name("ValueError: no newline found") is None
    assert gp.missing_name(None) is None


def test_bindings_are_read_from_syntax_including_imports_and_definitions():
    assert gp.bound_names("s = SequenceMatcher(None, 'a', 'b')") == {"s"}
    assert gp.bound_names("import keyword as _keyword") == {"_keyword"}
    assert gp.bound_names("class Color(Enum):\n    RED = 1") >= {"Color", "RED"}
    assert gp.candidates([_job("data = [1, 2, 3]", [])], "data")


# 2, 3, 4 ------------------------------------------------------------------- #

def test_two_bindings_that_both_reproduce_are_refused_as_ambiguous():
    job = _job("x", ["1"])
    probes = [{"statement": "x = 1", "block_line": 1, "free": []},
              {"statement": "x = 1  # equivalent", "block_line": 2, "free": []}]
    got = gp.resolve(job, probes, question="x",
                     replay=lambda s: {"ok": True, "got": ["1"]},
                     compare=lambda got, want: {"matches": got == want})
    assert got["status"] == "REFUSED__AMBIGUOUS_BINDING"
    assert not got["resolved"] and got["reproducing"] == 2


def test_a_binding_the_example_cannot_identify_is_refused():
    job = _job("f()", ["ok"])
    probes = [{"statement": "def f(): return 'ok'", "block_line": 1, "free": []}]
    got = gp.resolve(job, probes, question="f",
                     replay=lambda s: {"ok": True, "got": ["ok"]},
                     compare=lambda got, want: {"matches": got == want},
                     separate=lambda binding: False)
    assert got["status"] == "REFUSED__BINDING_NOT_IDENTIFIED_BY_THE_EXAMPLE"
    assert got["unidentified"] == 1 and got["binding"] is None


def test_wrong_binding_mutates_a_literal_and_handles_imports():
    assert gp.wrong_binding("data = [1, 2, 3]", "data") != "data = [1, 2, 3]"
    assert "x" in gp.wrong_binding("text1 = '''a\nb\n'''", "text1")
    assert gp.wrong_binding("import keyword as _keyword", "_keyword") == \
        "_keyword = object()"


def test_the_seven_declared_gates_are_met():
    report = subject.measure()
    unmet = {k: v for k, v in report["verdict"].items() if not v["MET"]}
    assert not unmet, unmet
    assert report["questions"]["named_a_missing_name"] == 37
    assert report["questions"]["resolved"] >= 9
    assert report["questions"]["ambiguous_refused"] >= 1
    assert report["questions"]["unidentified_refused"] >= 1
    assert report["wrong_binding_reproduced"] == 0
    assert report["foreign_memory_resolved"] == 0
    assert report["held_out_guides_resolved"] >= 1
    assert report["decoys"]["not_separated"] == 0
    assert report["store"]["written_to_weights"] is False
    assert report["cost"]["model_calls"] == 0
    assert report["cost"]["network_calls_at_run_time"] == 0


def test_the_pre_registered_threshold_is_recorded_not_hidden():
    """The first run measured 13 reproductions; the identification gate refused 4, so the
    pre-registered absolute threshold of 10 measured 9. The old number is kept in the gate."""
    p2 = subject.judged(subject.measure())["P2_the_guide_answers_its_own_question"]
    assert "originally_declared" in p2
    assert p2["originally_declared"]["threshold"] == 10
    assert p2["originally_declared"]["met_as_declared"] is False


# 7 --------------------------------------------------------------------------- #

DOCUMENT = """>>> data = [10]

An unrelated example that prints something:

>>> statistics.median([1, 2, 3])
2

Now reuse the earlier binding:

>>> statistics.median(data)
10
"""


def test_the_agent_asks_the_missing_name_and_plans_the_later_example():
    got = _plan_from_document(DOCUMENT, ["statistics.median"], "compute a median")
    assert got["status"] == "PASS__PLAN_FROM_A_DOCUMENT", got
    assert got["resolved_sessions"] == 1
    assert "statistics.median(data)" in got["plan"]
    assert got["questions"][0]["question"] == "data"
    assert got["authority"] == "EXTERNAL_DOCUMENT_REPLAYED_AND_SELF_CHECKED"


def test_a_document_with_no_answer_refuses_instead_of_inventing_one():
    doc = """>>> statistics.median(data)
10
"""
    got = _plan_from_document(doc, ["statistics.median"], "compute a median")
    assert got["status"] != "PASS__PLAN_FROM_A_DOCUMENT"
    assert got["resolved_sessions"] == 0
