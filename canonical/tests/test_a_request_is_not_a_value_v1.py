"""A REQUEST IS NOT A VALUE, AND A SUCCESS THAT DID NO WORK IS THE WORST OUTCOME.

Round A140 opened on one measurement:

    grounded_action_v1.act(
        "total the amounts by region in sales.csv and write it to summary.txt",
        root=<tmp holding sales.csv>)

    -> ok: True, status: VERIFIED_ACTION, capability_id: CAP_FS_WRITE_V1
       inputs: {'output_path': 'summary.txt',
                'text': '<the goal sentence, verbatim>'}

    summary.txt did not exist on the first run of this, and when it did appear it contained the request
    sentence. THE AGGREGATION NEVER HAPPENED. The machine copied what it was asked to do into a file and
    called that verified.

Four mechanisms combined to produce that, and each is pinned here by the behaviour it is supposed to
produce rather than by naming a function:

  1. `text` was treated as a META parameter and filled with the goal sentence (`world_binding_v1`),
  2. a destination without a slash -- "to summary.txt" -- was invisible, so one was invented elsewhere,
  3. a capability that declares nothing to prove counted as VERIFIED (`_check_expect`),
  4. memory could overrule fresh evidence, so a bad route became permanent (`grounded_action_v1`).

The last two are pinned in `test_gate_accepts_a_failed_repair_v1.py`, which tests the production checker
directly. This file covers 1 and 2, end to end, through the real front door.
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile

import pytest

_HERE = pathlib.Path(__file__).resolve()
_ROOT = _HERE.parents[2]
for _p in (str(_ROOT), str(_ROOT / "canonical" / "runtime")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from canonical.runtime import grounded_action_v1 as GA  # noqa: E402
from canonical.runtime import world_binding_v1 as WB  # noqa: E402


# ------------------------------------------------------------------------------------------
# 1. The binding layer
# ------------------------------------------------------------------------------------------
def test_a_content_slot_is_never_filled_with_the_request():
    """`text` is CONTENT. `goal`/`task`/`objective` are META, because a capability that ASKS receives a question.

    Conflating them meant `CAP_FS_WRITE_V1` was handed the request sentence as the text to write, which is
    how a file came to contain `"total the amounts by region in sales.csv and write it to summary.txt"`.
    """
    goal = "total the amounts by region in sales.csv and write it to summary.txt"
    registry = GA.load_registry()
    for cid, entry in registry.items():
        inputs = WB.complete_inputs(goal, _ROOT, entry).get("inputs") or {}
        for key, value in inputs.items():
            if key.lower() in ("goal", "task", "objective", "query", "question"):
                continue
            assert str(value) != goal, (cid, key, value)


def test_a_stated_operand_is_read_even_when_unquoted():
    """"for the text PROJECT BRAIN" states a value. Refusing it let a DECODER win a GENERATION task."""
    assert WB._text_marked_in("Generate a QR code for the text PROJECT BRAIN and save it as x.png.") == \
        "PROJECT BRAIN"
    assert WB._text_marked_in("write the text hello world into out.txt") == "hello world"
    # ...and no value is invented when the sentence names only a KING of content:
    assert WB._text_marked_in("Generate a QR code image from a text string.") is None


# ------------------------------------------------------------------------------------------
# 2. The destination
# ------------------------------------------------------------------------------------------
def test_a_destination_needs_no_slash():
    """A person names a file as "summary.txt". The pattern demanded a "/" and so saw nothing."""
    assert WB.named_destination("write it to summary.txt") == "summary.txt"
    assert WB.named_destination('write "hello" into out.txt') == "out.txt"
    assert WB.named_destination("save the report as dir/report.md") == "dir/report.md"
    # prose is not a filename
    assert WB.named_destination("pass it to grep") is None
    assert WB.named_destination("write it to the screen") is None


# ------------------------------------------------------------------------------------------
# 3. End to end, through the front door
# ------------------------------------------------------------------------------------------
def test_the_exact_request_that_lied_never_claims_verified():
    """THE MEASUREMENT THIS FILE EXISTS FOR.

    It may refuse. It may fail. It must NOT report VERIFIED_ACTION while `summary.txt` is absent, because
    nothing in this sentence can be done by one capability: it asks for an aggregation AND a write.
    """
    with tempfile.TemporaryDirectory() as tmp:
        (pathlib.Path(tmp) / "sales.csv").write_text("region,amount\nnorth,10\nsouth,20\n", encoding="utf-8")
        result = GA.act(
            "total the amounts by region in sales.csv and write it to summary.txt", root=tmp)
        summary = pathlib.Path(tmp) / "summary.txt"
        if result.get("status") == "VERIFIED_ACTION":
            pytest.fail(
                "reported VERIFIED_ACTION for work that cannot have been done: "
                + json.dumps({"inputs": result.get("inputs"),
                              "summary_exists": summary.exists(),
                              "expect": result.get("expect")}, default=str)[:400])
        assert not summary.exists(), "a refused task must not have produced its artifact"


def test_a_stated_value_is_written_to_the_stated_file():
    """The same capability, asked something it CAN do, must actually do it.

    This is the positive control: the fixes above must not simply make the front door refuse everything.
    """
    with tempfile.TemporaryDirectory() as tmp:
        result = GA.act('write "hello world" into out.txt', root=tmp)
        target = pathlib.Path(tmp) / "out.txt"
        assert result.get("status") == "VERIFIED_ACTION", result.get("status")
        assert target.is_file(), "VERIFIED_ACTION with no file is the defect this round is about"
        assert target.read_text(encoding="utf-8").strip() == "hello world"
        # and the destination was the one that was NAMED, not an invented tmp path
        assert (result.get("inputs") or {}).get("output_path") == "out.txt", result.get("inputs")


def test_a_git_question_that_can_be_answered_is_answered_with_real_commits():
    """The routed capability must return the thing asked for, read from the repository, not a claim."""
    result = GA.act("show me the last five git commits", root=_ROOT)
    assert result.get("status") == "VERIFIED_ACTION", result.get("status")
    receipt = result.get("result") or {}
    rows = receipt.get("rows") or []
    assert len(rows) == 5, [len(rows), receipt.get("observed_effect")]
    for row in rows:
        assert row.get("sha") and row.get("subject"), row
    assert (receipt.get("observed_effect") or {}).get("commit_count") == 5


# ------------------------------------------------------------------------------------------
# 4. A demonstrated case is a witness to a SHAPE, never to a VALUE
# ------------------------------------------------------------------------------------------
def test_a_demonstrated_fixture_never_stands_in_for_the_data_the_goal_named():
    """THE THIRD INSTANCE OF THE SAME DEFECT, and the one that was hardest to see.

    `capability_forge_v1` records the first test case a module ran on, so the capability carries the
    fixture's inputs as `_forged_defaults`. `world_binding_v1` then used them whenever the goal was silent --
    reasonably, since a demo is the only witness to what a slot ACCEPTS.

    Measured 2026-11-23: asked to "sum the amount column in sales.csv", the forged `sum_csv_column` was
    handed the forge fixture's bytes --

        'item,amount\nalpha,12.5\nbeta,27.5\ngamma,10.0\n'

    -- and the binding was reported as `filled_from_demonstrated_case`. Any number it returned would be a true
    statement about a file the person never mentioned, presented as the answer about theirs.

    The rule this repository already states is: SAVE THE RULE, NEVER THE TRACE. A payload slot is left
    missing, which makes the capability unbindable instead of confidently wrong about someone else's data.
    """
    forged = {cid: entry for cid, entry in GA.load_registry().items() if "sum_csv_column" in cid}
    if not forged:
        pytest.skip("the ordinary capabilities have not been forged on this machine")
    cid, entry = next(iter(forged.items()))
    fixture = (entry.get("_forged_defaults") or {}).get("csv_table")
    assert fixture, "this machine's forged row carries no demonstrated fixture, so the case cannot arise"

    with tempfile.TemporaryDirectory() as tmp:
        (pathlib.Path(tmp) / "sales.csv").write_text("region,amount\nnorth,10\n", encoding="utf-8")
        binding = WB.complete_inputs("sum the amount column in sales.csv", tmp, entry,
                                     goal_paths=["sales.csv"])
        bound = (binding.get("inputs") or {}).get("csv_table")
        assert bound != fixture, (
            "the forge fixture was substituted for the file the goal named: " + repr(str(bound)[:80]))
        assert "csv_table" in (binding.get("missing") or []) or bound is None, binding


def test_a_payload_slot_is_named_by_its_own_vocabulary():
    """The rule is read from the slot's name, which is vocabulary the registry already uses."""
    for payload in ("csv_table", "text", "records", "sample", "content", "body"):
        assert WB._is_payload_slot(payload), payload
    for reference in ("output_path", "archive_path", "repo_root", "limit", "op", "target"):
        assert not WB._is_payload_slot(reference), reference


