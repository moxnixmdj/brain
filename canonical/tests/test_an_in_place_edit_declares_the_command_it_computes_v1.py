#!/usr/bin/env python3
"""An in-place editor answers the sentence by declaring the command it computes.

`file.uppercased.v1` and `file.line.appended.v1` rewrite the file in process:
atomic temp write, digest, `os.replace`, read back.  Both were nevertheless
refused for the two plainest ways of asking for them,

    "Convert <f> to uppercase"      -> FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT
    "Append 'omega' to <f>"         -> FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT

because `composer_route_v1` settles those sentences as `sed`, and neither row
declared a command slot.  The refusal is the right rule -- a row that cannot run
the stated command answers nothing -- applied to the wrong rows: these two DO
compute the sentence's command, in process, and until now said so nowhere.

So each now declares it, and this file pins the claim rather than the wording:

* the declaration is TRUE: the row's bytes are compared with real `sed` on the
  same input, run here, in a copy, for several payloads including one with no
  trailing newline and one with a blank line;
* it is NARROW: the append declaration is the `$a ` subcommand, so a substitution
  at the same position does not match, and a sentence that asks for one is still
  refused with the file byte-identical;
* it did not open a door: the sentences that were refused before are refused
  now, and none of them changed the file;
* no process is spawned to answer either sentence.

The distinction this file is built around: a declaration wider than the
behaviour is a lie with a receipt, and a receipt for the wrong command is worse
than no receipt.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_composer_v1 as graph  # noqa: E402
from canonical.runtime import composer_route_v1 as composer_route  # noqa: E402
from canonical.runtime import declared_command_equivalence_v1 as declared  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/edit_declares_command_v1"

PAYLOADS = [
    b"alpha\nbeta gamma\n\ndelta\n",
    b"leading\nTRAILING no newline",           # no trailing newline
    b"one\n",
    b"",                                        # empty file
]


def _world(payload: bytes, name: str = "a.txt") -> pathlib.Path:
    WORK.mkdir(parents=True, exist_ok=True)
    target = WORK / name
    target.write_bytes(payload)
    return target


def _rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _row(cid: str) -> dict:
    entry = dict(graph.load_registry()[cid])
    entry.setdefault("capability_id", cid)
    return entry


def _real_sed(args: list[str], payload: bytes, *, write_back: bool) -> bytes:
    """The bytes the declared command line leaves on disk, using the real program.

    `write_back` is not a convenience.  The two declarations are not the same
    KIND of command and the difference is the repository's own:

    * `sed -i '$a <line>' <f>` writes the file itself; its stdout is empty.
    * `sed -e 's/.*/\\U&/' <f>` is a TRANSFORM.  It prints, and
      `raw_goal_trace_acceptance_v1` permits writing that stdout back over the
      file it read -- but only because a rewriting script is necessary and the
      sentence asked for the file to change ("Convert X to upper case" says so;
      "Show X in upper case" does not).  So the honest oracle for an in-place
      editor here is that stdout read in full and then written back, which is
      exactly the write-back the acceptance layer describes.
    """
    with tempfile.TemporaryDirectory() as tmp:
        target = pathlib.Path(tmp) / "a.txt"
        target.write_bytes(payload)
        done = subprocess.run(["sed", *args, str(target)], check=True, capture_output=True)
        if write_back:
            target.write_bytes(done.stdout)
        return target.read_bytes()


def _declared(cid: str) -> list[str]:
    return [str(token) for token in
            graph.load_registry()[cid]["computes_command"]["argvs"][0]]


# --------------------------------------------------------------------------
# The declaration is true, matched against the real program.
# --------------------------------------------------------------------------
def test_the_uppercase_row_is_byte_identical_to_the_sed_it_declares() -> None:
    cid = "file.uppercased.v1"
    template = _declared(cid)
    assert template == ["sed", "-e", "s/.*/\\U&/", "${path}"], template
    for payload in PAYLOADS:
        target = _world(payload)
        door.run_adapter_locally(_row(cid), {"args": {
            "command": "uppercase",
            "goal": "Convert %s to uppercase" % _rel(target),
            "path": _rel(target)}})
        expected = _real_sed(["-e", template[2]], payload, write_back=True)
        assert target.read_bytes() == expected, (payload, target.read_bytes(), expected)


def test_the_append_row_is_byte_identical_to_the_sed_it_declares() -> None:
    cid = "file.line.appended.v1"
    template = _declared(cid)
    assert template == ["sed", "-i", "$a ${line}", "${path}"], template
    line = "omega epsilon"
    # Every payload that has a last line.  The empty file is the one case where
    # the two disagree, and it has its own test below rather than being dropped.
    for payload in [p for p in PAYLOADS if p]:
        target = _world(payload, "append.txt")
        door.run_adapter_locally(_row(cid), {"args": {
            "command": "append_line",
            "goal": "Append '%s' to %s" % (line, _rel(target)),
            "path": _rel(target)}})
        expected = _real_sed(["-i", "$a " + line], payload, write_back=False)
        assert target.read_bytes() == expected, (payload, target.read_bytes(), expected)


def test_the_one_file_where_sed_and_the_append_row_differ_is_recorded() -> None:
    """`sed -i '$a x'` appends nothing to an empty file; this row adds the line.

    sed's `$a` addresses the LAST LINE, and an empty file has none, so the
    command the row declares would do nothing where the row does the useful
    thing.  That is a real difference between the declaration and the behaviour,
    so it is pinned here and stated in the registry's own `limitations` -- a
    declaration is allowed to have a boundary, not to have a secret.
    """
    cid = "file.line.appended.v1"
    target = _world(b"", "empty.txt")
    door.run_adapter_locally(_row(cid), {"args": {
        "command": "append_line",
        "goal": "Append 'omega' to %s" % _rel(target),
        "path": _rel(target)}})
    assert target.read_bytes() == b"omega\n", target.read_bytes()
    assert _real_sed(["-i", "$a omega"], b"", write_back=False) == b""
    limitations = " ".join(graph.load_registry()[cid].get("limitations") or []).lower()
    assert "empty" in limitations, (
        "the exception is real and is not stated where a reader would find it", limitations)


# --------------------------------------------------------------------------
# The declaration is narrow.
# --------------------------------------------------------------------------
def test_the_append_declaration_does_not_cover_a_substitution() -> None:
    entry = graph.load_registry()["file.line.appended.v1"]
    for argv in (["sed", "-i", "s/a/b/g", "f.txt"],
                 ["sed", "-i", "$a", "f.txt"],
                 ["sed", "-i", "$aX b", "f.txt"],
                 ["sed", "-e", "$a b", "f.txt"]):
        assert declared.matched_template(entry, argv) is None, argv


def test_the_declarations_are_exactly_the_argvs_the_composer_settles() -> None:
    name = "a.txt"
    for goal, cid in ((f"Convert {name} to uppercase", "file.uppercased.v1"),
                      (f"Append 'x' to {name}", "file.line.appended.v1")):
        argv = composer_route.extract_argv(goal)
        assert argv is not None, goal
        assert declared.matched_template(graph.load_registry()[cid], argv) is not None, (
            goal, cid, argv)


# --------------------------------------------------------------------------
# The door: served, with the effect on disk.
# --------------------------------------------------------------------------
def test_the_door_serves_convert_to_uppercase_and_the_bytes_change() -> None:
    target = _world(b"alpha\nbeta\n")
    result = door.solve({"task_id": "edit_declares_command",
                         "goal": "Convert %s to uppercase" % _rel(target)})
    assert result.get("pass") is True, (result.get("status"), result.get("reason"))
    assert result.get("compiled_capability_id") == "file.uppercased.v1", result
    assert target.read_bytes() == b"ALPHA\nBETA\n"


def test_the_door_serves_append_and_appends_only_the_stated_line() -> None:
    target = _world(b"alpha\nbeta\n")
    result = door.solve({"task_id": "edit_declares_command",
                         "goal": "Append 'omega' to %s" % _rel(target)})
    assert result.get("pass") is True, (result.get("status"), result.get("reason"))
    assert result.get("compiled_capability_id") == "file.line.appended.v1", result
    assert target.read_bytes() == b"alpha\nbeta\nomega\n", target.read_bytes()


def test_a_substitution_is_still_refused_and_the_file_is_untouched() -> None:
    target = _world(b"alpha\nbeta\n")
    before = target.read_bytes()
    for goal in ("Replace every 'a' with 'b' in %s" % _rel(target),
                 "Rewrite %s with the words swapped" % _rel(target)):
        result = door.solve({"task_id": "edit_declares_command", "goal": goal})
        assert result.get("pass") is not True, (goal, result.get("status"))
        assert target.read_bytes() == before, ("a refused sentence changed the file", goal)


def test_a_request_to_remove_is_not_answered_by_the_append_row() -> None:
    target = _world(b"alpha\nbeta\n")
    before = target.read_bytes()
    result = door.solve({"task_id": "edit_declares_command",
                         "goal": "Delete the last line of %s" % _rel(target)})
    assert result.get("pass") is not True, result.get("status")
    assert target.read_bytes() == before


def test_no_process_is_spawned_to_answer_either_sentence() -> None:
    armed: list[str] = []
    originals = {name: getattr(subprocess, name)
                 for name in ("run", "Popen", "check_output", "check_call")}

    def boom(name):
        def _raise(*_a, **_k):
            armed.append(name)
            raise AssertionError("PROCESS_API_CALLED:" + name)
        return _raise

    for name in originals:
        setattr(subprocess, name, boom(name))
    try:
        upper = _world(b"alpha\n")
        assert door.solve({"task_id": "x",
                           "goal": "Convert %s to uppercase" % _rel(upper)}).get("pass") is True
        appended = _world(b"alpha\n", "append.txt")
        assert door.solve({"task_id": "x",
                           "goal": "Append 'z' to %s" % _rel(appended)}).get("pass") is True
    finally:
        for name, fn in originals.items():
            setattr(subprocess, name, fn)
    assert armed == [], armed


def main() -> int:
    shutil.rmtree(WORK, ignore_errors=True)
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
    shutil.rmtree(WORK, ignore_errors=True)
    print("\n%d/%d passed" % (len(tests) - failures, len(tests)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
