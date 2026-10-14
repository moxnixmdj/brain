"""DOCX_EXACT_TEXT_EDIT_V1 under the true-capability harness, plus audit/ledger consistency.

Measurements run in a child process (the harness installs an irremovable audit hook).
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HARNESS = ROOT / "execution_guard" / "true_capability_harness_v1.py"
SPEC = ROOT / "canonical" / "capabilities" / "true" / "specs" / "DOCX_EXACT_TEXT_EDIT_V1.json"
KERNEL = ROOT / "canonical" / "runtime" / "docx_exact_text_edit.py"
LEDGER = ROOT / "canonical" / "capabilities" / "true" / "TRUE_CAPABILITY_LEDGER_V1.json"
AUDIT = ROOT / "canonical" / "capabilities" / "true" / "TRUE_CAPABILITY_AUDIT_20261014_V1.json"


def _run(spec: pathlib.Path, out_dir: pathlib.Path, instances: int = 500):
    cmd = [sys.executable, str(HARNESS), "run", "--spec", str(spec), "--instances", str(instances),
           "--receipt-dir", str(out_dir), "--ledger", str(out_dir / "ledger.json"), "--root", str(ROOT)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=str(ROOT))
    receipts = [p for p in sorted(out_dir.glob("*.json")) if p.name != "ledger.json"]
    assert receipts, proc.stdout + proc.stderr
    return proc, json.loads(receipts[-1].read_text())


def _mutant(tmp_path: pathlib.Path, name: str, replacements: list[tuple[str, str]]):
    src = KERNEL.read_text(encoding="utf-8")
    for a, b in replacements:
        assert a in src, a
        src = src.replace(a, b)
    mut_dir = ROOT / "tmp_true_capability_mutants"
    mut_dir.mkdir(exist_ok=True)
    mut = mut_dir / f"{name}.py"
    mut.write_text(src, encoding="utf-8")
    spec = json.loads(SPEC.read_text())
    spec["solver"]["module"] = str(mut.relative_to(ROOT))
    spec_path = mut_dir / f"{name}.json"
    spec_path.write_text(json.dumps(spec))
    try:
        return _run(spec_path, tmp_path)
    finally:
        mut.unlink(missing_ok=True)
        spec_path.unlink(missing_ok=True)
        try:
            mut_dir.rmdir()
        except OSError:
            pass


def test_docx_spec_measures_pass_on_fresh_instances(tmp_path):
    proc, rec = _run(SPEC, tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert rec["verdict"] == "PASS", rec.get("failures_sample")
    assert rec["instance_pass"] == rec["instances"] == 500
    assert rec["authority"] == "NONE" and rec["network_blocked"] is True and rec["banned_modules_detected"] == []


def test_docx_spec_catches_the_empty_replacement_defect(tmp_path):
    proc, rec = _mutant(tmp_path, "docx_mut_empty_replacement", [
        ('if (n.text or "")==old)', "if n.text==old)"),
        ('if (n.text or "")==new)', "if n.text==new)"),
    ])
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["EXPECTED_OUTCOME"]["fail"] > 0


def test_docx_spec_catches_loss_of_uniqueness_enforcement(tmp_path):
    proc, rec = _mutant(tmp_path, "docx_mut_no_uniqueness", [
        ("if len(matches)!=1:", "if len(matches)<1:"),
        ("if old_count!=0 or new_count<1:", "if new_count<1:"),
    ])
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["EXPECTED_OUTCOME"]["fail"] > 0


def test_generator_and_oracles_do_not_import_solver():
    for rel in ("canonical/capabilities/true/generators/docx_exact_text_edit_gen_v1.py",
                "canonical/capabilities/true/oracles/docx_exact_text_edit_oracles_v1.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "docx_exact_text_edit" not in text.replace("docx_exact_text_edit_gen", "").replace("docx_exact_text_edit_oracles", ""), rel
        assert "xml.etree" not in text, rel  # the oracle must use a different parser from the solver


def test_audit_is_consistent_with_the_ledger():
    audit = json.loads(AUDIT.read_text())
    ledger = json.loads(LEDGER.read_text())
    assert audit["authority"] == "NONE" and ledger["authority"] == "NONE"
    measured = [c for c in audit["components"] if c["classification"].startswith("MEASURED_")]
    assert len(measured) == audit["summary"]["components_measured_pass"] + audit["summary"]["components_measured_fail"]
    for c in measured:
        row = ledger["rows"][c["spec"]]
        expected = "PASS" if c["classification"] == "MEASURED_PASS" else "FAIL"
        assert row["verdict"] == expected, (c["spec"], row["verdict"])
    # every family whose quoted route contains a model is classified as external
    for f in audit["families"]:
        if f["model_in_route"]:
            assert f["classification"].startswith("EXTERNAL_"), f["family"]
    assert len(audit["families"]) == 19
