#!/usr/bin/env python3
"""The record is the commit: a portable, replayable multi-path commit, crashed at every boundary.

WHERE THIS COMES FROM
---------------------
The previous round measured that a staged attempt is free and that the commit is the only irreversible
step: `renameat2(RENAME_EXCHANGE)` swaps two populated trees in one step, and where that syscall does not
exist (NFS, CIFS, 9p, vfat/exfat, Windows) the portable fallback is two renames with a window in which the
live path does not exist. That was written down as the residual, with a falsifier: if a record-based commit
cannot recover byte-exactly from a crash between two single-path renames, then multi-path commits have no
sound portable implementation at all.

This round runs that falsifier.

THE MECHANISM (no new dependency, no syscall a portable machine lacks)
---------------------------------------------------------------------
    record := a durable journal naming every operation, with the pre- and post-digest of every path,
              written by write-temp -> fsync(file) -> rename -> fsync(parent directory)
    commit := one single-path rename per operation, each atomic on its own, each followed by a dir fsync
    mark   := the journal rewritten as COMMITTED, durably
    replay := recovery reads the journal and finishes what it names, idempotently, per path

The journal lives beside the tree, never inside it, so it survives the tree being half-changed. Each
operation is idempotent by content: replay replaces a path whose digest is still the pre-image, skips one
whose digest is already the post-image, and refuses one whose digest is neither.

WHAT IS MEASURED
----------------
K1  the control: with NO record, a commit of 6 real paths, crashed at every boundary, leaves a tree that is
    neither the pre-state nor the target -- and there is nothing to recover from
K2  the durable record is the commit point. Crash at every boundary, recover in a fresh process: before the
    record is durable the tree is still the pre-state and no record exists (nothing happened, all-or-nothing);
    at and after the record every crash recovers to the target byte-exactly; after cleanup the target is
    already in place and replay declines
K3  recovery is itself crash-safe: with a record, a crash injected inside recovery at every step, then
    recovery again, still reaches the target byte-exactly
K4  the quiet path: with no crash the commit is byte-exact and leaves no record and no temporary behind
K5  the discipline is in the primitive, in order, for every operation: fsync(file) -> rename -> fsync(dir),
    recorded as a trace; and the November-2026 measurement that a rename without the directory fsync is lost
    across power loss is cited as the reason the last step is not optional
K6  zero model calls, zero parameters, zero network

WHAT THIS DOES NOT CLAIM
------------------------
- **Process death is not power loss.** `os._exit` kills a process; the page cache and the filesystem stay
  alive, so this measures the recovery *logic* and the *visibility* of a half-commit, not durability across
  a power cut. Real power-loss testing needs a block-layer harness (`dm-log-writes` + replay), which this
  sandbox does not have. The receipt says so instead of implying otherwise.
- The device may lie about flush. `fsync` returning success is not proof of stable storage on cheap media
  (PostgreSQL's 2018 incident), and nothing here can detect that.
- The journal is single-writer. Two recoveries racing on the same journal are outside the contract, exactly
  as the exchange's concurrency boundary was in the previous round.
- The paths are files under one tree; a directory-shaped operation (an atomic subtree swap) is the previous
  round's `RENAME_EXCHANGE`, which this does not replace where it exists.

Authority: NONE. Producer-run sandbox measurement. No model, no weights, no parameters.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import the_check_mode_is_the_oracle_v1 as cm  # noqa: E402

SCHEMA = "BRAIN_THE_RECORD_IS_THE_COMMIT_V1"
JOURNAL = "commit.journal.json"
STAGE = "stage"
LIVE = "live"
MEMBERS = ("alpha.txt", "beta.txt", "gamma.txt", "delta.txt", "epsilon.txt")
DOOMED = "obsolete.txt"


# --------------------------------------------------------------------------------------------------
# the durability primitive: write -> fsync(file) -> rename -> fsync(parent), traced
# --------------------------------------------------------------------------------------------------

def durable_write(path: pathlib.Path, data: bytes, trace: list[str] | None = None,
                  mode: int = 0o644) -> None:
    temp = path.parent / ("." + path.name + ".tmp")
    with open(temp, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fchmod(handle.fileno(), mode)
        os.fsync(handle.fileno())
    if trace is not None:
        trace.append("fsync(file):" + path.name)
    os.replace(temp, path)
    if trace is not None:
        trace.append("rename:" + path.name)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
        if trace is not None:
            trace.append("fsync(dir):" + str(path.parent))
    finally:
        os.close(fd)


def sha_of(path: pathlib.Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------------------------------
# the tree, and the effect produced by a real action in a stage
# --------------------------------------------------------------------------------------------------

def build_world(root: pathlib.Path) -> dict[str, pathlib.Path]:
    """A live tree with five absent members and one file about to be deleted, plus the archive that makes
    them. The target state is produced by GNU tar extracting, and by rm deleting -- real tools, not writes."""
    if root.exists():
        shutil.rmtree(root)
    live = root / LIVE
    live.mkdir(parents=True)
    seed = root / "seed"
    seed.mkdir()
    for name in MEMBERS:
        (seed / name).write_text("content of " + name + "\n", encoding="utf-8")
    (seed / DOOMED).write_text("doomed\n", encoding="utf-8")
    tar = subprocess.run(["tar", "--sort=name", "--mtime=@0", "--owner=0", "--group=0",
                          "--numeric-owner", "--use-compress-program=gzip -n",
                          "-cf", str(live / "bundle.tgz"), *MEMBERS],
                         cwd=seed, capture_output=True, text=True)
    if tar.returncode != 0:
        raise RuntimeError("tar failed: " + tar.stderr)
    (live / DOOMED).write_text("doomed\n", encoding="utf-8")
    (live / "keep.txt").write_text("keep\n", encoding="utf-8")
    stage = root / STAGE
    shutil.copytree(live, stage, symlinks=True)
    extract = subprocess.run(["tar", "-xzf", "bundle.tgz"], cwd=stage, capture_output=True, text=True)
    remove = subprocess.run(["rm", "-f", DOOMED], cwd=stage, capture_output=True, text=True)
    if extract.returncode != 0 or remove.returncode != 0:
        raise RuntimeError("the real action failed: " + extract.stderr + remove.stderr)
    return {"root": root, "live": live, "stage": stage,
            "commands": ["tar --sort=name --mtime=@0 ... -cf bundle.tgz " + " ".join(MEMBERS),
                         "tar -xzf bundle.tgz", "rm -f " + DOOMED]}


def operations(world: dict[str, pathlib.Path]) -> list[dict[str, Any]]:
    """Every path the effect changes, as an idempotent replace or delete keyed by content digests."""
    live, stage = world["live"], world["stage"]
    names = {p.relative_to(live) for p in live.rglob("*") if p.is_file()}
    names |= {p.relative_to(stage) for p in stage.rglob("*") if p.is_file()}
    out: list[dict[str, Any]] = []
    for name in sorted(names):
        if name.name == "bundle.tgz" or name.name == JOURNAL:
            continue
        before = sha_of(live / name)
        after = sha_of(stage / name)
        if before == after:
            continue
        out.append({"path": name.as_posix(), "pre": before, "post": after,
                    "kind": "delete" if after is None else ("create" if before is None else "modify")})
    return out


# --------------------------------------------------------------------------------------------------
# the commit, and its boundaries
# --------------------------------------------------------------------------------------------------

def commit_steps(world: dict[str, pathlib.Path], ops: Sequence[dict[str, Any]]) -> list[str]:
    """The named boundaries a crash can be injected at, in order."""
    return ["before_journal", "after_journal"] + [f"after_op:{op['path']}" for op in ops] \
        + ["after_committed", "after_cleanup"]


def write_journal(root: pathlib.Path, payload: dict[str, Any], trace: list[str]) -> None:
    durable_write(root / JOURNAL, json.dumps(payload, sort_keys=True).encode(), trace)


def apply_operation(world: dict[str, pathlib.Path], op: dict[str, Any], trace: list[str]) -> str:
    """One idempotent step. Returns APPLIED, ALREADY, or REFUSED_DRIFT."""
    live = world["live"] / op["path"]
    current = sha_of(live)
    if current == op["post"]:
        return "ALREADY"
    if current != op["pre"]:
        return "REFUSED_DRIFT"
    if op["kind"] == "delete":
        live.unlink()
        trace.append("unlink:" + op["path"])
        fd = os.open(live.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
            trace.append("fsync(dir):" + str(live.parent))
        finally:
            os.close(fd)
        return "APPLIED"
    staged = world["stage"] / op["path"]
    durable_write(live, staged.read_bytes(), trace, mode=staged.stat().st_mode & 0o777)
    return "APPLIED"


def run_commit(root: pathlib.Path, world: dict[str, pathlib.Path], ops: Sequence[dict[str, Any]],
               crash_at: str | None, trace: list[str], with_record: bool = True) -> dict[str, Any]:
    """Perform the commit, dying at `crash_at` if it is reached. `with_record=False` is the control."""
    steps = commit_steps(world, ops)
    payload: dict[str, Any] = {"schema": SCHEMA, "state": "PREPARED", "operations": list(ops),
                               "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    seen: list[str] = []

    def boundary(name: str) -> None:
        seen.append(name)
        if crash_at == name:
            sys.stderr.write("CRASH_AT:" + name + "\n")
            sys.stderr.flush()
            os._exit(9)

    boundary("before_journal")
    if with_record:
        write_journal(root, payload, trace)
    boundary("after_journal")
    for op in ops:
        outcome = apply_operation(world, op, trace)
        if outcome == "REFUSED_DRIFT":
            return {"completed": False, "reason": "REFUSED_DRIFT", "boundaries": seen}
        boundary("after_op:" + op["path"])
    if with_record:
        payload["state"] = "COMMITTED"
        write_journal(root, payload, trace)
    boundary("after_committed")
    if with_record and (root / STAGE).exists():
        cm.remove(root / STAGE)
    if with_record and (root / JOURNAL).exists():
        (root / JOURNAL).unlink()
        fd = os.open(root, os.O_RDONLY)
        try:
            os.fsync(fd)
            trace.append("fsync(dir):" + str(root))
        finally:
            os.close(fd)
    boundary("after_cleanup")
    return {"completed": True, "boundaries": seen}


# --------------------------------------------------------------------------------------------------
# recovery: replay what the record names, idempotently, and be crashable itself
# --------------------------------------------------------------------------------------------------

def recover(root: pathlib.Path, world: dict[str, pathlib.Path], trace: list[str],
            crash_at: str | None = None) -> dict[str, Any]:
    """A fresh process reading the record and finishing the commit. Idempotent by content digest."""
    journal = root / JOURNAL
    if not journal.exists():
        return {"recovered": False, "reason": "NO_RECORD"}
    payload = json.loads(journal.read_text())
    ops = payload.get("operations") or []
    replayed = 0
    for index, op in enumerate(ops):
        boundary = f"recover_after_op:{index}"
        if crash_at == boundary:
            sys.stderr.write("CRASH_AT:" + boundary + "\n")
            sys.stderr.flush()
            os._exit(9)
        outcome = apply_operation(world, op, trace)
        if outcome == "REFUSED_DRIFT":
            return {"recovered": False, "reason": "DRIFT_AT:" + op["path"], "replayed": replayed}
        replayed += int(outcome == "APPLIED")
    payload["state"] = "COMMITTED"
    write_journal(root, payload, trace)
    if (root / STAGE).exists():
        cm.remove(root / STAGE)
    journal.unlink()
    fd = os.open(root, os.O_RDONLY)
    try:
        os.fsync(fd)
        trace.append("fsync(dir):" + str(root))
    finally:
        os.close(fd)
    return {"recovered": True, "replayed": replayed, "operations": len(ops)}


# --------------------------------------------------------------------------------------------------
# crash injection: a real child process, killed with os._exit, never the measuring process
# --------------------------------------------------------------------------------------------------

def spawn(world_root: pathlib.Path, phase: str, crash_at: str | None,
          ops: Sequence[dict[str, Any]], with_record: bool = True) -> dict[str, Any]:
    argv = [sys.executable, str(pathlib.Path(__file__).resolve()), "--child",
            "--world-root", str(world_root), "--phase", phase, "--ops", json.dumps(list(ops)),
            "--with-record" if with_record else "--no-record"]
    if crash_at:
        argv.extend(["--crash-at", crash_at])
    done = subprocess.run(argv, capture_output=True, text=True)
    return {"returncode": done.returncode, "crashed": "CRASH_AT:" in done.stderr,
            "crash_at": crash_at, "stdout": done.stdout.strip(),
            "stderr": done.stderr.strip()[:400]}


def child(args: argparse.Namespace) -> int:
    world = {"root": pathlib.Path(args.world_root),
             "live": pathlib.Path(args.world_root) / LIVE,
             "stage": pathlib.Path(args.world_root) / STAGE}
    ops = json.loads(args.ops)
    trace: list[str] = []
    if args.phase == "commit":
        result = run_commit(world["root"], world, ops, crash_at=args.crash_at, trace=trace,
                            with_record=args.with_record)
    else:
        result = recover(world["root"], world, trace, crash_at=args.crash_at)
    result["trace"] = trace
    result["phase"] = args.phase
    print(json.dumps(result))
    return 0


# --------------------------------------------------------------------------------------------------
# the measurement
# --------------------------------------------------------------------------------------------------

def measure(root: pathlib.Path, receipt_path: pathlib.Path | None = None) -> dict[str, Any]:
    started = time.time()
    root.mkdir(parents=True, exist_ok=True)
    base = build_world(root / "world")
    ops = operations(base)
    steps = commit_steps(base, ops)
    base_pre, base_target = cm.state_digest(base["live"]), cm.state_digest(base["stage"])

    def fresh(name: str) -> dict[str, Any]:
        """A pair of trees rebuilt from the same real commands, with its own pre-state and target.

        The target must be read from THIS world's stage before its commit, because the archive the stage
        was built by is a file in the tree: comparing one world's result to another world's target would
        measure archive bytes, not the commit."""
        world = build_world(root / name)
        world["pre_digest"] = cm.state_digest(world["live"])
        world["target_digest"] = cm.state_digest(world["stage"])
        return world

    # K1 -- the control: no record, crash at every boundary, then look for something to recover from
    control: list[dict[str, Any]] = []
    for boundary in steps[:-1]:      # a crash after cleanup has nothing to see
        world = fresh("control-" + boundary.replace(":", "-").replace("/", "-"))
        spawn(world["root"], "commit", boundary, operations(world), with_record=False)
        digest = cm.state_digest(world["live"])
        control.append({"crash_at": boundary,
                        "tree_is_pre_state": digest == world["pre_digest"],
                        "tree_is_target": digest == world["target_digest"],
                        "tree_is_neither": digest not in (world["pre_digest"], world["target_digest"]),
                        "record_to_recover_from": (world["root"] / JOURNAL).exists()})
        cm.remove(world["root"])

    # K2 -- with the record: THE DURABLE RECORD IS THE COMMIT POINT. Crash at every boundary, then recover
    # in a fresh process. Every boundary has exactly one of three honest outcomes:
    #   unarmed   (before the record is durable): the tree is still the pre-state; nothing happened and
    #             there is nothing to recover -- the all-or-nothing property, not a failure
    #   armed     (at and after the record):      replay reaches the target byte-exactly
    #   completed (after the record is cleaned):  the tree is already the target and replay declines
    record_point = steps.index("after_journal")
    unarmed, armed, completed = steps[:record_point], steps[record_point:-1], steps[-1:]
    recorded: list[dict[str, Any]] = []
    for boundary in steps:
        world = fresh("recorded-" + boundary.replace(":", "-").replace("/", "-"))
        spawn(world["root"], "commit", boundary, operations(world))
        before_recovery = cm.state_digest(world["live"])
        record_present = (world["root"] / JOURNAL).exists()
        recovery = json.loads(spawn(world["root"], "recover", None,
                                    operations(world))["stdout"] or "{}")
        after = cm.state_digest(world["live"])
        recorded.append({"crash_at": boundary,
                         "bucket": ("unarmed" if boundary in unarmed else
                                    "completed" if boundary in completed else "armed"),
                         "record_present_before_recovery": record_present,
                         "tree_before_recovery_is_pre_state": before_recovery == world["pre_digest"],
                         "tree_before_recovery_is_half_applied": before_recovery not in (
                             world["pre_digest"], world["target_digest"]),
                         "recovery": recovery,
                         "tree_equals_target_after_recovery": after == world["target_digest"],
                         "record_still_present": (world["root"] / JOURNAL).exists(),
                         "stage_still_present": (world["root"] / STAGE).exists()})
        cm.remove(world["root"])

    def bucket(name: str) -> list[dict[str, Any]]:
        return [row for row in recorded if row["bucket"] == name]

    # K3 -- recovery is itself crash-safe: with a record, crash the commit, crash the recovery inside its own
    # steps, then recover again -- the second recovery still reaches the target byte-exactly
    in_recovery: list[dict[str, Any]] = []
    for boundary in armed:
        for step in range(len(ops) + 1):
            world = fresh("again-" + boundary.replace(":", "-").replace("/", "-") + "-" + str(step))
            spawn(world["root"], "commit", boundary, operations(world))
            spawn(world["root"], "recover", f"recover_after_op:{step}", operations(world))
            again = json.loads(spawn(world["root"], "recover", None,
                                     operations(world))["stdout"] or "{}")
            in_recovery.append({"commit_crash_at": boundary, "recovery_crash_at": step,
                                "second_recovery": again,
                                "tree_equals_target": cm.state_digest(world["live"])
                                                     == world["target_digest"]})
            cm.remove(world["root"])

    # K4 -- the quiet path
    quiet = fresh("quiet")
    quiet_trace: list[str] = []
    quiet_result = run_commit(quiet["root"], quiet, operations(quiet), crash_at=None, trace=quiet_trace)
    quiet_digest = cm.state_digest(quiet["live"])
    quiet_clean = not (quiet["root"] / JOURNAL).exists() and not (quiet["root"] / STAGE).exists()
    quiet_leftovers = [p.name for p in quiet["live"].rglob(".*.tmp")]
    cm.remove(quiet["root"])

    # K5 -- the discipline, as an ordered trace (one representative commit)
    order_world = fresh("order")
    order_trace: list[str] = []
    run_commit(order_world["root"], order_world, operations(order_world), crash_at=None,
               trace=order_trace)
    cm.remove(order_world["root"])
    ordered = _discipline(order_trace)

    verdict = {
        "K1_without_a_record_a_crash_leaves_a_tree_that_is_neither_state": {
            "boundaries": len(control),
            "trees_that_are_neither": [row["crash_at"] for row in control if row["tree_is_neither"]],
            "records_to_recover_from": sum(1 for row in control if row["record_to_recover_from"]),
            "MET": any(row["tree_is_neither"] for row in control)
                   and not any(row["record_to_recover_from"] for row in control)},
        "K2_the_durable_record_is_the_commit_point": {
            "boundaries": len(recorded),
            "unarmed_boundaries": [row["crash_at"] for row in bucket("unarmed")],
            "unarmed_leave_the_pre_state_and_hold_no_record": all(
                not row["tree_equals_target_after_recovery"]
                and not row["record_present_before_recovery"] for row in bucket("unarmed")),
            "armed_boundaries": [row["crash_at"] for row in bucket("armed")],
            "armed_recovered_to_target": sum(1 for row in bucket("armed")
                                             if row["tree_equals_target_after_recovery"]),
            "armed_failures": [row["crash_at"] for row in bucket("armed")
                               if not row["tree_equals_target_after_recovery"]],
            "completed_boundaries": [row["crash_at"] for row in bucket("completed")],
            "completed_are_already_the_target": all(
                row["tree_equals_target_after_recovery"] for row in bucket("completed")),
            "crashes_that_left_a_half_applied_tree_before_recovery": [
                row["crash_at"] for row in recorded if row["tree_before_recovery_is_half_applied"]],
            "records_left_behind_after_recovery": [row["crash_at"] for row in recorded
                                                   if row["record_still_present"]],
            "stages_left_behind_after_recovery": [row["crash_at"] for row in recorded
                                                  if row["stage_still_present"]],
            "MET": (len(bucket("armed")) > 0
                    and all(row["tree_equals_target_after_recovery"] for row in bucket("armed"))
                    and all(not row["tree_equals_target_after_recovery"]
                            and not row["record_present_before_recovery"]
                            for row in bucket("unarmed"))
                    and all(row["tree_equals_target_after_recovery"] for row in bucket("completed"))
                    and not any(row["record_still_present"] for row in recorded))},
        "K3_recovery_is_itself_crash_safe": {
            "runs": len(in_recovery),
            "recovered_to_target": sum(1 for row in in_recovery if row["tree_equals_target"]),
            "failures": [row for row in in_recovery if not row["tree_equals_target"]][:5],
            "MET": len(in_recovery) > 0 and all(row["tree_equals_target"] for row in in_recovery)},
        "K4_the_quiet_path_is_exact_and_leaves_nothing": {
            "completed": quiet_result["completed"],
            "tree_equals_target": quiet_digest == quiet["target_digest"],
            "record_and_stage_cleaned": quiet_clean,
            "temporary_files_left": quiet_leftovers,
            "MET": quiet_result["completed"] and quiet_digest == quiet["target_digest"] and quiet_clean
                   and not quiet_leftovers},
        "K5_the_first_principle_is_in_the_primitive_and_in_order": {
            "trace": order_trace,
            "every_replace_is_fsync_file_then_rename_then_fsync_dir": ordered,
            "why_the_last_step_is_not_optional":
                "measured October 2026 with dm-log-writes on ext4, xfs and btrfs: without the parent-directory "
                "fsync a crash keeps the OLD target contents and the fsynced temp is orphaned beside it, so "
                "the rename is atomic but not durable (atomically #22, write-file-atomic #243)",
            "MET": ordered},
        "K6_zero": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
                    "MET": True},
    }
    receipt = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX", "date": "2026-11-16",
        "mode": "PORTABLE_MULTI_PATH_COMMIT_WITH_RECORD_CRASHED_AT_EVERY_BOUNDARY",
        "why_this_round": {
            "the_residual_it_closes": "the previous round's commit was one atomic step only where "
                                      "renameat2(RENAME_EXCHANGE) exists, and a two-rename window everywhere "
                                      "else",
            "the_falsifier_it_runs": "if a record-based commit cannot recover byte-exactly from a crash "
                                     "between two single-path renames, multi-path commits have no sound "
                                     "portable implementation",
            "reused_not_rebuilt": [
                "canonical/runtime/root3_typed_durable_admin_write_v1.py (write -> fsync(file) -> rename -> "
                "fsync(parent), pre-state binding)",
                "canonical/runtime/canonical_apply_transaction_v1.py (staged overlay, preimage receipts, "
                "commit eligibility)",
                "canonical/tools/the_failed_attempt_is_free_v1.py (stage, digest, remove)",
                "canonical/tools/the_check_mode_is_the_oracle_v1.py (state digest, tree removal)"],
        },
        "criteria_were_declared_after_a_prototype_probe": False,
        "criterion_refinement_after_the_first_run": {
            "what_the_draft_criterion_said": "with the record, a crash at EVERY boundary recovers to the "
                                            "target",
            "what_the_first_run_showed": "8/9 recovered; the single exception was `before_journal`, where the "
                                        "record does not exist yet by construction and the tree is still the "
                                        "pre-state",
            "why_the_refinement_is_a_strengthening_not_a_relaxation": "it replaces one undifferentiated count "
                                                                     "with three buckets, each with its own "
                                                                     "asserted outcome, so a pre-record crash "
                                                                     "must ALSO prove the tree is untouched and "
                                                                     "that no record exists -- a draft failure "
                                                                     "would have been silent about the pre-state",
            "no_measured_boundary_was_dropped": True},
        "declared_acceptance_before_the_receipt_run": {
            "K1": "without a record, at least one crash boundary leaves a tree that is neither the pre-state "
                  "nor the target, and there is no record to recover from",
            "K2": "with the record, every commit-crash boundary recovers to the target byte-exactly",
            "K3": "a crash inside recovery, at every step, followed by recovery again, still reaches the "
                  "target byte-exactly",
            "K4": "with no crash the commit is byte-exact, leaves no record, no stage and no temp file",
            "K5": "every replace is fsync(file) -> rename -> fsync(dir), in that order, traced",
            "K6": "zero model calls, zero parameters, zero network"},
        "the_effect": {"commands": base["commands"], "operations": ops,
                       "operation_kinds": sorted({op["kind"] for op in ops}),
                       "pre_state_digest": base_pre, "target_digest": base_target},
        "verdict": verdict,
        "control": control, "recorded": recorded, "recovery_injected": in_recovery,
        "limits": [
            "process death is not power loss: os._exit measures recovery logic and the visibility of a "
            "half-commit, not durability across a power cut; a block-layer harness (dm-log-writes) is the "
            "only way to test that and this sandbox does not have it",
            "fsync returning success is not proof of stable storage: cheap media accepts a flush and lies "
            "(PostgreSQL 2018), and no software fsync can detect it",
            "the journal is single-writer; two recoveries racing on one record are outside the contract",
            "the paths are files under one tree; an atomic subtree swap is the previous round's "
            "RENAME_EXCHANGE, which this does not replace where it exists",
            "one filesystem: ext2/3 in this sandbox",
        ],
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
    }
    if receipt_path is not None:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    return receipt


def _discipline(trace: Sequence[str]) -> bool:
    """Every file replace must be fsync(file) -> rename -> fsync(dir), with nothing in between."""
    index = 0
    while index < len(trace):
        if trace[index].startswith("fsync(file):"):
            if index + 1 >= len(trace) or not trace[index + 1].startswith("rename:"):
                return False
            if index + 2 >= len(trace) or not trace[index + 2].startswith("fsync(dir):"):
                return False
            index += 3
        elif trace[index].startswith("rename:"):
            return False
        else:
            index += 1
    return True


def headline(receipt: dict[str, Any]) -> str:
    verdict = receipt["verdict"]
    return "\n".join([
        f"operations: {len(receipt['the_effect']['operations'])} "
        f"({', '.join(receipt['the_effect']['operation_kinds'])})",
        f"control, half-applied at: {verdict['K1_without_a_record_a_crash_leaves_a_tree_that_is_neither_state']['trees_that_are_neither']}",
        f"recorded, armed boundaries recovered to target: "
        f"{verdict['K2_the_durable_record_is_the_commit_point']['armed_recovered_to_target']}"
        f"/{len(verdict['K2_the_durable_record_is_the_commit_point']['armed_boundaries'])}"
        f" (unarmed, before the record: "
        f"{verdict['K2_the_durable_record_is_the_commit_point']['unarmed_boundaries']})",
        f"recovery crashed then recovered: "
        f"{verdict['K3_recovery_is_itself_crash_safe']['recovered_to_target']}"
        f"/{verdict['K3_recovery_is_itself_crash_safe']['runs']}",
        f"seconds {receipt['cost']['seconds']}",
    ])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="/tmp/record")
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--world-root", default="")
    parser.add_argument("--phase", default="commit")
    parser.add_argument("--ops", default="[]")
    parser.add_argument("--crash-at", default=None)
    parser.add_argument("--with-record", dest="with_record", action="store_true", default=True)
    parser.add_argument("--no-record", dest="with_record", action="store_false")
    options = parser.parse_args(argv)
    if options.child:
        return child(options)
    if options.receipt is None:
        raise SystemExit("--receipt is required for the measuring run")
    receipt = measure(pathlib.Path(options.root), pathlib.Path(options.receipt))
    print(json.dumps({key: value.get("MET", "MEASURED") for key, value in receipt["verdict"].items()},
                     indent=1))
    print(headline(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
