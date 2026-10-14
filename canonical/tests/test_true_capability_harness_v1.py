"""Tests for the true-capability harness and the first measured spec.

Cheap (no network, stdlib only) so they run in every CI lane.  They check the
*harness* (can it fail? does it enforce the separations?) and that the SA-CCR
spec measures PASS on fresh instances.  Every measurement runs in a child
process because the harness installs an irremovable PEP 578 audit hook that
blocks network access for the rest of its process.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HARNESS = ROOT / "execution_guard" / "true_capability_harness_v1.py"
SPEC = ROOT / "canonical" / "capabilities" / "true" / "specs" / "SACCR_CREDIT_ADDON_V1.json"
KERNEL = ROOT / "canonical" / "runtime" / "saccr_credit_kernel.py"


def _run(spec: pathlib.Path, out_dir: pathlib.Path, instances: int = 500, seed: str | None = None) -> tuple[subprocess.CompletedProcess, dict, dict]:
    cmd = [sys.executable, str(HARNESS), "run", "--spec", str(spec), "--instances", str(instances),
           "--receipt-dir", str(out_dir), "--ledger", str(out_dir / "ledger.json"), "--root", str(ROOT)]
    if seed:
        cmd += ["--seed", seed]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(ROOT))
    receipts = sorted(out_dir.glob("*.json"))
    receipts = [p for p in receipts if p.name != "ledger.json"]
    assert receipts, proc.stdout + proc.stderr
    rec = json.loads(receipts[-1].read_text())
    ledger = json.loads((out_dir / "ledger.json").read_text())
    return proc, rec, ledger


def test_harness_self_test_passes():
    proc = subprocess.run([sys.executable, str(HARNESS), "self-test"], capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "TRUE_CAPABILITY_HARNESS_SELF_TEST_PASS" in proc.stdout


def test_saccr_spec_measures_pass_on_fresh_instances(tmp_path):
    proc, rec, ledger = _run(SPEC, tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert rec["schema"] == "TRUE_CAPABILITY_RECEIPT_V1"
    assert rec["verdict"] == "PASS", rec.get("failures_sample")
    assert rec["instance_pass"] == rec["instances"] == 500
    assert rec["canary_pass"] == "1/1"
    assert rec["authority"] == "NONE"
    assert rec["network_blocked"] is True
    assert rec["banned_modules_detected"] == []
    assert rec["replay"] is False
    assert rec["seed_source"] in {"OS_URANDOM", "GITHUB_RUN_ID_ATTEMPT_SHA"}
    row = ledger["rows"]["SACCR_CREDIT_ADDON_V1"]
    assert row["status"] in {"MEASURED_SANDBOX", "MEASURED_PUBLIC_RUNNER"}
    assert row["solver_git_blob_sha"] == rec["blobs"]["solver"]["git_blob_sha"]


def test_saccr_spec_catches_the_2026_10_01_bug(tmp_path):
    """A test that cannot fail is not a test: drop the supervisory duration and the harness must fail."""
    src = KERNEL.read_text(encoding="utf-8")
    broken = src.replace("return t.notional*supervisory_duration(t.start,t.end)", "return t.notional")
    assert broken != src
    mut_dir = ROOT / "tmp_true_capability_mutants"
    mut_dir.mkdir(exist_ok=True)
    mut = mut_dir / "saccr_mutant_no_sd.py"
    spec_path = mut_dir / "spec_mutant.json"
    try:
        mut.write_text(broken, encoding="utf-8")
        spec = json.loads(SPEC.read_text())
        spec["solver"]["module"] = str(mut.relative_to(ROOT))
        spec_path.write_text(json.dumps(spec))
        proc, rec, _ = _run(spec_path, tmp_path)
    finally:
        mut.unlink(missing_ok=True)
        spec_path.unlink(missing_ok=True)
        try:
            mut_dir.rmdir()
        except OSError:
            pass
    assert proc.returncode != 0
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["CRE52_CLOSED_FORM"]["pass"] == 0
    assert rec["per_oracle"]["DONOR_DIFFERENTIAL"]["pass"] == 0
    assert rec["canary_pass"] == "0/1"


def test_explicit_seed_is_replay_and_non_crediting(tmp_path):
    proc, rec, ledger = _run(SPEC, tmp_path, seed="00" * 32)
    assert rec["replay"] is True
    assert ledger["rows"]["SACCR_CREDIT_ADDON_V1"]["status"] == "REPLAY_NOT_CREDITING"


def test_generator_and_oracles_do_not_import_solver():
    for rel in ("canonical/capabilities/true/generators/saccr_credit_addon_gen_v1.py",
                "canonical/capabilities/true/oracles/saccr_credit_addon_oracles_v1.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "saccr_credit_kernel" not in text, rel


def test_spec_declares_independent_oracles_without_donor_lineage():
    spec = json.loads(SPEC.read_text())
    assert spec["schema"] == "TRUE_CAPABILITY_SPEC_V1"
    declared = {o["id"]: o for o in spec["oracles"]["declared"]}
    assert len({o["class"] for o in declared.values()}) >= 2
    for oid in spec["independent_oracle_ids"]:
        assert oid in declared
        assert "baselkit" not in declared[oid].get("lineage", "")
    assert spec["model_dependency_count"] == 0
    assert spec["falsification_condition"]


def test_vendored_oracle_sha256_is_pinned():
    oracles = ROOT / "canonical" / "capabilities" / "true" / "oracles" / "saccr_credit_addon_oracles_v1.py"
    spec = importlib.util.spec_from_file_location("tc_oracles_under_test", str(oracles))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # raises if the vendored file was edited
    assert mod.VENDOR_UPSTREAM_SHA256 == "f104b76b463035549fb5ffcf7d7287297b15aed93a92d4452c23e9b4e8287a28"
