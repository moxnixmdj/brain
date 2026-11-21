"""Pin the falsification: a constructed run did not beat cell labelling on TARBALL."""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = ROOT / "canonical" / "tools"
for path in (str(ROOT), str(TOOLS)):
    if path not in sys.path:
        sys.path.insert(0, path)

from intake.tests import test_purpose_gate_v1 as helper  # noqa: E402

import a_constructed_question_is_a_run_v1 as C  # noqa: E402

RECEIPTS = sorted((ROOT / "intake").glob("RECEIPT_CONSTRUCTED_QUESTION_*_20261121_V1.json"))


def test_four_declared_policies_are_recorded_and_keep_their_failure() -> None:
    assert {path.name for path in RECEIPTS} == {
        "RECEIPT_CONSTRUCTED_QUESTION_max_moved_20261121_V1.json",
        "RECEIPT_CONSTRUCTED_QUESTION_min_moved_20261121_V1.json",
        "RECEIPT_CONSTRUCTED_QUESTION_cell_split_20261121_V1.json",
        "RECEIPT_CONSTRUCTED_QUESTION_survivor_collapse_20261121_V1.json",
    }
    for path in RECEIPTS:
        report = json.loads(path.read_text(encoding="utf-8"))
        assert report["declared_before_the_runs"] == C.DECLARED
        assert report["all_criteria_met"] is False
        assert report["verdict"]["Q1_construction_without_verdict"]["MET"] is True
        assert report["verdict"]["Q2_one_harmful_answer_within_three_questions"]["MET"] is False
        assert report["verdict"]["Q4_no_worse_than_cell_labelling_control"]["MET"] is False
        assert report["cell_labelling_control"]["questions"] == 2


def test_no_construction_policy_produced_more_than_one_harmful_answer() -> None:
    for path in RECEIPTS:
        report = json.loads(path.read_text(encoding="utf-8"))
        assert report["constructed"]["harmful_answers"] <= 1
        assert report["constructed"]["questions"] >= 5


def test_image_projection_is_a_pure_lookup_without_verdicts() -> None:
    trace = helper._traces("BULK_COPY", pathlib.Path(__import__("tempfile").mkdtemp()))[0]
    generators = {"constant": lambda t, _t: (1,), "length": lambda t, _t: (len(t),)}
    assert C._image(generators, ["constant"], trace) == ((1,),)
    assert C._image(generators, ["constant", "length"], trace) == ((1,), (len(trace),))
