"""One decoy cannot find a judge that says yes to a kind that is not its own.

Round 11 admitted a judge if it said 0 to a real file of the kind and non-zero to a decoy.
That test has a hole, and measuring a real machine fell through it. Run every judge against
every OTHER real kind and the truth appears:

    judge        zip  gzip  json  python  text  elf  tar  png
    gzip           0     0     1       1     1    1    1    1     <- says yes to a ZIP
    tar            2     0     2       2     2    2    0    2     <- says yes to a gzip
    python/ast     1     1     0       0     1    1    1    1     <- says yes to JSON
    utf8_text      1     1     0       0     0    1    0    1     <- says yes to tar

`gzip -t` on a real zip prints "OK" and exits 0 -- measured, gzip 1.12. `tar -tf` on a real
gzip exits 0. A JSON document IS a valid Python program: `{"a": 1}` parses as an expression
statement. None of those is a judge of its kind, and all of them passed round 11.

Round 11 therefore claimed seven judges where the honest number was five. This module exists
so that number is measured rather than declared.
"""
from __future__ import annotations

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


# --------------------------------------------------------------------------- #
# the defect: another real kind, not another decoy
# --------------------------------------------------------------------------- #
def test_a_judge_that_accepts_another_real_kind_is_refused(receipt):
    """`gzip -t` exits 0 on a real ZIP. The strict test catches it; the round-11 test did not."""
    refused = {row["evidence"].get("candidate"): row for row in receipt["refused"]}
    lazy_or_gzip = refused.get("gzip")
    assert lazy_or_gzip is not None, "gzip -t was admitted; it accepts a zip file"
    assert lazy_or_gzip["status"] == E.REFUSED_ACCEPTS_ANOTHER_REAL_KIND
    assert lazy_or_gzip["evidence"]["accepts_other_real_kinds"], (
        "gzip was refused but no other kind is named; the evidence must say which")


def test_tar_that_accepts_a_gzip_is_refused(receipt):
    refused = {row["evidence"].get("candidate"): row for row in receipt["refused"]}
    assert "tar" in refused, "tar -tf was admitted; it accepts a gzip stream"
    assert refused["tar"]["status"] == E.REFUSED_ACCEPTS_ANOTHER_REAL_KIND


def test_the_same_kind_recovered_by_asking_a_different_question(receipt):
    """`gzip -t` tests INTEGRITY and calls a zip OK. Reading a byte through the decompressor
    asks "is this a gzip stream", and a zip fails it. Same for tarfile. The kind comes back
    with a judge that actually answers the question."""
    assert "gzip" in receipt["admitted_kinds"], "no honest gzip judge was earned"
    assert "tar" in receipt["admitted_kinds"], "no honest tar judge was earned"
    by_kind = {row["kind"]: row for row in receipt["admitted"]}
    assert by_kind["gzip"]["evidence"]["candidate"] == "gzip_stream"
    assert by_kind["tar"]["evidence"]["candidate"] == "tarfile"
    assert by_kind["gzip"]["evidence"]["accepts_other_real_kinds"] == []


def test_every_exclusive_judge_rejects_every_other_real_kind(receipt):
    for row in receipt["admitted"]:
        if row["status"] != E.EARNED:
            continue
        assert row["evidence"]["accepts_other_real_kinds"] == [], (
            f"{row['kind']} was admitted as exclusive but accepts "
            f"{row['evidence']['accepts_other_real_kinds']}")


# --------------------------------------------------------------------------- #
# nested kinds: the honest second class
# --------------------------------------------------------------------------- #
def test_a_nested_kind_is_admitted_as_nested_not_as_exclusive(receipt):
    """Requiring every judge to reject every other real kind kept 5 judges and read 0% of
    /usr/share/doc -- because a .py file IS utf8 text and a JSON document IS parseable
    python. A nested kind must accept a superset to be correct at all, so it is admitted
    under a name that says it can never prove a file is NOT something else."""
    nested = set(receipt["nested_kinds"])
    exclusive = set(receipt["exclusive_kinds"])
    assert nested == {"python", "utf8_text"}, nested
    assert not (nested & exclusive), "a kind cannot be both nested and exclusive"


def test_json_is_genuinely_valid_python():
    """The measured reason `python` cannot be exclusive. If this ever stops holding, the
    nested classification for python must be revisited rather than kept out of habit."""
    import ast
    ast.parse('{"a": 1}')            # raises SyntaxError if JSON stops parsing as python


def test_the_nested_class_does_not_leak_into_exclusive(receipt):
    for row in receipt["admitted"]:
        if row["status"] == E.NESTED:
            assert row["evidence"]["accepts_other_real_kinds"], (
                f"{row['kind']} was classified nested without accepting anything; it could "
                f"have been exclusive and the weaker label is losing information")


# --------------------------------------------------------------------------- #
# coverage on a real machine, which is the point
# --------------------------------------------------------------------------- #
def test_elf_is_judged_so_binaries_are_readable(receipt):
    """73% of /usr/bin was unreadable before this. Four programs on this machine judge ELF
    and all four agree; `readelf -h` is the one earned."""
    assert "elf" in receipt["admitted_kinds"]
    import subprocess
    binary = shutil.which("ls") or "/bin/ls"
    row = {r["kind"]: r for r in receipt["admitted"]}["elf"]
    assert subprocess.run([*row["argv"], binary], capture_output=True).returncode == 0
    decoy = tempfile.mktemp()
    try:
        pathlib.Path(decoy).write_bytes(b"\xff" * 8 + b"\x00\x01" * 8)
        assert subprocess.run([*row["argv"], decoy], capture_output=True).returncode != 0
    finally:
        pathlib.Path(decoy).unlink(missing_ok=True)


def test_a_scanned_item_can_be_rejudged(receipt):
    """THE API TRAP THAT MADE A MEASUREMENT LIE.

    `Item.path` is relative to the scan root, so `signature(item.path, judges)` resolves
    against the caller's cwd, finds nothing, and returns `()`. Measured: 0% of
    /usr/share/doc looked readable through that route while the same files read fine by
    absolute path. `rejudge()` uses the path the signature was actually taken from.
    """
    from canonical.runtime import scan_and_diff_against_memory_v1 as S
    root = tempfile.mkdtemp(prefix="brain-rejudge-")
    try:
        pathlib.Path(root, "note.txt").write_bytes(b"hello\n")
        item = S.scan(root)[0]
        assert item.abspath, "the item did not record where it came from"
        honest = E.judges_from(receipt)
        assert item.rejudge(honest) == item.sig
        assert item.rejudge(honest), "rejudging a readable file returned nothing"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_most_of_a_real_machine_is_readable(receipt):
    """The number that matters, measured rather than asserted. Before ELF was earned and the
    rejudge trap was fixed, /usr/bin was 73% unreadable."""
    from canonical.runtime import scan_and_diff_against_memory_v1 as S
    judges = E.judges_from(receipt)
    targets = [p for p in ("/usr/share/doc", "/usr/bin", "/usr/lib/python3")
               if pathlib.Path(p).is_dir()]
    if not targets:
        pytest.skip("no system directories to measure")
    total = readable = 0
    for root in targets:
        items = S.scan(root, max_files=40)
        total += len(items)
        readable += sum(1 for item in items if item.rejudge(judges))
    assert total > 0
    assert readable / total >= 0.9, f"only {readable}/{total} readable"
