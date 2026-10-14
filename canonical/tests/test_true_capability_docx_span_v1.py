"""The three DOCX span-editor specs under the true-capability harness, with mutants the tests must catch.

The kernels are byte-pinned by capability records (canonical/capabilities/opus55/M2_DOCX_*.json), so every measurement goes through
canonical/runtime/docx_true_capability_adapters_v1.py and the mutants are scratch copies.
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
SPAN = SPECS / "DOCX_RUN_SPAN_REPLACE_V1.json"
TXN = SPECS / "DOCX_TEXT_EDIT_TRANSACTION_V1.json"
STORY = SPECS / "DOCX_STORY_PART_REPLACE_V1.json"
RT = ROOT / "canonical" / "runtime"
K_SPAN, K_TXN, K_STORY = RT / "docx_run_span_replace.py", RT / "docx_text_edit_transaction.py", RT / "docx_story_part_replace.py"
ADAPTER = RT / "docx_true_capability_adapters_v1.py"
IMPORTS = {K_SPAN: "from canonical.runtime import docx_run_span_replace as _span",
           K_TXN: "from canonical.runtime import docx_text_edit_transaction as _txn",
           K_STORY: "from canonical.runtime import docx_story_part_replace as _story"}
PINS = {K_SPAN: "915cea0532a1a304f2f08c764135d2f6f44614e5",
        K_TXN: "5ada9da10b7fdc6592373a1ae2eaa579ee7992de",
        K_STORY: "d908ef95b4abe7d4d52be5700f94cd65e25de4f6"}
PIN_RECORDS = {K_SPAN: "M2_DOCX_RUN_SPAN_REPLACEMENT_001.json",
               K_TXN: "M2_DOCX_TEXT_EDIT_TRANSACTION_001.json",
               K_STORY: "M2_DOCX_STORY_PART_REPLACEMENT_001.json"}
OPUS55 = ROOT / "canonical" / "capabilities" / "opus55"
LEDGER = ROOT / "canonical" / "capabilities" / "true" / "TRUE_CAPABILITY_LEDGER_V1.json"
AUDIT = ROOT / "canonical" / "capabilities" / "true" / "TRUE_CAPABILITY_AUDIT_20261014_V1.json"


def _blob(path: pathlib.Path) -> str:
    return subprocess.run(["git", "hash-object", str(path)], capture_output=True, text=True, cwd=str(ROOT)).stdout.strip()


def _run(spec: pathlib.Path, out_dir: pathlib.Path, instances: int = 500):
    cmd = [sys.executable, str(HARNESS), "run", "--spec", str(spec), "--instances", str(instances),
           "--receipt-dir", str(out_dir), "--ledger", str(out_dir / "ledger.json"), "--root", str(ROOT)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900, cwd=str(ROOT))
    receipts = [p for p in sorted(out_dir.glob("*.json"), key=lambda p: p.stat().st_mtime) if p.name != "ledger.json"]
    assert receipts, proc.stdout + proc.stderr
    return proc, json.loads(receipts[-1].read_text())


def _mutant(tmp_path, spec_path, kernel, name, kernel_replacements, adapter_replacements=()):
    """Mutate the pinned kernel (and/or the adapter) in scratch copies under the repository root."""
    src = kernel.read_text(encoding="utf-8")
    for a, b in kernel_replacements:
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
    for a, b in adapter_replacements:
        assert a in adapter_src, a
        adapter_src = adapter_src.replace(a, b)
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
def test_span_spec_passes_on_fresh_instances(tmp_path):
    proc, rec = _run(SPAN, tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert rec["verdict"] == "PASS" and rec["instance_pass"] == rec["instances"] == 500, rec.get("failures_sample")
    assert rec["authority"] == "NONE" and rec["banned_modules_detected"] == []
    assert [k["path"] for k in rec["blobs"]["kernels"]] == ["canonical/runtime/docx_run_span_replace.py"]
    assert rec["blobs"]["kernels"][0]["git_blob_sha"] == PINS[K_SPAN]


def test_transaction_spec_passes_on_fresh_instances(tmp_path):
    proc, rec = _run(TXN, tmp_path)
    assert rec["verdict"] == "PASS" and rec["instance_pass"] == 500, rec.get("failures_sample")


def test_story_spec_passes_on_fresh_instances(tmp_path):
    proc, rec = _run(STORY, tmp_path)
    assert rec["verdict"] == "PASS" and rec["instance_pass"] == 500, rec.get("failures_sample")


# ----------------------------------------------------------------------------- mutants: one span
def test_span_catches_non_unique_target_accepted(tmp_path):
    proc, rec = _mutant(tmp_path, SPAN, K_SPAN, "span_mut_nonunique", [("    if len(matches) != 1:\n", "    if len(matches) < 1:\n")])
    assert rec["verdict"] == "FAIL" and rec["per_oracle"]["EXPECTED_OUTCOME"]["fail"] > 0


def test_span_catches_non_overlapping_occurrence_count(tmp_path):
    # "abab" in "ababab" occurs twice when overlaps are counted; a solver that skips past each match sees one
    proc, rec = _mutant(tmp_path, SPAN, K_SPAN, "span_mut_overlap_count", [("        i = j + 1\n", "        i = j + len(needle)\n")])
    assert rec["verdict"] == "FAIL" and rec["per_oracle"]["EXPECTED_OUTCOME"]["fail"] > 0


def test_span_catches_middle_runs_left_in_place(tmp_path):
    proc, rec = _mutant(tmp_path, SPAN, K_SPAN, "span_mut_middle_runs", [('            _set_text(node, "")\n', "            pass\n")])
    assert rec["verdict"] == "FAIL" and rec["per_oracle"]["EXPECTED_OUTCOME"]["fail"] > 0


def test_span_catches_output_left_behind_on_failure(tmp_path):
    proc, rec = _mutant(tmp_path, SPAN, K_SPAN, "span_mut_left_behind", [], adapter_replacements=[
        ('        return _finish(_span.replace_unique_paragraph_span(src, dst, old=instance["old"], new=instance["new"]), dst)',
         '        res = _span.replace_unique_paragraph_span(src, dst, old=instance["old"], new=instance["new"])\n'
         '        if res.get("status") != "PASS":\n            dst.write_bytes(src.read_bytes())\n'
         '        return _finish(res, dst)'),
    ])
    assert rec["verdict"] == "FAIL" and rec["per_oracle"]["EXPECTED_OUTCOME"]["fail"] > 0


# ----------------------------------------------------------------------------- mutants: transaction
def test_transaction_catches_overlap_check_removed(tmp_path):
    proc, rec = _mutant(tmp_path, TXN, K_TXN, "txn_mut_overlap", [("            if right[0] < left[1]:\n", "            if False:\n")])
    assert rec["verdict"] == "FAIL" and rec["per_oracle"]["EXPECTED_OUTCOME"]["fail"] > 0


def test_transaction_catches_touching_spans_rejected(tmp_path):
    proc, rec = _mutant(tmp_path, TXN, K_TXN, "txn_mut_touching", [("            if right[0] < left[1]:\n", "            if right[0] <= left[1]:\n")])
    assert rec["verdict"] == "FAIL" and rec["per_oracle"]["EXPECTED_OUTCOME"]["fail"] > 0


def test_transaction_catches_non_unique_target_accepted(tmp_path):
    proc, rec = _mutant(tmp_path, TXN, K_TXN, "txn_mut_nonunique", [("        if len(matches) != 1:\n", "        if len(matches) < 1:\n")])
    assert rec["verdict"] == "FAIL" and rec["per_oracle"]["EXPECTED_OUTCOME"]["fail"] > 0


def test_transaction_catches_best_effort_partial_apply(tmp_path):
    proc, rec = _mutant(tmp_path, TXN, K_TXN, "txn_mut_partial", [], adapter_replacements=[
        ("        return _finish(_txn.apply_text_edit_transaction(src, dst, edits=edits), dst)",
         "        res = _txn.apply_text_edit_transaction(src, dst, edits=edits)\n"
         "        if res.get('status') != 'PASS' and len(edits) > 1:\n"
         "            cur = src\n"
         "            for i, e in enumerate(edits):\n"
         "                nxt = Path(td) / f'step{i}.docx'\n"
         "                if _span.replace_unique_paragraph_span(cur, nxt, old=e.old, new=e.new).get('status') == 'PASS':\n"
         "                    cur = nxt\n"
         "            if cur != src:\n"
         "                dst.write_bytes(cur.read_bytes())\n"
         "                res = {'status': 'PASS', 'reason': None}\n"
         "        return _finish(res, dst)"),
    ])
    assert rec["verdict"] == "FAIL"
    assert rec["per_oracle"]["EXPECTED_OUTCOME"]["fail"] > 0 and rec["per_oracle"]["ATOMICITY_AND_INVERSE"]["fail"] > 0


# ----------------------------------------------------------------------------- mutants: story part
def test_story_catches_any_part_name_accepted(tmp_path):
    proc, rec = _mutant(tmp_path, STORY, K_STORY, "story_mut_any_part", [
        ("    return isinstance(part_name, str) and bool(_ALLOWED.fullmatch(part_name))\n",
         "    return isinstance(part_name, str) and part_name.startswith('word/')\n"),
    ])
    assert rec["verdict"] == "FAIL" and rec["per_oracle"]["EXPECTED_OUTCOME"]["fail"] > 0


def test_story_catches_non_unique_target_accepted(tmp_path):
    proc, rec = _mutant(tmp_path, STORY, K_STORY, "story_mut_nonunique", [("    if len(matches) != 1:\n", "    if len(matches) < 1:\n")])
    assert rec["verdict"] == "FAIL" and rec["per_oracle"]["EXPECTED_OUTCOME"]["fail"] > 0


# ----------------------------------------------------------------------------- separation and bookkeeping
def test_generator_and_oracles_do_not_import_solvers():
    for rel in ("canonical/capabilities/true/generators/docx_span_edit_gen_v1.py",
                "canonical/capabilities/true/oracles/docx_span_edit_oracles_v1.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        for banned in ("docx_run_span_replace", "docx_text_edit_transaction", "docx_story_part_replace",
                       "docx_true_capability_adapters", "canonical.runtime", "importlib", "ElementTree"):
            assert banned not in text, (rel, banned)


def test_kernels_are_byte_identical_to_their_governance_pins():
    # the adapters exist so that the pinned editors are measured unchanged
    for kernel, pinned in PINS.items():
        assert _blob(kernel) == pinned, (kernel.name, _blob(kernel))
        record = json.loads((OPUS55 / PIN_RECORDS[kernel]).read_text(encoding="utf-8"))
        assert record["implementation_blob_sha"] == pinned, kernel.name


def test_specs_declare_their_pinned_kernels():
    for spec_path, kernel in ((SPAN, K_SPAN), (TXN, K_TXN), (STORY, K_STORY)):
        spec = json.loads(spec_path.read_text())
        assert spec["solver"]["module"] == str(ADAPTER.relative_to(ROOT))
        assert spec["solver"]["kernels"] == [str(kernel.relative_to(ROOT))]
        assert spec["model_dependency_count"] == 0 and spec["pass_threshold"] == 1.0 and spec["min_instances"] >= 500


def test_ledger_rows_match_committed_receipts():
    ledger = json.loads(LEDGER.read_text())
    audit = json.loads(AUDIT.read_text())
    kernels = {"DOCX_RUN_SPAN_REPLACE_V1": K_SPAN, "DOCX_TEXT_EDIT_TRANSACTION_V1": K_TXN, "DOCX_STORY_PART_REPLACE_V1": K_STORY}
    for cap, kernel in kernels.items():
        row = ledger["rows"][cap]
        receipt = json.loads((ROOT / row["latest_receipt"]).read_text())
        assert receipt["capability_id"] == cap and receipt["verdict"] == row["verdict"] == "PASS"
        assert receipt["instances"] == row["instances"] >= 1000 and receipt["instance_pass"] == receipt["instances"]
        assert receipt["authority"] == "NONE" and receipt["banned_modules_detected"] == [] and receipt["network_blocked"] is True
        assert row["solver_git_blob_sha"] == _blob(ADAPTER)
        assert row["kernel_git_blob_shas"] == {str(kernel.relative_to(ROOT)): PINS[kernel]}
        comps = [c for c in audit["components"] if cap in (c.get("specs") or [c.get("spec")])]
        assert comps and all(c["classification"] == "MEASURED_PASS" for c in comps), cap
