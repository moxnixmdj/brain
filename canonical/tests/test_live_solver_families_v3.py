"""Wave-3 execution families and the executor-gap bridge (E1): independent readers, the
unified-diff applier, generator oracles, and the fail-closed paths of the local adapter runner.
No live solver run here."""
from __future__ import annotations

import json
import random
import shutil
from pathlib import Path

import pytest

from canonical.runtime import live_brain_route_admission_v1 as adm
from execution_guard import live_solver_end_to_end_measurement_v1 as h
from execution_guard import live_solver_families_v3 as v3


# --------------------------------------------------------------------------- readers

@pytest.mark.parametrize("hex_bytes, expected", [
    # bsonspec.org examples
    ("160000000268656c6c6f0006000000776f726c640000", {"hello": "world"}),
    ("310000000442534f4e002600000002300008000000617765736f6d65000131003333333333331440103200c20700000000", {"BSON": ["awesome", 5.05, 1986]}),
    # bool, null, int64, nested document
    ("17000000 08620001 0a6e00 1269000100000000000000 00".replace(" ", ""), {"b": True, "n": None, "i": 1}),
])
def test_bson_decoder_known_vectors(hex_bytes, expected):
    assert v3.bson_decode(bytes.fromhex(hex_bytes)) == expected


def test_bson_decoder_rejects_bad_length_and_trailing_bytes():
    with pytest.raises(ValueError):
        v3.bson_decode(bytes.fromhex("170000000268656c6c6f0006000000776f726c640000"))  # length says 23, doc is 22
    with pytest.raises(ValueError):
        v3.bson_decode(bytes.fromhex("160000000268656c6c6f0006000000776f726c64000000"))  # one extra byte


def test_bson_envelope_decoder_requires_the_adapter_envelope_key():
    with pytest.raises(ValueError):
        v3._bson_envelope_decoder(bytes.fromhex("160000000268656c6c6f0006000000776f726c640000"))


def test_safe_eval_matches_python_on_the_generated_shapes():
    assert v3.safe_eval("3*x**2 - y/4 + 7", {"x": 3, "y": 8}) == 3 * 9 - 2 + 7
    assert v3.safe_eval("(x + y)*2 - z**2", {"x": 1, "y": 2, "z": 3}) == -3
    with pytest.raises(ValueError):
        v3.safe_eval("__import__('os').system('true')", {})
    with pytest.raises(KeyError):
        v3.safe_eval("x + q", {"x": 1})


def test_apply_unified_diff_applies_a_real_patch_and_rejects_mismatches():
    original = "def f(n):\n    total = 0\n    for v in range(n):\n        total = total - v\n    return total\n"
    diff = ("--- a/m.py\n+++ b/m.py\n@@ -1,5 +1,5 @@\n def f(n):\n     total = 0\n     for v in range(n):\n"
            "-        total = total - v\n+        total = total + v\n     return total\n")
    assert v3.apply_unified_diff(original, diff) == original.replace("total - v", "total + v")
    with pytest.raises(ValueError):
        v3.apply_unified_diff(original.replace("total = 0", "total = 1"), diff)
    with pytest.raises(ValueError):
        v3.apply_unified_diff(original, "no hunks here")


def test_minimal_pdf_has_a_valid_xref_and_carries_the_text():
    pdf = v3._minimal_pdf(["alpha beta", "gamma"])
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF")
    startxref = int(pdf[pdf.rindex(b"startxref") + 9:].split()[0])
    assert pdf[startxref:startxref + 4] == b"xref"
    for n in range(1, 6):
        off = int(pdf[startxref:].split(b"\n")[2 + n].split()[0])
        assert pdf[off:].startswith(f"{n} 0 obj".encode())
    assert b"(alpha beta) Tj" in pdf and b"T* (gamma) Tj" in pdf


# --------------------------------------------------------------------------- generators

@pytest.fixture
def work(tmp_path):
    w = h.ROOT / "canonical" / "astra_runtime" / "tmp" / ("t_v3_" + tmp_path.name)
    w.mkdir(parents=True, exist_ok=True)
    yield w
    shutil.rmtree(w, ignore_errors=True)


