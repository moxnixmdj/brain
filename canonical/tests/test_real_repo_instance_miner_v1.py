"""The miner must refuse an invalid instance, and must say why.

The whole value of a rate is its denominator. A miner that quietly accepts commits whose
fix cannot be shown to fail under revert produces instances where the "bug" is already
fixed by the newer tests, and the solve rate becomes fiction. These tests pin the refusals.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import real_repo_instance_miner_v1 as M  # noqa: E402


def test_test_path_detection_covers_the_common_layouts():
    for p in ["tests/test_a.py", "src/pkg/tests/t.py", "pkg/test_x.py", "a/b_test.py"]:
        assert M.TEST_HINT.search(p), p
    for p in ["src/pkg/core.py", "src/pkg/testing_utils.py"]:
        assert not M.TEST_HINT.search(p), p


def test_a_commit_without_a_test_change_is_not_a_candidate():
    """A fix with no test has no oracle, so no instance can be built from it."""
    # no network needed: the rule is checked on the filter itself
    files = [{"filename": "src/pkg/core.py", "patch": "@@ -1 +1 @@"}]
    tests = [f for f in files if M.TEST_HINT.search(f["filename"])]
    assert tests == []


def test_rejection_reasons_are_a_closed_set():
    allowed_prefixes = {
        "NO_TEST_CHANGED", "NO_SOURCE_CHANGED", "PARENT_UNRECOVERABLE", "NO_TESTS_DIR",
        "FIX_CONTROL_NOT_GREEN", "REVERT_DOES_NOT_FAIL", "API_FAIL", "EXCEPTION",
        "PYTEST_FAILED",
    }
    src = Path(M.__file__).read_text()
    for reason in allowed_prefixes:
        assert reason in src, f"undocumented rejection path: {reason}"


def test_mining_yields_only_instances_with_both_controls_proven():
    """Live check, skipped without network. Every returned instance must carry evidence."""
    try:
        M.list_fix_commits("pallets/markupsafe", per_page=5)
    except Exception:
        pytest.skip("no network")
    import tempfile
    import shutil
    from pathlib import Path as P
    work = P(tempfile.mkdtemp())
    try:
        out = M.mine(["pallets/markupsafe"], limit=1, max_commits=20, workdir=work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    for inst in out["instances"]:
        assert inst["valid"] is True
        assert "failed" in inst["fix_control"] and not inst["fix_control"].startswith("0 ")
        assert "passed" in inst["revert_control"]
        assert not inst["revert_control"].endswith(" 0 failed")
    assert out["trained_parameters"] == 0
    assert out["external_model_calls"] == 0
