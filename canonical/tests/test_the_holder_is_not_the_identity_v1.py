"""Regression guards for the computed deictic holder-shape relation (iteration 5)."""
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

import the_holder_is_not_the_identity_v1 as tool  # noqa: E402
import instant_learning_in_a_new_environment_v1 as env  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "THE_HOLDER_IS_NOT_THE_IDENTITY_20261123_V1.json"
STORE = ROOT / "canonical" / "astra_runtime" / "state" / "COMPUTED_HOLDER_RELATION_V1.json"


def test_holder_shape_is_deictic_not_a_name_lookup():
    a = ((("seed", "X"),), (("copy", "X"),))
    b = ((("origin", "X"),), (("archive", "X"),))
    assert tool.holder_shape(a, "X") == ((0,), (1,))
    assert tool.holder_shape(b, "X") == ((0,), (1,))
    assert tool.shape_features(((0,), (1,)))["first_final_different"] is True
    assert tool.shape_features(((0,), (1,)))["max_holders<=1"] is True
    assert tool.shape_features(((0,), (0, 1), (1,)))["max_holders<=1"] is False
    assert not tool.contains_identity("holder_shape:first_final_different[probe_seed_content]", "seed")


def test_full_canonical_form_is_invariant_to_renaming_and_is_not_the_shipped_relation():
    a = ((("seed", "A"), ("other", "B")), (("copy", "A"), ("other", "B")))
    b = ((("origin", "X"), ("side", "Y")), (("archive", "X"), ("side", "Y")))
    assert tool.canonical_form(a) == tool.canonical_form(b)
    data = json.loads(RECEIPT.read_text(encoding="utf-8"))
    killed = data["verdict"]["R6_killed_designs_are_measured"]
    assert killed["full_canonical_trace_table_overwrite"]["abstentions"] == 43
    assert killed["full_canonical_trace_table_third"]["abstentions"] == 69
    assert "too fine" in killed["reason"]


def test_different_goal_content_refuses_and_store_deletion_refuses(tmp_path):
    different = ((("origin", "alpha_content"), ("side", "beta_content")),
                 (("archive", "alpha_content"), ("side", "beta_content")))
    terms = tool.terms_for_all_contents([different])
    assert not any("probe_seed_content" in text for text in terms)
    refused = tool.replay(STORE, [different], lambda _trace: False)
    assert refused["status"] == "REFUSED__GOAL_CONTENT_OR_TERMS_NOT_RECOMPUTED"
    assert refused["abstentions"] == 1
    missing = tmp_path / "missing.json"
    assert tool.replay(missing, [different], lambda _trace: False)["status"] == "REFUSED__NO_RELATION"


def test_receipt_pins_all_criteria_store_and_zeros():
    data = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert data["schema"] == tool.SCHEMA
    assert data["declared_before_the_run"] == tool.DECLARED_BEFORE_THE_RUN
    assert data["all_criteria_met"] is True
    assert all(row["MET"] for row in data["verdict"].values())
    r2 = data["verdict"]["R2_one_real_run_collapses_two_computed_statements"]
    assert len(r2["minimal_statements"]) == 2
    assert r2["judgments_on_runs"] == 1
    assert r2["questions_about_statements"] == 0
    assert r2["class_after"] == 1
    r3 = data["verdict"]["R3_exact_overwrite_and_prior_witnesses_fixed"]
    assert r3["prediction"]["false_accepts"] == 0
    assert r3["prediction"]["false_rejects"] == 0
    assert r3["prediction"]["abstentions"] == 0
    assert r3["prior_false_reject_witnesses"] == 4
    assert all(r3["witness_predictions"])
    r4 = data["verdict"]["R4_different_identity_names_and_external_store"]
    assert r4["third_prediction"]["status"] == "PREDICTED"
    assert r4["third_prediction"]["false_accepts"] == 0
    assert r4["third_prediction"]["false_rejects"] == 0
    assert r4["third_prediction"]["abstentions"] == 0
    assert r4["fit_identity_literals_in_store"] == []
    r5 = data["verdict"]["R5_fail_closed_and_what_not_to_save"]
    assert r5["different_content"]["status"] == "REFUSED__GOAL_CONTENT_OR_TERMS_NOT_RECOMPUTED"
    assert r5["deleted_store"]["status"] == "REFUSED__NO_RELATION"
    assert r5["raw_exact_experience"]["abstentions"] > 0
    assert data["cost"]["model_calls"] == 0
    assert data["cost"]["parameters_stored"] == 0
    assert data["cost"]["network_calls_at_run_time"] == 0
    store = json.loads(STORE.read_text(encoding="utf-8"))
    assert store["schema"] == tool.STORE_SCHEMA
    assert store["identity_literals"] == []
    assert store["relation"]["texts"] == data["store"]["texts"]
    assert all("holder_shape:" in text for text in store["relation"]["texts"])
    assert "goal content literal is still carried" in "\n".join(data["limits"])


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
