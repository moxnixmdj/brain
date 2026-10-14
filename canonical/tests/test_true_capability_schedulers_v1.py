"""The three scheduler specs under the true-capability harness, with mutants the tests must catch.

Measurements run in a child process (the harness installs an irremovable audit hook).
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HARNESS = ROOT / "execution_guard" / "true_capability_harness_v1.py"
SPECS = ROOT / "canonical" / "capabilities" / "true" / "specs"
RANKING = SPECS / "CAPABILITY_FIRST_RANKING_V1.json"
FRONTIER = SPECS / "PARETO_FRONTIER_UPDATE_V1.json"
SCHEDULE = SPECS / "AUTHENTICATED_PARETO_SCHEDULE_V1.json"
CORE = ROOT / "canonical" / "runtime" / "capability_first_scheduler_v1.py"
AUTH = ROOT / "canonical" / "runtime" / "authenticated_pareto_scheduler_v1.py"
ADAPTER = ROOT / "canonical" / "runtime" / "scheduler_true_capability_adapters_v1.py"
IMPORTS = {CORE: "from canonical.runtime import capability_first_scheduler_v1 as _core",
           AUTH: "from canonical.runtime import authenticated_pareto_scheduler_v1 as _auth"}
LEDGER = ROOT / "canonical" / "capabilities" / "true" / "TRUE_CAPABILITY_LEDGER_V1.json"
AUDIT = ROOT / "canonical" / "capabilities" / "true" / "TRUE_CAPABILITY_AUDIT_20261014_V1.json"


def _run(spec: pathlib.Path, out_dir: pathlib.Path, instances: int = 500):
    cmd = [sys.executable, str(HARNESS), "run", "--spec", str(spec), "--instances", str(instances),
           "--receipt-dir", str(out_dir), "--ledger", str(out_dir / "ledger.json"), "--root", str(ROOT)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=str(ROOT))
    receipts = [p for p in sorted(out_dir.glob("*.json"), key=lambda p: p.stat().st_mtime) if p.name != "ledger.json"]
    assert receipts, proc.stdout + proc.stderr
    return proc, json.loads(receipts[-1].read_text())


def _mutant(tmp_path: pathlib.Path, spec_path: pathlib.Path, kernel: pathlib.Path, name: str, replacements: list[tuple[str, str]]):
    """Mutate the byte-pinned kernel in a scratch copy and point a scratch adapter at it."""
    src = kernel.read_text(encoding="utf-8")
    for a, b in replacements:
        assert a in src, a
        src = src.replace(a, b)
    mut_dir = ROOT / "tmp_true_capability_mutants"
    mut_dir.mkdir(exist_ok=True)
    mut_kernel = mut_dir / f"{name}_kernel.py"
    mut_kernel.write_text(src, encoding="utf-8")
    adapter_src = ADAPTER.read_text(encoding="utf-8")
    assert IMPORTS[kernel] in adapter_src
    alias = IMPORTS[kernel].rsplit(" as ", 1)[1]
    adapter_src = adapter_src.replace(IMPORTS[kernel], f"from tmp_true_capability_mutants import {name}_kernel as {alias}")
    mut_adapter = mut_dir / f"{name}_adapter.py"
    mut_adapter.write_text(adapter_src, encoding="utf-8")
    spec = json.loads(spec_path.read_text())
    spec["solver"]["module"] = str(mut_adapter.relative_to(ROOT))
    spec["solver"]["kernels"] = [str(mut_kernel.relative_to(ROOT))]
    spec_file = mut_dir / f"{name}.json"
    spec_file.write_text(json.dumps(spec))
    try:
        return _run(spec_file, tmp_path)
    finally:
        for f in (mut_kernel, mut_adapter, spec_file):
            f.unlink(missing_ok=True)
        for leftover in mut_dir.glob("__pycache__/*"):
            leftover.unlink(missing_ok=True)
        for d in (mut_dir / "__pycache__", mut_dir):
            try:
                d.rmdir()
            except OSError:
                pass


# ----------------------------------------------------------------------------- fresh-instance PASS
def test_ranking_spec_passes_on_fresh_instances(tmp_path):
    proc, rec = _run(RANKING, tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert rec["verdict"] == "PASS" and rec["instance_pass"] == rec["instances"] == 500, rec.get("failures_sample")
    assert rec["authority"] == "NONE" and rec["banned_modules_detected"] == []


def test_frontier_spec_passes_on_fresh_instances(tmp_path):
    proc, rec = _run(FRONTIER, tmp_path)
    assert rec["verdict"] == "PASS" and rec["instance_pass"] == 500, rec.get("failures_sample")


def test_schedule_spec_passes_on_fresh_instances(tmp_path):
    proc, rec = _run(SCHEDULE, tmp_path)
    assert rec["verdict"] == "PASS" and rec["instance_pass"] == 500, rec.get("failures_sample")


# ----------------------------------------------------------------------------- mutants: ranking
def test_ranking_catches_demoted_work_outranking_eligible_work(tmp_path):
    proc, rec = _mutant(tmp_path, RANKING, CORE, "rank_mut_no_eligibility_lane", [
        ('            0 if x["eligibility"] == "ELIGIBLE" else 1,\n', ""),
    ])
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["REFERENCE_RANKING"]["fail"] > 0 and rec["per_oracle"]["ORDER_INVARIANTS"]["fail"] > 0


def test_ranking_catches_wrong_score_formula(tmp_path):
    proc, rec = _mutant(tmp_path, RANKING, CORE, "rank_mut_formula", [
        ("return (capability + efficiency + reliability) * breadth * generalization * success / costs",
         "return (capability + efficiency + reliability) * breadth * generalization * success / (costs + 1)"),
    ])
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["REFERENCE_RANKING"]["fail"] > 0
    assert rec["per_oracle"]["UNIFORM_COST_SCALING_INVARIANCE"]["fail"] > 0


def test_ranking_catches_benchmark_bookkeeping_admitted(tmp_path):
    proc, rec = _mutant(tmp_path, RANKING, CORE, "rank_mut_benchmark", [
        ('    if role in ALLOWED_BENCHMARK_ROLES:\n        return True, "ELIGIBLE"\n    return False, "DEMOTED_BENCHMARK_BOOKKEEPING"',
         '    return True, "ELIGIBLE"'),
    ])
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["REFERENCE_RANKING"]["fail"] > 0


def test_ranking_catches_lost_tie_break(tmp_path):
    proc, rec = _mutant(tmp_path, RANKING, CORE, "rank_mut_tiebreak", [
        ('            -x["checkpoint_audit_score_fraction"],\n            x["work_id"],\n',
         '            x["work_id"],\n'),
    ])
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["REFERENCE_RANKING"]["fail"] > 0


def test_ranking_catches_validation_removed(tmp_path):
    proc, rec = _mutant(tmp_path, RANKING, CORE, "rank_mut_validation", [
        ('    if success > 1:\n        raise CapabilityFirstSchedulerError("SUCCESS_PROBABILITY_LCB_GT_ONE")\n    costs = (',
         '    costs = ('),
        ('    if costs <= 0:\n        raise CapabilityFirstSchedulerError("TOTAL_RESOURCE_COST_MUST_BE_POSITIVE")\n',
         '    if costs <= 0:\n        return Fraction(0)\n'),
    ])
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["REFERENCE_RANKING"]["fail"] > 0


# ----------------------------------------------------------------------------- mutants: frontier update
def test_frontier_catches_weak_dominance(tmp_path):
    proc, rec = _mutant(tmp_path, FRONTIER, CORE, "frontier_mut_weak", [
        ("    return weak and strict\n\n\ndef update_pareto_frontier", "    return weak\n\n\ndef update_pareto_frontier"),
    ])
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["REFERENCE_FOLD"]["fail"] > 0


def test_frontier_catches_contract_check_removed(tmp_path):
    proc, rec = _mutant(tmp_path, FRONTIER, CORE, "frontier_mut_contract", [
        ("    if a_contract and b_contract and a_contract != b_contract:\n        return False\n", ""),
    ])
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["REFERENCE_FOLD"]["fail"] > 0 and rec["per_oracle"]["FRONTIER_INVARIANTS"]["fail"] > 0


def test_frontier_catches_unverified_admission(tmp_path):
    proc, rec = _mutant(tmp_path, FRONTIER, CORE, "frontier_mut_unverified", [
        ('    if candidate.get("independently_verified") is not True:\n        return {"admitted": False, "reason": "INDEPENDENT_VERIFICATION_REQUIRED", "frontier": list(frontier)}\n', ""),
    ])
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["FRONTIER_INVARIANTS"]["fail"] > 0


# ----------------------------------------------------------------------------- mutants: authenticated schedule
def test_schedule_catches_receipt_binding_removed(tmp_path):
    proc, rec = _mutant(tmp_path, SCHEDULE, AUTH, "sched_mut_binding", [
        ('        if receipt.get("subject_sha256") != subject:\n            return _fail("MEASUREMENT_RECEIPT_SUBJECT_MISMATCH", candidate_id=c["candidate_id"])\n', ""),
    ])
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["TAMPER_AFTER_RECEIPT_IS_REFUSED"]["fail"] > 0


def test_schedule_catches_spend_check_removed(tmp_path):
    proc, rec = _mutant(tmp_path, SCHEDULE, AUTH, "sched_mut_spend", [
        ('        if float(metrics["cost_usd_ucb"]) != 0.0:\n', '        if float(metrics["cost_usd_ucb"]) < 0.0:\n'),
    ])
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["REFERENCE_SCHEDULE"]["fail"] > 0


def test_schedule_catches_wrong_dominance(tmp_path):
    proc, rec = _mutant(tmp_path, SCHEDULE, AUTH, "sched_mut_dominance", [
        ("    return no_worse and strictly\n", "    return no_worse\n"),
    ])
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["REFERENCE_SCHEDULE"]["fail"] > 0


# ----------------------------------------------------------------------------- separation and bookkeeping
def test_generator_and_oracles_do_not_import_solvers():
    for rel in ("canonical/capabilities/true/generators/scheduler_gen_v1.py",
                "canonical/capabilities/true/oracles/scheduler_oracles_v1.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        for banned in ("capability_first_scheduler", "authenticated_pareto_scheduler", "scheduler_true_capability_adapters", "canonical.runtime", "importlib"):
            assert banned not in text, (rel, banned)


def test_kernels_are_byte_identical_to_their_governance_pins():
    # the adapters exist so that the pinned schedulers are measured unchanged
    for kernel, pinned in ((CORE, "6d2091cc1581b9aa1fd2c74e8a76519a41d9d957"), (AUTH, "0d351964d29690e676f116480a69b8c979b8b54a")):
        blob = subprocess.run(["git", "hash-object", str(kernel)], capture_output=True, text=True, cwd=str(ROOT)).stdout.strip()
        assert blob == pinned, (kernel.name, blob)


def test_ledger_rows_match_committed_receipts():
    ledger = json.loads(LEDGER.read_text())
    audit = json.loads(AUDIT.read_text())
    kernels = {"CAPABILITY_FIRST_RANKING_V1": CORE, "PARETO_FRONTIER_UPDATE_V1": CORE, "AUTHENTICATED_PARETO_SCHEDULE_V1": AUTH}
    for cap, kernel in kernels.items():
        row = ledger["rows"][cap]
        receipt = json.loads((ROOT / row["latest_receipt"]).read_text())
        assert receipt["capability_id"] == cap and receipt["verdict"] == row["verdict"] == "PASS"
        assert receipt["instances"] == row["instances"] >= 1000
        assert receipt["authority"] == "NONE" and receipt["banned_modules_detected"] == [] and receipt["network_blocked"] is True
        for path, kblob in (ADAPTER, row["solver_git_blob_sha"]), (kernel, row["kernel_git_blob_shas"][str(kernel.relative_to(ROOT))]):
            blob = subprocess.run(["git", "hash-object", str(path)], capture_output=True, text=True, cwd=str(ROOT)).stdout.strip()
            assert kblob == blob, (cap, path.name, kblob, blob)
        comps = [c for c in audit["components"] if cap in (c.get("specs") or [c.get("spec")])]
        assert comps and all(c["classification"] == "MEASURED_PASS" for c in comps), cap
