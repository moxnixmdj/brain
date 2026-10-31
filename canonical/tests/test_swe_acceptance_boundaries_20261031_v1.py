"""Regression controls for source promotion and honest SWE verification boundaries."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
from unittest import mock

import pytest

from canonical.runtime.bound_capabilities import _swe_static_soundness_v1 as static
from canonical.runtime.bound_capabilities import software_hardcore_final_supercomposer_v1 as composer
from canonical.runtime.bound_capabilities import software_patch_cegis_z3_v1 as cegis
from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as search

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def work():
    parent = ROOT / "canonical/astra_runtime/tmp"
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="acceptance-boundaries-", dir=parent) as directory:
        yield Path(directory)


def _fixture(work, extra="", *, crlf=False):
    source = work / "src"
    source.mkdir()
    module = source / "candidate.py"
    original = b"def f(x):\n    return 0\n"
    if crlf:
        original = original.replace(b"\n", b"\r\n")
    module.write_bytes(original)
    tests = work / "test_candidate.py"
    tests.write_text(
        "import unittest\nfrom candidate import f\n"
        "class T(unittest.TestCase):\n"
        "    def test_example(self):\n        self.assertEqual(f(1), 2)\n" + extra,
        encoding="utf-8",
    )
    args = {"source_root": str(source.relative_to(ROOT)),
            "test_paths": [str(tests.relative_to(ROOT))],
            "output_path": str((work / "report.json").relative_to(ROOT)),
            "timeout_s": 3, "apply_in_place": True}
    return module, original, args


@pytest.mark.parametrize("apply", [False, True])
@pytest.mark.parametrize("crlf", [False, True])
def test_failed_real_acceptance_restores_exact_bytes(work, apply, crlf):
    module, original, args = _fixture(work,
        "    def test_extra_obligation(self):\n"
        "        if f(3) != 999:\n            raise RuntimeError('unmet acceptance obligation')\n",
        crlf=crlf)
    args["apply_in_place"] = apply
    result = cegis.run(args, ROOT)
    assert result["verified"] is False
    assert result["pass"] is False
    assert module.read_bytes() == original


@pytest.mark.parametrize("apply", [False, True])
def test_successful_real_acceptance_applies_only_when_requested(work, apply):
    module, original, args = _fixture(work)
    args["apply_in_place"] = apply
    result = cegis.run(args, ROOT)
    assert result["verified"] is True
    assert result["result"]["post_test_returncode"] == 0
    assert (module.read_bytes() != original) is apply


def test_runner_exception_restores_exact_bytes(work):
    module, original, args = _fixture(work, crlf=True)
    real_run = search._run_tests
    calls = 0

    def fail_candidate(*a, **kw):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected runner failure")
        return real_run(*a, **kw)

    with mock.patch.object(search, "_run_tests", side_effect=fail_candidate):
        with pytest.raises(RuntimeError, match="injected runner failure"):
            cegis.run(args, ROOT)
    assert calls == 2
    assert module.read_bytes() == original


def test_candidate_timeout_restores_source(work):
    module, original, args = _fixture(work,
        "    def test_slow_candidate(self):\n"
        "        if f(3) != 0:\n            import time\n            time.sleep(4)\n")
    args["timeout_s"] = 1
    result = cegis.run(args, ROOT)
    assert result["verified"] is False
    assert module.read_bytes() == original


@pytest.mark.parametrize("annotation,value,expected", [
    ("int | None", '"wrong"', False),
    ("Optional[int]", '"wrong"', False),
    ("typing.Union[int, None]", '"wrong"', False),
    ("int | None", "None", True),
    ("Optional[int]", "1", True),
    ("str | int", '"ok"', True),
    ("Union[str, int]", "1", True),
    ("int | None", "True", False),
    ("Any", '"ok"', True),
    ("CompanyAny", '"wrong"', None),
    ("int | External", '"wrong"', None),
    ('Literal[1, "ok"]', '"bad"', False),
    ("Literal[1]", "True", False),
    ('Annotated[int, "units"]', '"bad"', False),
])
def test_annotation_matching_has_explicit_unknown(annotation, value, expected):
    import ast
    assert static._matches_prim_annotation(annotation, ast.literal_eval(value)) is expected


def test_union_violation_is_not_sound(work):
    module = work / "bad.py"
    module.write_text('x: int | None = "wrong"\ndef f() -> int | None:\n    return "wrong"\n')
    report = static.analyze_python_static_soundness(ROOT, module)
    assert report["sound"] is False
    assert {item["code"] for item in report["errors"]} == {
        "ANNOTATION_LITERAL_MISMATCH", "RETURN_TYPE_MISMATCH"}


def test_unknown_annotation_is_reported_not_certified(work):
    module = work / "unknown.py"
    module.write_text('class External: pass\nx: External = 1\n')
    report = static.analyze_python_static_soundness(ROOT, module)
    assert report["sound"] is False
    assert report["annotation_checks_complete"] is False
    assert "ANNOTATION_NOT_CHECKED" in {x["code"] for x in report["warnings"]}


def test_truncated_analysis_does_not_certify_whole_tree(work):
    (work / "a.py").write_text("x = 1\n")
    (work / "b.py").write_text("broken = missing\n")
    report = static.analyze_python_static_soundness(ROOT, work, max_files=1)
    assert report["sound"] is False
    assert report["analysis_complete"] is False
    assert report["files_omitted"] == 1


def test_final_composer_does_not_verify_registry_declarations(work):
    result = composer.run({"output_path": str((work / "composition.json").relative_to(ROOT))}, ROOT)
    report = json.loads((ROOT / result["output_path"]).read_text())
    assert report["workflow_executed"] is False
    assert report["verification_scope"] == "DECLARATIONS_ONLY"
    assert report["verified"] is False
    assert result["output_verified"] is False
    assert result["artifact_integrity_verified"] is True


def test_final_composer_preserves_existing_output(work):
    output = work / "occupied.json"
    output.write_bytes(b"do not overwrite")
    with pytest.raises(ValueError, match="OUTPUT_ALREADY_EXISTS"):
        composer.run({"output_path": str(output.relative_to(ROOT))}, ROOT)
    assert output.read_bytes() == b"do not overwrite"


def test_report_publication_failure_rolls_back_verified_source(work):
    module, original, args = _fixture(work, crlf=True)
    with mock.patch.object(cegis, "publish_report", side_effect=OSError("injected disk failure")):
        with pytest.raises(OSError, match="injected disk failure"):
            cegis.run(args, ROOT)
    assert module.read_bytes() == original


def test_baseline_timeout_does_not_attempt_or_promote_a_candidate(work):
    module, original, args = _fixture(work,
        "    def test_slow_baseline(self):\n        import time\n        time.sleep(4)\n")
    args["timeout_s"] = 1
    result = cegis.run(args, ROOT)
    assert result["verified"] is False
    assert result["result"]["failure_reason"] == "BASELINE_TIMEOUT"
    assert module.read_bytes() == original


def test_empty_static_analysis_does_not_certify_a_tree(work):
    result = static.analyze_python_static_soundness(ROOT, work)
    assert result["files_checked"] == 0
    assert result["sound"] is False
    assert result["analysis_complete"] is False


def test_complete_declarations_and_clean_static_check_still_are_not_delivery(work):
    registry = work / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
    registry.parent.mkdir(parents=True)
    producers = ["software.hardcore.swe.supercomposer.v1", "software.patch.synthesize.cegis.z3.v1",
                 "software.synthesis.grid_induction.v1", "software.hardcore.kernel.orchestrate.v1"]
    registry.write_text(json.dumps({"capabilities": {
        cid: {"provides": list(composer.REQUIRES)} for cid in producers}}))
    (work / "clean.py").write_text("x: int = 1\n")
    result = composer.run({"source_root": "clean.py", "output_path": "report.json"}, work)
    assert result["declarations_resolve"] is True
    assert result["static_soundness"]["sound"] is True
    assert result["workflow_executed"] is False
    assert result["verified"] is False
    assert result["output_verified"] is False
