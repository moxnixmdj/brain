from __future__ import annotations

import io
import json
import pathlib
import tarfile

import pytest

from canonical.runtime.bound_capabilities import archive_verify_gnu_tar as mod


def _bundle(root: pathlib.Path, *, mutate: bool = False, extra: bool = False) -> tuple[str, str]:
    src = root / "canonical" / "x.txt"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("hello\n", encoding="utf-8")
    manifest = root / "canonical" / "manifest.json"
    manifest.write_text(json.dumps({
        "records": [{"verification_paths": ["canonical/x.txt"]}]
    }), encoding="utf-8")
    archive = root / "bundle.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        for p in [manifest, src]:
            data = p.read_bytes()
            if mutate and p == src:
                data = b"evil\n"
            ti = tarfile.TarInfo(str(p.relative_to(root)).replace("\\", "/"))
            ti.size = len(data)
            tf.addfile(ti, io.BytesIO(data))
        if extra:
            data = b"x"
            ti = tarfile.TarInfo("extra.txt")
            ti.size = 1
            tf.addfile(ti, io.BytesIO(data))
    return str(manifest.relative_to(root)), str(archive.relative_to(root))


def test_exact_archive_passes_without_extraction(tmp_path):
    manifest, archive = _bundle(tmp_path)
    out = mod.run({"manifest_path": manifest, "archive_path": archive}, tmp_path)
    assert out["verified"] is True
    assert out["member_count"] == 2


def test_hash_mismatch_fails(tmp_path):
    manifest, archive = _bundle(tmp_path, mutate=True)
    with pytest.raises(RuntimeError, match="ARCHIVE_HASH_MISMATCH"):
        mod.run({"manifest_path": manifest, "archive_path": archive}, tmp_path)


def test_unexpected_member_fails(tmp_path):
    manifest, archive = _bundle(tmp_path, extra=True)
    with pytest.raises(RuntimeError, match="ARCHIVE_MEMBER_SET_MISMATCH"):
        mod.run({"manifest_path": manifest, "archive_path": archive}, tmp_path)


def test_symlink_member_fails_closed(tmp_path):
    src = tmp_path / "canonical" / "x.txt"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("hello\n", encoding="utf-8")
    manifest = tmp_path / "canonical" / "manifest.json"
    manifest.write_text(json.dumps({"records": [{"verification_paths": ["canonical/x.txt"]}]}), encoding="utf-8")
    archive = tmp_path / "bundle.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        data = manifest.read_bytes()
        ti = tarfile.TarInfo("canonical/manifest.json")
        ti.size = len(data)
        tf.addfile(ti, io.BytesIO(data))
        link = tarfile.TarInfo("canonical/x.txt")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        tf.addfile(link)
    with pytest.raises(RuntimeError, match="ARCHIVE_MEMBER_NOT_REGULAR_FILE"):
        mod.run({"manifest_path": "canonical/manifest.json", "archive_path": "bundle.tar.gz"}, tmp_path)


def test_runtime_source_has_no_process_creation():
    source = pathlib.Path(mod.__file__).read_text(encoding="utf-8")
    assert "subprocess." not in source
    assert "import subprocess" not in source
