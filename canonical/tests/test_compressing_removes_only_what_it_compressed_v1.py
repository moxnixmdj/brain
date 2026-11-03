#!/usr/bin/env python3
"""Compressing removes the original only after the archive is proved.

`file.compressed.gzip.v1` is the one row here that DELETES the caller's file, and
it does so because that is what the command it declares (`gzip <file>`) does. So
the ordering is the whole safety argument, and it is pinned as facts:

* the archive is written beside the file, read back and decompressed, and only
  then is the source removed;
* every refusal leaves the source exactly where it was, and leaves no archive;
* a sentence that names a DIFFERENT destination is refused outright. This is the
  failure the row produced on its first run: "Compress <p>/a.txt into
  <p>/a.tar.gz" was read as `gzip <p>/a.txt` (the "into" clause is not part of
  the command line), so the caller got `a.txt.gz` and lost `a.txt` while the
  archive they asked for was never written. An invented destination on a
  destructive write is not a near miss;
* no process is spawned and no temporary file survives.

The runs go through the real dispatcher.
"""
from __future__ import annotations

import gzip
import hashlib
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_composer_v1 as graph  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

CID = "file.compressed.gzip.v1"
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
    raise AssertionError("compress was not refused with " + expected)


def test_the_archive_decompresses_to_the_source_and_the_source_is_removed() -> None:
    target = _world()
    rel = _rel(target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    out = _run({"goal": "Compress " + rel, "path": rel})
    archive = target.with_name(target.name + ".gz")
    assert archive.is_file(), "no archive was written"
    assert gzip.decompress(archive.read_bytes()) == PAYLOAD, "the archive is not the file"
    assert not target.exists(), "the source was expected to be removed by gzip"
    assert out["source_removed"] is True, out
    assert out["source_sha256"] == digest, out
    assert out["output_verified"] is True, out


def test_binary_bytes_round_trip() -> None:
    payload = bytes(range(256)) * 4
    target = _world(payload)
    rel = _rel(target)
    _run({"goal": "Compress " + rel, "path": rel})
    archive = target.with_name(target.name + ".gz")
    assert gzip.decompress(archive.read_bytes()) == payload


def test_a_destination_the_sentence_names_is_refused_and_nothing_moves() -> None:
    target = _world()
    rel = _rel(target)
    base = target.parent.relative_to(ROOT).as_posix()
    _refuses({"goal": "Compress %s into %s/a.tar.gz" % (rel, base), "path": rel},
             "THE_SENTENCE_NAMES_A_DESTINATION_THIS_ROW_DOES_NOT_WRITE")
    assert target.is_file(), "the source was removed by a refused compress"
    assert target.read_bytes() == PAYLOAD
    assert not (target.parent / "a.tar.gz").exists(), "an archive nobody asked for was written"
    assert not target.with_name(target.name + ".gz").exists()


def test_an_existing_archive_is_never_overwritten() -> None:
    target = _world()
    rel = _rel(target)
    archive = target.with_name(target.name + ".gz")
    archive.write_bytes(b"AN OLDER ARCHIVE THAT MUST SURVIVE")
    _refuses({"goal": "Compress " + rel, "path": rel}, "THE_ARCHIVE_ALREADY_EXISTS")
    assert archive.read_bytes() == b"AN OLDER ARCHIVE THAT MUST SURVIVE"
    assert target.is_file() and target.read_bytes() == PAYLOAD


def test_nothing_outside_the_repository_is_compressed() -> None:
    _refuses({"goal": "Compress /etc/hosts", "path": "/etc/hosts"}, "PATH_OUTSIDE_REPOSITORY")


def test_a_file_the_sentence_does_not_name_is_refused() -> None:
    target = _world()
    _refuses({"goal": "Compress some_other_file.bin", "path": _rel(target)},
             "PATH_NOT_STATED_IN_THE_SENTENCE")
    assert target.is_file() and target.read_bytes() == PAYLOAD


def test_the_command_table_is_closed() -> None:
    target = _world()
    for command in ("gzip", "tar", "zip", ""):
        try:
            entry = dict(graph.load_registry()[CID])
            entry.setdefault("capability_id", CID)
            door.run_adapter_locally(entry, {"args": {"command": command,
                                                      "goal": "Compress " + _rel(target),
                                                      "path": _rel(target)}})
        except Exception as exc:  # noqa: BLE001
            assert "COMMAND_NOT_IMPLEMENTED" in str(exc), exc
        else:
            raise AssertionError("command not refused: " + command)
    assert target.is_file(), "a refused command touched the file"


def test_no_temporary_file_survives() -> None:
    target = _world()
    rel = _rel(target)
    _run({"goal": "Compress " + rel, "path": rel})
    assert list(target.parent.glob("*.brain-compress-tmp")) == []


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
        rel = _rel(target)
        _run({"goal": "Compress " + rel, "path": rel})
        assert target.with_name(target.name + ".gz").is_file()
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
