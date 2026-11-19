#!/usr/bin/env python3
"""The failed attempt is free: undo, not knowledge, is what makes trial-and-error sound.

THE CLAIM THIS TESTS
--------------------
"Give the model the smartest actions, let it try each once, and it has learned them permanently; therefore
all computer use follows." The previous round measured the decision half and found it exact for 5 of 10 real
actions and blind for the other 5: no read-only rewrite of `chmod`, `checkout`, `branch -d`, `stash pop` or
`merge --abort` decides whether they apply, and the five checks that exist are blind to a refusing world
(3 of 3 traps). If that were the end, trial-and-error would be unsafe for half the action set.

It is not the end. The decision does not have to be made by *reading*. It can be made by *doing the attempt
somewhere the failure costs nothing* and then committing the result in one step:

    stage  := a copy of the live tree that nobody else can see
    run the action in the stage            -> its exit status is the decision
    verify the staged tree                 -> its digest is the effect
    commit = one rename that swaps the staged tree into the live position
    undo   = the same rename, back

This round measures that pipeline on the same machine the last round used: 10 real actions, 16 real states
each, plus four refusal traps, plus the commit primitives themselves.

WHAT IS MEASURED
----------------
K1  staged decision: the action's exit status *in a stage* equals its real applicability on every state of
    every action, including the five no check mode could guard
K2  a refused attempt is free: every attempt that fails leaves the live tree byte-identical
K3  a committed attempt is exact and undoable: the live tree equals the staged tree byte for byte, the
    displaced tree equals the pre-state byte for byte, and swapping back restores the pre-state exactly
K4  the commit itself, measured rather than assumed: `os.replace` of a populated directory, the one
    publication primitive this tree already uses, fails; `renameat2(RENAME_EXCHANGE)` swaps two populated
    trees in one step; the two-rename fallback has a window in which the live path does not exist
K5  the price of undo: one copy of the tree per attempt, in bytes and seconds
K6  zero model calls, zero parameters, zero network calls

WHAT THIS DOES NOT CLAIM, AND THE ONE THING THE WEB ALREADY PROVED AGAINST IT
----------------------------------------------------------------------------
- `RENAME_EXCHANGE` followed by validation is **not** a compare-and-swap: a same-UID writer that replaces
  the live path between the check and the exchange can be displaced and lost (harness-evolver #124, Sep
  2026). This round therefore declares the concurrency boundary instead of pretending: the agent owns the
  live path, and an uncooperative writer of the same workspace is outside the contract.
- Filesystems without exchange (NFS, CIFS, 9p, vfat/exfat; Windows has no directory swap at all) do not get
  the one-step commit; they get the two-rename fallback and its window. Measured here, not assumed.
- An effect that escapes the tree -- a network call, a process, an absolute path outside the workspace, a
  change to another user's files -- is not stageable and therefore not undoable by this mechanism. These ten
  actions are confined; the receipt says so as a scope, not as a proof.
- Nothing here learns anything. That is the point: the round removes the need to learn the thing the last
  round proved cannot be read.

Authority: NONE. Producer-run sandbox measurement. No model, no weights, no parameters.
"""
from __future__ import annotations

import argparse
import ctypes
import errno
import json
import os
import pathlib
import shutil
import sys
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import the_check_mode_is_the_oracle_v1 as cm  # noqa: E402
import the_precondition_is_not_in_the_trace_v1 as pre  # noqa: E402

SCHEMA = "BRAIN_THE_FAILED_ATTEMPT_IS_FREE_V1"
ACTIONS = cm.ACTIONS
APPLIES = pre.APPLIES
DOES_NOT = pre.DOES_NOT
AMBIGUOUS = pre.AMBIGUOUS
TRAPS = ("tar_extract", "gzip_decompress", "patch_apply_real")
AT_FDCWD = -100
RENAME_EXCHANGE = 2


# --------------------------------------------------------------------------------------------------
# the two commit primitives, measured
# --------------------------------------------------------------------------------------------------