# ------------------------------------------------------------------------------------------
# 5. A report about something is not that something
# ------------------------------------------------------------------------------------------
def test_a_security_report_is_not_a_per_region_total():
    """THE WORST FALSE PASS THIS ROUND FOUND, reproduced end to end.

    Asked for `"total the amounts by region in data.csv and write it to summary.txt"`, the machine selected
    `python.source.taint_flow.v1` -- a SECURITY TAINT ANALYSER -- wrote its report into `summary.txt`,
    re-read those bytes from disk, confirmed the hash, and reported VERIFIED_ACTION. `summary.txt` held:

        {"analysis_model": "BOUNDED_NAME_BASED_DATAFLOW", "answer": "no", "files_scanned": 1,
         "finding_count": 0, "is_security_proof": false, ...}

    Every mechanism worked and the result was useless. A capability's `expect` proves what the ADAPTER did;
    nothing proved the bytes answer the QUESTION.
    """
    with tempfile.TemporaryDirectory() as tmp:
        (pathlib.Path(tmp) / "data.csv").write_text("region,amount\nnorth,10\nsouth,20\n", encoding="utf-8")
        (pathlib.Path(tmp) / "tally.py").write_text("print('x')\n", encoding="utf-8")
        result = GA.act("total the amounts by region in data.csv and write it to summary.txt", root=tmp)
        assert result.get("status") != "VERIFIED_ACTION", (
            "a taint report was accepted as a per-region total: "
            + json.dumps({"capability_id": result.get("capability_id"),
                          "expect": result.get("expect")}, default=str)[:300])


def test_the_gate_is_narrow_and_reads_the_sentence():
    """It fires only on arithmetic requests answered by a report, and never the other way round."""
    report = {"analysis_model": "X", "finding_count": 0, "is_security_proof": False}
    total = {"totals": {"north": 15.0}, "sum": 35.0}

    # an arithmetic request answered by a report -> refused, and it names what it saw
    reason = GA._answers_the_arithmetic_asked("total the amounts by region in data.csv", report)
    assert reason and reason.startswith("A_REPORT_ANSWERS_A_DIFFERENT_QUESTION"), reason
    # an arithmetic request answered by arithmetic -> nothing to say
    assert GA._answers_the_arithmetic_asked("total the amounts by region in data.csv", total) is None
    # a request FOR a report -> nothing to say, even though the result is a report
    assert GA._answers_the_arithmetic_asked("run a security analysis and write a report", report) is None
    # a request that asks for no arithmetic -> nothing to say
    assert GA._answers_the_arithmetic_asked("show me the last five git commits", report) is None
