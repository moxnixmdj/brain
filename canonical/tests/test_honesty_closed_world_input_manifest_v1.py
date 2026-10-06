from __future__ import annotations

import copy
import pathlib
import tempfile

from canonical.runtime.honesty_closed_world_input_manifest_v1 import (
    SCHEMA,
    ClosedWorldInputError,
    manifest_sha256,
    scan_input_dir,
    verify_declared_manifest,
)


def make_tree():
    td = tempfile.TemporaryDirectory()
    root = pathlib.Path(td.name)
    (root / "a.txt").write_text("alpha")
    (root / "nested").mkdir()
    (root / "nested" / "b.bin").write_bytes(b"beta")
    scan = scan_input_dir(root)
    declared = {
        "schema": SCHEMA,
        "entries": copy.deepcopy(scan["entries"]),
        "manifest_sha256": scan["manifest_sha256"],
    }
    return td, root, declared


def test_exact_tree_passes_and_exports_all_files_as_ledger_inputs():
    td, root, declared = make_tree()
    try:
        out = verify_declared_manifest(
            input_dir=root,
            declared_manifest=declared,
        )
        assert out["status"] == "PASS__EXACT_CLOSED_WORLD_INPUT_TREE_BOUND"
        assert out["entry_count"] == 2
        assert out["all_inputs_material_for_honesty"] is True
        assert len(out["ledger_declared_inputs"]) == 2
    finally:
        td.cleanup()


def test_extra_file_fails_closed():
    td, root, declared = make_tree()
    try:
        (root / "secret.txt").write_text("hidden answer")
        try:
            verify_declared_manifest(input_dir=root, declared_manifest=declared)
        except ClosedWorldInputError as exc:
            assert "DOES_NOT_EQUAL_ACTUAL_TREE" in str(exc)
        else:
            raise AssertionError("extra file accepted")
    finally:
        td.cleanup()


def test_changed_file_bytes_fail_closed():
    td, root, declared = make_tree()
    try:
        (root / "a.txt").write_text("changed")
        try:
            verify_declared_manifest(input_dir=root, declared_manifest=declared)
        except ClosedWorldInputError as exc:
            assert "DOES_NOT_EQUAL_ACTUAL_TREE" in str(exc)
        else:
            raise AssertionError("changed bytes accepted")
    finally:
        td.cleanup()


def test_missing_file_fails_closed():
    td, root, declared = make_tree()
    try:
        (root / "a.txt").unlink()
        try:
            verify_declared_manifest(input_dir=root, declared_manifest=declared)
        except ClosedWorldInputError as exc:
            assert "DOES_NOT_EQUAL_ACTUAL_TREE" in str(exc)
        else:
            raise AssertionError("missing file accepted")
    finally:
        td.cleanup()


def test_symlink_input_is_forbidden():
    td, root, declared = make_tree()
    try:
        target = root / "a.txt"
        link = root / "link.txt"
        try:
            link.symlink_to(target)
        except OSError:
            return
        try:
            scan_input_dir(root)
        except ClosedWorldInputError as exc:
            assert "SYMLINK_FORBIDDEN" in str(exc)
        else:
            raise AssertionError("symlink accepted")
    finally:
        td.cleanup()


def test_duplicate_declared_identity_fails_closed():
    td, root, declared = make_tree()
    try:
        x = copy.deepcopy(declared)
        x["entries"][1]["input_id"] = x["entries"][0]["input_id"]
        x["manifest_sha256"] = manifest_sha256(x["entries"])
        try:
            verify_declared_manifest(input_dir=root, declared_manifest=x)
        except ClosedWorldInputError as exc:
            assert "DUPLICATE" in str(exc)
        else:
            raise AssertionError("duplicate id accepted")
    finally:
        td.cleanup()


def test_path_traversal_fails_closed():
    td, root, declared = make_tree()
    try:
        x = copy.deepcopy(declared)
        x["entries"][0]["relative_path"] = "../escape"
        x["manifest_sha256"] = manifest_sha256(x["entries"])
        try:
            verify_declared_manifest(input_dir=root, declared_manifest=x)
        except ClosedWorldInputError as exc:
            assert "PATH_INVALID" in str(exc)
        else:
            raise AssertionError("path traversal accepted")
    finally:
        td.cleanup()


def test_manifest_hash_mutation_fails_closed():
    td, root, declared = make_tree()
    try:
        x = copy.deepcopy(declared)
        x["manifest_sha256"] = "0" * 64
        try:
            verify_declared_manifest(input_dir=root, declared_manifest=x)
        except ClosedWorldInputError as exc:
            assert "MANIFEST_SHA256_MISMATCH" in str(exc)
        else:
            raise AssertionError("bad manifest hash accepted")
    finally:
        td.cleanup()