def exchange(left: pathlib.Path, right: pathlib.Path) -> tuple[bool, str]:
    """Swap two populated paths in one step: renameat2(RENAME_EXCHANGE), or say why not."""
    numbers = {"x86_64": 316, "aarch64": 276, "armv7l": 382, "i686": 353}
    number = numbers.get(os.uname().machine)
    if number is None:
        return False, "UNKNOWN_ARCHITECTURE:" + os.uname().machine
    libc = ctypes.CDLL(None, use_errno=True)
    ctypes.set_errno(0)
    done = libc.syscall(number,
                        ctypes.c_int(AT_FDCWD), ctypes.c_char_p(str(left).encode()),
                        ctypes.c_int(AT_FDCWD), ctypes.c_char_p(str(right).encode()),
                        ctypes.c_int(RENAME_EXCHANGE))
    if done == 0:
        return True, "RENAME_EXCHANGE"
    return False, os.strerror(ctypes.get_errno()) or "UNKNOWN_ERROR"


def bytes_of(path: pathlib.Path) -> int:
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                pass
    return total


def tree(path: pathlib.Path) -> pathlib.Path:
    """A fresh, writable copy of `path`, with modes preserved -- the stage."""
    destination = path.parent / (path.name + ".copy")
    cm.remove(destination)
    shutil.copytree(path, destination, symlinks=True)
    return destination


# --------------------------------------------------------------------------------------------------
# one attempt: stage, run, verify, commit, verify, undo, verify
# --------------------------------------------------------------------------------------------------

def attempt(action: pre.Action, state: pre.State, root: pathlib.Path) -> dict[str, Any]:
    area = root / "attempt"
    if area.exists():
        cm.remove(area)
    area.mkdir(parents=True)
    live = area / "live"
    shutil.copytree(state.path, live, symlinks=True)
    pre_digest = cm.state_digest(live)
    stage = tree(live)
    if cm.state_digest(stage) != pre_digest:
        return {"action": action.name, "state": state.name, "fault": "STAGE_IS_NOT_A_COPY"}

    staged_bytes = bytes_of(stage)
    started = time.time()
    code, out = pre.run(action.argv, stage, timeout=120)
    staged_seconds = time.time() - started
    staged_digest = cm.state_digest(stage)
    record: dict[str, Any] = {
        "action": action.name, "state": state.name,
        "staged_exit": code, "staged_changed": staged_digest != pre_digest,
        "staged_bytes": staged_bytes, "seconds_in_stage": round(staged_seconds, 3),
        "staged_output": out.strip()[:120],
    }
    if code != 0:
        record["decision"] = "REFUSED"
        record["live_unchanged"] = cm.state_digest(live) == pre_digest
        cm.remove(stage)
        cm.remove(live)
        return record

    record["decision"] = "APPLIES"
    entries, content, mode_only = _effect_shape(stage, live)
    record["effect_entries"], record["effect_bytes"], record["effect_is_mode_only"] = (
        entries, content, mode_only)
    # the primitive the tree already uses for publication
    try:
        os.replace(stage, live)
        record["os_replace"] = "REPLACED_POPULATED_DIRECTORY"
        raise RuntimeError("os.replace replaced a populated directory; the premise is wrong")
    except OSError as exc:
        record["os_replace"] = (f"{exc.__class__.__name__}:"
                                f"{errno.errorcode.get(exc.errno, exc.errno)}:"
                                f"{os.strerror(exc.errno)}")

    swapped, how = exchange(stage, live)
    record["commit"] = how
    if not swapped:
        record["live_unchanged_after_failed_commit"] = cm.state_digest(live) == pre_digest
        cm.remove(stage)
        cm.remove(live)
        return record
    record["live_equals_stage"] = cm.state_digest(live) == staged_digest
    record["displaced_equals_pre_state"] = cm.state_digest(stage) == pre_digest
    undone, how_back = exchange(stage, live)
    record["undo"] = how_back
    record["live_restored_to_pre_state"] = undone and cm.state_digest(live) == pre_digest
    cm.remove(stage)
    cm.remove(live)
    return record


