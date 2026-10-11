from __future__ import annotations

import os
from pathlib import Path

from canonical.runtime.bound_capabilities.python_request_acceptance_model_v2 import compile_plan
from canonical.runtime.bound_capabilities.python_request_acceptance_model_v3 import (
    build_baseline_manifest,
    evaluate_plan,
)


def _repo(tmp_path: Path) -> Path:
    (tmp_path / "lib").mkdir()
    (tmp_path / "verification").mkdir()
    (tmp_path / "settings").mkdir()
    return tmp_path


def test_v3_heldout_complete_bound_content_request(tmp_path):
    root = _repo(tmp_path)
    (root / "lib/worker.py").write_text("def work(v):\n    return v * 2\n", encoding="utf-8")
    plan = compile_plan(
        'File "lib/worker.py" must exist. '
        'Python file "lib/worker.py" must parse. '
        'File "lib/worker.py" must contain "def work". '
        'File "lib/worker.py" must not contain "compile(".'
    )
    out = evaluate_plan(plan, repo_root=root)
    assert out["pass"] is True
    assert out["repair_stop_authorized_by_this_capability"] is True
    assert out["baseline_manifest_used"] is False


def test_v3_heldout_unbound_semantics_cannot_be_overridden_by_many_passing_tests(tmp_path):
    root = _repo(tmp_path)
    (root / "lib/decoder.py").write_text("def decode(v):\n    return v\n", encoding="utf-8")
    plan = compile_plan(
        'Python file "lib/decoder.py" must parse. '
        'Recover malformed nested records without losing valid siblings.'
    )
    out = evaluate_plan(
        plan,
        repo_root=root,
        existing_test_evidence={"status": "PASS", "tests_passed": 50000},
    )
    assert out["pass"] is False
    assert out["unbound_predicate_count"] >= 1
    assert out["existing_test_evidence_is_request_semantics_authority"] is False
    assert out["repair_stop_authorized_by_this_capability"] is False


def test_v3_heldout_scope_uses_baseline_diff_not_caller_claim(tmp_path):
    root = _repo(tmp_path)
    (root / "lib/main.py").write_text("VALUE=1\n", encoding="utf-8")
    (root / "lib/side.py").write_text("SIDE=1\n", encoding="utf-8")
    baseline = build_baseline_manifest(root)
    plan = compile_plan('Only modify "lib/main.py".')

    (root / "lib/main.py").write_text("VALUE=2\n", encoding="utf-8")
    good = evaluate_plan(plan, repo_root=root, baseline_manifest=baseline)
    assert good["pass"] is True
    assert good["predicate_results"][0]["details"]["changed_paths"] == ["lib/main.py"]

    (root / "lib/side.py").write_text("SIDE=2\n", encoding="utf-8")
    bad = evaluate_plan(plan, repo_root=root, baseline_manifest=baseline)
    assert bad["pass"] is False
    assert bad["predicate_results"][0]["reason"] == "CHANGED_PATH_OUTSIDE_SCOPE"
    assert set(bad["predicate_results"][0]["details"]["changed_paths"]) == {"lib/main.py", "lib/side.py"}


def test_v3_heldout_do_not_modify_uses_content_baseline(tmp_path):
    root = _repo(tmp_path)
    (root / "settings/locked.py").write_text("LOCKED=True\n", encoding="utf-8")
    (root / "lib/free.py").write_text("FREE=1\n", encoding="utf-8")
    baseline = build_baseline_manifest(root)
    plan = compile_plan('Must not modify "settings/locked.py".')

    (root / "lib/free.py").write_text("FREE=2\n", encoding="utf-8")
    assert evaluate_plan(plan, repo_root=root, baseline_manifest=baseline)["pass"] is True

    (root / "settings/locked.py").write_text("LOCKED=False\n", encoding="utf-8")
    bad = evaluate_plan(plan, repo_root=root, baseline_manifest=baseline)
    assert bad["pass"] is False
    assert bad["predicate_results"][0]["reason"] == "PATH_CHANGED"


