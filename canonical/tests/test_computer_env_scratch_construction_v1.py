"""Construction must not silently erase a caller's existing files."""
import pytest

from canonical.runtime.computer_env_v1 import ComputerEnv


def test_existing_nonempty_root_is_refused_without_any_changes(tmp_path):
    root = tmp_path / "user-files"
    (root / "nested").mkdir(parents=True)
    (root / "important.txt").write_bytes(b"keep")
    (root / "nested" / "notes.txt").write_bytes(b"also keep")
    with pytest.raises(ValueError, match="COMPUTER_ENV_ROOT_NOT_EMPTY"):
        ComputerEnv(root=root, programs=[])
    assert (root / "important.txt").read_bytes() == b"keep"
    assert (root / "nested" / "notes.txt").read_bytes() == b"also keep"
    assert sorted(path.name for path in root.iterdir()) == ["important.txt", "nested"]


def test_symlink_root_is_refused_without_touching_target(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "document.txt").write_bytes(b"keep")
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="COMPUTER_ENV_ROOT_IS_SYMLINK"):
        ComputerEnv(root=link, programs=[])
    assert (target / "document.txt").read_bytes() == b"keep"
    assert link.is_symlink()


@pytest.mark.parametrize("name", ["../outside.txt", "/tmp/outside.txt", "nested/file", "..", ".", "a\\b", "a\x00b"])
def test_seed_names_cannot_escape_or_name_a_directory(tmp_path, name):
    root = tmp_path / "scratch"
    with pytest.raises(ValueError, match="COMPUTER_ENV_INVALID_SEED_NAME"):
        ComputerEnv(root=root, seed={name: b"data"}, programs=[])
    assert not root.exists()


def test_empty_explicit_root_and_new_root_work_as_dedicated_scratch(tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    for root in (existing, tmp_path / "new"):
        env = ComputerEnv(root=root, seed={"source.txt": b"source"}, programs=[])
        try:
            assert env.read("source.txt") == b"source"
            (root / "temporary.txt").write_bytes(b"temporary")
            env.reset()
            assert env.read("source.txt") == b"source"
            assert not (root / "temporary.txt").exists()
        finally:
            env.close()
        assert root.is_dir()  # supplied roots remain owned by their callers


def test_bad_seed_data_fails_before_root_creation(tmp_path):
    root = tmp_path / "scratch"
    with pytest.raises(ValueError, match="COMPUTER_ENV_INVALID_SEED_BYTES"):
        ComputerEnv(root=root, seed={"source.txt": "not bytes"}, programs=[])
    assert not root.exists()