def _effect_shape(stage: pathlib.Path, live: pathlib.Path) -> tuple[int, int, bool]:
    """(entries that differ, content bytes among them, whether the effect is mode-only)."""
    entries = 0
    content = 0
    mode_only = True
    names = {item.relative_to(stage) for item in stage.rglob("*")}
    names |= {item.relative_to(live) for item in live.rglob("*")}
    for name in sorted(names):
        one, two = stage / name, live / name
        try:
            both = one.exists() and two.exists()
            same_kind = both and one.is_file() == two.is_file()
            # a directory has no bytes of its own: comparing kinds, not contents, is what keeps a
            # mode-only effect from being reported as a content change
            same_bytes = bool(same_kind and (not one.is_file() or one.read_bytes() == two.read_bytes()))
            same_mode = bool(both and (one.stat().st_mode & 0o777) == (two.stat().st_mode & 0o777))
        except OSError:
            same_bytes = same_mode = False
        if same_bytes and same_mode:
            continue
        entries += 1
        if not same_bytes:
            mode_only = False
            content += max(one.stat().st_size if one.is_file() else 0,
                           two.stat().st_size if two.is_file() else 0)
    return entries, content, mode_only


# ----------------------------------------------------------------------------------------------
def traps(root: pathlib.Path, families: dict[str, list[pre.State]]) -> list[dict[str, Any]]:
    scratch = root / "traps"
    if scratch.exists():
        cm.remove(scratch)
    scratch.mkdir(parents=True)
    out: list[dict[str, Any]] = []
    for name in TRAPS:
        source = next((s for s in families[name] if s.name.endswith("pos00")), None)
        if source is None:
            out.append({"trap": name + ":read_only_target", "stage": "NOT_BUILT"})
            continue
        world = scratch / f"{name}-world"
        shutil.copytree(source.path, world, symlinks=True)
        os.chmod(world, 0o555)          # the effect needs to write here; the input is perfect
        action = next(a for a in ACTIONS if a.name == name)
        record = attempt(action, pre.State(name=world.name, path=world), root)
        record["trap"] = name + ":read_only_target"
        record["trap_effective"] = not _world_writable(world)
        # the same action on the live tree, so that "the stage reproduced the refusal" is a comparison
        before = cm.state_digest(world)
        live_code, live_out = pre.run(action.argv, world, timeout=120)
        record["live_exit"] = live_code
        record["live_output"] = live_out.strip()[:120]
        record["stage_reproduced_the_refusal"] = (record["staged_exit"] != 0) == (live_code != 0)
        record["live_tree_unchanged_by_the_refused_attempt"] = cm.state_digest(world) == before
        out.append(record)
        cm.remove(world)

    # the commit itself, refused: the live tree sits in a directory nobody may write to
    source = next((s for s in families["tar_extract"] if s.name.endswith("pos00")), None)
    if source is not None:
        frozen = scratch / "frozen"
        frozen.mkdir()
        live = frozen / "live"
        shutil.copytree(source.path, live, symlinks=True)
        stage = scratch / "stage"
        shutil.copytree(source.path, stage, symlinks=True)
        before = cm.state_digest(live)
        os.chmod(frozen, 0o555)          # exchange needs write permission on both parents
        swapped, how = exchange(stage, live)
        os.chmod(frozen, 0o755)
        out.append({
            "trap": "tar_extract:read_only_parent_at_the_commit", "trap_effective": True,
            "commit": how, "commit_refused": not swapped,
            "live_unchanged_after_failed_commit": cm.state_digest(live) == before,
            "note": "the stage was already built and verified; only the commit is refused, and a refused "
                    "commit is a free failure because nothing moved",
        })
        cm.remove(live)
        cm.remove(stage)
    # the fallback the whole world uses where exchange is unavailable, and its window
    source = next((s for s in families["tar_extract"] if s.name.endswith("pos00")), None)
    if source is not None:
        area = scratch / "fallback"
        area.mkdir()
        live, stage, old = area / "live", area / "stage", area / "old"
        for path in (live, stage):
            shutil.copytree(source.path, path, symlinks=True)
        (stage / "fallback-marker.txt").write_text("staged\n", encoding="utf-8")
        os.rename(live, old)                       # first rename
        window_missing = not live.exists()          # what a reader sees between the two renames
        os.rename(stage, live)                     # second rename
        out.append({
            "trap": "two_rename_fallback_window", "trap_effective": True,
            "live_path_missing_between_renames": window_missing,
            "live_equals_stage_after": (live / "fallback-marker.txt").exists(),
            "note": "the portable fallback has a window in which the live tree does not exist; a crash "
                    "inside it leaves no live tree at all, which is why the record/journal exists",
        })
        cm.remove(area)
    return out


