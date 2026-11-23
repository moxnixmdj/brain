"""Regression guards for the computed content-deictic pointer (iteration 6)."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = ROOT / "canonical" / "tools"
for path in (str(TOOLS), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

import the_content_is_not_a_literal_v1 as tool  # noqa: E402
import the_holder_is_not_the_identity_v1 as holder  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "THE_CONTENT_IS_NOT_A_LITERAL_20261123_V1.json"
STORE = ROOT / "canonical" / "astra_runtime" / "state" / "COMPUTED_CONTENT_POINTER_RELATION_V1.json"


def _initial_source_record() -> tool.ExecutedRun:
    trace = (
        (("p", "X"), ("q", "Y")),
        (("r", "X"), ("q", "Y")),
    )
    frames = (("mv", "-f", "p", "r"),)
    return tool.ExecutedRun(trace, frames)


def _delayed_source_record() -> tool.ExecutedRun:
    trace = (
        (("a", "A"),),
        (("late", "B"), ("a", "A")),
        (("out", "B"), ("a", "A")),
    )
    frames = (
        ("sh", "-c", 'printf %s "$0" > "$1"', "B", "late"),
        ("mv", "-f", "late", "out"),
    )
    return tool.ExecutedRun(trace, frames)


def test_content_pointer_is_computed_from_call_log_and_is_not_a_literal():
    initial = _initial_source_record()
    delayed = _delayed_source_record()
    assert tool.content_pointer(initial) == "X"
    assert tool.content_pointer(delayed) == "B"
    assert tool.moved_judge(initial) is True
    assert tool.moved_judge(delayed) is True
    assert tool.relocation_source(("mv", "-f", "p", "r")) == "p"
    assert tool.relocation_source(("sh", "-c", "true")) is None
    assert not tool.contains_literal("content:first_relocation_source", "source")
    assert tool.contains_literal("origin -> archive", "origin")
    store_text = STORE.read_text(encoding="utf-8")
    assert "probe_seed_content" not in store_text
    assert "alpha_content" not in store_text
    assert "delta_content" not in store_text
    assert tool.POINTER_TEXT in store_text


def test_replay_recomputes_pointer_on_two_unseen_content_literals():
    records = [_initial_source_record(), _delayed_source_record()]
    result = tool.replay(STORE, records, tool.moved_judge)
    assert result["status"] == "PREDICTED"
    assert result["false_accepts"] == 0
    assert result["false_rejects"] == 0
    assert result["abstentions"] == 0
    assert result["pointer_contents_recomputed_from_this_machine"] == ["B", "X"]
    assert result["terms_recomputed_from_this_machine"] == 16
    assert all(tool.POINTER_TEXT in text for text in result["texts"])


def test_pointerless_machine_and_old_literal_store_fail_closed(tmp_path):
    pointerless = tool.ExecutedRun(
        ((("a", "A"),), (("a", "A"),)),
        (("ls", "-1"),),
    )
    assert tool.content_pointer(pointerless) is None
    refused = tool.replay(STORE, [pointerless], tool.moved_judge)
    assert refused["status"] == "REFUSED__CONTENT_POINTER_NOT_RECOMPUTED"
    assert refused["abstentions"] == 1
    missing = tmp_path / "missing_relation.json"
    assert tool.replay(missing, [pointerless], tool.moved_judge)["status"] == "REFUSED__NO_RELATION"
    old = holder.replay(tool.OLD_STORE, [pointerless.trace], lambda _trace: False)
    assert old["status"] == "REFUSED__GOAL_CONTENT_OR_TERMS_NOT_RECOMPUTED"
    assert all("probe_seed_content" in text for text in old["missing"])


def test_receipt_pins_three_statements_two_judgments_and_literal_free_store():
    data = json.loads(RECEIPT.read_text(encoding="utf-8"))
    store = json.loads(STORE.read_text(encoding="utf-8"))
    assert data["schema"] == tool.SCHEMA
    assert data["declared_before_the_run"] == tool.DECLARED_BEFORE_THE_RUN
    assert data["all_criteria_met"] is True
    assert all(row["MET"] for row in data["verdict"].values())
    c2 = data["verdict"]["C2_three_pointer_statements_and_two_real_delayed_judgments"]
    assert len(c2["minimal_statements"]) == 3
    assert c2["judgment_budget_ceil_log2_class"] == 2
    assert c2["judgments_on_runs"] == 2
    assert c2["questions_about_statements"] == 0
    assert c2["class_after"] == 1
    assert c2["survivor"] == (
        "holder_shape:first_final_different[content:first_relocation_source] and "
        "holder_shape:max_holders<=1[content:first_relocation_source]"
    )
    assert data["content_pointer"]["text"] == tool.POINTER_TEXT
    assert store["schema"] == tool.STORE_SCHEMA
    assert store["content_pointer"]["text"] == tool.POINTER_TEXT
    assert store["evidence"]["judgments_on_runs"] == 2
    assert store["evidence"]["judgment_budget_ceil_log2_class"] == 2
    assert store["identity_literals"] == []
    assert store["content_literals"] == []
    assert store["relation"]["texts"] == data["store"]["texts"]
    assert data["store"]["identity_literal_leaks"] == []
    assert data["store"]["content_literal_leaks"] == []
    assert data["cost"]["model_calls"] == 0
    assert data["cost"]["parameters_stored"] == 0
    assert data["cost"]["network_calls_at_run_time"] == 0
    assert "the pointer requires an executor call log" in "\n".join(data["limits"])


def test_receipt_pins_new_literal_predictions_refusals_and_killed_designs():
    data = json.loads(RECEIPT.read_text(encoding="utf-8"))
    c1 = data["verdict"]["C1_prior_literal_store_refuses_and_terms_are_literal_free"]
    assert c1["old_store"]["status"] == "REFUSED__GOAL_CONTENT_OR_TERMS_NOT_RECOMPUTED"
    assert c1["term_identity_literal_leaks"] == []
    assert c1["term_content_literal_leaks"] == []
    c3 = data["verdict"]["C3_exact_new_content_held_out_prediction"]["prediction"]
    c4 = data["verdict"]["C4_third_new_names_and_no_literals_in_store"]
    assert c3["status"] == c4["prediction"]["status"] == "PREDICTED"
    assert c3["false_accepts"] == c3["false_rejects"] == c3["abstentions"] == 0
    assert c4["prediction"]["false_accepts"] == 0
    assert c4["prediction"]["false_rejects"] == 0
    assert c4["prediction"]["abstentions"] == 0
    assert c3["pointer_contents_recomputed_from_this_machine"] == ["delta_content"]
    assert c4["prediction"]["pointer_contents_recomputed_from_this_machine"] == ["epsilon_content"]
    assert c4["identity_literals_in_store"] == []
    assert c4["content_literals_in_store"] == []
    c5 = data["verdict"]["C5_fail_closed_deletion_restore_raw_and_old_store"]
    assert c5["pointerless_machine"]["status"] == "REFUSED__CONTENT_POINTER_NOT_RECOMPUTED"
    assert c5["pointerless_machine"]["abstentions"] == 39
    assert c5["deleted_store"]["status"] == "REFUSED__NO_RELATION"
    assert c5["restored_store"]["status"] == "PREDICTED"
    assert c5["raw_exact_experience"]["abstentions"] == 258
    assert c5["relation_abstentions"] == 0
    c6 = data["verdict"]["C6_killed_designs_are_measured"]
    assert c6["naive_initial_content_pointer"]["errors"] > 0
    assert c6["raw_exact_experience"]["abstentions"] > 0
    assert c6["prior_full_canonical_trace_table"]["overwrite_abstentions"] == 43
    assert c6["prior_full_canonical_trace_table"]["third_name_abstentions"] == 69


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
