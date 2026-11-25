#!/usr/bin/env python3
"""The enrollment gate must count real defects, refuse to invent predicates, and be satisfiable.

Two of these tests build a fixture registry so the assertions are known to bite: a tool that only
ever agrees with the file it reads is decoration. The first test recomputes two of the five classes
straight from the JSON, so the gate cannot quietly stop looking at rows it should.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

from canonical.tools import capability_enrollment_gate_v1 as gate

ROOT = pathlib.Path(gate.ROOT)
LIVE = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
SNAPSHOT = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json"
LEDGER = ROOT / "canonical/capabilities/true/TRUE_CAPABILITY_LEDGER_V1.json"
ADAPTERS = ROOT / "canonical/runtime/bound_capabilities"


def _fixture(tmp: pathlib.Path, rows: dict, ledger_rows: dict | None = None) -> dict[str, pathlib.Path]:
    """A miniature repo: registry + snapshot + adapters dir + evidence dir + true-capability ledger."""
    adir = tmp / "canonical/runtime/bound_capabilities"
    adir.mkdir(parents=True, exist_ok=True)
    reg = tmp / "registry.json"
    reg.write_text(json.dumps({"capabilities": rows}), encoding="utf-8")
    snap = tmp / "snapshot.json"
    snap.write_text(json.dumps({"capabilities": rows}), encoding="utf-8")
    ledger = tmp / "ledger.json"
    ledger.write_text(json.dumps({"rows": ledger_rows or {}}), encoding="utf-8")
    (tmp / "evidence").mkdir(exist_ok=True)
    return {"root": tmp, "registry": reg, "snapshot": snap, "ledger": ledger, "adapters": adir}


def _build(f: dict) -> dict:
    return gate.build(f["root"], f["registry"], f["snapshot"], f["ledger"], f["adapters"])


def test_real_tree_defect_counts_match_an_independent_recomputation() -> None:
    r = gate.build(ROOT, LIVE, SNAPSHOT, LEDGER, ADAPTERS)
    rows = {**json.loads(LIVE.read_text())["capabilities"], **json.loads(SNAPSHOT.read_text())["capabilities"]}

    missing = {cid for cid, row in rows.items()
               if isinstance(row.get("verification"), dict) and row["verification"].get("receipt_path")
               and not (ROOT / row["verification"]["receipt_path"]).is_file()}
    assert missing, "the known-missing receipts must still be named, not summarized away"
    assert missing == {x.split(" -> ")[0] for x in r["defects"]["MISSING_VERIFICATION_RECEIPT"]}

    dangling = {cid for cid, row in rows.items()
                if row.get("adapter_module") and row["adapter_module"] != "runtime_native_action"
                and not (ADAPTERS / f"{row['adapter_module']}.py").is_file()}
    assert dangling == {x.split(" -> ")[0] for x in r["defects"]["DANGLING_ADAPTER"]}

    # `runtime_native_action` is a declared kind, so it is listed apart and never counted as broken.
    native = {cid for cid, row in rows.items() if row.get("adapter_module") == "runtime_native_action"}
    assert r["native_kind_rows"] == len(native) and native
    assert not any("runtime_native_action" in x for x in r["defects"]["DANGLING_ADAPTER"])

    assert r["certified_capabilities"] == 9
    assert r["defect_counts"]["UNENROLLED_CERTIFIED_CAPABILITY"] == r["certified_capabilities"] - 1, (
        "today exactly one certified capability (the SACCR kernel) is bound by a registry row; "
        "when a second is enrolled, this is where the change gets noticed"
    )
    assert r["clean"] is False


def test_gate_detects_a_fabricated_adapter_and_a_lost_receipt(tmp_path: pathlib.Path) -> None:
    rows = {
        "a.real": {"adapter_module": "a_real_adapter", "provides": ["x"], "requires": ["y"],
                   "verification": {"receipt_path": "evidence/a.json"}},
        "b.broken": {"adapter_module": "no_such_adapter", "provides": ["y"],
                      "verification": {"receipt_path": "evidence/gone.json"}},
        "c.native": {"adapter_module": "runtime_native_action", "provides": ["z"]},
    }
    f = _fixture(tmp_path, rows)
    (f["adapters"] / "a_real_adapter.py").write_text("#\n", encoding="utf-8")
    (tmp_path / "evidence/a.json").write_text("{}\n", encoding="utf-8")
    r = _build(f)
    assert r["defects"]["DANGLING_ADAPTER"] == ["b.broken -> no_such_adapter"]
    assert r["defects"]["MISSING_VERIFICATION_RECEIPT"] == ["b.broken -> evidence/gone.json"]
    assert r["native_kind_rows"] == 1
    assert r["defect_counts"]["UNENROLLED_CERTIFIED_CAPABILITY"] == 0
    assert r["clean"] is False


def test_unsatisfiable_requires_is_about_providers_not_spellings(tmp_path: pathlib.Path) -> None:
    """A requires term no row provides is a planning dead end; renaming the fixture fixes it, which
    is the point: the gate is checking the vocabulary, not the files."""
    base = {"p": {"adapter_module": "a", "provides": ["x"], "requires": ["y"]}}
    f = _fixture(tmp_path, base)
    (f["adapters"] / "a.py").write_text("#\n", encoding="utf-8")
    assert _build(f)["defects"]["UNSATISFIABLE_REQUIRES"] == ["y"]
    fixed = {**base, "q": {"adapter_module": "a", "provides": ["y"]}}
    f2 = _fixture(tmp_path, fixed)
    (f2["adapters"] / "a.py").write_text("#\n", encoding="utf-8")
    assert _build(f2)["clean"] is True


def test_cli_exit_code_is_the_defect_verdict(tmp_path: pathlib.Path) -> None:
    f = _fixture(tmp_path, {"p": {"adapter_module": "a", "provides": ["x"], "requires": ["y"],
                                  "verification": {"receipt_path": "evidence/y.json"}}})
    (f["adapters"] / "a.py").write_text("#\n", encoding="utf-8")
    (tmp_path / "evidence/y.json").write_text("{}\n", encoding="utf-8")

    def run() -> int:
        return subprocess.run(
            [sys.executable, str(ROOT / "canonical/tools/capability_enrollment_gate_v1.py"),
             "--root", str(tmp_path), "--registry", str(f["registry"]), "--snapshot", str(f["snapshot"]),
             "--ledger", str(f["ledger"]), "--adapters", str(f["adapters"]), "--fail-on-defect"],
            capture_output=True, text=True, check=False,
        ).returncode

    assert run() == 1, "y has no provider: a planner cannot reach this row, so CI must fail"
    # now give y a provider and confirm the same command exits 0: the gate is satisfiable, which is
    # what makes it a gate rather than a complaint.
    f["registry"].write_text(json.dumps({"capabilities": {
        "p": {"adapter_module": "a", "provides": ["x"], "requires": ["y"],
              "verification": {"receipt_path": "evidence/y.json"}},
        "q": {"adapter_module": "a", "provides": ["y"]},
    }}), encoding="utf-8")
    f["snapshot"].write_text(f["registry"].read_text(encoding="utf-8"), encoding="utf-8")
    assert run() == 0, "with a provider for y, the fixture is genuinely clean"


def test_candidates_carry_evidence_and_refuse_to_invent_predicates() -> None:
    r = gate.build(ROOT, LIVE, SNAPSHOT, LEDGER, ADAPTERS)
    cands = gate.candidates(ROOT, LEDGER, r)
    assert len(cands) == r["defect_counts"]["UNENROLLED_CERTIFIED_CAPABILITY"]
    for c in cands:
        assert c["provides"] is None and c["requires"] is None, "a predicate invented here is an unmeasured claim"
        assert c["incremental_spend_usd"] == 0
        assert c["status"].startswith("CANDIDATE_NOT_ADMITTED")
        assert c["evidence"]["true_capability_receipt"] and c["evidence"]["receipt_sha256_16_present"] is True
        assert (ROOT / c["evidence"]["true_capability_receipt"]).is_file()
        assert len(c["admission_blocked_until"]) == 3, "the two-condition rule must travel with the candidate"
        assert c["kernel_module"] and (ROOT / c["kernel_module"]).is_file()


def test_markdown_names_every_class_even_when_empty() -> None:
    r = gate.build(ROOT, LIVE, SNAPSHOT, LEDGER, ADAPTERS)
    md = gate.to_markdown(r)
    for k in gate.DEFECT_ORDER:
        assert f"`{k}`" in md
    assert "snapshot wins" in md
