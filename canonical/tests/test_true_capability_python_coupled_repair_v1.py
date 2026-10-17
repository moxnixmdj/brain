"""Fresh-instance checks for the bounded coupled Python comparison-repair capability.

The true-capability harness runs in child processes because it installs a permanent
network-blocking audit hook.  The mutation test copies the existing kernel closure
under a scratch namespace, so it tests the oracle against broken producer bytes
rather than monkeypatching the solver in memory.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HARNESS = ROOT / "execution_guard" / "true_capability_harness_v1.py"
SPEC = ROOT / "canonical" / "capabilities" / "true" / "specs" / "PYTHON_COUPLED_COMPARISON_REPAIR_V1.json"
ADAPTER = ROOT / "canonical" / "runtime" / "python_coupled_comparison_repair_true_adapter_v1.py"
KERNEL_DIR = ROOT / "canonical" / "runtime" / "bound_capabilities"
KERNEL = KERNEL_DIR / "python_coupled_software_repair_loop_v1.py"
PATCH_KERNEL = KERNEL_DIR / "python_test_guided_patch_search_v1.py"
STRICT_KERNEL = KERNEL_DIR / "python_iterative_software_repair_loop_v1.py"
GENERATOR = ROOT / "canonical" / "capabilities" / "true" / "generators" / "python_coupled_comparison_repair_gen_v1.py"
ORACLES = ROOT / "canonical" / "capabilities" / "true" / "oracles" / "python_coupled_comparison_repair_oracles_v1.py"
LEDGER = ROOT / "canonical" / "capabilities" / "true" / "TRUE_CAPABILITY_LEDGER_V1.json"
AUDIT = ROOT / "canonical" / "capabilities" / "true" / "TRUE_CAPABILITY_AUDIT_20261014_V1.json"


def _run(spec: pathlib.Path, out_dir: pathlib.Path, instances: int = 500):
    cmd = [
        sys.executable,
        str(HARNESS),
        "run",
        "--spec",
        str(spec),
        "--instances",
        str(instances),
        "--receipt-dir",
        str(out_dir),
        "--ledger",
        str(out_dir / "ledger.json"),
        "--root",
        str(ROOT),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900, cwd=str(ROOT))
    receipts = [path for path in out_dir.glob("*.json") if path.name != "ledger.json"]
    assert len(receipts) == 1, proc.stdout + proc.stderr
    return proc, json.loads(receipts[0].read_text(encoding="utf-8"))


def _mutant_spec() -> tuple[pathlib.Path, pathlib.Path]:
    """Create a copied kernel closure whose left-comparison mutation is wrong."""
    parent = ROOT / "tmp_true_capability_mutants"
    work = parent / "coupled_comparison_kernel_mutant"
    work.mkdir(parents=True, exist_ok=False)
    for source in (KERNEL, PATCH_KERNEL, STRICT_KERNEL):
        shutil.copyfile(source, work / source.name)
    patch_kernel = work / PATCH_KERNEL.name
    text = patch_kernel.read_text(encoding="utf-8")
    original = "    ast.Lt:ast.LtE, ast.LtE:ast.Lt,\n"
    assert original in text
    patch_kernel.write_text(
        text.replace(original, "    ast.Lt:ast.GtE, ast.LtE:ast.Lt,\n"),
        encoding="utf-8",
    )
    adapter = ADAPTER.read_text(encoding="utf-8")
    import_line = (
        "from canonical.runtime.bound_capabilities import "
        "python_coupled_software_repair_loop_v1 as _coupled"
    )
    assert import_line in adapter
    mutant_adapter = work / "adapter.py"
    mutant_adapter.write_text(
        adapter.replace(
            import_line,
            "from tmp_true_capability_mutants.coupled_comparison_kernel_mutant "
            "import python_coupled_software_repair_loop_v1 as _coupled",
        ),
        encoding="utf-8",
    )
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    spec["solver"]["module"] = str(mutant_adapter.relative_to(ROOT))
    spec["solver"]["kernels"] = [str((work / KERNEL.name).relative_to(ROOT))]
    mutant_spec = work / "spec.json"
    mutant_spec.write_text(json.dumps(spec), encoding="utf-8")
    return work, mutant_spec


def test_coupled_repair_spec_passes_on_fresh_instances(tmp_path):
    proc, receipt = _run(SPEC, tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert receipt["verdict"] == "PASS", receipt.get("failures_sample")
    assert receipt["instances"] == receipt["instance_pass"] == 500
    assert receipt["authority"] == "NONE"
    assert receipt["network_blocked"] is True
    assert receipt["banned_modules_detected"] == []
    assert receipt["per_oracle"]["ANALYTIC_CLOSED_FORM"]["pass"] == 500


def test_coupled_repair_spec_catches_wrong_comparison_mutation(tmp_path):
    work, mutant_spec = _mutant_spec()
    try:
        proc, receipt = _run(mutant_spec, tmp_path)
    finally:
        shutil.rmtree(work, ignore_errors=True)
        try:
            work.parent.rmdir()
        except OSError:
            pass
    assert proc.returncode != 0
    assert receipt["verdict"] == "FAIL"
    assert receipt["instance_pass"] == 0
    assert receipt["per_oracle"]["ANALYTIC_CLOSED_FORM"]["fail"] > 0
    assert receipt["per_oracle"]["BOUNDARY_METAMORPHIC"]["fail"] > 0
    assert receipt["per_oracle"]["PATCH_AND_PROVENANCE_PROPERTIES"]["fail"] > 0


def test_generator_and_oracles_are_separate_from_the_repair_runtime():
    for path in (GENERATOR, ORACLES):
        text = path.read_text(encoding="utf-8")
        for forbidden in (
            "python_coupled_comparison_repair_true_adapter",
            "python_coupled_software_repair_loop",
            "canonical.runtime",
            "importlib",
        ):
            assert forbidden not in text, (path.name, forbidden)


def test_committed_measurement_binds_current_adapter_and_kernel():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    row = ledger["rows"]["PYTHON_COUPLED_COMPARISON_REPAIR_V1"]
    receipt = json.loads((ROOT / row["latest_receipt"]).read_text(encoding="utf-8"))
    assert receipt["verdict"] == row["verdict"] == "PASS"
    assert receipt["authority"] == "NONE"
    assert receipt["instances"] == row["instances"] >= 2000
    assert receipt["banned_modules_detected"] == []
    expected_blobs = (
        (ADAPTER, row["solver_git_blob_sha"], receipt["blobs"]["solver"]["git_blob_sha"]),
        (
            KERNEL,
            row["kernel_git_blob_shas"][str(KERNEL.relative_to(ROOT))],
            receipt["blobs"]["kernels"][0]["git_blob_sha"],
        ),
        (GENERATOR, receipt["blobs"]["generator"]["git_blob_sha"], receipt["blobs"]["generator"]["git_blob_sha"]),
        (ORACLES, receipt["blobs"]["oracles"]["git_blob_sha"], receipt["blobs"]["oracles"]["git_blob_sha"]),
    )
    for path, ledger_or_receipt_expected, receipt_expected in expected_blobs:
        actual = subprocess.run(
            ["git", "hash-object", str(path)],
            capture_output=True,
            check=True,
            text=True,
            cwd=str(ROOT),
        ).stdout.strip()
        assert ledger_or_receipt_expected == receipt_expected, path.name
        assert actual == receipt_expected, (path.name, actual, receipt_expected)
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    components = [
        component for component in audit["components"]
        if component.get("spec") == "PYTHON_COUPLED_COMPARISON_REPAIR_V1"
    ]
    assert len(components) == 1
    assert components[0]["classification"] == "MEASURED_PASS"
    measured = [
        component for component in audit["components"]
        if component["classification"].startswith("MEASURED_")
    ]
    assert len(measured) == (
        audit["summary"]["components_measured_pass"]
        + audit["summary"]["components_measured_fail"]
    )
    measured_spec_count = sum(len(component.get("specs", [component["spec"]])) for component in measured)
    assert measured_spec_count == audit["summary"]["measured_specs_total"] == 10
