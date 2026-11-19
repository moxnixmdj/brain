"""Tests for the record-based portable multi-path commit.

These tests do not trust the receipt: they drive the mechanism themselves on trees built by GNU tar and rm,
and they assert the properties the receipt claims -- the order inside the primitive, idempotence and refusal
of replay, where the record lives, what a crash before the record leaves behind, and the control that proves
the previous round's residual was real.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys

import pytest

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import the_check_mode_is_the_oracle_v1 as cm  # noqa: E402
import the_record_is_the_commit_v1 as t  # noqa: E402

RECEIPT = (pathlib.Path(__file__).resolve().parents[1] / "verification"
           / "THE_RECORD_IS_THE_COMMIT_20261116_V1.json")


@pytest.fixture()
def world(tmp_path):
    built = t.build_world(tmp_path / "world")
    built["pre_digest"] = cm.state_digest(built["live"])
    built["target_digest"] = cm.state_digest(built["stage"])
    return built


def digest_of(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------------
# the effect is real: a tar extraction and an rm, not a hand-written target
# ------------------------------------------------------------------------------------------------------

def test_the_effect_is_produced_by_real_tools_not_by_writing_the_target(world):
    ops = t.operations(world)
    assert [op["path"] for op in ops] == ["alpha.txt", "beta.txt", "delta.txt", "epsilon.txt",
                                         "gamma.txt", "obsolete.txt"]
    assert {op["kind"] for op in ops} == {"create", "delete"}

    # every post-image digest is the digest of the file that tar actually extracted
    for op in ops:
        if op["kind"] == "delete":
            assert op["post"] is None
            continue
        staged = world["stage"] / op["path"]
        assert op["post"] == digest_of(staged)
        assert staged.read_text(encoding="utf-8") == "content of " + op["path"] + "\n"

    # and it really removes something that was there before
    doomed = next(op for op in ops if op["kind"] == "delete")
    assert doomed["pre"] == digest_of(world["live"] / doomed["path"])
    assert not (world["stage"] / doomed["path"]).exists()


def test_the_two_trees_differ_only_by_the_effect(world):
    live_files = {p.name for p in world["live"].iterdir() if p.is_file()}
    stage_files = {p.name for p in world["stage"].iterdir() if p.is_file()}
    assert t.DOOMED in live_files and t.DOOMED not in stage_files
    for member in t.MEMBERS:
        assert member not in live_files and member in stage_files
    assert "keep.txt" in live_files and "keep.txt" in stage_files
    # the untouched file is not part of the effect at all
    assert "keep.txt" not in [op["path"] for op in t.operations(world)]


# ------------------------------------------------------------------------------------------------------
# the primitive: write -> fsync(file) -> rename -> fsync(dir), and the file's identity survives it
# ------------------------------------------------------------------------------------------------------

def test_the_primitive_orders_fsync_file_then_rename_then_fsync_dir(tmp_path):
    trace: list[str] = []
    target = tmp_path / "thing.bin"
    t.durable_write(target, b"payload", trace)
    assert [entry.split(":")[0] for entry in trace] == ["fsync(file)", "rename", "fsync(dir)"]
    assert target.read_bytes() == b"payload"
    assert not (tmp_path / ".thing.bin.tmp").exists()


def test_the_primitive_carries_the_mode_the_staged_file_had(tmp_path):
    staged = tmp_path / "staged.bin"
    staged.write_bytes(b"same bytes")
    os.chmod(staged, 0o640)
    live = tmp_path / "live.bin"
    t.durable_write(live, staged.read_bytes(), [], mode=staged.stat().st_mode & 0o777)
    assert oct(live.stat().st_mode & 0o777) == "0o640"


def test_the_mode_mismatch_would_have_been_a_silent_byte_difference(world):
    """The reason the mode is carried: the state digest includes it, so a mode-losing commit could never
    equal its own target -- this test pins the failure mode rather than trusting the fix."""
    staged = world["stage"] / "alpha.txt"
    os.chmod(staged, 0o600)
    reference = cm.state_digest(world["stage"])
    os.chmod(staged, 0o644)
    assert cm.state_digest(world["stage"]) != reference


# ------------------------------------------------------------------------------------------------------
# replay: idempotent per path, refusing anything it cannot prove
# ------------------------------------------------------------------------------------------------------

def test_replay_is_idempotent_per_path(world):
    op = next(op for op in t.operations(world) if op["kind"] == "create")
    trace: list[str] = []
    assert t.apply_operation(world, op, trace) == "APPLIED"
    after_first = digest_of(world["live"] / op["path"])
    assert after_first == op["post"]
    assert t.apply_operation(world, op, trace) == "ALREADY"
    assert digest_of(world["live"] / op["path"]) == after_first


def test_replay_deletes_idempotently_too(world):
    op = next(op for op in t.operations(world) if op["kind"] == "delete")
    trace: list[str] = []
    assert t.apply_operation(world, op, trace) == "APPLIED"
    assert not (world["live"] / op["path"]).exists()
    assert t.apply_operation(world, op, trace) == "ALREADY"
    assert not (world["live"] / op["path"]).exists()


def test_replay_refuses_a_path_that_has_drifted(world):
    op = next(op for op in t.operations(world) if op["kind"] == "create")
    (world["live"] / op["path"]).write_text("someone else wrote this\n", encoding="utf-8")
    trace: list[str] = []
    assert t.apply_operation(world, op, trace) == "REFUSED_DRIFT"
    # a refusal must not touch what it refused: no overwrite, no delete
    assert (world["live"] / op["path"]).read_text(encoding="utf-8") == "someone else wrote this\n"


# ------------------------------------------------------------------------------------------------------
# the record: beside the tree, before the first operation, and the commit point
# ------------------------------------------------------------------------------------------------------

def test_the_record_lives_beside_the_tree_and_never_inside_it(world):
    trace: list[str] = []
    t.write_journal(world["root"], {"schema": t.SCHEMA, "state": "PREPARED",
                                    "operations": t.operations(world)}, trace)
    journal = world["root"] / t.JOURNAL
    assert journal.exists()
    assert not (world["live"] / t.JOURNAL).exists()
    assert not (world["stage"] / t.JOURNAL).exists()
    payload = json.loads(journal.read_text())
    assert payload["state"] == "PREPARED"
    assert len(payload["operations"]) == 6
    assert t.JOURNAL not in [op["path"] for op in t.operations(world)]


def test_before_the_record_a_crash_leaves_the_pre_state_and_no_record(world):
    ops = t.operations(world)
    result = t.spawn(world["root"], "commit", "before_journal", ops)
    assert result["returncode"] == 9 and result["crashed"]
    assert not (world["root"] / t.JOURNAL).exists()
    assert cm.state_digest(world["live"]) == world["pre_digest"]
    # the abandoned attempt leaves its stage, which is disposable by construction
    assert (world["root"] / t.STAGE).exists()
    assert json.loads(t.spawn(world["root"], "recover", None, ops)["stdout"])["reason"] == "NO_RECORD"


def test_at_the_record_zero_operations_have_been_applied(world):
    ops = t.operations(world)
    t.spawn(world["root"], "commit", "after_journal", ops)
    payload = json.loads((world["root"] / t.JOURNAL).read_text())
    assert payload["state"] == "PREPARED"
    assert cm.state_digest(world["live"]) == world["pre_digest"]
    recovery = json.loads(t.spawn(world["root"], "recover", None, ops)["stdout"])
    assert recovery["recovered"] is True and recovery["replayed"] == 6
    assert cm.state_digest(world["live"]) == world["target_digest"]


def test_without_a_record_a_half_commit_cannot_be_recovered(world):
    """The control, and the reason the previous round's residual was real: no record, no recovery."""
    ops = t.operations(world)
    t.spawn(world["root"], "commit", "after_op:gamma.txt", ops, with_record=False)
    half = cm.state_digest(world["live"])
    assert half not in (world["pre_digest"], world["target_digest"])
    assert not (world["root"] / t.JOURNAL).exists()
    recovery = json.loads(t.spawn(world["root"], "recover", None, ops)["stdout"])
    assert recovery == {"recovered": False, "reason": "NO_RECORD", "trace": [], "phase": "recover"}
    assert cm.state_digest(world["live"]) == half


