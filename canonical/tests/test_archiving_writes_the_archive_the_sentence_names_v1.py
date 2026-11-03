#!/usr/bin/env python3
"""Archiving writes the archive the sentence names, and keeps the source.

`file.archive.tar_gz.v1` exists because a sentence can name BOTH a file and the
archive it wants: "Compress <d>/a.txt into <d>/a.tar.gz".  `gzip <file>` cannot
serve that -- it writes `<file>.gz` and removes the source -- so the row that
computes gzip's command line must not be the row for it.  The command line this
sentence does settle is `tar czf <archive> <file>`, which copies.

What is pinned here, as facts about the disk rather than about the report:

* the archive lands at the path the sentence named, and holds the file's bytes;
* the source is STILL THERE afterwards, unchanged -- this row never removes;
* an existing archive is never overwritten, and its bytes survive the refusal;
* a destination that is not a tar archive, a missing destination directory, a
  destination equal to the source, a path outside the repository, and a path the
  sentence never named are all refused before anything is written;
* the same input produces the same archive twice (no clock, no owner in it);
* no process is spawned and no temporary file survives.

The runs go through the real dispatcher, the same way a sentence reaches the row.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys
import tarfile
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_composer_v1 as graph  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

CID = "file.archive.tar_gz.v1"
PAYLOAD = b"alpha\nbeta\n" + bytes(range(64))


def _rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _world(payload: bytes = PAYLOAD) -> pathlib.Path:
    base = pathlib.Path(tempfile.mkdtemp(dir=str(ROOT / "canonical/astra_runtime/tmp")))
    target = base / "payload.bin"
    target.write_bytes(payload)
    return target


def _run(args: dict) -> dict:
    entry = dict(graph.load_registry()[CID])
    entry.setdefault("capability_id", CID)
    return door.run_adapter_locally(entry, {"args": dict(args, command="compress")})


def _refuses(args: dict, expected: str) -> str:
    try:
        _run(args)
    except Exception as exc:  # noqa: BLE001 - the reason is what is checked
        assert expected in str(exc), (expected, str(exc))
        return str(exc)
    raise AssertionError("archive was not refused with " + expected)


def _member_of(archive: pathlib.Path, name: str) -> bytes:
    with tarfile.open(archive, "r:gz") as handle:
        return handle.extractfile(handle.getmember(name)).read()


def test_the_archive_lands_where_the_sentence_says_and_the_source_survives() -> None:
    target = _world()
    source = _rel(target)
    archive = target.parent / "a.tar.gz"
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    goal = "Compress %s into %s" % (source, _rel(archive))
    out = _run({"goal": goal, "path": source, "output_path": _rel(archive)})
    assert archive.is_file(), "no archive was written at the named path"
    assert _member_of(archive, target.name) == PAYLOAD, "the archive is not the file"
    assert target.is_file() and target.read_bytes() == PAYLOAD, "the source was removed"
    assert out["source_removed"] is False and out["source_kept"] is True, out
    assert out["destination_path"] == _rel(archive), out
    assert out["source_sha256"] == digest, out
    assert out["output_verified"] is True, out


def test_the_archive_is_not_the_gzip_name() -> None:
    target = _world()
    source = _rel(target)
    archive = target.parent / "a.tar.gz"
    _run({"goal": "Compress %s into %s" % (source, _rel(archive)),
          "path": source, "output_path": _rel(archive)})
    assert not target.with_name(target.name + ".gz").exists(), (
        "gzip's own archive was written for a tar request")


def test_binary_bytes_round_trip_through_the_archive() -> None:
    payload = bytes(range(256)) * 4
    target = _world(payload)
    source = _rel(target)
    archive = target.parent / "bin.tar.gz"
    _run({"goal": "Compress %s into %s" % (source, _rel(archive)),
          "path": source, "output_path": _rel(archive)})
    assert _member_of(archive, target.name) == payload


def test_the_same_bytes_produce_the_same_archive_twice() -> None:
    target = _world()
    source = _rel(target)
    first = target.parent / "one.tar.gz"
    second = target.parent / "two.tar.gz"
    _run({"goal": "Compress %s into %s" % (source, _rel(first)),
          "path": source, "output_path": _rel(first)})
    _run({"goal": "Compress %s into %s" % (source, _rel(second)),
          "path": source, "output_path": _rel(second)})
    assert first.read_bytes() == second.read_bytes(), (
        "the archive carries the clock or the owner in it")


def test_an_existing_archive_is_never_overwritten() -> None:
    target = _world()
    source = _rel(target)
    archive = target.parent / "keep.tar.gz"
    archive.write_bytes(b"AN OLDER ARCHIVE THAT MUST SURVIVE")
    _refuses({"goal": "Compress %s into %s" % (source, _rel(archive)),
              "path": source, "output_path": _rel(archive)},
             "THE_ARCHIVE_ALREADY_EXISTS")
    assert archive.read_bytes() == b"AN OLDER ARCHIVE THAT MUST SURVIVE"
    assert target.is_file() and target.read_bytes() == PAYLOAD


def test_a_destination_that_is_not_a_tar_archive_is_refused() -> None:
    target = _world()
    source = _rel(target)
    for name in ("a.zip", "a.txt", "a.gz", "a"):
        destination = target.parent / name
        _refuses({"goal": "Compress %s into %s" % (source, _rel(destination)),
                  "path": source, "output_path": _rel(destination)},
                 "DESTINATION_IS_NOT_A_TAR_ARCHIVE")
        assert not destination.exists(), name


def test_a_destination_the_sentence_does_not_name_is_refused() -> None:
    target = _world()
    source = _rel(target)
    archive = target.parent / "a.tar.gz"
    _refuses({"goal": "Compress " + source, "path": source, "output_path": _rel(archive)},
             "DESTINATION_NOT_STATED_IN_THE_SENTENCE")
    assert not archive.exists(), "an archive the sentence never named was written"


def test_a_source_the_sentence_does_not_name_is_refused() -> None:
    target = _world()
    archive = target.parent / "a.tar.gz"
    _refuses({"goal": "Compress something_else.bin into %s" % _rel(archive),
              "path": _rel(target), "output_path": _rel(archive)},
             "PATH_NOT_STATED_IN_THE_SENTENCE")
    assert target.is_file() and target.read_bytes() == PAYLOAD


def test_a_missing_destination_directory_is_refused_rather_than_created() -> None:
    target = _world()
    source = _rel(target)
    archive = target.parent / "not-a-directory" / "a.tar.gz"
    _refuses({"goal": "Compress %s into %s" % (source, _rel(archive)),
              "path": source, "output_path": _rel(archive)},
             "DESTINATION_DIRECTORY_MISSING")
    assert not (target.parent / "not-a-directory").exists(), "a directory was invented"


def test_archiving_a_file_onto_itself_is_refused() -> None:
    target = _world()
    source = _rel(target)
    _refuses({"goal": "Compress %s into %s" % (source, source),
              "path": source, "output_path": source}, "THE_DESTINATION_IS_THE_SOURCE")
    assert target.read_bytes() == PAYLOAD


def test_nothing_outside_the_repository_is_archived() -> None:
    _refuses({"goal": "Compress /etc/hosts into canonical/astra_runtime/tmp/x.tar.gz",
              "path": "/etc/hosts", "output_path": "canonical/astra_runtime/tmp/x.tar.gz"},
             "PATH_OUTSIDE_REPOSITORY")


def test_the_command_table_is_closed() -> None:
    target = _world()
    source = _rel(target)
    archive = target.parent / "a.tar.gz"
    for command in ("gzip", "cp", "tar", ""):
        try:
            entry = dict(graph.load_registry()[CID])
            entry.setdefault("capability_id", CID)
            door.run_adapter_locally(entry, {"args": {
                "command": command,
                "goal": "Compress %s into %s" % (source, _rel(archive)),
                "path": source, "output_path": _rel(archive)}})
        except Exception as exc:  # noqa: BLE001
            assert "COMMAND_NOT_IMPLEMENTED" in str(exc), exc
        else:
            raise AssertionError("command not refused: " + command)
    assert not archive.exists(), "a refused command wrote an archive"
    assert target.is_file(), "a refused command touched the source"


def test_no_temporary_file_survives() -> None:
    target = _world()
    source = _rel(target)
    archive = target.parent / "a.tar.gz"
    _run({"goal": "Compress %s into %s" % (source, _rel(archive)),
          "path": source, "output_path": _rel(archive)})
    assert list(target.parent.glob("*.brain-tar-tmp")) == []


def test_no_process_is_spawned() -> None:
    armed: list[str] = []
    originals = {"subprocess.run": subprocess.run, "subprocess.Popen": subprocess.Popen,
                 "subprocess.check_output": subprocess.check_output}

    def boom(name):
        def _raise(*_a, **_k):
            armed.append(name)
            raise AssertionError("PROCESS_API_CALLED:" + name)
        return _raise

    subprocess.run = boom("subprocess.run")
    subprocess.Popen = boom("subprocess.Popen")
    subprocess.check_output = boom("subprocess.check_output")
    try:
        target = _world()
        source = _rel(target)
        archive = target.parent / "a.tar.gz"
        _run({"goal": "Compress %s into %s" % (source, _rel(archive)),
              "path": source, "output_path": _rel(archive)})
        assert archive.is_file()
    finally:
        subprocess.run = originals["subprocess.run"]
        subprocess.Popen = originals["subprocess.Popen"]
        subprocess.check_output = originals["subprocess.check_output"]
    assert armed == [], armed


def main() -> int:
    tests = [value for key, value in sorted(globals().items())
             if key.startswith("test_") and callable(value)]
    failures = 0
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            failures += 1
            print("FAIL %s: %s" % (test.__name__, exc))
        else:
            print("ok   %s" % test.__name__)
    print("\n%d/%d passed" % (len(tests) - failures, len(tests)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