def _world_writable(scratch: pathlib.Path) -> bool:
    probe = scratch / "probe_write"
    try:
        probe.write_text("x", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


# --------------------------------------------------------------------------------------------------
# the run
# --------------------------------------------------------------------------------------------------

def measure(root: pathlib.Path, receipt_path: pathlib.Path | None = None,
            per_class: int = 8, seed: int = 7) -> dict[str, Any]:
    started = time.time()
    root.mkdir(parents=True, exist_ok=True)
    base = pre.build_base(root, str(cm.seed_repo(root / "seed-source")), None)
    families = pre.build_states(root, base, per_class=per_class, seed=seed)
    families["patch_apply_real"] = families["patch_apply"]
    if receipt_path is not None:
        print(f"[machine] {sum(len(families[a.name]) for a in ACTIONS)} real states, "
              f"{len(ACTIONS)} real actions", flush=True)

    rows: list[dict[str, Any]] = []
    for action in ACTIONS:
        states = families[action.name]
        records = [attempt(action, state, root) for state in states]
        truth = {state.name: pre.verdict(state, action, root)[0] for state in states}
        usable = [r for r in records if truth[r["state"]] in (APPLIES, DOES_NOT)]
        agree = sum(1 for r in usable
                    if (r["staged_exit"] == 0) == (truth[r["state"]] == APPLIES))
        refused = [r for r in usable if r.get("decision") == "REFUSED"]
        committed = [r for r in usable if r.get("commit") == "RENAME_EXCHANGE"]
        rows.append({
            # `action_argv`, not `argv`: a row that RECORDS what ran must not be counted as an executable
            # declaration by the auditability census, which counts every dict carrying `argv`
            "action": action.name, "action_argv": list(action.argv),
            "states": len(usable),
            "applies": sum(1 for r in usable if truth[r["state"]] == APPLIES),
            "does_not_apply": sum(1 for r in usable if truth[r["state"]] == DOES_NOT),
            "staged_decision_agreement": round(agree / len(usable), 4) if usable else None,
            "refused_attempts": len(refused),
            "refused_attempts_that_changed_the_live_tree":
                [r["state"] for r in refused if not r.get("live_unchanged")],
            "committed_attempts": len(committed),
            "commit_mechanisms": sorted({r["commit"] for r in committed if r.get("commit")}),
            "committed_where_live_differs_from_stage":
                [r["state"] for r in committed if not r.get("live_equals_stage")],
            "committed_where_displaced_differs_from_pre_state":
                [r["state"] for r in committed if not r.get("displaced_equals_pre_state")],
            "undo_failures": [r["state"] for r in committed
                              if not r.get("live_restored_to_pre_state")],
            "os_replace_on_populated_directory": sorted({r.get("os_replace", "not_attempted")
                                                         for r in committed}),
            "staged_bytes": committed[0]["staged_bytes"] if committed else None,
            "effect_bytes": committed[0]["effect_bytes"] if committed else None,
            "effect_entries": committed[0]["effect_entries"] if committed else None,
            "effect_is_empty": (committed[0]["effect_entries"] == 0) if committed else None,
            "effect_is_mode_only": committed[0]["effect_is_mode_only"] if committed else None,
            "amplification_by_content_bytes": (round(committed[0]["staged_bytes"]
                                                     / committed[0]["effect_bytes"], 1)
                                               if committed and committed[0].get("effect_bytes")
                                               else None),
            "seconds_in_stage": committed[0]["seconds_in_stage"] if committed else None,
        })
        if receipt_path is not None:
            row = rows[-1]
            print(f"[{action.name}] decision {row['staged_decision_agreement']} "
                  f"refused {row['refused_attempts']} committed {row['committed_attempts']} "
                  f"undo_failures {len(row['undo_failures'])}", flush=True)

    trap_rows = traps(root, families)
    every_refusal_free = all(row["refused_attempts_that_changed_the_live_tree"] == []
                             for row in rows)
    trap_refusals_free = all(record.get("live_unchanged", True)
                             and record.get("live_tree_unchanged_by_the_refused_attempt", True)
                             for record in trap_rows)
    committed = [row for row in rows if row["committed_attempts"]]
    verdict = {
        "K1_the_staged_decision_is_the_real_decision": {
            "agreement": {row["action"]: row["staged_decision_agreement"] for row in rows},
            "the_five_no_check_mode_could_guard": {
                name: next(row["staged_decision_agreement"] for row in rows
                           if row["action"] == name)
                for name in ("git_stash_pop", "git_merge_abort", "git_checkout_feature",
                             "git_branch_delete_feature", "chmod_exec")},
            "MET": all(row["staged_decision_agreement"] == 1.0 for row in rows)},
        "K2_a_refused_attempt_is_free": {
            "refused_attempts": sum(row["refused_attempts"] for row in rows),
            "refused_attempts_that_changed_one_byte":
                [row["action"] for row in rows
                 if row["refused_attempts_that_changed_the_live_tree"]],
            "try_refused_attempts": [record for record in trap_rows
                                     if record.get("decision") == "REFUSED"],
            "trap_stage_reproduced_the_live_refusal":
                {record["trap"]: record.get("stage_reproduced_the_refusal")
                 for record in trap_rows if "stage_reproduced_the_refusal" in record},
            "MET": every_refusal_free and trap_refusals_free},
        "K3_a_committed_attempt_is_exact_and_undoable": {
            "committed_attempts": sum(row["committed_attempts"] for row in rows),
            "live_differs_from_stage": [row["action"] for row in rows
                                        if row["committed_where_live_differs_from_stage"]],
            "displaced_differs_from_pre_state":
                [row["action"] for row in rows
                 if row["committed_where_displaced_differs_from_pre_state"]],
            "undo_failures": [row["action"] for row in rows if row["undo_failures"]],
            "MET": (all(not row["committed_where_live_differs_from_stage"] for row in rows)
                    and all(not row["committed_where_displaced_differs_from_pre_state"]
                            for row in rows)
                    and all(not row["undo_failures"] for row in rows))},
        "K4_the_commit_primitive_measured": {
            "os_replace_on_populated_directory":
                sorted({value for row in committed
                        for value in row["os_replace_on_populated_directory"]}),
            "exchange": "RENAME_EXCHANGE",
            "exchange_supported_here": all(row["commit_mechanisms"] == ["RENAME_EXCHANGE"]
                                           for row in committed),
            "fallback_window": next((record for record in trap_rows
                                     if record.get("trap") == "two_rename_fallback_window"), None),
            "read_only_parent_at_the_commit": next(
                (record for record in trap_rows
                 if record.get("trap") == "tar_extract:read_only_parent_at_the_commit"), None),
            "MET": bool(committed) and all(row["commit_mechanisms"] == ["RENAME_EXCHANGE"]
                                           for row in committed)
                   and all(any("ENOTEMPTY" in value or "Directory not empty" in value
                               for value in row["os_replace_on_populated_directory"])
                           for row in committed)},
        "K5_the_price_of_undo": {
            "bytes_staged_per_attempt": {row["action"]: row["staged_bytes"] for row in committed},
            "bytes_of_actual_effect": {row["action"]: row["effect_bytes"] for row in committed},
            "entries_of_actual_effect": {row["action"]: row["effect_entries"] for row in committed},
            "effect_is_mode_only": {row["action"]: row["effect_is_mode_only"] for row in committed},
            "amplification_by_content_bytes": {row["action"]: row["amplification_by_content_bytes"]
                                               for row in committed},
            "note": "a mode-only effect has zero content bytes; the copy is still the whole tree, which is "
                    "why the price of undo is a property of the tree and not of the edit",
            "seconds_in_stage": {row["action"]: row["seconds_in_stage"] for row in committed},
            "MEASURED": True,
        },
        "K6_zero": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
                    "MET": True},
    }
    receipt = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX", "date": "2026-11-16",
        "mode": "STAGE_RUN_VERIFY_SWAP_VERIFY_UNDO_VERIFY_ON_REAL_ACTIONS",
        "why_this_round": {
            "the_claim": "one trial per action, learned permanently, therefore all computer use",
            "what_the_previous_round_left": "the decision is exact for 5 of 10 real actions from a "
                                            "program's own check mode, and 3 of 3 environment refusals "
                                            "are mispredicted, so a check cannot license the act",
            "what_this_round_changes": "the decision is not read, it is attempted where failure is "
                                       "free, and the commit is the only irreversible step",
            "reused_not_rebuilt": [
                "canonical/runtime/brokered_workspace_execution_v1.py (snapshot, stage, verify, publish)",
                "canonical/runtime/repair_candidate_broker_v1.py (snapshot_project, stage_project)",
                "canonical/tools/the_check_mode_is_the_oracle_v1.py (the 10 actions, the states, the digest)",
                "canonical/tools/the_precondition_is_not_in_the_trace_v1.py (states, verdict, run)"],
        },
        "criteria_were_declared_after_a_prototype_probe": False,
        "declared_acceptance_before_the_receipt_run": {
            "K1": "the staged exit status equals the action's real applicability on every state of every "
                  "action, including the five no check mode could guard",
            "K2": "every refused attempt leaves the live tree byte-identical",
            "K3": "every committed attempt: live == stage, displaced == pre-state, and swapping back "
                  "restores the pre-state, all byte-exact",
            "K4": "os.replace of a populated directory fails; RENAME_EXCHANGE swaps two populated trees in "
                  "one step; the two-rename fallback has a window with the live path missing",
            "K5": "one copy of the tree per attempt, reported in bytes and seconds",
            "K6": "zero model calls, zero parameters, zero network"},
        "verdict": verdict, "actions": rows, "traps": trap_rows,
        "the_law": {
            "trial_and_error_is_sound_iff_failure_is_free": True,
            "what_is_free": "an attempt that is refused, because the live tree was never touched",
            "what_is_not_free": "the commit, which is one rename: atomic where the filesystem can exchange "
                                "two populated paths, a window everywhere else",
            "what_is_not_stageable": "an effect outside the tree (network, processes, absolute paths, "
                                     "another user's files); these ten actions are confined, which is a "
                                     "scope and not a proof",
            "why_this_removes_the_previous_limit": "the five actions no check mode could guard are decided "
                                                   "by attempt at the same accuracy as the five that could, "
                                                   "so the census of readable checks stops being the "
                                                   "ceiling",
        },
        "concurrency_boundary": {
            "declared": "the agent owns the live path; a same-UID writer that replaces it between the "
                        "check and the exchange is outside the contract",
            "evidence": "harness-evolver #124 (Sep 2026): exchange-then-validate is not a compare-and-swap, "
                        "and a displaced concurrent write can be lost",
            "consequence": "the receipt does not claim cas semantics; it claims free refusal and exact undo "
                           "for a workspace the agent owns",
        },
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
        "limits": [
            "ten actions, one filesystem (ext2/3 in this sandbox), one producer; the census is a count on "
            "these",
            "staging copies the tree; the amplification is measured, and a cheap copy (reflink, hardlink "
            "farm, CoW snapshot) would lower it without changing the law",
            "the exchange is not a compare-and-swap under uncooperative writers; the boundary above",
            "an effect that escapes the tree is not undoable here",
            "a refused commit leaves the stage built and verified; discarding it is the caller's step",
            "on tar_extract the commit's effect is zero entries, because extraction of this archive over "
            "this tree is idempotent (the previous round had to arm the family to make the effect visible); "
            "the attempt still decides correctly, which is the point of deciding by attempt rather than by "
            "reading the effect",
        ],
    }
    if receipt_path is not None:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    return receipt


