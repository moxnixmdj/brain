"""Real subprocess/property/repair tests; no fake tools or producer-only verdicts."""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

import pytest

from canonical.runtime.bound_capabilities import evidence_oracle_concrete_v1 as concrete
from canonical.runtime.bound_capabilities import evidence_oracle_hypothesis_v1 as hypothesis
from canonical.runtime.bound_capabilities import software_repair_loop_cegis_hypothesis_v1 as repair


@pytest.mark.parametrize("oracle", [concrete, hypothesis])
def test_real_contract_not_hardcoded_nonnegative(oracle, tmp_path):
    source = 'def f(x):\n    """post: _ == x - 1000"""\n    return x - 1000\n'
    result = oracle.run({"source": source, "output_path": "result.json"}, tmp_path)
    assert result["verified"] is True
    assert result["check_completed"] is True
    assert result["checked"] > 0
    assert result["violations"] == []
    assert result["proves_absence"] is False
    raw = (tmp_path / "result.json").read_bytes()
    assert result["output_sha256"] == hashlib.sha256(raw).hexdigest()
    assert json.loads(raw)["source_sha256"] == hashlib.sha256(source.encode()).hexdigest()


@pytest.mark.parametrize("oracle", [concrete, hypothesis])
@pytest.mark.parametrize("source", [
    'def f(x):\n    """post: _ == x + 1"""\n    return x\n',
    'def f(x):\n    """post: _ >= 0"""\n    raise ValueError("broken")\n',
])
def test_actual_violation_never_passes(oracle, source, tmp_path):
    result = oracle.run({"source": source, "output_path": "result.json"}, tmp_path)
    assert result["status"] == "CONTRACT_VIOLATION_FOUND"
    assert result["check_completed"] is True
    assert result["verified"] is False
    assert result["output_verified"] is False
    assert result["checked"] > 0
    assert len(result["violations"]) > 0


@pytest.mark.parametrize("oracle", [concrete, hypothesis])
@pytest.mark.parametrize("source", [
    "not valid Python !!!",
    "def f(x): return abs(x)\n",
    'def g(x):\n    """post: _ >= 0"""\n    return abs(x)\n',
    'def f(x):\n    """post: unknown_name(_)"""\n    return x\n',
])
def test_invalid_missing_or_unevaluable_contract_never_passes(oracle, source, tmp_path):
    result = oracle.run({"source": source, "output_path": "result.json"}, tmp_path)
    assert result["verified"] is False
    assert result["output_verified"] is False
    assert result["check_completed"] is False


