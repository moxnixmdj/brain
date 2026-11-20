#!/usr/bin/env python3
"""Measure whether a contrast-bought applicability condition transfers.

Retention is already solved: a stored program replayed on a copied state is
exact. The unsolved part is deciding WHEN to replay it. This tool buys a
requirement with designed contrasts in one real repository, writes only the
computed requirement to the external instant-condition store, reloads that
store from disk, and applies it in a SECOND real repository with zero target
learning executions. The target's own process exit statuses are the oracle.

The target action set is deliberately different: it includes unseen actions
with no store entry. The chooser must refuse them instead of guessing.

Authority NONE. Producer-run measurement, no model calls, no parameters.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import applicability_v1 as APP  # noqa: E402
from canonical.runtime import contrast_selection_v1 as CONTRAST  # noqa: E402
from canonical.runtime import instant_condition_store_v1 as STORE  # noqa: E402
from canonical.tools.the_precondition_is_not_in_the_trace_v1 import (  # noqa: E402
    ACTIONS, APPLIES, build_base, build_states, verdict,
)

SCHEMA = "BRAIN_CONDITION_TRANSFER_ACROSS_ENVIRONMENTS_V1"

BY_NAME = {action.name: action for action in ACTIONS}
#: Actions whose condition is observable in the cheap sensor vocabulary and
#: whose construction is portable across real repositories.
STORED_ACTIONS = (
    "git_stash_pop", "git_merge_abort", "git_rebase_abort",
    "git_checkout_feature", "git_branch_delete_feature", "chmod_exec",
)
#: Target-only actions: no store entry exists, so the only correct behaviour is
#: a refusal. These are real actions, not synthetic placeholders.
UNSEEN_ACTIONS = ("tar_extract", "gzip_decompress", "patch_apply")


def _resolved_commit(base: pathlib.Path) -> str:
    code, out = None, ""
    # The machine helper prefixes git with identity configuration; for a plain
    # read the local command is sufficient and has no network dependency.
    import subprocess
    done = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(base),
                          capture_output=True, text=True)
    code, out = done.returncode, done.stdout.strip()
    return out if code == 0 and out else "UNRESOLVED"


def _index(name: str) -> int:
    import re
    match = re.search(r"(\d+)$", name)
    if not match:
        raise RuntimeError("STATE_NAME_HAS_NO_INDEX:" + name)
    return int(match.group(1))


def _training_and_held(states: Sequence[Any]) -> tuple[list[Any], list[Any]]:
    """First half of EACH class may teach; the last half never does.

    Splitting by even/odd index would put all 'no such branch' negatives in
    training and all 'unmerged branch' negatives in held-out -- an accidental
    construction artifact, not a property of the environment.
    """
    by_class: dict[str, list[Any]] = {}
    for state in states:
        by_class.setdefault(state.name.rsplit("-", 1)[-1].rstrip("0123456789"), []).append(state)
    training: list[Any] = []
    held: list[Any] = []
    for group in by_class.values():
        group.sort(key=lambda state: _index(state.name))
        cut = len(group) // 2
        training.extend(group[:cut])
        held.extend(group[cut:])
    return training, held


def _buy_condition(root: pathlib.Path, action: Any, states: Sequence[Any],
                   *, max_executions: int) -> dict[str, Any]:
    """Use observed facts and process outcomes; return the learned requirement."""
    training, held = _training_and_held(states)
    if not training or not held:
        return {"stage": "REFUSED__NO_TRAIN_OR_HELD", "executions": 0}

    def outcome(state: Any) -> bool:
        result, _note = verdict(state, action, root)
        return result == APPLIES

    first = training[0]
    evidence: list[tuple[list[str], bool]] = [(sorted(first.facts), outcome(first))]
    executions = 1
    boundary = APP.learn(evidence)
    by_signature: dict[frozenset[str], Any] = {}
    for state in training[1:]:
        by_signature.setdefault(frozenset(state.facts), state)
    observed = {frozenset(facts) for facts, _truth in evidence}
    trajectory: list[dict[str, Any]] = []
    while (not boundary.identified and executions < max_executions and by_signature):
        candidates = [sorted(sig) for sig in by_signature if sig not in observed]
        if not candidates:
            trajectory.append({"stop": "NO_UNOBSERVED_REACHABLE_FACT_SIGNATURE"})
            break
        choice = CONTRAST.select_contrast(evidence, candidates)
        if not choice.informative:
            trajectory.append({"stop": choice.reason, "status": choice.status})
            break
        signature = frozenset(choice.state)
        state = by_signature.pop(signature, None)
        if state is None:
            trajectory.append({"stop": "CHOSEN_STATE_ALREADY_OBSERVED"})
            break
        truth = outcome(state)
        evidence.append((sorted(signature), truth))
        observed.add(signature)
        executions += 1
        boundary = APP.learn(evidence)
        trajectory.append({"outcome": truth, "status": boundary.status,
                           "survivors": boundary.survivor_count})

    required = boundary.required if boundary.identified else boundary.most_general
    correct = 0
    for state in held:
        guess = APP.admits(required, state.facts)
        correct += int(guess == outcome(state))
    return {
        "stage": "MEASURED",
        "executions": executions,
        "boundary_status": boundary.status,
        "survivor_count": boundary.survivor_count,
        "required": list(required),
        "successes": boundary.successes,
        "failures": boundary.failures,
        "held_out_accuracy": round(correct / max(1, len(held)), 4),
        "held_out_states": len(held),
        "trajectory": trajectory,
    }


def _score_target(root: pathlib.Path, action: Any, states: Sequence[Any],
                  store: Mapping[str, Any]) -> dict[str, Any]:
    """Zero learning: sense only, then score against the program's own exit status."""
    correct = 0
    false_applies = 0
    missed_applies = 0
    decisions: dict[str, int] = {}
    truth_counts: dict[str, int] = {}
    for state in states:
        truth, _note = verdict(state, action, root)
        applies = truth == APPLIES
        truth_label = "applies" if applies else "does_not_apply"
        truth_counts[truth_label] = truth_counts.get(truth_label, 0) + 1
        decision = STORE.choose(store, action.argv, state.facts)
        label = str(decision["decision"])
        decisions[label] = decisions.get(label, 0) + 1
        if label == STORE.APPLIES:
            correct += int(applies)
            false_applies += int(not applies)
        elif label == STORE.DOES_NOT_APPLY:
            correct += int(not applies)
            missed_applies += int(applies)
        # OPEN is a refusal, never a wrong APPLIES; it is counted in decisions.
    return {
        "action": action.name,
        "in_store": STORE.action_key(action.argv) in store.get("entries", {}),
        "states": len(states),
        "decisions": decisions,
        "truth": truth_counts,
        "correct": correct,
        "accuracy": round(correct / max(1, len(states)), 4),
        "false_applies": false_applies,
        "missed_applies": missed_applies,
    }