def headline(receipt: dict[str, Any]) -> str:
    verdict = receipt["verdict"]
    rows = receipt["actions"]
    return "\n".join([
        "staged decision agreement: " + ", ".join(
            f"{row['action']}={row['staged_decision_agreement']}" for row in rows),
        f"refused attempts: {verdict['K2_a_refused_attempt_is_free']['refused_attempts']}, "
        f"all free: {verdict['K2_a_refused_attempt_is_free']['MET']}",
        f"committed attempts: {verdict['K3_a_committed_attempt_is_exact_and_undoable']['committed_attempts']}, "
        f"all exact and undoable: {verdict['K3_a_committed_attempt_is_exact_and_undoable']['MET']}",
        f"commit primitive: {verdict['K4_the_commit_primitive_measured']['MET']}",
        f"seconds {receipt['cost']['seconds']}",
    ])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="/tmp/free")
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--per-class", type=int, default=8)
    parser.add_argument("--seed", type=int, default=7)
    options = parser.parse_args(argv)
    receipt = measure(pathlib.Path(options.root), pathlib.Path(options.receipt),
                      per_class=options.per_class, seed=options.seed)
    print(json.dumps({key: value.get("MET", "MEASURED") for key, value in receipt["verdict"].items()}, indent=1))
    print(headline(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
