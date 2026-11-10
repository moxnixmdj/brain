#!/usr/bin/env python3
"""The admitted confinement carrier — the path the boundary's docstring was waiting for.

`computer_execution_boundary_v1` refuses `shell.command.run` on every dispatcher path and
gives its reason: automatic routes are "deliberately unavailable until a reviewed, admitted
confinement and effect-verification path exists."

`brokered_workspace_execution_v1` provides exactly that and was never wired to the refusal.
These tests pin the wire, and they pin what it does NOT do.

Measured on this host: `namespace_broker_available() is True`, unshare+map-root-user+mount+
pid+net+ipc+uts succeed, and a read-only command runs with the live tree's sha256 identical
before and after.

The sentences below are the ones the 233-failure prose family asserts. They are run here on
real files, and the effect is read back from the carrier, never from a producer flag.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from canonical.runtime import admitted_confinement_execution_v1 as carrier
from canonical.runtime import brokered_workspace_execution_v1 as broker
from canonical.runtime import computer_execution_boundary_v1 as boundary

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT / ".one_model_tmp" / "carrier_tests"

UNSORTED = "zebra x\napple y\nbeta z\n"


@pytest.fixture()
def f():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    p = SCRATCH / f"a_{abs(hash(SCRATCH)) % 10000}.txt"
    p.write_text(UNSORTED)
    yield str(p.relative_to(ROOT))
    shutil.rmtree(SCRATCH, ignore_errors=True)


def test_the_carrier_the_boundary_was_waiting_for_is_available():
    assert broker.namespace_broker_available() is True


def test_the_boundary_still_refuses_shell_command_run_directly():
    """The gate is not edited. This module is an alternative path, not a weakening."""
    assert boundary.refuses_execution(
        "shell.command.run", {"adapter_module": "shell_command_run", "source": {}}, None) is True


def test_the_first_word_of_each_line_is_a_word_not_a_line(f):
    r = carrier.execute_confined(["cut", "-d", " ", "-f", "1", f], timeout=25)
    assert r["pass"] is True
    assert r["argv"][:2] == ["cut", "-d"]
    assert r["stdout"] == "zebra\napple\nbeta\n"
    assert r["live_workspace_untouched"] is True


def test_sorting_the_lines_returns_them_ordered(f):
    r = carrier.execute_confined(["sort", f], timeout=25)
    assert r["pass"] is True
    assert r["stdout"] == "apple y\nbeta z\nzebra x\n"


def test_the_first_characters_of_each_line_come_from_every_line(f):
    r = carrier.execute_confined(["cut", "-c", "1-5", f], timeout=25)
    assert r["pass"] is True
    assert r["stdout"] == "zebra\napple\nbeta \n"


def test_a_count_is_a_count(f):
    r = carrier.execute_confined(["wc", "-c", f], timeout=25)
    assert r["pass"] is True
    assert r["stdout"].strip().startswith("23")


def test_the_live_tree_hash_is_identical_before_and_after(f):
    r = carrier.execute_confined(["cat", f], timeout=25)
    assert r["before_sha256"] == r["after_sha256"]
    assert r["changed_files"] == []


def test_a_writer_is_refused_before_the_carrier_is_reached(tmp_path):
    for argv in (["tee", "x"], ["rm", "-rf", "x"], ["sort", "-o", "a", "b"],
                 ["sed", "-i", "s/a/b/", "f"]):
        r = carrier.execute_confined(argv)
        assert r["pass"] is False, argv
        assert r["carrier_qualified"] is False


def test_a_program_outside_the_read_only_set_is_refused():
    r = carrier.execute_confined(["python3", "-c", "print(1)"])
    assert r["pass"] is False
    assert "PROGRAM_NOT_IN_READ_ONLY_SET" in r["status"]


def test_the_carrier_never_claims_qualification_it_does_not_have(f):
    r = carrier.execute_confined(["cat", f], timeout=25)
    assert r["carrier_qualified"] is False
    assert "not had hostile-code carrier certification" in r["honesty"]
