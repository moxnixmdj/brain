"""The source snapshot notices persistent non-excluded tree changes."""
import pytest

from canonical.runtime.bound_capabilities import python_issue_to_pr_orchestrate as orchestrator


@pytest.mark.parametrize("kind", ["add", "delete", "content", "empty_directory", "symlink_target"])
def test_manifest_detects_tree_changes(tmp_path, kind):
    (tmp_path / "a.txt").write_text("one")
    if kind == "symlink_target":
        try:
            (tmp_path / "link").symlink_to("a.txt")
        except (OSError, NotImplementedError):
            pytest.skip("symlinks unavailable")
    before = orchestrator._tree_manifest(tmp_path)
    if kind == "add":
        (tmp_path / "new.lock").write_text("one")
    elif kind == "delete":
        (tmp_path / "a.txt").unlink()
    elif kind == "content":
        (tmp_path / "a.txt").write_text("two")
    elif kind == "empty_directory":
        (tmp_path / "empty").mkdir()
    else:
        (tmp_path / "link").unlink()
        (tmp_path / "link").symlink_to("missing")
    assert orchestrator._tree_manifest(tmp_path) != before


def test_module_path_refuses_symlink_outside_worktree(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (work / "pkg").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(SystemExit, match="PATH_ESCAPE"):
        orchestrator._module_path(work, "pkg/new.py")
    assert not (outside / "new.py").exists()
