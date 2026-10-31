"""Real namespace and normal-entry execution, with no tool substitutes."""
import json
from pathlib import Path

import pytest

from canonical.runtime.confined_crossfile_qualification_v1 import qualify
from canonical.tests.test_task_bound_crossfile_workflow_v1 import repo, contents
from canonical.tests.test_zero_ambient_namespace_launcher_v1 import UID, GID


@pytest.mark.parametrize("kind", ["issue", "task"])
def test_normal_entry_baseline_change_and_replay_are_confined(tmp_path, kind):
    project = repo.__wrapped__(tmp_path)
    outside = tmp_path / "private-canary"
    outside.write_text("must not be visible or changed")
    test = project / "src/tests/test_core.py"
    test.write_text(test.read_text() + f'''\n
def test_actual_confinement():
    import os, pathlib
    assert not pathlib.Path({str(outside)!r}).exists()
    assert all(not pathlib.Path(p).exists() for p in ['/home', '/proc', '/sys', '/etc'])
    assert list(pathlib.Path('/dev').iterdir()) == [pathlib.Path('/dev/null')]
    try:
        pathlib.Path('/input/request.json').write_text('tampered')
    except OSError:
        pass
    else:
        raise AssertionError('declared input was writable')
''')
    before = contents(project / "src")
    result = qualify(project / "src", json.loads((project / (kind + ".json")).read_bytes()),
                     input_kind=kind, host_uid=UID, host_gid=GID)
    assert result["pass"] is True, result
    assert result["source_unchanged"] is True
    assert result["input_snapshot_unchanged"] is True
    assert result["source_promotion_performed"] is False
    assert result["independent_semantic_oracle_credit"] is False
    assert result["terminal_credit_delta"] == 0
    assert result["execution"]["returncode"] == 0
    observed = result["observed"]
    assert observed["baseline"]["completed"] == 2
    assert observed["report"]["regression"]["completed"] == 2
    assert observed["solve"]["crossfile_acceptance_complete"] is True
    ledger = observed["solve"]["raw_goal_acceptance"]["reinspection_ledger"]
    assert ledger[0]["reinspection"]["tests_replayed"] == 2
    assert contents(project / "src") == before
    assert outside.read_text() == "must not be visible or changed"
    assert not (project / "out").exists()


def test_real_test_failure_cannot_become_qualification_success(tmp_path):
    project = repo.__wrapped__(tmp_path)
    test = project / "src/tests/test_core.py"
    test.write_text(test.read_text().replace("== 2", "== 999"))
    result = qualify(project / "src", json.loads((project / "issue.json").read_bytes()),
                     host_uid=UID, host_gid=GID)
    assert result["pass"] is False
    assert result["observed"]["baseline"]["failed"] == 1
    assert result["observed"]["solve"]["pass"] is False
    assert result["source_unchanged"] is True


@pytest.mark.parametrize("limit", [True, 0, 301, "10"])
def test_invalid_wallclock_refuses_before_execution(tmp_path, limit):
    project = repo.__wrapped__(tmp_path)
    with pytest.raises(ValueError, match="WALLCLOCK_MUST_BE_BOUNDED_INTEGER"):
        qualify(project / "src", {}, wallclock_s=limit)
    assert not (project / "out").exists()


def test_symlink_input_is_rejected_before_copy(tmp_path):
    project = repo.__wrapped__(tmp_path)
    canary = project / "secret"
    canary.write_text("not authorized project input")
    (project / "src/link.py").symlink_to(canary)
    with pytest.raises(ValueError, match="SOURCE_TREE_INVALID"):
        qualify(project / "src", {})
