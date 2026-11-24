"""A judge is earned by separating a real file from a decoy, not by being typed.

Round 10 named its own ceiling: seven hand-written validators decide how much of an unseen
environment can be called known, and seven is a seed, not coverage. The obvious next move --
write more of them -- is the move that never ends, because every new environment brings kinds
nobody wrote one for.

Everything needed to stop writing them was already in the repository: a refusal NAMES A KIND
(`a_refusal_is_a_specification_v1`, 601 of them), and a program's verdict on a file IS a
judgement about that kind. So the judge does not need to be typed. It needs to be MEASURED.

These tests hold the three ways a measured judge can be fake, each of which this round
actually produced before being fixed:

  1. ACCEPTS EVERYTHING. `gzip.open(path, 'rb')` is lazy, reads nothing, and returns a handle
     for any file -- `yes=0 no=0`. That is `cat`, which round 10 excluded because it tells
     you nothing. A candidate that cannot separate the pair is refused.
  2. REJECTS EVERYTHING. A wrong call signature exits non-zero on the real file too. Refused.
  3. A DECOY THAT IS LEGAL. The first decoy was `bytes(range(0,64))`, which is perfectly
     valid UTF-8, so `utf8_text` accepted it and was reported as `cat`. The refusal was
     correct and the probe was wrong. A decoy one kind accepts turns that kind's judge into a
     false positive, so the decoy must be illegal for every kind.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import earn_a_judge_v1 as E  # noqa: E402


@pytest.fixture(scope="module")
def receipt():
    return E.earn_set()


def test_the_probe_pair_is_made_by_producers_not_typed():
    """The real member of each pair is written by the library that defines the kind, so the
    probe is not a fixture asserting my own expectation."""
    root = tempfile.mkdtemp(prefix="brain-probe-")
    try:
        pairs = E.probe_pairs(root)
        assert set(pairs) >= {"zip", "gzip", "json", "png", "tar", "python", "utf8_text"}
        for kind, pair in pairs.items():
            assert os.path.exists(pair["real"]), kind
            assert os.path.getsize(pair["real"]) > 0, kind
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_the_decoy_is_illegal_for_every_kind():
    """THE PROBE BUG THAT MADE A GOOD JUDGE LOOK LIKE `cat`.

    `bytes(range(0,64))` is valid UTF-8, so `utf8_text` accepted it and was refused. The
    judge was right and the decoy was wrong. 0xFF cannot begin a UTF-8 sequence.
    """
    root = tempfile.mkdtemp(prefix="brain-decoy-")
    try:
        decoy = E.probe_pairs(root)["zip"]["decoy"]
        data = pathlib.Path(decoy).read_bytes()
        assert b"\xff" in data
        with pytest.raises(UnicodeDecodeError):
            data.decode("utf-8")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_a_judge_that_accepts_everything_is_refused(receipt):
    """`gzip.open(path,'rb')` is lazy: it never reads, so it accepts a decoy. It must be
    refused, and that refusal is the reason this module exists rather than a wider table.

    Note it is keyed by CANDIDATE, not by kind: after round 12 the honest gzip judge is
    `gzip_stream`, so a lookup by kind would find the wrong row.
    """
    refused = {row["evidence"].get("candidate"): row for row in receipt["refused"]}
    lazy = refused.get("gzip_lazy_WRONG")
    assert lazy is not None, "the cat-shaped candidate was not refused"
    # round 12 runs the stricter test first, so this candidate is caught as accepting
    # another real kind; either label is a refusal, and both are checked to be non-admission
    assert lazy["status"] in (E.REFUSED_ACCEPTS_EVERYTHING,
                              E.REFUSED_ACCEPTS_ANOTHER_REAL_KIND)
    assert lazy["evidence"]["exit_on_real"] == 0
    assert lazy["evidence"]["exit_on_decoy"] == 0


def test_every_admitted_judge_separated_its_pair(receipt):
    for row in receipt["admitted"]:
        assert row["evidence"]["exit_on_real"] == 0, row["kind"]
        assert row["evidence"]["exit_on_decoy"] != 0, row["kind"]
        # round 12 admits two classes; both must separate their own pair
        assert row["status"] in (E.EARNED, E.NESTED), row["kind"]


def test_the_earned_set_is_measured_against_the_typed_set_not_assumed_equal(receipt):
    """ROUND 11 ASSERTED THESE WERE EQUAL. ROUND 12 MEASURED, AND THEY ARE NOT.

    Round 11 reported seven earned judges and "0 disagreements across 210 judgements". That
    test compared each judge only against the file kinds it already agreed on, and its decoy
    was a single nonsense blob, so a judge that says yes to ANOTHER REAL KIND passed. Running
    every judge against every real kind (round 12) shows the honest number was five
    exclusive plus two nested.

    The equality is gone on purpose. What is asserted now is the relationship that must
    hold: every earned kind is one the typed table also knows, and the earned set is not
    described as larger than it is.
    """
    from canonical.runtime import scan_and_diff_against_memory_v1 as S
    earned = set(receipt["admitted_kinds"])
    typed = set(S.VALIDATORS)
    assert earned <= typed | {"elf"}, (
        f"earned judges exist that the typed table never had: {sorted(earned - typed)}")
    assert "elf" in earned, "ELF was earnable and is not in the set"


def test_no_candidate_is_admitted_without_evidence(receipt):
    for row in receipt["admitted"]:
        assert row["evidence"], f"{row['kind']} was admitted with no evidence"
        assert row["argv"], f"{row['kind']} was admitted with no command"


def test_an_unavailable_program_is_not_silently_dropped():
    """A missing program is `REFUSED_UNAVAILABLE`, which is a different statement from
    'refuted'. The scan keeps its typed fallback so a scan still works on such a machine."""
    result = E.earn_set(candidates={"nosuch": ("definitely-not-a-program-xyz", "-t")})
    assert result["earned"] == 0
    assert result["refused"][0]["status"] == E.REFUSED_UNAVAILABLE


def test_the_scan_uses_earned_judges_and_agrees_with_the_typed_ones():
    """The join: the scan takes its judges from the earned set. Same verdicts on real files,
    obtained by measurement instead of by assertion."""
    from canonical.runtime import scan_and_diff_against_memory_v1 as S
    earned = S.earned_validators()
    # round 12: the earned set is a SUBSET that has been independently judged, plus ELF.
    # Equality with the typed table was round 11's claim and it was wrong.
    assert set(S.VALIDATORS) <= set(earned), "a typed judge went missing from the merge"
    assert "elf" in earned
    sample = pathlib.Path(__file__).resolve().parents[1] / "runtime" / "jit_knowledge_v1.py"
    if not sample.exists():
        pytest.skip("needs a source file to judge")
    for kind in ("python", "utf8_text"):
        by_earned = (kind in S.signature(str(sample), {kind: earned[kind]}))
        by_typed = (kind in S.signature(str(sample), {kind: S.VALIDATORS[kind]}))
        assert by_earned == by_typed, kind


def test_earning_costs_nothing_and_calls_nothing(receipt):
    assert receipt["model_calls"] == 0
    assert receipt["network_calls"] == 0