def test_a_recovery_that_is_interrupted_finishes_on_the_next_attempt(world):
    ops = t.operations(world)
    t.spawn(world["root"], "commit", "after_op:beta.txt", ops)
    interrupted = t.spawn(world["root"], "recover", "recover_after_op:2", ops)
    assert interrupted["returncode"] == 9 and interrupted["crashed"]
    second = json.loads(t.spawn(world["root"], "recover", None, ops)["stdout"])
    assert second["recovered"] is True
    assert cm.state_digest(world["live"]) == world["target_digest"]
    assert not (world["root"] / t.JOURNAL).exists()
    assert not (world["root"] / t.STAGE).exists()


def test_a_crash_after_cleanup_finds_the_target_and_nothing_to_replay(world):
    ops = t.operations(world)
    t.spawn(world["root"], "commit", "after_cleanup", ops)
    assert cm.state_digest(world["live"]) == world["target_digest"]
    assert not (world["root"] / t.JOURNAL).exists()
    assert json.loads(t.spawn(world["root"], "recover", None, ops)["stdout"])["reason"] == "NO_RECORD"


def test_the_quiet_path_is_exact_and_leaves_nothing(world):
    trace: list[str] = []
    result = t.run_commit(world["root"], world, t.operations(world), crash_at=None, trace=trace)
    assert result["completed"] is True
    assert cm.state_digest(world["live"]) == world["target_digest"]
    assert not (world["root"] / t.JOURNAL).exists()
    assert not (world["root"] / t.STAGE).exists()
    assert [p.name for p in world["live"].rglob(".*.tmp")] == []
    assert (world["live"] / "keep.txt").read_text(encoding="utf-8") == "keep\n"
    assert not (world["live"] / t.DOOMED).exists()


