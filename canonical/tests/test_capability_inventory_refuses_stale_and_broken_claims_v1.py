#!/usr/bin/env python3
"""The inventory must be derived, and it must refuse to launder a stale or broken claim.

These tests are about the *instrument*, not the numbers: an inventory that prints whatever the
ledgers say is decoration. Three properties matter, and each is checked against a mutation of
the inputs so the assertion is known to bite:

1. every measured capability is bound to bytes present at HEAD, and a changed solver flips the
   binding to STALE_MEASUREMENT rather than staying green;
2. a claim whose evidence pointer does not resolve is reported (that is how a broken receipt
   path becomes visible instead of invisible);
3. prose counts that disagree with the fields they summarize are named, not averaged.
"""
from __future__ import annotations

import json
import pathlib
import re

import pytest

from canonical.tools import capability_inventory_v1 as inv

pytest.importorskip("yaml")  # the tool reads workflow YAML elsewhere; keep this suite self-contained


def test_inventory_builds_from_the_tree_and_costs_nothing() -> None:
    doc = inv.build()
    assert doc["model_calls"] == 0 and doc["cost_usd"] == 0.0
    assert doc["n_tracked_files"] > 1000
    mc = doc["measured_capabilities"]
    assert mc["n_capabilities"] >= 9
    assert mc["n_pass"] == mc["n_capabilities"], "every listed capability must be a PASS row"
    # A capability measured against bytes that no longer exist is not a pass.
    assert mc["n_stale"] == 0, {
        cap: r["binding"] for cap, r in mc["rows"].items() if r["binding"] != "MEASURED_BYTES_STILL_IN_HEAD"
    }
    assert doc["frontier_ownership_matrix"]["n_families"] == 19
    assert doc["benchmark_runs"]["n_reports"] >= 1
    assert doc["capability_law"]["available"], doc["capability_law"].get("error")
    assert re.fullmatch(r"[0-9a-f]{16}", doc["inventory_sha256_16"])


def test_inventory_is_reproducible_from_the_same_head() -> None:
    a, b = inv.build(), inv.build()
    for key in ("head", "n_tracked_files", "measured_capabilities", "frontier_ownership_matrix"):
        assert a[key] == b[key], key
    # The only field allowed to move between two builds in the same second is nothing: digest first.
    assert a["inventory_sha256_16"] == b["inventory_sha256_16"]


def test_solver_blob_binding_is_a_real_check_not_a_constant(tmp_path: pathlib.Path, monkeypatch) -> None:
    """Mutate the ledger row's recorded blob and the binding must report staleness."""
    ledger = json.loads(inv.TRUE_LEDGER.read_text(encoding="utf-8"))
    row = next(iter(ledger["rows"].values()))
    assert row["solver_git_blob_sha"] in set(inv._git_blob_shas_at_head().values())
    row["solver_git_blob_sha"] = "0" * 40
    fake = tmp_path / "ledger.json"
    fake.write_text(json.dumps(ledger), encoding="utf-8")
    monkeypatch.setattr(inv, "TRUE_LEDGER", fake)
    out = inv._true_capabilities(inv._git_blob_shas_at_head())
    assert out["n_stale"] == 1
    assert list(out["rows"].values())[0]["binding"] == "STALE_MEASUREMENT"


def test_broken_evidence_pointer_is_reported_as_a_finding(monkeypatch, tmp_path: pathlib.Path) -> None:
    matrix = json.loads(inv.OWNERSHIP_MATRIX.read_text(encoding="utf-8"))
    matrix["rows"][0]["evidence"] = "canonical/verification/THIS_RECEIPT_DOES_NOT_EXIST_V1.json"
    fake = tmp_path / "matrix.json"
    fake.write_text(json.dumps(matrix), encoding="utf-8")
    monkeypatch.setattr(inv, "OWNERSHIP_MATRIX", fake)
    out = inv._frontier_matrix()
    fam = matrix["rows"][0]["family"]
    assert out["broken_pointers"].get(fam) == ["canonical/verification/THIS_RECEIPT_DOES_NOT_EXIST_V1.json"]
    assert out["n_broken_pointers"] == 1


def test_a_directory_pointer_is_not_broken(monkeypatch, tmp_path: pathlib.Path) -> None:
    matrix = json.loads(inv.OWNERSHIP_MATRIX.read_text(encoding="utf-8"))
    for row in matrix["rows"]:
        row["evidence"] = "canonical/capabilities/internalized/artifact_creation/aws_sample_agent_skills_dd0bdc07"
    fake = tmp_path / "matrix.json"
    fake.write_text(json.dumps(matrix), encoding="utf-8")
    monkeypatch.setattr(inv, "OWNERSHIP_MATRIX", fake)
    assert inv._frontier_matrix()["n_broken_pointers"] == 0


def test_self_reported_counts_are_compared_to_the_fields_they_summarize(monkeypatch, tmp_path: pathlib.Path) -> None:
    # Whatever the current tree says, the check must be able to fail: doctor the prose and it must.
    inv._count_mismatch()
    doc = json.loads(inv.OPUS55_FRONTIER_FILE.read_text(encoding="utf-8"))
    doc["status"] = "ACTIVE_FAIL_CLOSED__99_OF_19_ACCEPTED__99_OF_19_VERIFIED_OWNED__TERMINAL_FALSE"
    fake = tmp_path / "frontier.json"
    fake.write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setattr(inv, "OPUS55_FRONTIER_FILE", fake)
    tampered = inv._count_mismatch()
    assert not tampered["agrees_with_fields"]
    assert any("99" in p for p in tampered["problems"]), tampered["problems"]


def test_no_committed_report_appears_without_its_refusal() -> None:
    """Not "assert the string OFFICIAL_TASK_VERDICTS is present" -- that pinned one run's verdict and
    went stale the moment CI overwrote the hard51 report with a void one. The property that actually
    matters: every report printed here is either quotable with its gates, or arrives with its
    refusal attached, and a void run is never rendered as a table of zeros."""
    results = pathlib.Path(inv.EVAL_RESULTS)
    reports = sorted(results.glob("*-latest.json"))
    assert reports, "the inventory must be looking at the real results dir"
    doc = inv.build()
    md = inv.to_markdown(doc)
    assert "STALE_MEASUREMENT" not in md or doc["measured_capabilities"]["n_stale"] > 0
    for path in reports:
        rep = json.loads(path.read_text(encoding="utf-8"))
        label = path.stem.replace("-latest", "")
        assert label in md, f"{path.name} is missing from the report"
        if rep.get("run_produced_number") is False or rep.get("run_failed"):
            assert "claimable=False" in md, "a void run must arrive with its refusal attached"
    for entry in (doc.get("benchmark_runs") or {}).get("reports", {}).values():
        gates = entry.get("gates") or {}
        if gates.get("nop_gate_pass") and gates.get("oracle_gate_pass"):
            assert entry.get("receipt_claimable") is True, "a run that passed both gates must be quotable"
    assert "Disagree" in md or inv._count_mismatch()["agrees_with_fields"]
