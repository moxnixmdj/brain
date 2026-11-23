"""The memory must make the second visit nearly free WITHOUT making it wrong.

Every test here encodes a measured fact from a host the system had never seen
(/usr/sbin, 216 programs, 213 names never encountered while learning on /usr/bin):

  * predicting a flag from a class scored 0/45 -- so this module never predicts;
  * reusing only positive answers saved 4% (6.97 s vs 7.18 s), which is not a memory;
  * reusing READ negative answers took the warm visit to 0.058 s (119x), and the answer set
    was identical;
  * `fstab-decode` matches the word "decode" and offers only `--help`, so a page that names
    the role but associates no flag must answer ABSENT, not PRESENT.
"""
from __future__ import annotations

import sys
import pathlib
import json

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import ask_the_host_the_right_question_v1 as A


def _row(name="x", digest="a" * 64):
    return {"name": name, "digest": digest, "path": "/bin/" + name, "key": digest[:16] + ":" + name}


def test_absent_is_not_present_when_only_help_is_offered():
    """`fstab-decode --help` mentions decode; --help is not a decompress flag."""
    import re
    text = "Usage: fstab-decode COMMAND [ARGUMENT...]\n\t-h\tDisplay this help\n"
    got = {"ok": True, "text": text}
    orig = A.SRF.ask
    A.SRF.ask = lambda *a, **k: got
    try:
        ans = A.ask_role(_row("fstab-decode"), "/tmp", "decompress")
    finally:
        A.SRF.ask = orig
    assert ans["state"] == A.ABSENT and ans["flag"] is None


def test_present_flag_is_read_off_the_line_that_names_the_role():
    text = "  -c, --stdout   write to standard output\n"
    got = {"ok": True, "text": text}
    orig = A.SRF.ask
    A.SRF.ask = lambda *a, **k: got
    try:
        ans = A.ask_role(_row("gzip"), "/tmp", "stdout")
    finally:
        A.SRF.ask = orig
    assert ans["state"] == A.PRESENT and ans["flag"] == "--stdout"


def test_unreadable_page_is_unknown_not_absent():
    orig = A.SRF.ask
    A.SRF.ask = lambda *a, **k: {"ok": False, "text": "", "reason": "TIMEOUT"}
    try:
        ans = A.ask_role(_row("broken"), "/tmp", "decompress")
    finally:
        A.SRF.ask = orig
    assert ans["state"] == A.UNREADABLE


def test_a_remembered_absent_answer_is_reused():
    memory = {"schema": A.MEMORY_SCHEMA, "known": {}}
    row = _row("silent")
    memory["known"][A.key_of(row)] = {"name": "silent",
                                      "roles": {"decompress": {"flag": None,
                                                               "state": A.ABSENT}}}
    assert A.known_answer(memory, row, "decompress") == (A.ABSENT, None)


def test_a_remembered_unreadable_page_is_re_asked():
    memory = {"schema": A.MEMORY_SCHEMA, "known": {}}
    row = _row("flaky")
    memory["known"][A.key_of(row)] = {"name": "flaky",
                                      "roles": {"decompress": {"flag": None,
                                                               "state": A.UNREADABLE}}}
    assert A.known_answer(memory, row, "decompress") == (A.UNREADABLE, None)


def test_name_is_part_of_the_key_so_a_changed_program_is_re_asked():
    """Bytes identical, name different: `xz` and `unxz` behave oppositely (measured)."""
    a, b = _row("xz"), _row("unxz")
    assert A.key_of(a) != A.key_of(b)


def test_memory_round_trips_and_stores_no_prose_and_no_digest():
    """The saved form is names + flags only.

    The digest identifies a BUILD, and the scan recomputes it on every visit, so writing 16
    hex characters per program into the file was measured at ~17 KB of pure redundancy out of
    19,097 bytes. The round trip must preserve the KNOWLEDGE, not the byte layout.
    """
    memory = {"schema": A.MEMORY_SCHEMA, "known": {}}
    path = pathlib.Path("/tmp/_asktest.json")
    row = _row("gzip")
    memory["known"][A.key_of(row)] = {"name": "gzip",
                                      "roles": {"decompress": {"flag": "--decompress",
                                                               "state": A.PRESENT}}}
    A.save(memory, path)
    raw = path.read_text()
    assert "description" not in raw and "help_digest" not in raw
    assert "a" * 16 not in raw, "the digest must not be stored"
    back = A.load(path)
    assert back["known"]["gzip"]["roles"]["decompress"] == {"flag": "--decompress",
                                                            "state": A.PRESENT}
    path.unlink()


def test_a_changed_binary_is_a_miss_even_though_the_digest_is_not_stored():
    memory = {"schema": A.MEMORY_SCHEMA, "known": {}}
    row = _row("gzip")
    memory["known"][A.key_of(row)] = {"name": "gzip", "digest": row["digest"][:16],
                                      "roles": {"decompress": {"flag": "--decompress",
                                                               "state": A.PRESENT}}}
    changed = _row("gzip", digest="b" * 64)
    assert A.known_answer(memory, changed, "decompress") == (A.UNREADABLE, None)
    assert A.known_answer(memory, row, "decompress") == (A.PRESENT, "--decompress")