# ------------------------------------------------------------------------------------------------------
# the whole measurement, twice, and the receipt it produced
# ------------------------------------------------------------------------------------------------------

def test_every_boundary_is_accounted_for_and_the_law_holds_twice(tmp_path):
    first = t.measure(tmp_path / "m1")
    second = t.measure(tmp_path / "m2")

    for receipt in (first, second):
        verdict = receipt["verdict"]
        assert [key for key, value in verdict.items() if not value["MET"]] == []
        k2 = verdict["K2_the_durable_record_is_the_commit_point"]
        assert k2["boundaries"] == 10
        assert k2["armed_recovered_to_target"] == len(k2["armed_boundaries"]) == 8
        assert k2["armed_failures"] == []
        assert k2["unarmed_boundaries"] == ["before_journal"]
        assert k2["completed_boundaries"] == ["after_cleanup"]
        assert k2["records_left_behind_after_recovery"] == []
        assert len(k2["crashes_that_left_a_half_applied_tree_before_recovery"]) == 5
        assert verdict["K3_recovery_is_itself_crash_safe"]["runs"] == 56
        assert verdict["K3_recovery_is_itself_crash_safe"]["recovered_to_target"] == 56

    def normalise(receipt: dict, root: pathlib.Path) -> str:
        """The K5 trace names the world's absolute path, which is the trial's, not the law's."""
        return json.dumps(receipt["verdict"], sort_keys=True).replace(str(root), "<world>")

    assert normalise(first, tmp_path / "m1") == normalise(second, tmp_path / "m2")


def test_the_committed_receipt_meets_every_claim(tmp_path):
    receipt = json.loads(RECEIPT.read_text())
    verdict = receipt["verdict"]
    assert [key for key, value in verdict.items() if not value["MET"]] == []
    assert receipt["criteria_were_declared_after_a_prototype_probe"] is False
    refinement = receipt["criterion_refinement_after_the_first_run"]
    assert refinement["no_measured_boundary_was_dropped"] is True
    assert "before_journal" in refinement["what_the_first_run_showed"]
    assert receipt["cost"]["model_calls"] == 0
    assert receipt["cost"]["parameters_stored"] == 0
    assert receipt["cost"]["network_calls_at_run_time"] == 0
    assert len(receipt["control"]) == 9 and len(receipt["recorded"]) == 10
    assert len([row for row in receipt["control"] if row["tree_is_neither"]]) == 5


def test_the_producer_has_no_model_no_parameters_no_network():
    source = pathlib.Path(t.__file__).read_text(encoding="utf-8")
    for forbidden in ("import requests", "import urllib", "import socket", "import torch",
                      "import openai", "from openai", "http://", "https://"):
        assert forbidden not in source, forbidden
    import_lines = [line.split("#")[0].strip() for line in source.splitlines()
                    if line.startswith("import ") or line.startswith("from ")]
    assert import_lines == [
        "from __future__ import annotations",
        "import argparse", "import hashlib", "import json", "import os", "import pathlib",
        "import shutil", "import subprocess", "import sys", "import time",
        "from typing import Any, Sequence",
        "import the_check_mode_is_the_oracle_v1 as cm",
    ]