def test_fresh_bug_has_exactly_one_failing_per_function_script(work):
    import subprocess, sys
    bug = v3.fresh_bug(random.Random(8), work, 0)
    failing = []
    for t in bug.test_files:
        proc = subprocess.run([sys.executable, str(t)], capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            failing.append(t.name)
    assert len(failing) == 1 and bug.buggy_function in failing[0]
    all_run = subprocess.run([sys.executable, str(bug.all_test)], capture_output=True, text=True, timeout=60)
    assert all_run.returncode != 0 and "FAILED (failures=1)" in all_run.stderr


def test_repair_oracle_requires_a_patch_that_makes_every_script_pass(work):
    case = v3.gen_python_repair(random.Random(8), work, 0)
    bug_dir = next(work.glob("repair_0_*"))
    src = next(bug_dir.glob("calc_*.py"))
    out = case.artifacts[0]
    source = src.read_text()
    fixed = source.replace("a - b", "a + b").replace("total - v", "total + v").replace("v <= limit", "v < limit")
    import difflib
    rel = str(src.relative_to(h.ROOT))
    diff = "".join(difflib.unified_diff(source.splitlines(keepends=True), fixed.splitlines(keepends=True), "a/" + rel, "b/" + rel))
    assert case.oracle({"pass": False, "status": "FAIL"})[0] is False
    out.write_text(json.dumps({"patches": []}))
    assert case.oracle({"pass": True, "status": "PASS"})[0] is False
    out.write_text(json.dumps({"patches": [{"source_path": rel, "unified_diff": diff}]}))
    assert case.oracle({"pass": True, "status": "PASS"})[0] is True
    # a patch that changes the wrong operator does not pass the independent re-run
    wrong = "".join(difflib.unified_diff(source.splitlines(keepends=True), source.replace("return 'high'", "return 'low'").splitlines(keepends=True), "a/" + rel, "b/" + rel))
    out.write_text(json.dumps({"patches": [{"source_path": rel, "unified_diff": wrong}]}))
    assert case.oracle({"pass": True, "status": "PASS"})[0] is False
    # writing into the source is a violation of the tool's declared non-authority
    src.write_text(fixed)
    out.write_text(json.dumps({"patches": [{"source_path": rel, "unified_diff": diff}]}))
    assert case.oracle({"pass": True, "status": "PASS"})[0] is False


def test_fault_localize_oracle_requires_the_buggy_function_on_top(work):
    case = v3.gen_python_fault_localize(random.Random(2), work, 0)
    bug_dir = next(work.glob("fault_0_*"))
    src = next(bug_dir.glob("calc_*.py"))
    rel = str(src.relative_to(h.ROOT))
    names = [l.split("(")[0][4:] for l in src.read_text().splitlines() if l.startswith("def ")]
    buggy = [n for n in names if case.goal and n][0]
    out = case.artifacts[0]
    # discover the injected function from the source text itself
    text = src.read_text()
    if "a - b" in text:
        buggy = names[0]
    elif "total - v" in text:
        buggy = names[1]
    else:
        buggy = names[2]
    other = [n for n in names if n != buggy][0]
    out.write_text(json.dumps({"failing_test_count": 1, "ranked_symbols": [{"path": rel, "kind": "FunctionDef", "symbol": other}, {"path": rel, "kind": "FunctionDef", "symbol": buggy}]}))
    assert case.oracle({"pass": True, "status": "PASS"})[0] is False
    out.write_text(json.dumps({"failing_test_count": 1, "ranked_symbols": [{"path": "elsewhere.py", "kind": "FunctionDef", "symbol": other}, {"path": rel, "kind": "FunctionDef", "symbol": buggy}]}))
    assert case.oracle({"pass": True, "status": "PASS"})[0] is True
    out.write_text(json.dumps({"failing_test_count": 3, "ranked_symbols": [{"path": rel, "kind": "FunctionDef", "symbol": buggy}]}))
    assert case.oracle({"pass": True, "status": "PASS"})[0] is False


def test_sqlite_verify_generator_tampers_every_third_database(work):
    import sqlite3
    intact = v3.gen_sqlite_verify(random.Random(4), work, 0)
    tampered = v3.gen_sqlite_verify(random.Random(4), work, 2)
    assert intact.expect_pass is True and tampered.expect_pass is False
    db = next(work.glob("vdb_2_*.sqlite"))
    records = json.loads(next(work.glob("vrecords_2_*.json")).read_text())["items"]
    table = tampered.goal.split("table named ")[1].rstrip(".")
    conn = sqlite3.connect(str(db))
    rows = dict((r[0], r[1]) for r in conn.execute(f'SELECT capability_id, owner FROM "{table}"'))
    conn.close()
    assert any(rows[k] != records[k]["owner"] for k in rows)
    assert tampered.oracle({"pass": True, "status": "PASS"})[0] is False
    assert intact.oracle({"pass": True, "status": "PASS"})[0] is True


def test_yaml_and_numeric_oracles_check_values_not_existence(work):
    y = v3.gen_yaml_to_json(random.Random(6), work, 0)
    y.artifacts[0].write_text(json.dumps({"name": "x"}))
    assert y.oracle({"pass": True, "status": "PASS"})[0] is False
    src = next(work.glob("cfg_0_*.yaml")).read_text()
    name = src.splitlines()[0].split(": ")[1]
    y.artifacts[0].write_text(json.dumps({"name": name}))
    assert y.oracle({"pass": True, "status": "PASS"})[0] is False  # the whole structure must match, not one key
    n = v3.gen_numeric_expression(random.Random(6), work, 1)
    expr = n.goal.split('"')[1]
    variables = {k: int(v) for k, v in (kv.strip().split(" = ") for kv in n.goal.split("with variables ")[1].split(" using")[0].split(","))}
    n.artifacts[0].write_text(json.dumps({"value": v3.safe_eval(expr, variables) + 1}))
    assert n.oracle({"pass": True, "status": "PASS"})[0] is False
    n.artifacts[0].write_text(json.dumps({"value": v3.safe_eval(expr, variables)}))
    assert n.oracle({"pass": True, "status": "PASS"})[0] is True


def test_pdf_oracle_reads_the_text_field_of_the_execution_row(work):
    case = v3.gen_pdf_text(random.Random(9), work, 0)
    pdf = next(work.glob("paper_0_*.pdf")).read_bytes()
    words = [w.decode() for w in pdf[pdf.index(b"(") + 1:pdf.index(b") Tj")].split()]
    assert case.oracle({"pass": True, "execution": [{"result": {"text": " ".join(words)}}]})[0] is False  # second line missing
    full = " ".join(w.decode() for chunk in pdf.split(b" Tj")[:-1] for w in chunk[chunk.rindex(b"(") + 1:].split())
    assert case.oracle({"pass": True, "execution": [{"result": {"text": full}}]})[0] is True
    assert case.oracle({"pass": True, "execution": []})[0] is False


# --------------------------------------------------------------------------- executor bridge (E1)

def test_kernel_refuses_exactly_the_registry_source_types_the_kernel_rejects():
    from canonical.runtime import goal_compiler as gc
    from canonical.runtime.live_integrated_brain_v1 import load_verified_registry
    registry = gc._platform_admissible_registry(dict(load_verified_registry()))
    refused = sorted(cid for cid, e in registry.items() if adm.kernel_refuses(e))
    assert "python.software.repair.loop.test_guided.ast.v1" in refused
    assert "python.fault.localize.dynamic.dataflow.v1" not in refused  # python_stdlib: the kernel runs it
    assert "json.query.jq" not in refused
    assert all(str(registry[c]["source"]["type"]) in adm.KERNEL_UNSUPPORTED_SOURCE_TYPES for c in refused)
    assert len(refused) == 16


def test_run_adapter_locally_fails_closed():
    base = {"capability_id": "x.y", "adapter_module": "python_source_audit", "source": {"type": "python_stdlib_composition", "modules": ["ast"]}}
    action = {"type": "x.y", "args": {"capability_id": "x.y", "source_root": "canonical/runtime/bound_capabilities", "output_path": "canonical/astra_runtime/tmp/t_v3_audit.json"},
              "expect": {"field": "output_verified", "type": "field_equals", "value": True}}
    with pytest.raises(adm.LocalExecutionFailure, match="NONZERO_COST"):
        adm.run_adapter_locally({**base, "incremental_spend_usd": 1}, action)
    with pytest.raises(adm.LocalExecutionFailure, match="DEPENDENCY_MISSING"):
        adm.run_adapter_locally({**base, "source": {"type": "python_stdlib_composition", "modules": ["no_such_module_xyz"]}}, action)
    with pytest.raises(adm.LocalExecutionFailure, match="ADAPTER_MISSING"):
        adm.run_adapter_locally({**base, "source": {"type": "python_stdlib_composition", "adapter_path": "../../etc/passwd"}}, action)
    with pytest.raises(adm.LocalExecutionFailure, match="ADAPTER_INVALID"):
        adm.run_adapter_locally({**base, "adapter_module": "../evil"}, action)
    with pytest.raises(adm.LocalExecutionFailure, match="ENTRYPOINT_MISSING"):
        adm.run_adapter_locally({**base, "entrypoint": "no_such_function"}, action)
    # a real stdlib adapter runs, and a failed expectation is a closed failure
    result = adm.run_adapter_locally(base, action)
    assert result["output_verified"] is True and result["dependency"]["executor"] == adm.LOCAL_EXECUTION_PROOF
    with pytest.raises(adm.LocalExecutionFailure, match="ACTION_EXPECTATION_FAILED"):
        adm.run_adapter_locally(base, {**action, "expect": {"field": "output_verified", "type": "field_equals", "value": "never"}})
    Path(h.ROOT / "canonical/astra_runtime/tmp/t_v3_audit.json").unlink(missing_ok=True)


def test_check_expectation_semantics_match_the_kernel():
    adm._check_expectation(None, {})
    adm._check_expectation({"field": "text"}, {"text": "x"})
    with pytest.raises(adm.LocalExecutionFailure):
        adm._check_expectation({"field": "text"}, {"text": ""})
    adm._check_expectation({"field": "status", "type": "field_contains", "value": "PASS"}, {"status": "PASS__X"})
    with pytest.raises(adm.LocalExecutionFailure, match="TYPE_UNKNOWN"):
        adm._check_expectation({"field": "a", "type": "json_field_equals"}, {"a": 1})
    with pytest.raises(adm.LocalExecutionFailure, match="FIELD_REQUIRED"):
        adm._check_expectation({"type": "field_equals"}, {})


def test_wave_three_families_are_registered():
    gens = h.all_generators()
    for fam in v3.GENERATORS_V3:
        assert fam in gens
    assert len(v3.GENERATORS_V3) == 9