def test_v3_heldout_changed_test_cannot_self_certify(tmp_path):
    root = _repo(tmp_path)
    test = root / "verification/test_rule.py"
    test.write_text("assert 7 * 6 == 42\n", encoding="utf-8")
    baseline = build_baseline_manifest(root)
    plan = compile_plan('Test file "verification/test_rule.py" must pass.')

    assert evaluate_plan(plan, repo_root=root, baseline_manifest=baseline)["pass"] is True

    test.write_text("assert True\n", encoding="utf-8")
    bad = evaluate_plan(plan, repo_root=root, baseline_manifest=baseline)
    assert bad["pass"] is False
    assert bad["predicate_results"][0]["reason"] == "TEST_VERIFIER_CHANGED_SINCE_BASELINE"


def test_v3_heldout_side_effecting_test_is_rejected(tmp_path):
    root = _repo(tmp_path)
    test = root / "verification/test_side_effect.py"
    test.write_text(
        "from pathlib import Path\nPath('created-by-test.txt').write_text('x')\nassert True\n",
        encoding="utf-8",
    )
    baseline = build_baseline_manifest(root)
    plan = compile_plan('Test file "verification/test_side_effect.py" must pass.')
    out = evaluate_plan(plan, repo_root=root, baseline_manifest=baseline)
    assert out["pass"] is False
    assert out["predicate_results"][0]["reason"] == "TEST_VERIFIER_SIDE_EFFECT"
    assert "created-by-test.txt" in out["predicate_results"][0]["details"]["side_effect_paths"]


def test_v3_heldout_scope_without_baseline_fails_closed(tmp_path):
    root = _repo(tmp_path)
    (root / "lib/only.py").write_text("X=1\n", encoding="utf-8")
    plan = compile_plan('Only modify "lib/only.py".')
    out = evaluate_plan(plan, repo_root=root)
    assert out["pass"] is False
    assert out["predicate_results"][0]["reason"] == "BASELINE_MANIFEST_REQUIRED"


def test_v3_heldout_tampered_baseline_hash_fails_closed(tmp_path):
    root = _repo(tmp_path)
    (root / "lib/a.py").write_text("A=1\n", encoding="utf-8")
    baseline = build_baseline_manifest(root)
    baseline = dict(baseline)
    baseline["manifest_sha256"] = "0" * 64
    plan = compile_plan('Only modify "lib/a.py".')
    out = evaluate_plan(plan, repo_root=root, baseline_manifest=baseline)
    assert out["pass"] is False
    assert out["predicate_results"][0]["reason"] == "BASELINE_MANIFEST_HASH_MISMATCH"


def test_v3_heldout_symlink_verifier_path_is_rejected(tmp_path):
    root = _repo(tmp_path)
    real = root / "lib/real.py"
    real.write_text("Y=1\n", encoding="utf-8")
    link = root / "lib/alias.py"
    try:
        link.symlink_to(real)
    except (OSError, NotImplementedError):
        return
    plan = compile_plan('File "lib/alias.py" must exist.')
    out = evaluate_plan(plan, repo_root=root)
    assert out["pass"] is False
    assert out["predicate_results"][0]["reason"] == "SYMLINK_REJECTED:lib/alias.py"


def test_v3_heldout_quote_aware_mapping_still_covers_every_raw_obligation(tmp_path):
    root = _repo(tmp_path)
    (root / "lib/live.py").write_text("Z=(3+4)\n", encoding="utf-8")
    plan = compile_plan('File "lib/gone.py" must not exist. Python file "lib/live.py" must parse.')
    assert plan["raw_obligation_count"] > plan["predicate_count"]
    out = evaluate_plan(plan, repo_root=root)
    assert out["pass"] is True
    assert out["verified_pass_raw_obligation_count"] == out["raw_obligation_count"]
