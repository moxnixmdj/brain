#!/usr/bin/env python3
"""A writer must not overwrite or remove a pre-existing scratch file.

Before this test, all three adapters silently truncated and deleted an existing
file at their predictable temporary name. The archive publishers also used
os.replace after checking destination absence, allowing a newly created
archive to be overwritten in the check-to-publish interval.

The tests use real files and a Python audit callback to introduce a real
competing destination immediately before publication (or rename symbol lookup).
The callback runs in a fresh interpreter; it does not replace a library function.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.bound_capabilities import file_archive_tar, file_compress, file_edit, file_ops  # noqa: E402

SCRATCH_ROOT = ROOT / "canonical/astra_runtime/tmp"
ORIGINAL = b"alpha\nbeta\n"
PRECIOUS = b"do not overwrite or remove\n"


def _setup(base: pathlib.Path, kind: str):
    src = base / "source.txt"
    src.write_bytes(ORIGINAL)
    rel = src.relative_to(ROOT).as_posix()
    if kind == "edit":
        dest = src
        scratch = src.with_name(src.name + ".brain-edit-tmp")
        args = {"command": "uppercase", "path": rel, "goal": "Uppercase " + rel}
        adapter = file_edit
    elif kind == "gzip":
        dest = src.with_name(src.name + ".gz")
        scratch = src.with_name(src.name + ".gz.brain-compress-tmp")
        args = {"command": "compress", "path": rel, "goal": "Compress " + rel}
        adapter = file_compress
    elif kind == "tar":
        dest = base / "output.tar.gz"
        scratch = dest.with_name(dest.name + ".brain-tar-tmp")
        dst_rel = dest.relative_to(ROOT).as_posix()
        args = {"command": "compress", "path": rel, "output_path": dst_rel,
                "goal": "Compress %s into %s" % (rel, dst_rel)}
        adapter = file_archive_tar
    elif kind in ("copy", "backup", "rename"):
        dest = base / ("source.txt.bak" if kind == "backup" else "destination.txt")
        scratch = None
        dst_rel = dest.relative_to(ROOT).as_posix()
        goal = ("Make a backup of " + rel if kind == "backup" else
                "%s %s to %s" % (kind, rel, dst_rel))
        args = {"command": kind, "path": rel, "goal": goal}
        if kind != "backup":
            args["output_path"] = dst_rel
        adapter = file_ops
    else:
        raise ValueError(kind)
    return src, dest, scratch, args, adapter


def test_existing_temporary_file_is_neither_truncated_nor_removed() -> None:
    SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    for kind in ("edit", "gzip", "tar"):
        with tempfile.TemporaryDirectory(dir=SCRATCH_ROOT) as world:
            src, dest, scratch, args, adapter = _setup(pathlib.Path(world), kind)
            scratch.write_bytes(PRECIOUS)
            try:
                adapter.run(args, ROOT)
            except RuntimeError as exc:
                assert "TEMPORARY_PATH_ALREADY_EXISTS" in str(exc), (kind, exc)
            else:
                raise AssertionError("%s accepted an occupied scratch path" % kind)
            assert scratch.read_bytes() == PRECIOUS, kind
            assert src.read_bytes() == ORIGINAL, kind
            if dest != src:
                assert not dest.exists(), kind


def test_existing_scratch_symlink_and_its_target_are_not_touched() -> None:
    SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    for kind in ("edit", "gzip", "tar"):
        with tempfile.TemporaryDirectory(dir=SCRATCH_ROOT) as world:
            base = pathlib.Path(world)
            src, dest, scratch, args, adapter = _setup(base, kind)
            target = base / "precious.txt"
            target.write_bytes(PRECIOUS)
            scratch.symlink_to(target.name)
            try:
                adapter.run(args, ROOT)
            except RuntimeError as exc:
                assert "TEMPORARY_PATH_ALREADY_EXISTS" in str(exc), (kind, exc)
            else:
                raise AssertionError("%s accepted a scratch symlink" % kind)
            assert scratch.is_symlink(), kind
            assert os.readlink(scratch) == target.name, kind
            assert target.read_bytes() == PRECIOUS, kind
            assert src.read_bytes() == ORIGINAL, kind
            if dest != src:
                assert not dest.exists(), kind


def _race_worker(kind: str, negated_overwrite: bool = False) -> None:
    SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=SCRATCH_ROOT) as world:
        src, dest, scratch, args, adapter = _setup(pathlib.Path(world), kind)
        if negated_overwrite:
            args["goal"] += " and do not overwrite it"
        events = []

        def race(event, event_args):
            if events:
                return
            is_publish = event == "os.link" and pathlib.Path(event_args[1]) == dest
            is_atomic_rename = (kind == "rename" and event == "ctypes.dlsym"
                                and event_args[1] == "renameat2")
            is_creation = (event == "open" and pathlib.Path(event_args[0]) == dest
                           and bool(event_args[2] & os.O_WRONLY))
            if is_publish or is_atomic_rename or (kind in ("copy", "backup") and is_creation):
                events.append(event)
                # A real competitor wins after the adapter's initial exists check.
                with dest.open("xb") as competing:
                    competing.write(PRECIOUS)

        sys.addaudithook(race)
        try:
            adapter.run(args, ROOT)
        except RuntimeError as exc:
            expected = ("THE_ARCHIVE_ALREADY_EXISTS" if kind in ("gzip", "tar") else
                        "A_BACKUP_OF_THIS_FILE_ALREADY_EXISTS" if kind == "backup" else
                        "DESTINATION_EXISTS_AND_THE_SENTENCE_DID_NOT_ASK_TO_OVERWRITE")
            assert expected in str(exc), (kind, exc)
        else:
            raise AssertionError("%s overwrote a competing archive" % kind)
        expected_event = ("open" if kind in ("copy", "backup") else
                          "ctypes.dlsym" if kind == "rename" else "os.link")
        assert events == [expected_event], events
        assert dest.read_bytes() == PRECIOUS, kind
        assert src.read_bytes() == ORIGINAL, kind
        if scratch is not None:
            assert not scratch.exists(), kind


def test_archive_destination_created_during_publish_is_not_overwritten() -> None:
    for kind in ("gzip", "tar"):
        result = subprocess.run([sys.executable, "-B", __file__, "--race", kind],
                                capture_output=True, text=True, check=False)
        assert result.returncode == 0, (kind, result.stdout, result.stderr)


def test_file_ops_destination_created_during_publish_is_not_overwritten() -> None:
    for kind in ("copy", "backup", "rename"):
        result = subprocess.run([sys.executable, "-B", __file__, "--race", kind],
                                capture_output=True, text=True, check=False)
        assert result.returncode == 0, (kind, result.stdout, result.stderr)


def test_negated_overwrite_does_not_overwrite_a_racing_destination() -> None:
    for kind in ("copy", "rename"):
        result = subprocess.run([sys.executable, "-B", __file__, "--race-negated", kind],
                                capture_output=True, text=True, check=False)
        assert result.returncode == 0, (kind, result.stdout, result.stderr)


def test_copy_or_rename_cannot_overwrite_a_hard_link_to_the_source() -> None:
    SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    for kind in ("copy", "rename"):
        with tempfile.TemporaryDirectory(dir=SCRATCH_ROOT) as world:
            src, dest, _scratch, args, adapter = _setup(pathlib.Path(world), kind)
            os.link(src, dest)
            args["goal"] += " and overwrite it"
            try:
                adapter.run(args, ROOT)
            except RuntimeError as exc:
                assert "SOURCE_AND_DESTINATION_ARE_THE_SAME_FILE" in str(exc), (kind, exc)
            else:
                raise AssertionError("%s accepted a hard link to its source" % kind)
            assert src.read_bytes() == dest.read_bytes() == ORIGINAL, kind
            assert os.path.samefile(src, dest), kind


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001 - report all cases
            failures += 1
            print("FAIL %s: %s" % (test.__name__, exc))
        else:
            print("ok   %s" % test.__name__)
    print("%d/%d passed" % (len(tests) - failures, len(tests)))
    return int(bool(failures))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] in ("--race", "--race-negated"):
        _race_worker(sys.argv[2], negated_overwrite=(sys.argv[1] == "--race-negated"))
    else:
        raise SystemExit(main())
