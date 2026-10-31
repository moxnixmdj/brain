"""An inferred archive manifest must actually contain a valid member list."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from canonical.runtime import goal_compiler, world_binding_v1

CID = "archive.tar_gz.create_from_manifest"


@pytest.mark.parametrize("bad", [
    {"nested": {"record": {"status": "ok"}}},
    {"records": "not a list"},
    {"records": [{"verification_paths": "not a list"}]},
    {"records": [{"verification_paths": ["canonical/../outside.txt"]}]},
    {"records": [{"verification_paths": ["canonical/missing.txt"]}]},
])
def test_world_binding_skips_invalid_manifest_shapes_and_missing_sources(tmp_path: Path, bad):
    folder = tmp_path / "canonical"
    folder.mkdir()
    (folder / "A_manifest.json").write_text(json.dumps(bad))
    (folder / "source.txt").write_text("data")
    (folder / "Z_manifest.json").write_text(json.dumps({"records": [
        {"verification_paths": ["canonical/source.txt"]}]}))
    found = world_binding_v1._world_path_for("manifest_path", CID, tmp_path)
    assert found == "canonical/Z_manifest.json"


def test_world_binding_refuses_when_no_complete_archive_manifest_exists(tmp_path: Path):
    folder = tmp_path / "canonical"
    folder.mkdir()
    (folder / "not_a_manifest.json").write_text(json.dumps({"nested": {"record": {"x": 1}}}))
    assert world_binding_v1._world_path_for("manifest_path", CID, tmp_path) is None


def test_world_binding_does_not_infer_a_symlinked_manifest_member(tmp_path: Path):
    folder = tmp_path / "canonical"
    folder.mkdir()
    (folder / "real.txt").write_text("data")
    (folder / "link.txt").symlink_to("real.txt")
    (folder / "A_manifest.json").write_text(json.dumps({"records": [
        {"verification_paths": ["canonical/link.txt"]}]}))
    (folder / "Z_manifest.json").write_text('{"records": []}')
    assert world_binding_v1._world_path_for("manifest_path", CID, tmp_path) == "canonical/Z_manifest.json"


def test_explicit_manifest_path_is_not_replaced_with_a_world_guess(tmp_path: Path):
    folder = tmp_path / "canonical"
    folder.mkdir()
    (folder / "bad_manifest.json").write_text('{}')
    (folder / "good_manifest.json").write_text('{"records": []}')
    entry = {"capability_id": CID, "action_template": {"args": {
        "manifest_path": "${input.manifest_path}", "output_path": "${input.output_path}"}}}
    goal = "Create a tar.gz archive from canonical/bad_manifest.json."
    got = world_binding_v1.complete_inputs(goal, tmp_path, entry, compiler=goal_compiler)
    assert got["inputs"].get("manifest_path") == "canonical/bad_manifest.json", got
