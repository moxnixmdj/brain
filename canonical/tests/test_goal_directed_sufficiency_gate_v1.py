"""Frozen regressions for the goal-directed sufficiency boundary.

These are local adversarial tests. They do not qualify arbitrary computer use,
GUI/DOM environments, own weights, a benchmark, independent cloud verification,
or §6. Truth fields remain false.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from canonical.runtime import goal_directed_sufficiency_gate_v1 as gate
from canonical.runtime import settlement_v1 as sv
from canonical.tools import goal_directed_sufficiency_gate_v1 as runner
from canonical.tools import goal_directed_sufficiency_independent_verifier_v1 as verifier

ROOT = Path(__file__).resolve().parents[2]


def _case(case_id: str) -> dict:
    return next(dict(c) for c in runner.frozen_cases() if c["case_id"] == case_id)


def _assess(case: dict, *, store_path: Path, write_store: bool = False) -> dict:
    return gate.assess(case, oracle=runner.oracle_for(str(case.get("oracle_name") or "none")),
                       store_path=store_path, write_store=write_store)


def test_frozen_decision_classes_and_truth_fields(tmp_path: Path) -> None:
    receipt = runner.evaluate(
        store_path=tmp_path / "nostore.json",
        write_store=False,
        receipt_path=None,
    )
    payload = receipt["canonical_payload"]
    decisions = {row["case_id"]: row for row in payload["decisions"]}
    assert set(decisions) == set(runner.EXPECTED)
    for case_id, expected in runner.EXPECTED.items():
        assert decisions[case_id]["decision"] == expected
    assert payload["counts"]["expected_decision_matches"] == 12
    assert payload["counts"]["admitted_arms"] == 3
    assert payload["counts"]["negative_arms"] == 9
    assert payload["counts"]["negative_refusals"] == 9
    assert decisions["A1_READ_ONLY"]["probes_executed"] == 0
    assert decisions["A2_CONFLICT_ASK"]["store_write"] is False
    assert decisions["A3_SAVE_ABSTRACT"]["store_write"] is False
    for row in payload["decisions"]:
        assert row["runtime_model_calls"] == 0
        assert row["runtime_network_calls"] == 0
        assert row["parameters_written"] == 0
        assert row["written_to_weights"] is False
    assert payload["truth"]["section_6"] == "NOT_DONE"
    assert payload["truth"]["truth_achieved"] is False
    assert payload["truth"]["completion_claim"] is False
    assert payload["truth"]["hardest_open_nov_2026_score"] == "NO_SCORE"


def test_caller_authority_and_raw_payload_are_denied(tmp_path: Path) -> None:
    case = _case("A3_SAVE_ABSTRACT")
    case["force_learn"] = True
    case["caller_flags"] = {"independent_verified": True}
    row = _assess(case, store_path=tmp_path / "authority.json")
    assert row["decision"] == gate.DENY_AUTHORITY
    assert "force_learn" in row["caller_authority_claims"]
    assert "caller_flags.independent_verified" in row["caller_authority_claims"]

    raw = _case("N2_RAW_RECORDING")
    payload = raw["candidate_store_payload"]
    assert {"path", "argv", "content", "reward"} <= set(payload)
    assert gate.forbidden_fields(payload)
    row = _assess(raw, store_path=tmp_path / "raw.json", write_store=True)
    assert row["decision"] == gate.DENY_RAW
    assert row["forbidden_fields"]


def test_reading_determines_action_without_a_question_or_store(tmp_path: Path) -> None:
    store = tmp_path / "read_only.json"
    row = _assess(_case("A1_READ_ONLY"), store_path=store, write_store=True)
    assert row["decision"] == gate.READ_ONLY
    assert row["reading"]["learning_forbidden"] is True
    assert row["probes_executed"] == 0
    assert row["store_write"] is False
    assert not store.exists()


def test_one_settled_closed_question_predicts_the_goal_probe(tmp_path: Path) -> None:
    store = tmp_path / "question.json"
    row = _assess(_case("A2_CONFLICT_ASK"), store_path=store, write_store=True)
    assert row["decision"] == gate.ASK_SETTLED
    question = row["question"]
    assert question["policy"] == "EIG"
    assert question["settlement"]["status"] == sv.SETTLED
    assert question["winner"] == "latest_email_authoritative"
    assert len(question["asked"]) == 1
    assert row["prediction"] not in {"UNKNOWN", ""}
    assert not row["prediction"].startswith("REFUSED")
    assert row["store_write"] is False
    assert not store.exists()


def test_all_negative_arms_refuse_and_never_write(tmp_path: Path) -> None:
    store = tmp_path / "negatives.json"
    for case in runner.frozen_cases():
        if case["case_id"] in runner.ADMITTED_IDS:
            continue
        store.unlink(missing_ok=True)
        row = _assess(case, store_path=store, write_store=True)
        assert row["decision"] == runner.EXPECTED[case["case_id"]]
        assert row["decision"].startswith("REFUSED")
        assert row["store_write"] is False
        assert not store.exists()


def test_hidden_state_and_fresh_admission_failures_are_named(tmp_path: Path) -> None:
    decisions = {row["case_id"]: row for row in
                 (runner.evaluate(store_path=tmp_path / "hidden.json",
                                  write_store=False, receipt_path=None)
                  ["canonical_payload"]["decisions"])}
    hidden = decisions["N3_SAME_STATE_HIDDEN_PRECONDITION"]
    assert hidden["decision"] == gate.DENY_INSUFFICIENT
    assert hidden["witness"]["kind"] == "SAME_OBSERVED_STATE_OPPOSITE_OUTCOMES"
    assert hidden["witness"]["unrepairable_by_repetition"] is True
    separation = decisions["N4_SEPARATION_IMPOSSIBLE"]
    assert separation["decision"] == gate.DENY_INSUFFICIENT
    unadmitted = decisions["N9_UNADMITTED_FRESH_INSTANCES"]
    assert unadmitted["decision"] == gate.DENY_ADMISSION
    assert unadmitted["admission"]["reached"] == 0


def test_external_store_has_only_one_abstract_rule_and_is_removable(tmp_path: Path) -> None:
    store = tmp_path / "external_store.json"
    receipt = runner.evaluate(store_path=store, write_store=True, receipt_path=None)
    payload = receipt["canonical_payload"]
    assert payload["counts"]["store_write_count"] == 1
    rule = payload["store_action"]["rule"]
    assert gate.forbidden_fields(rule) == []
    encoded = json.dumps(rule).lower()
    for forbidden in ("purchase_order.xlsx", "exact bytes", '"argv"', '"reward"',
                      '"outcome"', '"answer"', "click the"):
        assert forbidden not in encoded
    assert "mechanism_signature" in rule
    assert rule["admission_counts"] == {
        "fresh_instances": 3,
        "fresh_instances_reached": 3,
        "contrast_guaranteed_elimination": 1,
    }
    data = json.loads(store.read_text(encoding="utf-8"))
    assert len(data["rules"]) == 1
    before = gate.store_status(store)
    assert before["status"] == "PASS__STORE_VERIFIED"
    original = store.read_bytes()
    store.unlink()
    missing = gate.store_status(store)
    assert missing["status"] == "STORE_MISSING__REFUSE"
    store.write_bytes(original)
    after = gate.store_status(store)
    assert after["status"] == "PASS__STORE_VERIFIED"
    assert after["digest"] == before["digest"]
    edit = payload["store_editability"]
    assert edit["removal_refused"] is True
    assert edit["restore_verified"] is True
    assert edit["restart_digest_matches"] is True


def test_separate_different_code_recheck_passes_and_kills_a_mutation(tmp_path: Path) -> None:
    store = tmp_path / "recheck_store.json"
    receipt_path = tmp_path / "receipt.json"
    attestation_path = tmp_path / "attestation.json"
    receipt = runner.evaluate(
        store_path=store,
        write_store=True,
        receipt_path=receipt_path,
        attestation_path=attestation_path,
    )
    recheck = receipt["separate_local_recheck"]
    assert recheck["status"] == verifier.PASS
    assert all(recheck["checks"].values())
    assert recheck["checked_decisions"] == 12
    producer_refs = {value for key, value in receipt["canonical_payload"]["run_refs"].items()
                     if key != "run_refs_distinct"}
    assert len(producer_refs) == 4
    assert recheck["run_ref"] not in producer_refs
    assert recheck["independent_attestation"] is False
    assert recheck["section_6"] == "NOT_DONE"
    assert receipt_path.read_text(encoding="utf-8")
    assert attestation_path.read_text(encoding="utf-8")
    verifier_source = Path(runner.VERIFIER_PATH).read_text(encoding="utf-8")
    assert "import canonical" not in verifier_source
    assert "from canonical" not in verifier_source

    tampered = json.loads(receipt_path.read_text(encoding="utf-8"))
    tampered["canonical_payload"]["counts"]["expected_decision_matches"] = 11
    receipt_path.write_text(json.dumps(tampered, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    refused_path = tmp_path / "refused.json"
    proc = subprocess.run(
        [sys.executable, "-I", str(runner.VERIFIER_PATH),
         "--receipt", str(receipt_path), "--prereg", str(runner.PREREG_PATH),
         "--store", str(store), "--out", str(refused_path)],
        cwd=str(ROOT), capture_output=True, text=True, timeout=120, check=False,
    )
    assert proc.returncode != 0
    refused = json.loads(refused_path.read_text(encoding="utf-8"))
    assert refused["status"] == verifier.REFUSE
    assert refused["checks"]["receipt_digest_match"] is False
    assert refused["checks"]["counts_match"] is False


def test_verifier_recomputes_frozen_classes_without_the_gate_modules() -> None:
    for case in runner.frozen_cases():
        case_id = case["case_id"]
        assert verifier.classify(case) == runner.EXPECTED[case_id]
    assert verifier.classify({"case_id": "NO_SPACE", "instruction": "unknown",
                              "observation": {}, "goal_facts": ["authority.source"],
                              "scan_facts": [], "evidence": [], "regime_rows": [],
                              "probes": [], "oracle_name": "none"}) == "REFUSED__NO_CLOSED_HYPOTHESIS_SPACE"
