"""Pins the transfer instrument: shape portability, key sharpness, and refusal to guess.

Real hosts are measured by the runner. These fixtures make the three claims fail
loudly if the mechanism drifts: a shape the base never saw must be reported
missing, the producer key must beat the family key on a host of one producer, and
the selector must ask rather than reuse an unbanked key.
"""
from __future__ import annotations

import json
import pathlib
import sys

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import what_transfers_to_a_second_host_v1 as transfer  # noqa: E402

ELF_ISH = "\x00fake elf payload with Usage: solid --flag\n"
PERL = """#!/usr/bin/perl
print "Usage: perly --mode FILE\\n";
print "options: --verbose --dry-run\\n";
"""
# A real console script is a stub: it imports the logic, so its own bytes contain no
# flags at all. That is the measured shape of 11 of 12 programs in the venv host.
PY_SCRIPT = """#!/usr/bin/env python3
import sys
from pything.main import main
if __name__ == '__main__':
    sys.argv[0] = 'pything'
    sys.exit(main())
"""
NODE = """#!/usr/bin/env node
console.log("usage: nodething --watch");
"""


def _host(tmp_path: pathlib.Path, name: str, files: dict[str, tuple[str, int]]) -> dict:
    bindir = tmp_path / name
    bindir.mkdir(parents=True, exist_ok=True)
    for filename, (body, mode) in files.items():
        path = bindir / filename
        path.write_text(body, encoding="utf-8")
        path.chmod(mode)
    return transfer.land(str(bindir))


def test_producer_reads_the_shebang_not_the_extension(tmp_path: pathlib.Path) -> None:
    perl = tmp_path / "a"
    perl.write_text(PERL, encoding="utf-8")
    node = tmp_path / "b"
    node.write_text(NODE, encoding="utf-8")
    env_py = tmp_path / "c"
    env_py.write_text(PY_SCRIPT, encoding="utf-8")
    assert transfer.producer(perl) == "perl"
    assert transfer.producer(node) == "env:node"
    assert transfer.producer(env_py) == "env:python3"


def test_a_shape_the_base_never_saw_is_reported_missing(tmp_path: pathlib.Path) -> None:
    base = _host(tmp_path, "base", {"solid": (ELF_ISH, 0o755)})
    novel = _host(tmp_path, "novel", {"perly": (PERL, 0o755)})
    base_shapes = transfer.shapes_of(base)
    novel_shapes = transfer.shapes_of(novel)
    assert base_shapes, "the base must land at least one shape"
    missing = novel_shapes - base_shapes
    assert missing, "a new artifact family must show up as a missing shape, not be smoothed away"


def test_the_selector_asks_instead_of_reusing_an_unbanked_key(tmp_path: pathlib.Path) -> None:
    base = _host(tmp_path, "base", {"solid": (ELF_ISH, 0o755)})
    memory = {"base": base, **transfer.build_memory(base)}
    # one lone member is a perfect "agreement" of 1.0 and must still not be banked:
    # a key needs more than one witness before its outcome is a rule
    assert memory["banked"] == {}, memory["banked"]
    target = _host(tmp_path, "target", {"perly": (PERL, 0o755)})
    chosen = transfer.select(memory, target)
    assert chosen["by_action"].get("MEMORY", 0) == 0, chosen
    assert chosen["by_action"].get("LOOK") == 1, "the bytes had flags, so LOOK was chosen"
    assert chosen["memory_activation_precision"] is None, "no activation means no precision claim"


def test_a_stable_key_is_banked_and_reused(tmp_path: pathlib.Path) -> None:
    files = {f"p{index}": (PERL, 0o755) for index in range(6)}
    base = _host(tmp_path, "base", files)
    memory = {"base": base, **transfer.build_memory(base)}
    assert memory["banked"], "six identical producers must bank their key"
    assert all(entry["agreement"] == 1.0 for entry in memory["banked"].values())
    target = _host(tmp_path, "target", {"perly": (PERL, 0o755)})
    chosen = transfer.select(memory, target)
    assert chosen["by_action"].get("MEMORY") == 1
    assert chosen["memory_activation_precision"] == 1.0


def test_look_discoverability_separates_a_binary_host_from_wrappers(tmp_path: pathlib.Path) -> None:
    binary = _host(tmp_path, "binary", {"solid": (ELF_ISH, 0o755)})
    wrappers = _host(tmp_path, "wrappers", {"pything": (PY_SCRIPT, 0o755)})
    assert transfer.look_discoverability(binary)["fraction_discoverable"] > 0
    assert transfer.look_discoverability(wrappers)["fraction_discoverable"] == 0


def test_statement_text_is_not_carried_across(tmp_path: pathlib.Path) -> None:
    base = _host(tmp_path, "base", {f"q{index}": (PERL, 0o755) for index in range(6)})
    other = _host(tmp_path, "other", {"different": (PY_SCRIPT, 0o755)})
    result = transfer.content_transfer(base, other)
    assert result["verdict"] in ("TEXT_DOES_NOT_TRANSFER", "SOME_TEXT_TRANSFERS")
    assert "text_exactly_right" in result


def test_receipt_keeps_both_keys(tmp_path: pathlib.Path) -> None:
    base = _host(tmp_path, "base", {f"r{index}": (PERL, 0o755) for index in range(4)})
    target = _host(tmp_path, "target", {"perly": (PERL, 0o755)})
    memory = {"base": base, **transfer.build_memory(base)}
    score = {"family": transfer.predict(memory, target, "family"),
             "producer": transfer.predict(memory, target, "producer")}
    for row in score.values():
        assert {"precision", "recall", "true_positive", "false_positive"} <= set(row)
    assert score["producer"]["precision"] >= score["family"]["precision"]
