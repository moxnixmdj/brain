"""The composed run must try arms in cost order and let only the corpus's pytest decide.

These tests pin the *order* and the *fall-through*, not any corpus number: an arm that is refused
must not stop the next arm, and the cheapest arm must be offered first.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import composed_repair_one_run_v1 as composed  # noqa: E402


class TestTheOrderIsByMeasuredCost:
    def test_the_vocabulary_free_arm_is_offered_first(self) -> None:
        assert composed.ARMS[0] == "SYNTHESIZED_FROM_THE_FAILURE"

    def test_the_replayed_arm_is_last_and_says_it_is_a_replay(self) -> None:
        assert composed.ARMS[-1] == "RECORDED_LEARNED_REPAIR"


class TestOnlyTheJudgeDecides:
    def test_a_refused_candidate_increments_the_rejection_count_and_falls_through(
            self, tmp_path: pathlib.Path, monkeypatch) -> None:
        # a corpus where arm 1 proposes something and the judge refuses it, arm 2 proposes nothing
        root = tmp_path / "corpus"
        (root / "python_programs").mkdir(parents=True)
        (root / "json_testcases").mkdir()
        (root / "python_testcases").mkdir()
        (root / "python_programs" / "bug.py").write_text("def bug(x):\n    return 0\n")
        (root / "json_testcases" / "bug.json").write_text('[[1], 1]\n')  # json-lines: args, expected
        (root / "python_testcases" / "test_bug.py").write_text("def test1():\n    assert True\n")

        monkeypatch.setattr(composed.gen, "_install_alarm", lambda: True)
        monkeypatch.setattr(composed.synth, "synthesize_return",
                            lambda *a, **k: {"status": "FOUND", "expressions": ["1"]})
        monkeypatch.setattr(composed.synth, "install_return",
                            lambda source, name, expression: source.replace("return 0", "return 1"))
        monkeypatch.setattr(composed.gen, "score", lambda *a, **k: 1)
        monkeypatch.setattr(composed, "judged", lambda *a, **k: {"returncode": 1, "tail": []})
        monkeypatch.setattr(composed.gen, "repair_task",
                            lambda *a, **k: {"stage": "NOT_REPAIRED__NO_IMPROVING_CANDIDATE"})

        row = composed.measures_one(root, "bug", budget_s=1, per_example_timeout=0.01,
                                    verify_timeout=1, recorded={})
        assert row["stage"] == "NOT_REPAIRED__NO_IMPROVING_CANDIDATE"
        assert row["arms_tried"] == ["SYNTHESIZED_FROM_THE_FAILURE", "REWRITE_FAMILIES"]
        assert row["arms_rejected"] == 1

    def test_an_accepted_candidate_stops_the_run_and_names_its_arm(
            self, tmp_path: pathlib.Path, monkeypatch) -> None:
        root = tmp_path / "corpus"
        (root / "python_programs").mkdir(parents=True)
        (root / "json_testcases").mkdir()
        (root / "python_testcases").mkdir()
        (root / "python_programs" / "bug.py").write_text("def bug(x):\n    return 0\n")
        (root / "json_testcases" / "bug.json").write_text('[[1], 1]\n')  # json-lines: args, expected

        monkeypatch.setattr(composed.gen, "_install_alarm", lambda: True)
        monkeypatch.setattr(composed.synth, "synthesize_return",
                            lambda *a, **k: {"status": "FOUND", "expressions": ["1"]})
        monkeypatch.setattr(composed.synth, "install_return",
                            lambda source, name, expression: source.replace("return 0", "return 1"))
        monkeypatch.setattr(composed.gen, "score", lambda *a, **k: 1)
        monkeypatch.setattr(composed, "judged", lambda *a, **k: {"returncode": 0, "tail": []})

        row = composed.measures_one(root, "bug", budget_s=1, per_example_timeout=0.01,
                                    verify_timeout=1, recorded={})
        assert row["stage"] == "REPAIRED"
        assert row["winner"] == "SYNTHESIZED_FROM_THE_FAILURE"
        assert row["arms_tried"] == ["SYNTHESIZED_FROM_THE_FAILURE"]
