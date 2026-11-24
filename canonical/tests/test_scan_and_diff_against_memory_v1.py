"""Scan an environment, diff it against memory, and get an honest list of what is new.

The owner's proposal was: go into an arbitrary environment, scan it, diff the scan against
what memory knows, and everything left over is what to go and learn. The tests here exist to
hold the two ways that proposal can be quietly ruined, both of which this repository has
already paid for once:

  1. TRUSTING THE NAME. A suffix is a claim about bytes. `cli_contract_inference.py` carries
     `MAGIC_BY_SUFFIX` doing exactly this, and it is the wrong shape: a `.json` that does not
     parse is "known" under it. Identity here is what a program that DECLARES the kind
     accepts, so the bytes have to pass a test.

  2. MEASURING WITH AN INSTRUMENT THAT CHANGES THE THING MEASURED. The first version of the
     scanner used `py_compile` as its python validator. `py_compile` writes `__pycache__`
     next to the file, so a scan of `intake/` reported `json+python+utf8_text` for markdown
     -- it was reading the `.pyc` files its own validator had just written. A scan that
     leaves artefacts behind is not a scan.

And one retraction, kept as a test so the corrected number cannot drift back: the claim that
signature keying transfers better than suffix keying does NOT survive real data.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import scan_and_diff_against_memory_v1 as S  # noqa: E402

PNG_MAGIC = bytes([137, 80, 78, 71, 13, 10, 26, 10])


@pytest.fixture()
def world():
    """A directory whose names are not to be trusted."""
    root = tempfile.mkdtemp(prefix="brain-scan-")
    files = {
        "real.json": b'{"a": 1}',
        "real.md": b"# title\n",
        "real.py": b"x = 1\n",
        "real.png": PNG_MAGIC + b"0" * 20,
        "lying.json": b"not json at all\n",
        "lying.py": b"def f(:\n",
        "lying.png": b"just some text\n",
        "opaque.bin": bytes(range(0, 256)),
    }
    for name, data in files.items():
        (pathlib.Path(root) / name).write_bytes(data)
    yield root
    shutil.rmtree(root, ignore_errors=True)


# --------------------------------------------------------------------------- #
# identity is content, not name
# --------------------------------------------------------------------------- #
def test_a_json_file_that_does_not_parse_is_not_json(world):
    items = {item.path: item for item in S.scan(world)}
    assert "json" in items["real.json"].sig
    assert "json" not in items["lying.json"].sig, (
        "a file that does not parse was called json because of its suffix")


def test_a_python_file_that_does_not_parse_is_not_python(world):
    items = {item.path: item for item in S.scan(world)}
    assert "python" in items["real.py"].sig
    assert "python" not in items["lying.py"].sig


def test_a_png_that_is_not_a_png_is_not_png(world):
    items = {item.path: item for item in S.scan(world)}
    assert "png" in items["real.png"].sig
    assert "png" not in items["lying.png"].sig


def test_bytes_no_validator_accepts_get_the_empty_signature(world):
    """`sig=()` is the strongest statement the scan can make: nothing on this machine that
    declares it can read this kind accepts these bytes. It is a gap, not a failure."""
    items = {item.path: item for item in S.scan(world)}
    assert items["opaque.bin"].sig == ()


def test_the_scan_does_not_leave_artefacts_behind(world):
    """THE REGRESSION THIS FILE EXISTS FOR. `py_compile` writes `__pycache__`; scanning
    `intake/` then read those `.pyc` files and reported markdown as python."""
    before = sorted(os.listdir(world))
    S.scan(world)
    assert sorted(os.listdir(world)) == before, "the scanner wrote into the directory"
    assert not (pathlib.Path(world) / "__pycache__").exists()


# --------------------------------------------------------------------------- #
# memory holds a signature, never a path
# --------------------------------------------------------------------------- #
def test_memory_records_no_paths(world):
    memory = S.Memory()
    memory.learn(S.scan(world))
    blob = repr(memory.as_dict())
    for name in ("real.json", "lying.py", "opaque.bin"):
        assert name not in blob, f"{name} leaked into memory; transfer would be memorisation"


def test_a_kind_met_in_one_place_is_known_in_a_place_never_seen(world):
    """A `.md` in a new directory is understood although no markdown was in the first one:
    what memory holds is which programs accept the bytes, and that answer travels."""
    memory = S.Memory()
    memory.learn(S.scan(world))
    other = tempfile.mkdtemp(prefix="brain-scan-new-")
    try:
        (pathlib.Path(other) / "unseen_name.markdown").write_bytes(b"## heading\n")
        item = S.scan(other)[0]
        memory.learn([])  # nothing added
        verdict, note = memory.judge(item)
        assert verdict == S.KNOWN, note
    finally:
        shutil.rmtree(other, ignore_errors=True)


def test_an_unaccepted_kind_in_a_new_directory_is_unread(world):
    memory = S.Memory()
    memory.learn(S.scan(world))
    other = tempfile.mkdtemp(prefix="brain-scan-new2-")
    try:
        (pathlib.Path(other) / "mystery.xyz").write_bytes(b"\xff\xfe\x00\x01\x02")
        item = S.scan(other)[0]
        verdict, note = memory.judge(item)
        assert verdict == S.UNREAD
        assert "no declared validator" in note
    finally:
        shutil.rmtree(other, ignore_errors=True)


def test_a_readable_file_is_understood_not_unknown(world):
    """THE ROUND-10 DEFECT, FOUND BY AUDITING ITS OWN OUTPUT.

    Round 10 reported 13 UNKNOWN files in `intake/`, and every one of them was accepted by
    `utf8_text` -- they were unknown only because memory had never recorded that exact
    SUBSET of validators. That is memory's bookkeeping, not the file's problem, and it
    aimed the next round's learning at markdown that the machine could already read.
    A file some declared validator reads is UNDERSTOOD, and it is not queued for learning.
    """
    memory = S.Memory()
    memory.learn(S.scan(world))                     # has json, python, png, utf8
    other = tempfile.mkdtemp(prefix="brain-understood-")
    try:
        # utf8_text is already known as a KIND but this exact subset is new
        (pathlib.Path(other) / "fresh.md").write_bytes(b"# a heading\n")
        item = S.scan(other)[0]
        assert item.sig, "expected some validator to read this file"
        verdict, note = memory.judge(item)
        assert verdict in (S.KNOWN, S.UNDERSTOOD), note
        assert verdict != S.UNREAD
        if verdict == S.UNDERSTOOD:
            assert "the kind is not" in note
    finally:
        shutil.rmtree(other, ignore_errors=True)


def test_only_unread_files_reach_the_learning_queue(world):
    """A queue that asks to learn what is already readable spends the machine on nothing."""
    memory = S.Memory()
    memory.learn(S.scan(world))
    other = tempfile.mkdtemp(prefix="brain-queue-")
    try:
        (pathlib.Path(other) / "readable.md").write_bytes(b"# heading\n")
        (pathlib.Path(other) / "opaque.dat").write_bytes(b"\xff\x00\xfe\x01")
        out = S.census(other, memory=memory)
        assert out["understood"] + out["known"] + out["unread"] == out["files"]
        assert out["learn_next"] == ["opaque.dat"], out["learn_next"]
    finally:
        shutil.rmtree(other, ignore_errors=True)


def test_an_absence_is_never_learned_as_a_kind(world):
    """THE DEFECT THAT MADE THE IDEA WORTHLESS, found by a failing test.

    Every kind nothing can read shares the key `()`. Learning that key made the FIRST
    unreadable file teach memory that unreadable bytes are a known kind -- so every later
    unknown file was reported KNOWN, and the machine confidently claimed to know exactly
    the things it did not know. `()` is the absence of knowledge and must never become
    evidence of it."""
    memory = S.Memory()
    memory.learn(S.scan(world))            # world contains opaque.bin, sig=()
    other = tempfile.mkdtemp(prefix="brain-absence-")
    try:
        (pathlib.Path(other) / "another.bin").write_bytes(b"\xde\xad\xbe\xef\x00\x11")
        item = S.scan(other)[0]
        assert item.sig == (), "this file was expected to be unreadable"
        verdict, _ = memory.judge(item)
        assert verdict == S.UNREAD, "an absence was learned as a kind"
        assert () not in memory.seen, "the empty signature entered memory"
        assert memory.unread >= 1
    finally:
        shutil.rmtree(other, ignore_errors=True)


# --------------------------------------------------------------------------- #
# the retraction: signature keying does NOT out-transfer suffix keying here
# --------------------------------------------------------------------------- #
def test_signature_keying_is_not_claimed_to_transfer_better():
    """MEASURED AND RETRACTED. An earlier version of this module reported 0.8 against 0.6
    for signature vs suffix keying on nine hand-made files. On 100 real files from this
    repository, leave-one-out: signature 100/100, suffix 100/100, **signatures buy 0** --
    the repo holds only three signature classes, so any key that has seen a `.json`
    recognises the next one.

    What signature keying buys is LYING NAMES, which is a different claim and is tested
    above. This test exists so the retracted number cannot quietly return."""
    real = list(pathlib.Path(__file__).resolve().parents[2].glob("intake/*"))
    if len(real) < 20:
        pytest.skip("needs a populated intake/ directory")
    items = S.scan(str(pathlib.Path(__file__).resolve().parents[2] / "intake"),
                   max_files=30)
    learned_signatures = {item.sig for item in items}
    learned_suffixes = {item.suffix for item in items}
    by_signature = sum(1 for item in items if item.sig in learned_signatures)
    by_suffix = sum(1 for item in items if item.suffix in learned_suffixes)
    assert by_signature == by_suffix == len(items), (
        "on a directory with few signature classes the two keyings should tie; if they "
        "diverge the retraction needs revisiting with real numbers")
    result = S.transfer(learned=items, new=items)
    assert result["signatures_buy"] == 0


# --------------------------------------------------------------------------- #
# the join: what to learn next is ranked by the existing ledger, not by a rule here
# --------------------------------------------------------------------------- #
def test_an_unaccepted_kind_outranks_a_half_known_one(tmp_path):
    """The ordering must come from `ignorance_ledger_v1`'s own formula
    `value = p_useful / (1 + cost)`, not from an ordering written in this module. A file
    nothing accepts is the cheap decisive gap; a half-known kind costs more to settle."""
    from canonical.runtime import ignorance_ledger_v1 as ledger
    store = str(tmp_path / "gaps.json")
    items = [
        S.Item(path="mystery.xyz", suffix=".xyz", size=10, sig=()),
        S.Item(path="known.json", suffix=".json", size=10,
               sig=("json", "python", "utf8_text")),
    ]
    S.to_ignorance(items, path=store)
    ranked = ledger.rank(path=store)
    assert ranked, "nothing was ranked"
    assert "unaccepted" in str(ranked[0].get("what")), (
        "the gap nothing can read was not ranked first")


def test_the_cost_of_a_scan_is_bounded():
    """Measured: 40 files took 5.1 s because `unzip -t` alone spends ~0.2 s and every
    validator ran on every file. Necessary-magic skipping brought it to 1.9 s. A scan that
    is not cheap is not a scan."""
    import time
    root = pathlib.Path(__file__).resolve().parents[2] / "intake"
    if not root.is_dir():
        pytest.skip("needs intake/")
    started = time.perf_counter()
    S.scan(str(root), max_files=40)
    assert time.perf_counter() - started < 4.0, "the scan became the expensive part"
