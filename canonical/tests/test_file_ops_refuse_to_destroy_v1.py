"""The write rows copy and rename, and refuse every shape that destroys something.

Writes are the one class where a wrong answer is not just a wrong answer, so this
file is mostly about what the adapters will NOT do:

* a copy onto ITS OWN SOURCE is refused (resolved, so `a` and `./a` are the same);
* a copy onto an EXISTING destination is refused unless the sentence itself says
  "overwrite" or "replace" -- `cp` overwrites silently and that is precisely the
  default not taken here;
* any path that resolves outside the repository is refused before a byte is read;
* a missing destination is refused rather than invented;
* `rename` must leave nothing behind at the source and must not change the bytes.

And the positive half, which is the only reason the refusals are affordable: the
copy that IS allowed really lands, and `output_verified` is a digest of what is
on disk afterwards, not a restatement of intent.

usage:
  python3 -B canonical/tests/test_file_ops_refuse_to_destroy_v1.py
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.bound_capabilities import file_ops  # noqa: E402

WORK_NAME = "test_file_ops_refuse_to_destroy"


def _rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _refuses(call, expected: str) -> str:
    try:
        call()
    except RuntimeError as exc:
        assert expected in str(exc), (expected, str(exc))
        return str(exc)
    raise AssertionError("the adapter did not refuse with " + expected)


def test_a_copy_lands_and_is_verified_by_reading_it_back() -> None:
    base = pathlib.Path(tempfile.mkdtemp(dir=str(ROOT / "canonical/astra_runtime/tmp")))
    source = base / "src.txt"
    source.write_text("alpha\nbeta\n", encoding="utf-8")
    out = file_ops.run({"command": "copy", "path": _rel(source),
                        "output_path": _rel(base / "dst.txt"),
                        "goal": "Copy %s to dst.txt" % _rel(source)}, ROOT)
    written = base / "dst.txt"
    assert written.is_file(), "no copy was made"
    assert written.read_bytes() == source.read_bytes(), "the copy differs from the source"
    assert out["source_sha256"] == hashlib.sha256(written.read_bytes()).hexdigest(), out
    assert out["destination_sha256"] == out["source_sha256"], out
    assert out["output_verified"] is True, out


def test_a_copy_onto_its_own_source_is_refused_even_when_spelled_differently() -> None:
    base = pathlib.Path(tempfile.mkdtemp(dir=str(ROOT / "canonical/astra_runtime/tmp")))
    source = base / "same.txt"
    source.write_text("keep me\n", encoding="utf-8")
    _refuses(lambda: file_ops.run(
        {"command": "copy", "path": _rel(source),
         "output_path": _rel(source) + "/../same.txt",
         "goal": "Copy %s to same.txt" % _rel(source)}, ROOT),
        "SOURCE_AND_DESTINATION_ARE_THE_SAME_FILE")
    assert source.read_text(encoding="utf-8") == "keep me\n", "the source was altered"


def test_an_existing_destination_is_not_overwritten_without_being_asked() -> None:
    base = pathlib.Path(tempfile.mkdtemp(dir=str(ROOT / "canonical/astra_runtime/tmp")))
    source = base / "s.txt"
    source.write_text("new\n", encoding="utf-8")
    existing = base / "e.txt"
    existing.write_text("OLD CONTENT THAT MUST SURVIVE\n", encoding="utf-8")
    _refuses(lambda: file_ops.run({"command": "copy", "path": _rel(source),
                                   "output_path": _rel(existing),
                                   "goal": "Copy %s to e.txt" % _rel(source)}, ROOT),
             "DESTINATION_EXISTS_AND_THE_SENTENCE_DID_NOT_ASK_TO_OVERWRITE")
    assert existing.read_text(encoding="utf-8") == "OLD CONTENT THAT MUST SURVIVE\n"
    # ...and the same call with the word "overwrite" in the sentence is allowed.
    file_ops.run({"command": "copy", "path": _rel(source), "output_path": _rel(existing),
                  "goal": "Copy %s to %s and overwrite it" % (_rel(source), _rel(existing))}, ROOT)
    assert existing.read_text(encoding="utf-8") == "new\n"


def test_nothing_outside_the_repository_is_written() -> None:
    base = pathlib.Path(tempfile.mkdtemp(dir=str(ROOT / "canonical/astra_runtime/tmp")))
    source = base / "s.txt"
    source.write_text("x\n", encoding="utf-8")
    outside = pathlib.Path(tempfile.mkdtemp()) / "escaped.txt"
    _refuses(lambda: file_ops.run({"command": "copy", "path": _rel(source),
                                   "output_path": str(outside),
                                   "goal": "Copy %s to escaped.txt" % _rel(source)}, ROOT),
             "PATH_OUTSIDE_REPOSITORY")
    assert not outside.exists(), "a file was written outside the repository"


def test_a_missing_destination_is_refused_rather_than_invented() -> None:
    base = pathlib.Path(tempfile.mkdtemp(dir=str(ROOT / "canonical/astra_runtime/tmp")))
    source = base / "s.txt"
    source.write_text("x\n", encoding="utf-8")
    _refuses(lambda: file_ops.run({"command": "copy", "path": _rel(source),
                                   "goal": "Copy %s somewhere" % _rel(source)}, ROOT),
             "PATH_REQUIRED")
    assert sorted(p.name for p in base.iterdir()) == ["s.txt"], "something was written anyway"


def test_rename_moves_the_bytes_and_leaves_nothing_behind() -> None:
    base = pathlib.Path(tempfile.mkdtemp(dir=str(ROOT / "canonical/astra_runtime/tmp")))
    source = base / "before.txt"
    source.write_text("payload\n", encoding="utf-8")
    out = file_ops.run({"command": "rename", "path": _rel(source),
                        "output_path": _rel(base / "after.txt"),
                        "goal": "Rename %s to after.txt" % _rel(source)}, ROOT)
    assert not source.exists(), "the source is still there"
    moved = base / "after.txt"
    assert moved.read_text(encoding="utf-8") == "payload\n"
    assert out["source_sha256"] == out["destination_sha256"], out


def test_a_backup_lands_beside_the_file_and_keeps_the_original() -> None:
    base = pathlib.Path(tempfile.mkdtemp(dir=str(ROOT / "canonical/astra_runtime/tmp")))
    source = base / "note.txt"
    source.write_text("payload\n", encoding="utf-8")
    out = file_ops.run({"command": "backup", "path": _rel(source),
                        "goal": "Make a backup of %s" % _rel(source)}, ROOT)
    landed = base / "note.txt.bak"
    assert landed.is_file(), "no backup was made"
    assert landed.read_bytes() == source.read_bytes()
    assert source.read_text(encoding="utf-8") == "payload\n", "the original was changed"
    assert out["source_retained"] is True, out
    assert out["source_sha256"] == out["destination_sha256"] == hashlib.sha256(b"payload\n").hexdigest()
    # A second backup never eats the first one.
    _refuses(lambda: file_ops.run({"command": "backup", "path": _rel(source),
                                   "goal": "Make a backup of %s" % _rel(source)}, ROOT),
             "A_BACKUP_OF_THIS_FILE_ALREADY_EXISTS")
    assert landed.read_text(encoding="utf-8") == "payload\n"


def test_the_command_table_is_closed() -> None:
    base = pathlib.Path(tempfile.mkdtemp(dir=str(ROOT / "canonical/astra_runtime/tmp")))
    source = base / "s.txt"
    source.write_text("x\n", encoding="utf-8")
    for command in ("rm", "mv", "cp", "truncate", "chmod", ""):
        _refuses(lambda command=command: file_ops.run(
            {"command": command, "path": _rel(source),
             "output_path": _rel(base / "out.txt")}, ROOT),
            "COMMAND_NOT_IMPLEMENTED")


def test_no_process_is_spawned_by_either_row() -> None:
    """Armed spy: every process API raises. A clean copy must still happen."""
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
        base = pathlib.Path(tempfile.mkdtemp(dir=str(ROOT / "canonical/astra_runtime/tmp")))
        source = base / "s.txt"
        source.write_text("bytes\n", encoding="utf-8")
        file_ops.run({"command": "copy", "path": _rel(source),
                      "output_path": _rel(base / "d.txt"),
                      "goal": "Copy %s to d.txt" % _rel(source)}, ROOT)
        assert (base / "d.txt").read_text(encoding="utf-8") == "bytes\n"
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
