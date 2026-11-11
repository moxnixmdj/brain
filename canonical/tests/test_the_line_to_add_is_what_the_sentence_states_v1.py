"""The line a request asks to add is the text it states: without its quotation marks, and only one.

Each defect was found 2026-11-11 by fresh instances asked through the front door
(canonical/capabilities/true/specs/FILE_CHANGE_REQUEST_COPY_RENAME_APPEND_V1.json).  In each, the
write had been re-read from disk and reported verified: the disk held what the adapter wrote, and
what the adapter wrote was not what the sentence said.

* `add a line containing "v481f vc31f" to <f>` appended the line with its quotation marks.
* `add a line encrypted to the file <f> containing "vcea1 vc03c"` appended `encrypted` and dropped
  the quoted text without a word.
* A quoted line with a mark inside it was cut at that mark.

Run:  PYTHONPATH=. python3 canonical/tests/test_the_line_to_add_is_what_the_sentence_states_v1.py
"""
from __future__ import annotations

import shutil
import sys

from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime.bound_capabilities import file_edit

SCRATCH = "canonical/astra_runtime/tmp/zqla"


def _ask(sentence: str, before: str) -> tuple[bool, str]:
    folder = door.ROOT / SCRATCH
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    try:
        (folder / "k1.txt").write_bytes(before.encode("utf-8"))
        result = door.solve({"task_id": "line_to_add", "goal": sentence.replace("{f}", SCRATCH + "/k1.txt")})
        return result.get("pass") is True, (folder / "k1.txt").read_bytes().decode("utf-8")
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def test_a_quoted_line_is_added_without_its_quotation_marks() -> None:
    for sentence in ('add a line containing "v481f vc31f" to {f}',
                     'append the line "v481f vc31f" to {f}',
                     "add a line to the file {f} containing 'v481f vc31f'"):
        answered, after = _ask(sentence, "one\n")
        assert answered and after == "one\nv481f vc31f\n", (sentence, answered, after)


def test_an_unquoted_line_is_still_added_as_stated() -> None:
    for sentence in ("append the line v7 to {f}", "add a line containing v7 to {f}", "add the line v7 to {f}"):
        answered, after = _ask(sentence, "one")
        assert answered and after == "one\nv7\n", (sentence, answered, after)


def test_a_sentence_that_states_two_lines_is_refused_and_the_file_keeps_its_bytes() -> None:
    answered, after = _ask('add a line encrypted to the file {f} containing "vcea1 vc03c"', "one\n")
    assert not answered and after == "one\n", (answered, after)
    for stated in ('add a line encrypted to the file containing "vcea1 vc03c"', 'append the line v1 to it saying v2 at the end'):
        try:
            line = file_edit._stated_line(stated)
        except RuntimeError as exc:
            assert "MORE_THAN_ONE_LINE" in str(exc), exc
        else:
            raise AssertionError((stated, line))


def test_a_quoted_line_keeps_a_mark_that_stands_inside_a_word() -> None:
    assert file_edit._stated_line("append the line 'it`s v9' to") == "it`s v9"
    assert file_edit._stated_line("add a line saying it's v9 to") == "it's v9"
    # Through the front door this sentence is refused today: the door's word check does not account
    # for a word with an apostrophe.  Refused and untouched is the safe side; it is asserted exactly
    # so that the day the door reads it, this line has to be changed on purpose.
    answered, after = _ask('append the line "it\'s v9" to {f}', "one\n")
    assert not answered and after == "one\n", (answered, after)


def test_marks_that_do_not_pair_are_refused_and_the_file_keeps_its_bytes() -> None:
    for sentence in ('append the line "v9 to {f}', 'append the line "say \'v9\'" to {f}', 'add a line containing "v9" saying v8 to {f}'):
        answered, after = _ask(sentence, "one\n")
        assert not answered and after == "one\n", (sentence, answered, after)


def main() -> int:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_") and callable(value)]
    failed = 0
    for test in tests:
        try:
            test()
            print("ok  ", test.__name__)
        except Exception as exc:  # noqa: BLE001 - every failure is reported, none hides another
            failed += 1
            print("FAIL", test.__name__ + ":", repr(exc)[:400])
    print("%d/%d passed" % (len(tests) - failed, len(tests)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
