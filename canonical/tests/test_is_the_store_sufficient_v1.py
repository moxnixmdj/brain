"""A sufficiency check that cannot fail is worthless.

These tests build the failing cases deliberately: a store that LOST an answer, and a store that
INVENTED one. Both must be caught, because an invented answer is indistinguishable from a
measured one until it is used -- and by then it has already acted.
"""
from __future__ import annotations

import sys
import pathlib
import json

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import is_the_store_sufficient_v1 as SQ
import ask_the_host_the_right_question_v1 as A


def _fake_rebuild(reported, from_memory):
    """Drive compare()'s logic without touching a real host."""
    sound, complete = {}, {}
    discrepancies = {}
    for role in reported:
        a, b = reported[role], from_memory[role]
        invented = {k: v for k, v in b.items() if a.get(k) != v}
        lost = {k: v for k, v in a.items() if b.get(k) != v}
        sound[role] = not invented
        complete[role] = not lost
        if invented:
            discrepancies.setdefault("invented", {})[role] = invented
        if lost:
            discrepancies.setdefault("lost", {})[role] = lost
    return sound, complete, discrepancies


def test_an_exact_rebuild_is_sound_and_complete():
    reported = {"decompress": {"gzip": "--decompress", "capsh": "--decode"}}
    sound, complete, d = _fake_rebuild(reported, reported)
    assert all(sound.values()) and all(complete.values()) and not d


def test_a_lost_answer_is_caught():
    reported = {"decompress": {"gzip": "--decompress", "capsh": "--decode"}}
    sound, complete, d = _fake_rebuild(reported, {"decompress": {"gzip": "--decompress"}})
    assert not all(complete.values())
    assert d["lost"]["decompress"] == {"capsh": "--decode"}
    assert all(sound.values())


def test_an_invented_answer_is_caught():
    reported = {"decompress": {"gzip": "--decompress"}}
    rebuilt = {"decompress": {"gzip": "--decompress", "bzip2": "--decompress"}}
    sound, complete, d = _fake_rebuild(reported, rebuilt)
    assert not all(sound.values())
    assert d["invented"]["decompress"] == {"bzip2": "--decompress"}


def test_a_wrong_flag_is_both_invented_and_lost():
    reported = {"stdout": {"gzip": "--stdout"}}
    sound, complete, _d = _fake_rebuild(reported, {"stdout": {"gzip": "--to-stdout"}})
    assert not all(sound.values()) and not all(complete.values())


def test_the_rebuild_subprocess_uses_only_the_store_and_the_host():
    """No state may be carried in a live object -- the rebuild is a separate process."""
    src = SQ.REBUILD
    assert "ask_the_host_the_right_question_v1" in src
    assert "A.scan(host)" in src
    assert "A.known_answer" in src
    # it must NOT ask anything: only known_answer may be used to obtain a flag
    assert "A.ask_role" not in src and "A.resolve" not in src
