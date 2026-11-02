#!/usr/bin/env python3
"""An in-place edit either lands exactly as asked, or the file never changes.

`file.uppercased.v1` and `file.line.appended.v1` are the first rows in this
repository that rewrite the caller's own file. That is the write where a wrong
answer is unrecoverable, so every property is pinned here rather than described:

* the bytes on disk after the run are the bytes computed before it;
* a refusal leaves the file byte-identical -- not "restored", untouched;
* no temporary file survives the run, whatever happened;
* source code is refused by suffix, because upper-casing a module is not a text
  transformation and destroys the program while looking like it worked;
* "add a line" without a stated line refuses rather than inventing one, and a
  sentence that asks to REMOVE something is refused by name -- the append row was
  selected for "Delete the last line of <f>" on the word "line";
* no process is spawned: an armed spy on the process APIs never fires.

The runs go through the real dispatcher, not through a direct import.
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

from canonical.runtime import capability_composer_v1 as graph  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

ORIGINAL = "alpha\nbeta\nGamma Delta\n"


def _rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _world(name: str, text: str = ORIGINAL) -> pathlib.Path:
    base = pathlib.Path(tempfile.mkdtemp(dir=str(ROOT / "canonical/astra_runtime/tmp")))
    target = base / name
    target.write_text(text, encoding="utf-8")
    return target


def _run(cid: str, args: dict) -> dict:
    entry = dict(graph.load_registry()[cid])
    entry.setdefault("capability_id", cid)
    return door.run_adapter_locally(entry, {"args": args})


def _digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _refuses(cid: str, args: dict, expected: str) -> str:
    before = None
    path = ROOT / str(args.get("path") or "")
    if path.is_file():
        before = _digest(path)
    try:
        _run(cid, args)
    except Exception as exc:  # noqa: BLE001 - the reason is what is checked
        assert expected in str(exc), (expected, str(exc))
        if before is not None:
            assert _digest(path) == before, "a refused edit changed the file anyway"
        return str(exc)
    raise AssertionError("the edit was not refused with " + expected)


def test_upper_casing_lands_exactly_and_is_verified() -> None:
    target = _world("upper.txt")
    out = _run("file.uppercased.v1", {"command": "uppercase",
                                      "goal": "Uppercase every line in " + _rel(target),
                                      "path": _rel(target)})
    assert target.read_text(encoding="utf-8") == "ALPHA\nBETA\nGAMMA DELTA\n"
    assert out["output_verified"] is True, out
    assert out["after_sha256"] == _digest(target), out
    assert out["before_sha256"] == hashlib.sha256(ORIGINAL.encode()).hexdigest(), out


def test_appending_lands_the_line_the_sentence_states() -> None:
    target = _world("append.txt")
    out = _run("file.line.appended.v1", {"command": "append_line",
                                         "goal": "Add a line containing omega to " + _rel(target),
                                         "path": _rel(target)})
    assert target.read_text(encoding="utf-8") == ORIGINAL + "omega\n"
    assert out["output_verified"] is True and out["unchanged"] is False, out


def test_a_quoted_line_is_the_line_appended() -> None:
    target = _world("quoted.txt")
    _run("file.line.appended.v1", {"command": "append_line",
                                   "goal": "Append a line 'delta epsilon' to " + _rel(target),
                                   "path": _rel(target)})
    assert target.read_text(encoding="utf-8").endswith("delta epsilon\n")


def test_a_line_that_is_not_stated_is_not_invented() -> None:
    target = _world("nostated.txt")
    _refuses("file.line.appended.v1", {"command": "append_line",
                                       "goal": "Add a line to " + _rel(target),
                                       "path": _rel(target)},
             "THE_LINE_TO_ADD_IS_NOT_STATED")
    assert target.read_text(encoding="utf-8") == ORIGINAL


def test_a_sentence_that_asks_to_remove_is_not_an_append() -> None:
    target = _world("delete.txt")
    _refuses("file.line.appended.v1", {"command": "append_line",
                                       "goal": "Delete the last line of " + _rel(target),
                                       "path": _rel(target)},
             "THE_SENTENCE_ASKS_TO_REMOVE_SOMETHING_NOT_ADD_IT")
    assert target.read_text(encoding="utf-8") == ORIGINAL


def test_source_code_is_refused_by_suffix() -> None:
    target = _world("module.py", "value = 1\n")
    _refuses("file.uppercased.v1", {"command": "uppercase",
                                    "goal": "Uppercase every line in " + _rel(target),
                                    "path": _rel(target)},
             "REFUSES_TO_REWRITE_SOURCE_CODE_IN_PLACE")
    assert target.read_text(encoding="utf-8") == "value = 1\n"


def test_nothing_outside_the_repository_is_edited() -> None:
    _refuses("file.uppercased.v1", {"command": "uppercase",
                                    "goal": "Uppercase every line in /etc/hosts",
                                    "path": "/etc/hosts"},
             "PATH_OUTSIDE_REPOSITORY")


def test_a_file_the_sentence_does_not_name_is_refused() -> None:
    target = _world("unnamed.txt")
    _refuses("file.uppercased.v1", {"command": "uppercase",
                                    "goal": "Uppercase every line in some_other_file.txt",
                                    "path": _rel(target)},
             "PATH_NOT_STATED_IN_THE_SENTENCE")
    assert target.read_text(encoding="utf-8") == ORIGINAL


def test_the_command_table_is_closed() -> None:
    target = _world("closed.txt")
    for command in ("rm", "truncate", "delete", ""):
        _refuses("file.uppercased.v1", {"command": command, "path": _rel(target),
                                        "goal": "Uppercase every line in " + _rel(target)},
                 "COMMAND_NOT_IMPLEMENTED")


def test_no_temporary_file_survives_a_successful_edit() -> None:
    target = _world("tmpcheck.txt")
    _run("file.uppercased.v1", {"command": "uppercase",
                                "goal": "Uppercase every line in " + _rel(target),
                                "path": _rel(target)})
    leftovers = list(target.parent.glob("*.brain-edit-tmp"))
    assert leftovers == [], leftovers


def test_no_process_is_spawned_by_an_edit() -> None:
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
        target = _world("noproc.txt")
        _run("file.uppercased.v1", {"command": "uppercase",
                                    "goal": "Uppercase every line in " + _rel(target),
                                    "path": _rel(target)})
        assert target.read_text(encoding="utf-8") == "ALPHA\nBETA\nGAMMA DELTA\n"
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
