"""Pins the cross-host claim: a type read from a program's own sentence, on a host the
code never names.

Every test here corresponds to a bug that shipped and was caught by running against a real
host. None of them need a real host: the fixtures stand in for programs that lie, inherit
the wrong help text, or are named in a way that invites a wrong inference.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import compose_a_host_never_seen_v1 as unseen  # noqa: E402
import cost_to_learn_a_host_v1 as cost  # noqa: E402

GZIP_HELP = """Usage: gzip [OPTION]... [FILE]...
Compress or uncompress FILEs (by default, compress FILES in-place).

  -c, --stdout      write on standard output, keep original files unchanged
  -d, --decompress  decompress
"""

BZIP2_HELP = """bzip2, a block-sorting file compressor.  Version 1.0.8, 13-Jul-2019.

   -c --stdout     write on standard output
   -d --decompress force decompression
"""


def test_the_verb_comes_from_the_programs_own_sentence() -> None:
    assert cost.transform_of(cost.self_description(GZIP_HELP)) == "compress"
    # `bzip2` names its transform by its PRODUCT, not a verb: "a ... file compressor"
    assert cost.transform_of(cost.self_description(BZIP2_HELP)) == "compress"


def test_a_banner_synopsis_or_error_is_not_a_self_description() -> None:
    assert cost.self_description("Version: ImageMagick 6.9.11 https://x") == ""
    assert cost.self_description("wall [options] [<file> | <message>]") == ""
    assert cost.self_description("Unknown option: help") == ""
    assert cost.self_description("identify: unable to open image `--help'") == ""


def test_a_two_word_name_needs_two_agreeing_statements() -> None:
    """A prefix alone is not evidence; the base must also call itself constructive."""
    names = {"bzip2", "gzip", "xz", "der", "code", "under", "decode"}
    constructive = {"bzip2", "gzip", "xz"}
    assert unseen.inverse_base("bunzip2", names, constructive) == "bzip2"
    assert unseen.inverse_base("gunzip", names, constructive) == "gzip"
    assert unseen.inverse_base("unxz", names, constructive) == "xz"
    # the false positives the first rule produced on a real host
    assert unseen.inverse_base("under", names, constructive) is None
    assert unseen.inverse_base("decode", names, constructive) is None
    # a plain filename prefix is not an inverse marker
    assert unseen.inverse_base("base64", names, constructive) is None


def test_the_reverse_marker_is_not_only_a_prefix() -> None:
    """`bunzip2` is b+un+zip2; a prefix-only rule typed a decompressor as a compressor."""
    names = {"bzip2"}
    assert unseen.inverse_base("bunzip2", names, {"bzip2"}) == "bzip2"


def test_a_flag_is_looked_up_in_the_programs_own_help() -> None:
    assert unseen.flag_for(GZIP_HELP, "decompress") == "--decompress"
    assert unseen.flag_for(GZIP_HELP, "stdout") == "--stdout"
    assert unseen.flag_for("no help at all", "decompress") is None


def test_the_flag_lookup_prefers_the_long_form() -> None:
    """A short flag's meaning has to be taken on faith; a long one states itself."""
    assert unseen.flag_for("  -d, --decompress  decompress\n", "decompress") == "--decompress"


def test_executables_are_counted_by_name_not_by_target(tmp_path: pathlib.Path) -> None:
    """`unxz` sorts before `xz`; deduping by target silently deleted `xz` from the census."""
    real = tmp_path / "xz"
    real.write_text("#!/bin/sh\necho 'Compress or decompress FILEs.'\n")
    real.chmod(0o755)
    (tmp_path / "unxz").symlink_to(real)
    (tmp_path / "xzcat").symlink_to(real)
    names = [p.name for p in cost.executables(tmp_path)]
    assert names == ["unxz", "xz", "xzcat"], names


def test_a_probe_is_bounded_in_bytes_and_never_waits_forever(tmp_path: pathlib.Path) -> None:
    """An untrusted executable must not be able to make the learner read gigabytes."""
    hog = tmp_path / "hog"
    hog.write_text("#!/bin/sh\nyes 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'\n")
    hog.chmod(0o755)
    got = cost.probe(hog, budget=4096, deadline=1.5)
    assert got["bytes"] <= 4096, got
    assert got["reason"] in ("BUDGET", "DEADLINE"), got
    assert got["seconds"] < 5.0, got


def test_a_probe_kills_the_whole_process_group(tmp_path: pathlib.Path) -> None:
    """A child that daemonises must not outlive the probe."""
    marker = tmp_path / "survived"
    spawner = tmp_path / "spawner"
    spawner.write_text(
        "#!/bin/sh\n"
        f"( sleep 2; touch {marker} ) &\n"
        "sleep 30\n"
    )
    spawner.chmod(0o755)
    cost.probe(spawner, budget=1024, deadline=0.5)
    import time
    time.sleep(2.6)
    assert not marker.exists(), "the probe's grandchildren were not killed"


def test_no_branch_in_the_instrument_names_a_program() -> None:
    """The claim in one line: the host supplies the knowledge, not a lookup table."""
    source = (TOOLS / "compose_a_host_never_seen_v1.py").read_text()
    forbidden = ('== "gzip"', "== 'gzip'", '== "bzip2"', "== 'bzip2'",
                 '== "base64"', "== 'base64'", '== "xz"', "== 'xz'",
                 '== "pygmentize"', "== 'pygmentize'")
    for needle in forbidden:
        assert needle not in source, f"per-program branch found: {needle}"


def test_composition_is_at_least_two_stages_away_from_the_source() -> None:
    """A chain of one is the program's own help executed, not composition."""
    rows = {
        "enc_a": {"program": "enc_a", "path": "/bin/false", "roles": {},
                  "schemes": [{"from": "ANY", "to": "A[_]", "polymorphic": True}]},
        "enc_b": {"program": "enc_b", "path": "/bin/false", "roles": {},
                  "schemes": [{"from": "ANY", "to": "B[_]", "polymorphic": True}]},
    }
    found = unseen.algebra.find_path(rows, "TEXT", "B[A[TEXT]]")
    assert found["found"] and len(found["chain"]) == 2, found


def test_a_chain_writes_nothing_into_the_callers_tree(tmp_path: pathlib.Path) -> None:
    """17 stray `gz*` files were committed because a chain ran in the repository root.

    A compressor with no output redirection writes a file beside itself. Every stage now
    runs in a directory the caller owns, so the learner cannot dirty the tree it learns in.
    """
    import os
    fake = tmp_path / "fake" / "compressor"
    fake.parent.mkdir()
    fake.write_text("#!/bin/sh\ncat > junk-artifact\necho compressed\n")
    fake.chmod(0o755)
    rows = {"compressor": {"program": "compressor", "path": str(fake), "roles": {},
                           "schemes": [{"from": "ANY", "to": "C[_]", "polymorphic": True}]}}
    caller = tmp_path / "caller"
    caller.mkdir()
    before = set(os.listdir(caller))
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    result = unseen.run_chain(rows, ["compressor"], "forward", b"payload", workdir)
    assert result["status"] == "OK", result
    assert set(os.listdir(caller)) == before, "the chain wrote into the caller's tree"
    assert (workdir / "junk-artifact").exists(), "the junk should land in the workdir"
