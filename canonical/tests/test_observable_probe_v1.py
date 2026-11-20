"""Tests for read-only probes that make latent conditions observable."""
from __future__ import annotations

import pathlib
import subprocess

from canonical.runtime import observable_probe_v1 as PROBE


def _git(path: pathlib.Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=brain", "-c", "user.email=brain@example.com",
                    *args], cwd=str(path), check=True, capture_output=True)


def test_tar_and_gzip_probes_distinguish_valid_from_invalid_without_mutation(tmp_path):
    root = pathlib.Path(tmp_path)
    (root / "data.txt").write_text("hello\n", encoding="utf-8")
    subprocess.run(["tar", "-czf", "bundle.tgz", "data.txt"], cwd=str(root), check=True)
    subprocess.run(["gzip", "-kf", "data.txt"], cwd=str(root), check=True)
    (root / "data.txt.gz").rename(root / "payload.gz")

    for name in ("archive_valid", "gzip_valid"):
        before = PROBE.state_digest(root)
        result = PROBE.run_probe(name, root)
        assert result["read_only"] is True
        assert result["fact"] == name + ".valid"
        assert PROBE.state_digest(root) == before

    (root / "bundle.tgz").write_bytes(b"not an archive\n")
    (root / "payload.gz").write_bytes(b"not gzip\n")
    assert PROBE.run_probe("archive_valid", root)["fact"] == "archive_valid.invalid"
    assert PROBE.run_probe("gzip_valid", root)["fact"] == "gzip_valid.invalid"


def test_patch_probe_uses_git_apply_check_and_is_read_only(tmp_path):
    root = pathlib.Path(tmp_path)
    _git(root, "init", "-q")
    (root / "file.txt").write_text("one\n", encoding="utf-8")
    _git(root, "add", "file.txt")
    _git(root, "commit", "-q", "-m", "first")
    (root / "file.txt").write_text("two\n", encoding="utf-8")
    _git(root, "commit", "-q", "-am", "second")
    patch = subprocess.run(["git", "--no-pager", "diff", "HEAD~1", "HEAD"],
                           cwd=str(root), check=True, capture_output=True, text=True).stdout
    (root / "change.patch").write_text(patch, encoding="utf-8")
    subprocess.run(["git", "checkout", "-q", "HEAD~1"], cwd=str(root), check=True)

    before = PROBE.state_digest(root)
    result = PROBE.run_probe("patch_applies", root)
    assert result["read_only"] is True
    assert result["fact"] == "patch_applies.valid"
    assert PROBE.state_digest(root) == before

    (root / "file.txt").write_text("three\n", encoding="utf-8")
    assert PROBE.run_probe("patch_applies", root)["fact"] == "patch_applies.invalid"


def test_augment_adds_only_probe_facts_and_preserves_existing_facts(tmp_path):
    root = pathlib.Path(tmp_path)
    (root / "data.txt").write_text("hello\n", encoding="utf-8")
    subprocess.run(["tar", "-czf", "bundle.tgz", "data.txt"], cwd=str(root), check=True)
    subprocess.run(["gzip", "-kf", "data.txt"], cwd=str(root), check=True)
    (root / "data.txt.gz").rename(root / "payload.gz")
    state = type("State", (), {})()
    state.facts = ("worktree.clean",)
    state.path = root
    PROBE.augment(state)
    assert "worktree.clean" in state.facts
    assert "archive_valid.valid" in state.facts
    assert "gzip_valid.valid" in state.facts
    assert "patch_applies.absent" in state.facts
