"""SAME_IDENTITY_SUPERVISOR_V1 under the true-capability harness, with mutants the test must catch.

Measurements run in a child process (the harness installs an irremovable audit hook).
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HARNESS = ROOT / "execution_guard" / "true_capability_harness_v1.py"
SPEC = ROOT / "canonical" / "capabilities" / "true" / "specs" / "SAME_IDENTITY_SUPERVISOR_V1.json"
KERNEL = ROOT / "canonical" / "runtime" / "same_identity_supervisor.py"
LEDGER = ROOT / "canonical" / "capabilities" / "true" / "TRUE_CAPABILITY_LEDGER_V1.json"
AUDIT = ROOT / "canonical" / "capabilities" / "true" / "TRUE_CAPABILITY_AUDIT_20261014_V1.json"


def _run(spec: pathlib.Path, out_dir: pathlib.Path, instances: int = 500):
    cmd = [sys.executable, str(HARNESS), "run", "--spec", str(spec), "--instances", str(instances),
           "--receipt-dir", str(out_dir), "--ledger", str(out_dir / "ledger.json"), "--root", str(ROOT)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900, cwd=str(ROOT))
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


def test_supervisor_spec_measures_pass_on_fresh_instances(tmp_path):
    proc, rec = _run(SPEC, tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert rec["verdict"] == "PASS", rec.get("failures_sample")
    assert rec["instance_pass"] == rec["instances"] == 500
    assert rec["authority"] == "NONE" and rec["network_blocked"] is True and rec["banned_modules_detected"] == []


def test_catches_intruder_taking_over_a_lease(tmp_path):
    # Inside the contract the agent id is part of the hashed manifest, so the identity
    # checks and the manifest-drift check defend the same door; a mutant must open all of
    # them for an intruder to get through (removing only the LeaseConflict raises is a
    # second-defense mutant that legitimately survives).
    proc, rec = _mutant(tmp_path, "sup_mut_lease_takeover", [
        ('    if state.get("agent_id") != agent_id:\n        raise LeaseConflict("STATE_AGENT_ID_MISMATCH")\n', ""),
        ('    if lease.get("owner") != agent_id:\n        raise LeaseConflict("LEASE_OWNER_MISMATCH")\n', ""),
        ('    if state.get("task_sha256") != _task_sha(task):\n        raise SupervisorError("TASK_MANIFEST_DRIFT")\n', ""),
        ('    if state.get("agent_id") != agent_id or state.get("task_sha256") != _task_sha(task):\n'
         '        raise SupervisorError("CLAIM_BINDING_INVALID")\n', ""),
    ])
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["LEASE_EXCLUSIVITY"]["fail"] > 0
    assert rec["per_oracle"]["REFERENCE_MODEL_TRACE"]["fail"] > 0


def test_catches_runtime_relaunch_after_terminal_state(tmp_path):
    # the gap found on 2026-10-14: execute without the terminal guard
    proc, rec = _mutant(tmp_path, "sup_mut_terminal_relaunch", [
        ('    if state.get("status") in {"COMPLETE", "FAILED"}:\n        # claim_task already refuses terminal tasks; the execute entry must refuse them too\n'
         '        # (gap found by fresh-instance measurement, 2026-10-14).\n        raise TaskAlreadyTerminal(str(state.get("status")))\n', ""),
    ])
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["NO_TERMINAL_REEXECUTION"]["fail"] > 0


def test_catches_manifest_drift_acceptance(tmp_path):
    proc, rec = _mutant(tmp_path, "sup_mut_drift", [
        ('    if state.get("task_sha256") != _task_sha(task):\n        raise SupervisorError("TASK_MANIFEST_DRIFT")\n', ""),
        ('    if state.get("agent_id") != agent_id or state.get("task_sha256") != _task_sha(task):',
         '    if state.get("agent_id") != agent_id:'),
    ])
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["REFERENCE_MODEL_TRACE"]["fail"] > 0


def test_catches_mission_hash_not_enforced(tmp_path):
    proc, rec = _mutant(tmp_path, "sup_mut_mission_sha", [
        ('    if _sha_file(mission) != task["mission_sha256"]:\n        raise SupervisorError("MISSION_SHA_MISMATCH")\n', ""),
        ('        if not mission.is_file() or _sha_file(mission) != task["mission_sha256"]:\n            continue\n',
         '        if not mission.is_file():\n            continue\n'),
    ])
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["REFERENCE_MODEL_TRACE"]["fail"] > 0


def test_catches_wrong_selection_order(tmp_path):
    proc, rec = _mutant(tmp_path, "sup_mut_order", [
        ("    candidates.sort()\n    return candidates[0][2]", "    candidates.sort()\n    return candidates[-1][2]"),
    ])
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["REFERENCE_MODEL_TRACE"]["fail"] > 0


def test_catches_missing_checkpoint(tmp_path):
    proc, rec = _mutant(tmp_path, "sup_mut_checkpoint", [
        ('    if bool(task.get("checkpoint_before_runtime_once")) and int(state.get("checkpoint_count", 0)) == 0:',
         '    if False:'),
    ])
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["REFERENCE_MODEL_TRACE"]["fail"] > 0


def test_generator_and_oracles_do_not_import_solver():
    for rel in ("canonical/capabilities/true/generators/same_identity_supervisor_gen_v1.py",
                "canonical/capabilities/true/oracles/same_identity_supervisor_oracles_v1.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "same_identity_supervisor" not in text.replace("same_identity_supervisor_gen", "").replace("same_identity_supervisor_oracles", ""), rel
        assert "canonical.runtime" not in text and "importlib" not in text, rel


def test_ledger_row_matches_committed_receipt():
    ledger = json.loads(LEDGER.read_text())
    row = ledger["rows"]["SAME_IDENTITY_SUPERVISOR_V1"]
    receipt = json.loads((ROOT / row["latest_receipt"]).read_text())
    assert receipt["capability_id"] == "SAME_IDENTITY_SUPERVISOR_V1"
    assert receipt["verdict"] == row["verdict"] == "PASS"
    assert receipt["instances"] == row["instances"] >= 1000
    assert receipt["authority"] == "NONE" and receipt["banned_modules_detected"] == [] and receipt["network_blocked"] is True
    # the receipt measured the committed solver, not some other version of it
    blob = subprocess.run(["git", "hash-object", str(KERNEL)], capture_output=True, text=True, cwd=str(ROOT)).stdout.strip()
    assert row["solver_git_blob_sha"] == blob, (row["solver_git_blob_sha"], blob)
    audit = json.loads(AUDIT.read_text())
    comp = [c for c in audit["components"] if c.get("spec") == "SAME_IDENTITY_SUPERVISOR_V1"]
    assert len(comp) == 1 and comp[0]["classification"] == "MEASURED_PASS"