@pytest.mark.parametrize("oracle", [concrete, hypothesis])
def test_missing_source_cannot_run_default_demo(oracle, tmp_path):
    with pytest.raises(ValueError, match="SOURCE_REQUIRED"):
        oracle.run({"output_path": "out.json"}, tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("oracle", [concrete, hypothesis])
def test_source_and_existing_output_are_preserved(oracle, tmp_path):
    path = tmp_path / "source.py"
    original = b'def f(x):\n    """post: _ == x"""\n    return x\n'
    path.write_bytes(original)
    with pytest.raises(ValueError, match="OUTPUT_ALIASES_SOURCE"):
        oracle.run({"source_path": "source.py", "output_path": "source.py"}, tmp_path)
    report = tmp_path / "existing.json"
    report.write_bytes(b"user work")
    with pytest.raises(ValueError, match="OUTPUT_ALREADY_EXISTS"):
        oracle.run({"source_path": "source.py", "output_path": "existing.json"}, tmp_path)
    assert path.read_bytes() == original
    assert report.read_bytes() == b"user work"


@pytest.mark.parametrize("oracle", [concrete, hypothesis])
def test_source_path_escape_is_refused(oracle, tmp_path):
    with pytest.raises(ValueError, match="PATH_OUTSIDE_REPOSITORY"):
        oracle.run({"source_path": "../outside.py", "output_path": "out.json"}, tmp_path)


def test_missing_hypothesis_does_not_fabricate_checks(tmp_path):
    # -S runs a real child without site packages, not an import/mock shim.
    proc = subprocess.run(
        [sys.executable, "-I", "-S", str(pathlib.Path(hypothesis.__file__).resolve()), "--worker"],
        input=json.dumps({"source": "def f(x): return x"}), capture_output=True,
        text=True, cwd=tmp_path, timeout=5,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["status"] == "UNAVAILABLE__HYPOTHESIS"
    assert result["checked"] == 0
    assert result["check_completed"] is False
    assert result["verified"] is False


@pytest.mark.parametrize("oracle", [concrete, hypothesis])
def test_nonterminating_source_is_bounded(oracle, tmp_path):
    result = oracle.run({"source": "while True: pass\n", "timeout_s": 1,
                         "output_path": "out.json"}, tmp_path)
    # Hypothesis can refuse unsupported source without evaluating it.
    assert result["status"] in {"TIMEOUT__PROPERTY_CHECK", "UNSUPPORTED__FUNCTION_F_REQUIRED"}
    assert result["verified"] is False
    assert result["checked"] == 0


@pytest.mark.parametrize("oracle", [concrete, hypothesis])
def test_candidate_stdout_does_not_corrupt_protocol(oracle, tmp_path):
    result = oracle.run({
        "source": 'print("candidate noise")\ndef f(x):\n    """post: _ == x"""\n    return x\n',
        "output_path": "out.json",
    }, tmp_path)
    assert result["verified"] is True
    assert result["checked"] > 0


def test_finite_input_domain_reports_actual_not_requested_count(tmp_path):
    result = hypothesis.run({
        "source": 'def f(x):\n    """post: _ == x"""\n    return x\n',
        "min_value": 0, "max_value": 0, "max_examples": 50, "output_path": "out.json",
    }, tmp_path)
    assert result["verified"] is True
    assert result["checked"] == 1


@pytest.mark.parametrize("extra", [{"min_value": 10, "max_value": 1},
                                   {"max_examples": 0}, {"max_examples": True}])
def test_invalid_property_bounds_are_refused(extra, tmp_path):
    with pytest.raises(ValueError, match="INVALID"):
        hypothesis.run({"source": "def f(x): return x", **extra}, tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("budget", [0, -1, True, "3", 101])
def test_empty_or_invalid_repair_budget_cannot_pass(budget, tmp_path):
    with pytest.raises(ValueError, match="BUDGET"):
        repair.run({"budget": budget}, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_budget_only_registry_invocation_is_not_task_success(tmp_path):
    with pytest.raises(ValueError, match="SOURCE_ROOT_REQUIRED"):
        repair.run({"budget": 1}, tmp_path)
    assert list(tmp_path.iterdir()) == []


def _repair_args(tmp_path, post="_ == (x <= 3)"):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "m.py").write_text(f'def f(x):\n    """post: {post}"""\n    return x < 3\n')
    (pkg / "trace_fail.py").write_text("from m import f\nassert f(3)\n")
    (pkg / "trace_pass.py").write_text("from m import f\nassert f(2)\n")
    (pkg / "test_all.py").write_text(
        "from m import f\nassert f(3)\nassert f(2)\nassert not f(4)\n")
    return {
        "source_root": "pkg", "test_paths": ["pkg/trace_fail.py", "pkg/trace_pass.py"],
        "test_argv": [sys.executable, "pkg/test_all.py"],
        "task_text": "tests_pass must be true.\npython_parse_ok must be true.",
        "output_path": "out.json", "timeout_s": 4, "budget": 1,
        "contract_checks": [{"source_path": "m.py", "max_examples": 30}],
        "max_guided_files": 1, "max_guided_symbols_per_file": 3,
        "mutations_per_file": 12, "max_pair_candidates": 100,
        "max_control_files": 6, "max_control_symbols_per_file": 6,
    }


def test_real_repair_candidate_is_checked_and_original_source_preserved(tmp_path):
    args = _repair_args(tmp_path)
    before = {p.name: p.read_bytes() for p in (tmp_path / "pkg").glob("*.py")}
    result = repair.run(args, tmp_path)
    assert result["pass"] is True, result
    assert result["verified"] is True
    assert result["iterations"] == 1
    assert result["source_restored"] is True
    assert result["independent_semantic_oracle_credit"] is False
    measurement = result["measurement"]
    assert measurement["measured_fields"]["tests_pass"] is True
    assert measurement["measured_fields"]["python_parse_ok"] is True
    checks = measurement["contract_checks"]
    assert len(checks) == 1
    assert checks[0]["pass"] is True
    assert checks[0]["concrete"]["checked"] == 13
    assert checks[0]["hypothesis"]["checked"] > 0
    assert before == {p.name: p.read_bytes() for p in (tmp_path / "pkg").glob("*.py")}
    # Apply the emitted diff with the existing applier, then use an independently
    # written exhaustive predicate over this finite domain, not producer flags.
    from canonical.runtime.bound_capabilities import python_repair_measured_acceptance_controller_v1 as controller
    patch = result["patches"][0]
    fixed = controller._apply_unified_diff(before["m.py"].decode(), patch["unified_diff"])
    ns = {}
    exec(compile(fixed, "<test-candidate>", "exec"), ns)
    assert all(ns["f"](x) == (x <= 3) for x in range(-200, 201))
    assert checks[0]["source_sha256"] == hashlib.sha256(fixed.encode()).hexdigest()
    assert list(tmp_path.glob(".repair-check-*")) == []


def test_passing_tests_do_not_override_failing_candidate_contract(tmp_path):
    args = _repair_args(tmp_path, post="_ is False")
    original = (tmp_path / "pkg/m.py").read_bytes()
    result = repair.run(args, tmp_path)
    assert result["measurement"]["repair_pass"] is True
    assert result["measurement"]["measured_fields"]["tests_pass"] is True
    assert result["measurement"]["contract_checks_pass"] is False
    assert result["measurement"]["contract_checks"][0]["concrete"]["violations"]
    assert result["pass"] is False
    assert result["verified"] is False
    assert result["patches"] == []
    assert (tmp_path / "pkg/m.py").read_bytes() == original


def test_semantic_residual_cannot_be_laundered_by_property_checks(tmp_path):
    args = _repair_args(tmp_path)
    args["task_text"] = "Fix every possible bug."
    result = repair.run(args, tmp_path)
    assert result["measurement"]["contract_checks_pass"] is True
    assert result["measurement"]["acceptance_stop_authorized"] is False
    assert result["pass"] is False
    assert result["verified"] is False


@pytest.mark.parametrize("check", [
    {}, {"source_path": "../outside.py"}, {"source_path": "missing.py"},
    {"source_path": "m.py", "max_examples": 0},
    {"source_path": "m.py", "min_value": 10, "max_value": 1},
    {"source_path": "m.py", "unexpected": "ignored checks are unsafe"},
])
def test_invalid_contract_request_is_rejected_before_repair(check, tmp_path):
    args = _repair_args(tmp_path)
    args["contract_checks"] = [check]
    before = {p.name: p.read_bytes() for p in (tmp_path / "pkg").glob("*.py")}
    with pytest.raises((ValueError, RuntimeError), match="INVALID"):
        repair.run(args, tmp_path)
    assert before == {p.name: p.read_bytes() for p in (tmp_path / "pkg").glob("*.py")}
    assert not (tmp_path / "out.json").exists()
    assert list(tmp_path.glob(".repair-check-*")) == []


def test_skipped_property_checks_are_not_reported_as_executed(tmp_path):
    from canonical.runtime.bound_capabilities import python_repair_measured_acceptance_controller_v1 as controller
    args = _repair_args(tmp_path)
    args.pop("contract_checks")
    args.pop("budget")
    result = controller.run(args, tmp_path)
    assert result["pass"] is True
    assert result["contract_checks"] == []
    assert result["contract_checks_executed"] is False
    assert result["contract_checks_pass"] is None