def measure(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    root = pathlib.Path(args.root)
    if root.exists() and args.fresh:
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    store_path = pathlib.Path(args.store)
    store = STORE.new_store()
    (root / "source").mkdir(parents=True, exist_ok=True)
    (root / "target").mkdir(parents=True, exist_ok=True)
    source_base = build_base(root / "source", args.source_repo, args.source_commit)
    source_commit = _resolved_commit(source_base)
    source_states = build_states(root / "source", source_base,
                                 per_class=args.per_class, seed=args.source_seed)

    source_rows: list[dict[str, Any]] = []
    learning_executions = 0
    for name in STORED_ACTIONS:
        action = BY_NAME[name]
        learned = _buy_condition(root / "source", action, source_states[name],
                                 max_executions=args.max_contrasts)
        learning_executions += int(learned["executions"])
        if learned["stage"] == "MEASURED":
            STORE.record_one_success(store, action.argv, source_states[name][0].facts,
                                     source={"environment": "source", "repo": args.source_repo,
                                             "commit": source_commit})
            STORE.upsert_rule(
                store, action.argv,
                required=learned["required"],
                condition_status=(STORE.IDENTIFIED if learned["boundary_status"] == APP.IDENTIFIED
                                  else STORE.PROVISIONAL),
                source={"environment": "source", "repo": args.source_repo,
                        "commit": source_commit, "learned": learned},
            )
        source_rows.append({"action": name, **learned})
    STORE.save(store, store_path)
    store_digest = STORE.digest(store)

    # Reload from disk: the target must use only the external store, not the
    # in-memory object that learned in the source environment.
    reloaded = STORE.load(store_path)
    if STORE.digest(reloaded) != store_digest:
        raise RuntimeError("STORE_RELOAD_DIGEST_MISMATCH")

    target_base = build_base(root / "target", args.target_repo, args.target_commit)
    target_commit = _resolved_commit(target_base)
    target_states = build_states(root / "target", target_base,
                                 per_class=args.per_class, seed=args.target_seed)
    target_rows = []
    for name in (*STORED_ACTIONS, *UNSEEN_ACTIONS):
        action = BY_NAME[name]
        target_rows.append(_score_target(root / "target", action, target_states[name], reloaded))

    stored_rows = [row for row in target_rows if row["in_store"]]
    unseen_rows = [row for row in target_rows if not row["in_store"]]
    summary = {
        "source_repo": args.source_repo,
        "source_commit": source_commit,
        "source_seed": args.source_seed,
        "source_actions": len(STORED_ACTIONS),
        "source_learning_executions": learning_executions,
        "source_identified": sum(1 for row in source_rows
                                 if row.get("boundary_status") == APP.IDENTIFIED),
        "target_repo": args.target_repo,
        "target_commit": target_commit,
        "target_seed": args.target_seed,
        "target_actions": len(target_rows),
        "target_stored_actions": len(stored_rows),
        "target_unseen_actions": len(unseen_rows),
        "target_learning_executions": 0,
        "target_evaluation_oracles": sum(row["states"] for row in target_rows),
        "target_stored_accuracy": round(
            sum(row["correct"] for row in stored_rows)
            / max(1, sum(row["states"] for row in stored_rows)), 4),
        "target_stored_false_applies": sum(row["false_applies"] for row in stored_rows),
        "target_unseen_false_applies": sum(row["false_applies"] for row in unseen_rows),
        "target_unseen_open_states": sum(
            row["decisions"].get(STORE.OPEN, 0) for row in unseen_rows),
        "target_unseen_states": sum(row["states"] for row in unseen_rows),
        "store_actions": len(reloaded["entries"]),
        "store_digest": store_digest,
        "model_calls": 0,
        "parameters_stored": 0,
        "seconds": round(time.time() - started, 1),
    }
    receipt = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date": "2026-11-20",
        "claim": ("An applicability requirement bought by contrasts in one real repository "
                  "transfers through an external JSON store to a second real repository with "
                  "zero target learning executions, and unseen actions fail closed."),
        "oracle": "each real program's own exit status; no action label is used for scoring",
        "summary": summary,
        "source_rows": source_rows,
        "target_rows": target_rows,
    }
    if args.receipt:
        receipt_path = pathlib.Path(args.receipt)
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="/tmp/condition-transfer")
    parser.add_argument("--source-repo", default="https://github.com/pypa/packaging.git")
    parser.add_argument("--target-repo", default="https://github.com/pallets/click.git")
    parser.add_argument("--source-commit", default=None)
    parser.add_argument("--target-commit", default=None)
    parser.add_argument("--source-seed", type=int, default=7)
    parser.add_argument("--target-seed", type=int, default=19)
    parser.add_argument("--per-class", type=int, default=8)
    parser.add_argument("--max-contrasts", type=int, default=12)
    parser.add_argument("--store", default=str(STORE.DEFAULT_STORE))
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--fresh", action="store_true", default=True)
    args = parser.parse_args(argv)
    receipt = measure(args)
    print(json.dumps(receipt["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
