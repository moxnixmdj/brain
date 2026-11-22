"""Pins the scan-retrieve-fetch loop: memory keyed by (content, name), and its bounds.

Each test corresponds to a failure that actually happened while building this, and one of
them hung a 900-second run. None of them need /usr/bin or /usr/bin/busybox.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import plans_compose_v1 as algebra  # noqa: E402
import scan_retrieve_fetch_v1 as srf  # noqa: E402


def test_a_name_change_is_a_cache_miss() -> None:
    """`xz` and `unxz` are byte-identical and behave oppositely.

    A cache keyed on content alone would answer "compresses" for the decompressor, so the
    key is (content digest, invoked name) and a changed name must miss.
    """
    memory = {"schema": srf.MEMORY_SCHEMA,
              "entries": {"abc123:xz": {"name": "xz", "transform": "compress",
                                        "flags": {}, "key": "abc123:xz"}}}
    rows = [{"name": "xz", "path": "/x/xz", "digest": "abc123", "key": "abc123:xz"},
            {"name": "unxz", "path": "/x/unxz", "digest": "abc123", "key": "abc123:unxz"}]
    known, unknown = srf.retrieve(memory, rows)
    assert list(known) == ["xz"]
    assert [r["name"] for r in unknown] == ["unxz"]


def test_a_content_change_is_a_cache_miss() -> None:
    memory = {"schema": srf.MEMORY_SCHEMA,
              "entries": {"abc123:gzip": {"name": "gzip", "transform": "compress",
                                          "flags": {}, "key": "abc123:gzip"}}}
    rows = [{"name": "gzip", "path": "/x/gzip", "digest": "ffff99", "key": "ffff99:gzip"}]
    known, unknown = srf.retrieve(memory, rows)
    assert not known and len(unknown) == 1


def test_the_reading_rule_handles_both_help_layouts() -> None:
    """GNU puts the description first; busybox puts a banner and usage first."""
    gnu = ("Usage: gzip [OPTION]... [FILE]...\n"
           "Compress or uncompress FILEs (by default, compress FILES in-place).\n"
           "\n  -d, --decompress  decompress\n")
    bb = ("BusyBox v1.36.1 (2026-04-09) multi-call binary.\n"
          "\nUsage: gzip [-cfkdt] [FILE]...\n"
          "\nCompress FILEs (or stdin)\n"
          "\n\t-d\tDecompress\n\t-c\tWrite to stdout\n")
    assert srf.read_type(gnu)["transform"] == "compress"
    assert srf.read_type(bb)["transform"] == "compress"
    assert srf.read_flag(gnu, "decompress") == "--decompress"
    assert srf.read_flag(bb, "decompress") == "-d"
    assert srf.read_flag(bb, "stdout") == "-c"


def test_a_banner_is_not_a_self_description() -> None:
    banner = "BusyBox v1.36.1 (2026-04-09 10:34:48 UTC) multi-call binary.\n"
    assert srf.read_type(banner) is None


def test_an_untyped_program_does_not_enter_the_search_graph() -> None:
    """398 `TEXT -> X[TEXT]` edges made a one-hop goal unfindable.

    A program that only prints or searches names no input type, so it must be recorded as
    untyped rather than guessed into composition.
    """
    known = {"ls": {"transform": "list", "path": "/bin/ls", "flags": {}, "name": "ls"}}
    rows = srf.rows_for_algebra(known)
    assert rows["ls"]["schemes"][0].get("untyped") is True
    assert rows["ls"]["schemes"][0]["from"] == "UNTYPED"


def test_the_search_refuses_instead_of_running_forever() -> None:
    """An unbounded nesting search hung a 900 s run; the ceiling is the fix."""
    rows = {f"w{i}": {"program": f"w{i}", "path": "/bin/false", "roles": {},
                      "schemes": [{"from": "ANY", "to": f"W{i}[_]", "polymorphic": True}]}
            for i in range(12)}
    started = time.perf_counter()
    found = algebra.find_path(rows, "TEXT", "NOPE[X[Y[Z[Q]]]]", max_states=500)
    elapsed = time.perf_counter() - started
    assert found["found"] is False
    assert elapsed < 5.0, f"search took {elapsed:.1f}s; the state ceiling did not hold"


def test_the_search_bound_is_on_nesting_not_only_chain_length() -> None:
    """Types grow unboundedly, so a chain-length cap alone cannot terminate the search."""
    rows = {"w": {"program": "w", "path": "/bin/false", "roles": {},
                  "schemes": [{"from": "ANY", "to": "W[_]", "polymorphic": True}]}}
    deep = algebra.find_path(rows, "TEXT", "W[W[W[W[W[W[TEXT]]]]]]", max_depth=3)
    assert deep["found"] is False, "a type nested deeper than max_depth must not be reached"
    shallow = algebra.find_path(rows, "TEXT", "W[W[TEXT]]", max_depth=4)
    assert shallow["found"] is True


def test_a_sink_is_built_from_the_type_not_the_program_name() -> None:
    """`base32[TEXT]` never matches `BASE32[TEXT]`; this reported zero compositions."""
    known = {"base32": {"transform": "encode", "path": "/bin/false", "name": "base32",
                        "flags": {"decompress": "--decode"}}}
    rows = srf.rows_for_algebra(known)
    assert rows["base32"]["constructor"] == "BASE32"
    assert algebra.find_path(rows, "TEXT", "BASE32[TEXT]")["found"] is True
    assert algebra.find_path(rows, "TEXT", "base32[TEXT]")["found"] is False


def test_memory_round_trips_through_the_file(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "m.json"
    memory = {"schema": srf.MEMORY_SCHEMA,
              "entries": {"k": {"key": "k", "name": "n", "transform": "compress",
                                "flags": {}, "path": "/p"}}}
    srf.save_memory(memory, path)
    assert srf.load_memory(path)["entries"]["k"]["name"] == "n"


def test_a_corrupt_memory_file_is_not_fatal(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "m.json"
    path.write_text("{not json")
    assert srf.load_memory(path)["entries"] == {}
    path.write_text(json.dumps({"schema": "SOMETHING_ELSE", "entries": {"x": {}}}))
    assert srf.load_memory(path)["entries"] == {}
