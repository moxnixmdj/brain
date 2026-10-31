"""Reinspection and world inference do not traverse symlinked path components."""
import io
import json
import tarfile

import pytest

from canonical.runtime import world_binding_v1
from canonical.runtime.raw_goal_archive_acceptance_v1 import (
    ArchiveReinspectionError, inspect_archive_manifest,
)


def _member(tar, name, raw):
    info = tarfile.TarInfo(name)
    info.size = len(raw)
    tar.addfile(info, io.BytesIO(raw))


def test_world_binding_skips_symlinked_source_directory(tmp_path):
    canonical = tmp_path / "canonical"
    canonical.mkdir()
    (canonical / "real").mkdir()
    (canonical / "real" / "source.txt").write_text("hello")
    (canonical / "links").symlink_to("real", target_is_directory=True)
    (canonical / "A_manifest.json").write_text(json.dumps({"records": [
        {"verification_paths": ["canonical/links/source.txt"]}]}))
    (canonical / "Z_manifest.json").write_text('{"records": []}')
    assert world_binding_v1._world_path_for("manifest_path", "archive.tar_gz.create_from_manifest", tmp_path) == "canonical/Z_manifest.json"


def test_reinspection_refuses_a_symlinked_source_directory(tmp_path):
    canonical = tmp_path / "canonical"
    canonical.mkdir()
    (canonical / "real").mkdir()
    source = b"hello"
    (canonical / "real" / "source.txt").write_bytes(source)
    (canonical / "links").symlink_to("real", target_is_directory=True)
    manifest = json.dumps({"records": [{"verification_paths": ["canonical/links/source.txt"]}]}).encode()
    (canonical / "manifest.json").write_bytes(manifest)
    with tarfile.open(tmp_path / "bundle.tar.gz", "w:gz") as tar:
        _member(tar, "canonical/manifest.json", manifest)
        _member(tar, "canonical/links/source.txt", source)
    with pytest.raises(ArchiveReinspectionError):
        inspect_archive_manifest(tmp_path, "canonical/manifest.json", "bundle.tar.gz")


@pytest.mark.parametrize("which", ["manifest_parent", "archive_parent"])
def test_reinspection_refuses_symlinked_manifest_or_output_directory(tmp_path, which):
    canonical = tmp_path / "canonical"
    canonical.mkdir()
    (canonical / "real").mkdir()
    (canonical / "alias").symlink_to("real", target_is_directory=True)
    manifest = b'{"records": []}'
    (canonical / "real" / "manifest.json").write_bytes(manifest)
    manifest_path = "canonical/alias/manifest.json" if which == "manifest_parent" else "canonical/real/manifest.json"
    archive_path = "canonical/alias/bundle.tar.gz" if which == "archive_parent" else "bundle.tar.gz"
    with tarfile.open(tmp_path / archive_path, "w:gz") as tar:
        _member(tar, manifest_path, manifest)
    with pytest.raises(ArchiveReinspectionError):
        inspect_archive_manifest(tmp_path, manifest_path, archive_path)
