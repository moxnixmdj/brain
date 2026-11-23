"""Verification derived from the tool, not from a format table.

`program_synthesis_v1._ROUND_TRIP` is a hand-grown table mapping a suffix to a snippet that opens
the file with the library that owns the format. It is a knowledge house in miniature: a format the
author never met is *unverifiable* rather than merely unknown, and "encode this as base64" came back
NO_VERIFIER_FOR_FORMAT with `base64` on PATH able to do it.

The table is not needed for the largest class, because the tool states its own inverse in its own
help:

    gzip    -d, --decompress  decompress
    xz      -d, --decompress  force decompression
    bzip2   -d --decompress   force decompression
    base64  -d, --decode      decode data

Both directions are the same flag with a reversing prefix. So the round trip is derivable: run the
tool's stated inverse on the output, and the source bytes come back or they do not.

Two things this file pins, and the second matters more than the first:

* the inverse is FOUND from help text, with no table;
* the inverse is CHECKED against bytes, so a flag that merely looks like an inverse (`tar --delete`
  also starts with `de`) is rejected by what it does, not accepted for what it is called.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess

import pytest

from canonical.runtime import program_synthesis_v1 as ps

def _source(tmp_path: pathlib.Path) -> pathlib.Path:
    path = tmp_path / "src.txt"
    path.write_text("alpha\nbeta\ngamma\ndelta\n" * 40, encoding="utf-8")
    return path


def _made_by(argv: list[str], source: pathlib.Path, out: pathlib.Path) -> bool:
    proc = subprocess.run(argv, stdin=source.open("rb"), capture_output=True)
    if proc.returncode != 0 or not proc.stdout:
        return False
    out.write_bytes(proc.stdout)
    return True


@pytest.mark.parametrize("program", ["gzip", "xz", "bzip2", "base64"])
def test_a_reversing_flag_is_found_in_the_programs_own_help(program, tmp_path):
    if shutil.which(program) is None:
        pytest.skip(f"no {program} on this host")
    flag = ps.inverse_flag_for(program, ["-c"])
    assert flag is not None, f"{program} states no inverse but was expected to"
    # and it really is the inverse: running it gives the source bytes back
    source = _source(tmp_path)
    out = tmp_path / "out.bin"
    assert _made_by([program, "-c"] if program != "base64" else [program],
                    source, out), "could not produce a forward output"
    good, why = ps.verify_by_inverse(out, {"program": program, "argv": [program, "-c"]}, source)
    assert good is True, (program, why)


def test_a_flag_that_only_looks_like_an_inverse_is_rejected_by_its_bytes(tmp_path):
    """`tar --delete` starts with `de` and is not an inverse of `tar -c`.

    Spelling proposes it; the bytes dispose of it. This is the case that decides whether the
    mechanism understands anything or merely matches a prefix.
    """
    if shutil.which("tar") is None:
        pytest.skip("no tar on this host")
    source = _source(tmp_path)
    out = tmp_path / "out.tar"
    subprocess.run(["tar", "-cf", str(out), str(source)], check=True)
    good, why = ps.verify_by_inverse(out, {"program": "tar", "argv": ["tar", "-c", "{input}"]}, source)
    assert good is False, why
    assert "DIFFERENT_BYTES" in why, why


def test_an_unknown_suffix_verifies_where_the_table_cannot(tmp_path):
    """The gain, measured on a suffix the table has never seen.

    `base64` output has no entry in `_ROUND_TRIP`; it is verified here because the tool says how to
    undo it and the bytes prove it. Before this mechanism the answer was NO_VERIFIER_FOR_FORMAT.
    """
    if shutil.which("base64") is None:
        pytest.skip("no base64 on this host")
    source = _source(tmp_path)
    out = tmp_path / "payload.unknownext"
    assert _made_by(["base64"], source, out)

    table_only = ps.verify_round_trip(out, ".unknownext")
    assert table_only[0] is False, "the table was expected to have no entry for this suffix"

    with_recipe = ps.verify_round_trip(
        out, ".unknownext", recipe={"program": "base64", "argv": ["base64", "{input}"]},
        source=source)
    assert with_recipe[0] is True, with_recipe
    assert "INVERSE_RETURNED_THE_SOURCE" in with_recipe[1], with_recipe


def test_a_tool_with_no_stated_inverse_is_still_not_verified(tmp_path):
    """The mechanism must not turn every unverifiable format into a verified one.

    `cat` has no reversing flag, so nothing can be concluded from it and the answer stays a
    refusal -- which is the honest answer, not a pass.
    """
    if shutil.which("cat") is None:
        pytest.skip("no cat on this host")
    source = _source(tmp_path)
    out = tmp_path / "copy.unknownext"
    assert _made_by(["cat"], source, out)
    assert ps.inverse_flag_for("cat", []) is None
    good, why = ps.verify_by_inverse(out, {"program": "cat", "argv": ["cat", "{input}"]}, source)
    assert good is False
    assert why == "PROGRAM_STATES_NO_INVERSE", why
