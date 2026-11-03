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
            is_creation = (event == "open" and pathlib.Path(event_args[0]) in (dest, pathlib.Path(dest.name))
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


def _overwrite_symlink_race_worker() -> None:
    SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=SCRATCH_ROOT) as world, tempfile.TemporaryDirectory() as outside:
        source, destination, _scratch, args, adapter = _setup(pathlib.Path(world), "copy")
        destination.write_bytes(PRECIOUS)
        victim = pathlib.Path(outside) / "outside.txt"
        victim.write_bytes(PRECIOUS)
        args["goal"] += " and overwrite it"
        events = []

        def replace_destination(event, event_args):
            if (not events and event == "open" and pathlib.Path(event_args[0]) in
                    (destination, pathlib.Path(destination.name)) and bool(event_args[2] & os.O_WRONLY)):
                events.append(event)
                destination.unlink()
                destination.symlink_to(victim)

        sys.addaudithook(replace_destination)
        try:
            adapter.run(args, ROOT)
        except RuntimeError as exc:
            assert "DESTINATION_IS_SYMLINK_OR_UNSAFE" in str(exc), exc
        else:
            raise AssertionError("an overwrite followed a competing symlink")
        assert events == ["open"], events
        assert source.read_bytes() == ORIGINAL
        assert victim.read_bytes() == PRECIOUS
        assert destination.is_symlink() and os.readlink(destination) == str(victim)


def test_overwrite_does_not_follow_a_competing_symlink_outside_the_root() -> None:
    result = subprocess.run([sys.executable, "-B", __file__, "--race-overwrite-symlink"],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, (result.stdout, result.stderr)


def _parent_symlink_race_worker(overwrite: bool) -> None:
    SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=SCRATCH_ROOT) as world, tempfile.TemporaryDirectory() as outside:
        base = pathlib.Path(world)
        source = base / "source.txt"
        source.write_bytes(ORIGINAL)
        parent = base / "race_parent"
        parent.mkdir()
        destination = parent / "destination.txt"
        if overwrite:
            destination.write_bytes(b"old destination\n")
        external = pathlib.Path(outside) / "destination.txt"
        if overwrite:
            external.write_bytes(PRECIOUS)
        source_rel, dest_rel = (path.relative_to(ROOT).as_posix() for path in (source, destination))
        args = {"command": "copy", "path": source_rel, "output_path": dest_rel,
                "goal": "Copy %s to %s%s" % (source_rel, dest_rel,
                                                " and overwrite it" if overwrite else "")}
        events = []

        def replace_parent(event, event_args):
            if (not events and event == "open" and event_args[0] == "race_parent"
                    and bool(event_args[2] & os.O_DIRECTORY)):
                events.append(event)
                parent.rename(base / "old_parent")
                parent.symlink_to(outside, target_is_directory=True)

        sys.addaudithook(replace_parent)
        try:
            file_ops.run(args, ROOT)
        except RuntimeError as exc:
            assert "DESTINATION_PARENT_IS_SYMLINK_OR_UNSAFE" in str(exc), exc
        else:
            raise AssertionError("copy followed a competing parent symlink")
        assert events == ["open"], events
        assert source.read_bytes() == ORIGINAL
        assert parent.is_symlink() and os.readlink(parent) == outside
        if overwrite:
            assert external.read_bytes() == PRECIOUS
            assert (base / "old_parent" / "destination.txt").read_bytes() == b"old destination\n"
        else:
            assert not external.exists()
            assert not (base / "old_parent" / "destination.txt").exists()


def test_copy_neither_creates_nor_overwrites_through_a_competing_parent_symlink() -> None:
    for mode in ("new", "overwrite"):
        result = subprocess.run([sys.executable, "-B", __file__, "--race-parent-symlink", mode],
                                capture_output=True, text=True, check=False)
        assert result.returncode == 0, (mode, result.stdout, result.stderr)


def _overwrite_hardlink_race_worker() -> None:
    SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=SCRATCH_ROOT) as world, tempfile.TemporaryDirectory() as outside:
        source, destination, _scratch, args, adapter = _setup(pathlib.Path(world), "copy")
        destination.write_bytes(b"original destination\n")
        victim = pathlib.Path(outside) / "outside.txt"
        victim.write_bytes(PRECIOUS)
        args["goal"] += " and overwrite it"
        events = []

        def replace_destination(event, event_args):
            if (not events and event == "open" and event_args[0] == destination.name
                    and bool(event_args[2] & os.O_WRONLY)):
                events.append(event)
                destination.unlink()
                os.link(victim, destination)

        sys.addaudithook(replace_destination)
        try:
            adapter.run(args, ROOT)
        except RuntimeError as exc:
            assert "DESTINATION_HAS_MULTIPLE_LINKS" in str(exc), exc
        else:
            raise AssertionError("copy truncated a competing hard link")
        assert events == ["open"], events
        assert source.read_bytes() == ORIGINAL
        assert victim.read_bytes() == PRECIOUS
        assert os.path.samefile(victim, destination)


def test_overwrite_does_not_truncate_a_competing_hardlink() -> None:
    result = subprocess.run([sys.executable, "-B", __file__, "--race-overwrite-hardlink"],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, (result.stdout, result.stderr)


def test_copy_does_not_create_an_unstated_parent_directory() -> None:
    SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=SCRATCH_ROOT) as world:
        base = pathlib.Path(world)
        source = base / "source.txt"
        source.write_bytes(ORIGINAL)
        parent = base / "not-created"
        destination = parent / "destination.txt"
        source_rel, dest_rel = (p.relative_to(ROOT).as_posix() for p in (source, destination))
        try:
            file_ops.run({"command": "copy", "path": source_rel, "output_path": dest_rel,
                          "goal": "Copy %s to %s" % (source_rel, dest_rel)}, ROOT)
        except FileNotFoundError:
            pass  # The descriptor walk refuses a missing parent.
        else:
            raise AssertionError("copy created a missing parent directory")
        assert not parent.exists()
        assert source.read_bytes() == ORIGINAL


def test_copy_refuses_an_existing_hard_link_to_another_file() -> None:
    SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=SCRATCH_ROOT) as world:
        base = pathlib.Path(world)
        source, destination, _scratch, args, adapter = _setup(base, "copy")
        protected = base / "protected.txt"
        protected.write_bytes(PRECIOUS)
        os.link(protected, destination)
        args["goal"] += " and overwrite it"
        try:
            adapter.run(args, ROOT)
        except RuntimeError as exc:
            assert "DESTINATION_HAS_MULTIPLE_LINKS" in str(exc), exc
        else:
            raise AssertionError("copy truncated an existing hard link")
        assert source.read_bytes() == ORIGINAL
        assert protected.read_bytes() == destination.read_bytes() == PRECIOUS
        assert os.path.samefile(protected, destination)


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
    elif len(sys.argv) == 2 and sys.argv[1] == "--race-overwrite-symlink":
        _overwrite_symlink_race_worker()
    elif len(sys.argv) == 2 and sys.argv[1] == "--race-overwrite-hardlink":
        _overwrite_hardlink_race_worker()
    elif len(sys.argv) == 3 and sys.argv[1] == "--race-parent-symlink":
        _parent_symlink_race_worker(overwrite=sys.argv[2] == "overwrite")
    else:
        raise SystemExit(main())
