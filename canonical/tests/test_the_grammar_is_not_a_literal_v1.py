"""Regression guards for transported declarative relation grammars (iteration 7)."""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = ROOT / "canonical" / "tools"
for path in (str(TOOLS), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

import recomputed_relation_grammar_v1 as generic  # noqa: E402
import the_content_is_not_a_literal_v1 as content_pointer_v1  # noqa: E402
import the_grammar_is_not_a_literal_v1 as tool  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "THE_GRAMMAR_IS_NOT_A_LITERAL_20261123_V1.json"
RAW_LOG = tool.RAW_LOG
NETWORK_MODEL_IMPORTS = {
    "urllib", "requests", "httpx", "socket", "http", "openai", "anthropic",
    "transformers", "torch", "tensorflow", "boto3",
}
VERIFIER_FORBIDDEN_IMPORTS = NETWORK_MODEL_IMPORTS | {
    "canonical", "intake", "subprocess",
    "the_content_is_not_a_literal_v1", "the_holder_is_not_the_identity_v1",
    "breadth_buys_what_repetition_cannot_v1", "the_goal_is_a_discriminator_v1",
}


def _imported_top_level_names(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "__import__":
            names.add("__import__")
    return names


def _moved_record() -> content_pointer_v1.ExecutedRun:
    return content_pointer_v1.ExecutedRun(
        ((("p", "X"), ("q", "Y")), (("r", "X"), ("q", "Y"))),
        (("mv", "-f", "p", "r"),),
    )


def _copied_record() -> content_pointer_v1.ExecutedRun:
    return content_pointer_v1.ExecutedRun(
        ((("p", "X"),), (("p", "X"), ("r", "X"))),
        (("cp", "-f", "p", "r"),),
    )


def _pointerless_record() -> content_pointer_v1.ExecutedRun:
    return content_pointer_v1.ExecutedRun(
        ((("a", "A"),), (("a", "A"),)),
        (("ls", "-1"),),
    )


def test_declarative_descriptor_changes_grammar_and_verifier_imports_are_disjoint():
    assert generic._grammar_errors(tool.GRAMMAR) == []
    assert tool.GRAMMAR["family"] == "computed_copy_cardinality_v1"
    assert tool.GRAMMAR["family"] != "computed_deictic_holder_shape_v1"
    texts = generic.term_texts(tool.GRAMMAR)
    assert len(texts) == 16
    assert all(text.startswith("copy:") for text in texts)
    assert not any("holder_shape:" in text for text in texts)
    assert generic.goal_verdict(tool.GRAMMAR, _moved_record()) is True
    assert generic.goal_verdict(tool.GRAMMAR, _copied_record()) is False
    verifier_imports = _imported_top_level_names(tool.VERIFIER)
    producer_imports = _imported_top_level_names(TOOLS / "the_grammar_is_not_a_literal_v1.py")
    assert not (verifier_imports & VERIFIER_FORBIDDEN_IMPORTS)
    assert not (verifier_imports & NETWORK_MODEL_IMPORTS)
    assert not (producer_imports & NETWORK_MODEL_IMPORTS)
    assert "recomputed_relation_grammar_v1" not in verifier_imports


def test_receipt_store_and_raw_log_pin_grammar_transport():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    store = json.loads(tool.STORE.read_text(encoding="utf-8"))
    raw_log = json.loads(RAW_LOG.read_text(encoding="utf-8"))
    assert receipt["schema"] == tool.SCHEMA
    assert receipt["declared_before_the_run"] == tool.DECLARED_BEFORE_THE_RUN
    assert receipt["all_criteria_met"] is True
    assert all(row["MET"] for row in receipt["verdict"].values())
    assert receipt["cost"]["model_calls"] == 0
    assert receipt["cost"]["parameters_stored"] == 0
    assert receipt["cost"]["network_calls_at_run_time"] == 0
    assert receipt["truth"] == {"achieved": False, "independent_verification_completed": False,
                                "section_6": "NOT_MET"}
    assert receipt["store"]["sha256"] == hashlib.sha256(tool.STORE.read_bytes()).hexdigest()
    assert receipt["raw_log"]["sha256"] == hashlib.sha256(RAW_LOG.read_bytes()).hexdigest()
    assert store["schema"] == generic.STORE_SCHEMA
    assert store["term_family"] == tool.GRAMMAR["family"]
    assert store["evidence"]["grammar_sha256"] == generic.canonical_hash(store["grammar"])
    assert store["evidence"]["raw_log_sha256"] == hashlib.sha256(RAW_LOG.read_bytes()).hexdigest()
    assert store["evidence"]["independent_verification_completed"] is False
    assert store["identity_literals"] == []
    assert store["content_literals"] == []
    assert store["cost"] == {"model_calls": 0, "parameters_stored": 0,
                             "network_calls_at_run_time": 0}
    assert store["relation"]["texts"] == [
        "copy:final_count==1[content:first_relocation_source]",
        "copy:max_count<=1[content:first_relocation_source]",
    ]
    assert raw_log["schema"] == generic.RAW_LOG_SCHEMA
    assert len(raw_log["machines"]) == 6
    assert sum(len(machine["records"]) for machine in raw_log["machines"]) == 2404
    assert all("expected" not in record
               for machine in raw_log["machines"] for record in machine["records"])
    identities, contents = generic._machine_literals(raw_log)
    store_text = json.dumps(store, sort_keys=True, ensure_ascii=False)
    assert not [literal for literal in identities + contents if generic.literal_scan(store_text, literal)]
    d3 = receipt["verdict"]["D3_fit_is_four_exact_minimal_statements"]
    assert (d3["fit_runs"], d3["truth_popcount"], d3["terms"], len(d3["minimal_statements"])) == (798, 240, 16, 4)
    d4 = receipt["verdict"]["D4_two_real_judgments_collapse_the_class"]
    assert (d4["usable_delayed_runs"], d4["separating_runs"],
            d4["judgment_budget_ceil_log2_class"], d4["judgments_on_runs"],
            d4["class_after"]) == (584, 28, 2, 2, 1)
    assert d4["survivor"] == ("copy:final_count==1[content:first_relocation_source] and "
                              "copy:max_count<=1[content:first_relocation_source]")
    d5 = receipt["verdict"]["D5_held_out_grammar_transport"]
    assert d5["held_delta"]["runs"] == 399 and d5["third_epsilon"]["runs"] == 584
    for prediction in (d5["held_delta"], d5["third_epsilon"]):
        assert prediction["false_accepts"] == prediction["false_rejects"] == prediction["abstentions"] == 0


def test_fresh_isolated_process_recomputes_pointer_terms_and_goal_from_each_machine(tmp_path):
    result = tool.fresh_process_verify(tool.STORE, tool.RAW_LOG, cwd=tmp_path)
    assert result["status"] == "PASS"
    assert result["exit_code"] == 0
    parsed = result["parsed"]
    assert parsed["status"] == "PASS"
    assert parsed["python_isolated_mode"] is True
    assert parsed["python_pid"] > 0
    assert parsed["normal_machines"] == 5
    assert parsed["pointerless_controls"] == 1
    assert parsed["terms_recomputed_per_machine"] == 16
    assert parsed["false_accepts"] == parsed["false_rejects"] == 0
    by_name = {machine["name"]: machine for machine in parsed["machines"]}
    assert set(by_name) == {"FIT_ALPHA", "FIT_BETA", "SELECT_GAMMA", "HELD_DELTA",
                            "THIRD_EPSILON", "NO_RELOCATION_SOURCE"}
    for name in ("FIT_ALPHA", "FIT_BETA", "SELECT_GAMMA", "HELD_DELTA", "THIRD_EPSILON"):
        row = by_name[name]
        assert row["status"] == "PREDICTED"
        assert row["terms_recomputed_from_this_machine"] == 16
        assert row["term_evaluations"] == row["runs"] * 16
        assert row["false_accepts"] == row["false_rejects"] == row["abstentions"] == 0
        assert len(row["pointer_contents_recomputed_from_this_machine"]) == 1
    assert by_name["NO_RELOCATION_SOURCE"]["status"] == "REFUSED__CONTENT_POINTER_NOT_RECOMPUTED"
    assert by_name["NO_RELOCATION_SOURCE"]["abstentions"] == 39


def test_hard_unseen_cli_failures_are_pinned_and_fail_closed(tmp_path):
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    expected = {
        "unknown_argument": "HARD_CLI_FAILURE__UNKNOWN_ARGUMENT",
        "missing_store": "REFUSED__NO_STORE",
        "missing_raw_log": "REFUSED__NO_RAW_LOG",
        "malformed_store": "REFUSED__MALFORMED_JSON",
        "malformed_raw_log": "REFUSED__MALFORMED_RAW_LOG",
        "mutated_grammar_hash": "REFUSED__GRAMMAR_DESCRIPTOR_HASH_MISMATCH",
        "unseen_primitive": "REFUSED__UNKNOWN_GRAMMAR_PRIMITIVE",
        "mutated_raw_log_hash": "REFUSED__RAW_LOG_HASH_MISMATCH",
        "stored_expected_labels": "REFUSED__RAW_LOG_HAS_STORED_VERDICTS",
        "no_normal_machine": "REFUSED__NO_NORMAL_MACHINE",
        "no_pointerless_control": "REFUSED__NO_POINTERLESS_CONTROL",
        "iteration_6_store_schema": "REFUSED__STORE_SCHEMA_MISMATCH",
    }
    pinned = {row["case"]: row["status"] for row in receipt["fresh_process"]["hard_cli_failures"]}
    assert pinned == expected
    rerun = tool.hard_cli_failures(tool.STORE, tool.RAW_LOG, cwd=tmp_path)
    assert len(rerun) == 12
    assert {row["case"]: row["status"] for row in rerun} == expected
    assert all(row["exit_code"] == 2 for row in rerun)
    assert all(row["status"] == row["expected_status"] for row in rerun)
    probe = receipt["fresh_process"]["separate_identity_probe"]
    assert probe["status"] == "UNAVAILABLE__SEPARATE_UID_DENIED"
    assert probe["independent_verification_completed"] is False


def test_replay_controls_fail_closed_and_grammar_mutations_are_refused(tmp_path):
    moved = _moved_record()
    copied = _copied_record()
    prediction = generic.predict_from_store(tool.STORE, [moved, copied])
    assert prediction["status"] == "PREDICTED"
    assert prediction["false_accepts"] == prediction["false_rejects"] == 0
    assert prediction["terms_recomputed_from_this_machine"] == 16
    assert prediction["predictions"] == [True, False]
    refused = generic.predict_from_store(tool.STORE, [_pointerless_record()])
    assert refused["status"] == "REFUSED__CONTENT_POINTER_NOT_RECOMPUTED"
    assert refused["abstentions"] == 1
    missing = tmp_path / "missing_relation.json"
    assert generic.predict_from_store(missing, [moved])["status"] == "REFUSED__NO_RELATION"
    restored = tmp_path / "restored_relation.json"
    restored.write_text(tool.STORE.read_text(encoding="utf-8"), encoding="utf-8")
    assert generic.predict_from_store(restored, [moved])["status"] == "PREDICTED"
    old = generic.predict_from_store(content_pointer_v1.STORE, [moved])
    assert old["status"] == "REFUSED__STORE_SCHEMA_MISMATCH"
    store = json.loads(tool.STORE.read_text(encoding="utf-8"))
    mutated = json.loads(json.dumps(store))
    mutated["grammar"]["terms"][0]["value"] = 99
    assert generic.predict_from_store(mutated, [moved])["status"] == "REFUSED__GRAMMAR_DESCRIPTOR_HASH_MISMATCH"
    unknown = json.loads(json.dumps(store))
    unknown["grammar"]["terms"][0]["kind"] = "UNSEEN_PRIMITIVE"
    unknown["evidence"]["grammar_sha256"] = generic.canonical_hash(unknown["grammar"])
    assert generic.predict_from_store(unknown, [moved])["status"] == "REFUSED__UNKNOWN_GRAMMAR_PRIMITIVE"


def test_killed_prototypes_old_stores_and_honest_limits_are_preserved():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    d1 = receipt["verdict"]["D1_goal_and_grammar_family_changed"]
    assert d1["iteration_6_content_pointer_store_on_copy_goal"]["false_rejects"] == 3
    assert d1["iteration_5_literal_store_on_copy_goal"]["status"] == "REFUSED__GOAL_CONTENT_OR_TERMS_NOT_RECOMPUTED"
    d6 = receipt["verdict"]["D6_fail_closed_controls"]
    assert d6["pointerless_machine"]["abstentions"] == 39
    assert d6["deleted_store"]["status"] == "REFUSED__NO_RELATION"
    assert d6["restored_store"]["status"] == "PREDICTED"
    assert d6["raw_exact_experience"]["abstentions"] > 0
    d7 = receipt["verdict"]["D7_killed_designs_are_preserved"]
    prototypes = d7["unsaved_producer_prototypes"]
    assert len(prototypes) == 3
    assert prototypes[0]["separating_runs"] == 0
    assert prototypes[1]["cause"].startswith("all separating verdicts")
    assert prototypes[2]["separating_runs"] == 28
    holder_control = d7["old_holder_grammar_on_copy_fit"]
    assert holder_control["exact_on_copy_goal_fit"] is True
    assert len(holder_control["minimal_statements"]) == 3
    limits = "\n".join(receipt["limits"])
    assert "not independent identity verification" in limits
    assert "no OSWorld 2.1" in limits
    assert "no capability registered" in limits


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
