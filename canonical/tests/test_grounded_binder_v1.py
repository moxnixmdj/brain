#!/usr/bin/env python3
"""The grounded binder must bind, must refuse, and must never accept a plaque.

Each test here is written so it can fail: the plaque test fails if the differential is removed,
the binding test fails if the door is chosen by anything other than the sentence's own words,
and the refusal tests fail if the binder invents a program or an object.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import grounded_binder_v1 as binder
from canonical.runtime import machine_self_index_v1 as index_module

TEXT = "alpha\nbeta\ngamma\ndelta\nepsilon\n"


@pytest.fixture()
def workspace(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / "data.txt").write_text(TEXT)
    return tmp_path


# --------------------------------------------------------------------------- #
# grounding: objects come from the workspace
# --------------------------------------------------------------------------- #

def test_a_name_the_workspace_does_not_hold_is_not_an_object(tmp_path: pathlib.Path) -> None:
    (tmp_path / "data.txt").write_text(TEXT)
    named = binder.named_objects("Read data.txt and write to count.json.", tmp_path)
    assert named["files"] == ["data.txt"]
    assert named["artifacts"] == ["count.json"]

    empty = binder.named_objects("Read report.csv and write to out.json.", tmp_path)
    assert empty["files"] == [], "a file that is not there must not be bound as an object"
    assert set(empty["artifacts"]) == {"report.csv", "out.json"}


def test_only_words_the_machine_answers_to_are_programs() -> None:
    assert "wc" in binder.named_programs("Count the lines with wc.")
    assert binder.named_programs("Please tally the entries politely.") == []


def test_a_file_name_is_not_mistaken_for_a_program(workspace: pathlib.Path) -> None:
    """`data.txt` must not be read as a program, even though `data` may be one."""
    assert "data.txt" not in binder.named_programs("Write the sha256 of data.txt to digest.txt.")


# --------------------------------------------------------------------------- #
# the differential: a plaque is not a door
# --------------------------------------------------------------------------- #

def test_a_self_description_is_not_an_action(workspace: pathlib.Path) -> None:
    """`networkctl --version` answers the same for every object, so it does not depend on one.

    This is the test that would have caught the bug where the perturbed object was included in
    the tree digest: with that mistake the two answers always differ and every plaque passes.
    """
    assert binder.depends_on(["networkctl", "--version"], workspace, "data.txt") is False


def test_a_reader_depends_on_its_object(workspace: pathlib.Path) -> None:
    assert binder.depends_on(["wc", "--lines", "data.txt"], workspace, "data.txt") is True


def test_a_writer_that_changes_the_workspace_depends_on_its_object(workspace: pathlib.Path) -> None:
    """`gzip` prints nothing; its dependence shows up as a changed workspace, not as output."""
    assert binder.depends_on(["gzip", "--keep", "data.txt"], workspace, "data.txt") is True
    assert (workspace / "data.txt").exists(), "the test's own run must not mutate the fixture"


def test_the_sentence_names_the_measure(workspace: pathlib.Path) -> None:
    """`--lines` and `--bytes` are both depended-on; only one is what the sentence said."""
    doors = binder.drivable_doors("wc", timeout=1.0)
    by_id = {door["id"]: door for door in doors}
    lines, bytes_ = by_id.get("wc_lines"), by_id.get("wc_bytes")
    assert lines and bytes_, sorted(by_id)
    said = "Count the lines of data.txt."
    assert binder.speaks_to(lines, said, "wc") > binder.speaks_to(bytes_, said, "wc")


# --------------------------------------------------------------------------- #
# execution: the artifact is real, and refusal is named
# --------------------------------------------------------------------------- #

def test_binding_a_named_program_produces_the_artifact(workspace: pathlib.Path) -> None:
    attempt = binder.run("Write the sha256 of data.txt to digest.txt using sha256sum.", workspace)
    assert attempt["outcome"] == "EXECUTED", attempt
    digest = (workspace / "digest.txt").read_text()
    import hashlib
    assert hashlib.sha256(TEXT.encode()).hexdigest() in digest


def test_counting_with_wc_writes_the_number_the_sentence_asked_for(workspace: pathlib.Path) -> None:
    attempt = binder.run("Count the lines of data.txt with wc and write them to count.txt.",
                         workspace)
    assert attempt["outcome"] == "EXECUTED", attempt
    assert (workspace / "count.txt").read_text().split()[0] == "5"


def test_no_named_program_and_no_route_is_a_named_refusal(workspace: pathlib.Path) -> None:
    # `make` is a program this machine answers to, so a sentence containing it is NOT a
    # no-program sentence -- that case is covered below by a sentence with no program in it.
    attempt = binder.run("Improve the report somehow.", workspace)
    assert attempt["outcome"] == "REFUSED"
    assert attempt["reason"] == "NO_NAMED_PROGRAM"


def test_a_door_that_leaves_nothing_is_not_success(workspace: pathlib.Path) -> None:
    """`gzip --stdout` exits 0 and leaves the workspace alone; that is not an achievement."""
    attempt = binder.run("Compress data.txt with gzip.", workspace,
                         routed=["gzip"], max_doors=8)
    if attempt["outcome"] == "EXECUTED":
        assert (workspace / "data.txt.gz").exists() or (workspace / "data.txt").read_bytes() != TEXT.encode()


# --------------------------------------------------------------------------- #
# the machine's own index
# --------------------------------------------------------------------------- #

def test_the_index_reads_the_machine_and_weights_are_computed() -> None:
    index = index_module.build(names=["wc", "gzip", "tar", "sha256sum", "mv"], timeout=0.6)
    assert index["count"] >= 4, "a machine with an empty PATH cannot be routed against"
    assert index["parameters"] == 0 and index["model_calls"] == 0
    # a word every program uses cannot route anything, so its weight is not the largest
    assert max(index["idf"].values()) > 0


def test_routing_returns_programs_the_sentence_named() -> None:
    index = index_module.build(names=["wc", "gzip", "tar", "sha256sum", "mv", "sort"], timeout=0.6)
    routed = [row["program"] for row in index_module.route("Count the lines with wc.", index)]
    assert "wc" in routed, routed


def test_an_option_the_sentence_names_routes_to_the_program_that_publishes_it() -> None:
    """No program named: the sentence says "lines", and only `wc` publishes `--lines`."""
    index = index_module.build(names=["wc", "gzip", "tar", "sha256sum", "mv", "sort"], timeout=0.6)
    routed = [row["program"] for row in index_module.route("How many lines are in data.txt?", index)]
    assert routed and routed[0] == "wc", routed
