#!/usr/bin/env python3
"""Test targeted refutation of a PROVISIONAL rule in a fourth real repository.

No new learner is used. One genuine positive state records the support facts
missing from the existing store; one real counterexample in a new repository
then forces a scope change. The repair is computed from the support facts and
the falsifying state's own facts and exit status, or the rule is quarantined.
A dynamic affordance shift is tested by changing the same state and re-sensing,
with no further learning.

Authority NONE. Producer-run measurement only.
"""
from __future__ import annotations

import argparse
import copy
import json
import pathlib
import shutil
import sys
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import instant_condition_store_v1 as STORE  # noqa: E402
from canonical.runtime import observable_probe_v1 as PROBE  # noqa: E402
from canonical.runtime import provisional_repair_v1 as REPAIR  # noqa: E402
from canonical.tools.condition_transfer_across_environments_v1 import (  # noqa: E402
    _resolved_commit, _score_target,
)
from canonical.tools.the_precondition_is_not_in_the_trace_v1 import (  # noqa: E402
    ACTIONS, APPLIES, build_base, build_states, sense, verdict,
)

SCHEMA = "BRAIN_PROVISIONAL_REFUTATION_V1"
BY_NAME = {action.name: action for action in ACTIONS}
REPAIR_ACTION = "git_stash_pop"
PRESERVED_ACTION = "tar_extract"
ACTION_NAMES = (REPAIR_ACTION, PRESERVED_ACTION)


def _all_states(families: Mapping[str, Sequence[Any]]) -> None:
    for states in families.values():
        for state in states:
            PROBE.augment(state)


def _support_for(store: dict[str, Any], repo_root: pathlib.Path,
                 families: Mapping[str, Sequence[Any]]) -> dict[str, Any]:
    """Record facts from one real positive state; do not re-buy the condition."""
    out: dict[str, Any] = {}
    for name in ACTION_NAMES:
        action = BY_NAME[name]
        key = STORE.action_key(action.argv)
        if key not in store["entries"]:
            continue
        chosen = None
        for state in families[name]:
            if not state.name.startswith(name + "-pos"):
                continue
            truth, _note = verdict(state, action, repo_root)
            decision = STORE.choose(store, action.argv, state.facts)
            if truth == APPLIES and decision["applies"] is True:
                chosen = state
                break
        if chosen is None:
            out[name] = {"stage": "REFUSED__NO_MATCHING_POSITIVE_STATE"}
            continue
        REPAIR.attach_support(store, action.argv, chosen.facts,
                              source={"role": "one_real_positive_support_state",
                                      "state": chosen.name})
        out[name] = {"stage": "ATTACHED", "state": chosen.name,
                     "facts": list(chosen.facts)}
    return out


def _make_conflicting_stash(path: pathlib.Path) -> str:
    """Real commands that make `git stash pop` refuse while a stash is present.

    A stash that changes a tracked file is set aside; the same file is then
    changed differently in the worktree. The program itself reports the
    conflict through its exit status. No expected answer is written anywhere.
    """
    import subprocess
    listed = subprocess.run(["git", "ls-files"], cwd=str(path), capture_output=True,
                            text=True, check=True)
    for name in (line.strip() for line in listed.stdout.splitlines() if line.strip()):
        target = path / name
        if not target.is_file():
            continue
        original = target.read_text(encoding="utf-8", errors="replace")
        target.write_text(original + "\n// stashed change\n", encoding="utf-8")
        staged = subprocess.run(["git", "add", "--", name], cwd=str(path),
                                capture_output=True, text=True)
        if staged.returncode:
            continue
        pushed = subprocess.run(["git", "stash", "push", "-q", "-m", "refutation change"],
                                cwd=str(path), capture_output=True, text=True)
        if pushed.returncode == 0:
            target.write_text(original + "\n// conflicting local change\n", encoding="utf-8")
            return name
        target.write_text(original, encoding="utf-8")
    raise RuntimeError("NO_TRACKED_FILE_COULD_STASH")


def _counterexample(root: pathlib.Path, source: Any, action: Any) -> dict[str, Any]:
    """Real state where the stored rule claims APPLIES but the program refuses."""
    target = root / "counterexample"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source.path, target, symlinks=True)
    dirty_file = _make_conflicting_stash(target)
    facts = tuple(sorted(set(sense(target)) | set(PROBE.sense(target))))
    truth, note = verdict(type("State", (), {"path": target, "facts": facts,
                                            "name": "counterexample", "built_by": []})(),
                          action, root)
    return {"facts": list(facts), "applies": truth == APPLIES,
            "note": note[:200], "path": str(target), "dirty_file": dirty_file}


def measure(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    root = pathlib.Path(args.root)
    if root.exists() and args.fresh:
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "source").mkdir(exist_ok=True)
    (root / "target").mkdir(exist_ok=True)
    store_path = pathlib.Path(args.store)
    store = STORE.load(store_path)
    digest_before = STORE.digest(store)

    source_base = build_base(root / "source", args.source_repo, args.source_commit)
    source_commit = _resolved_commit(source_base)
    source_states = build_states(root / "source", source_base,
                                 per_class=args.per_class, seed=args.source_seed)
    _all_states(source_states)
    support = _support_for(store, root / "source", source_states)
    STORE.save(store, store_path)
    digest_with_support = STORE.digest(store)

    target_base = build_base(root / "target", args.target_repo, args.target_commit)
    target_commit = _resolved_commit(target_base)
    target_states = build_states(root / "target", target_base,
                                 per_class=args.per_class, seed=args.target_seed)
    _all_states(target_states)

    before_rows = []
    after_rows = []
    pre_repair_store = copy.deepcopy(store)
    for name in ACTION_NAMES:
        before_rows.append(_score_target(root / "target", BY_NAME[name],
                                         target_states[name], pre_repair_store))

    action = BY_NAME[REPAIR_ACTION]
    positive_state = next(state for state in target_states[REPAIR_ACTION]
                          if state.name.startswith(REPAIR_ACTION + "-pos"))
    counterexample = _counterexample(root / "target", positive_state, action)
    pre_decision = STORE.choose(pre_repair_store, action.argv, counterexample["facts"])
    repair_result = REPAIR.repair(store, action.argv, counterexample["facts"],
                                  counterexample["applies"])
    STORE.save(store, store_path)
    reloaded = STORE.load(store_path)
    if STORE.digest(reloaded) != STORE.digest(store):
        raise RuntimeError("STORE_RELOAD_DIGEST_MISMATCH")
    post_decision = STORE.choose(reloaded, action.argv, counterexample["facts"])

    for name in ACTION_NAMES:
        after_rows.append(_score_target(root / "target", BY_NAME[name],
                                        target_states[name], reloaded))

    # Dynamic shift: the same state is re-sensed after a real mutation, with
    # no learning call between the two decisions.
    clean_facts = tuple(positive_state.facts)
    clean_decision = STORE.choose(reloaded, action.argv, clean_facts)
    dynamic_file = _make_conflicting_stash(positive_state.path)
    dirty_facts = tuple(sorted(set(sense(positive_state.path))
                               | set(PROBE.sense(positive_state.path))))
    dirty_decision = STORE.choose(reloaded, action.argv, dirty_facts)
    dirty_truth, _note = verdict(positive_state, action, root / "target")
    dynamic = {
        "clean_prediction": clean_decision["decision"],
        "dirty_prediction": dirty_decision["decision"],
        "dirty_oracle_applies": dirty_truth == APPLIES,
        "dirty_file": dynamic_file,
        "flipped_without_learning": (
            clean_decision["applies"] is True and dirty_decision["applies"] is False
        ),
    }

    summary = {
        "source_repo": args.source_repo,
        "source_upstream_commit": args.source_commit,
        "source_constructed_head": source_commit,
        "target_repo": args.target_repo,
        "target_upstream_commit": args.target_commit,
        "target_constructed_head": target_commit,
        "target_learning_executions": 0,
        "targeted_refutation_executions": 1,
        "support_acquisition_executions": sum(
            1 for row in support.values() if row.get("stage") == "ATTACHED"),
        "counterexample_pre_prediction": pre_decision["decision"],
        "counterexample_oracle_applies": counterexample["applies"],
        "repair": repair_result["repair"],
        "repair_status": repair_result["status"],
        "required_before": repair_result.get("required_before"),
        "required_after": repair_result.get("required"),
        "counterexample_post_prediction": post_decision["decision"],
        "repair_blocked_counterexample": post_decision["applies"] is False,
        "before_accuracy": {
            row["action"]: row["accuracy"] for row in before_rows
        },
        "after_accuracy": {
            row["action"]: row["accuracy"] for row in after_rows
        },
        "after_false_applies": sum(row["false_applies"] for row in after_rows),
        "dynamic": dynamic,
        "store_digest_before": digest_before,
        "store_digest_with_support": digest_with_support,
        "store_digest_after": STORE.digest(reloaded),
        "model_calls": 0,
        "parameters_stored": 0,
        "seconds": round(time.time() - started, 1),
    }
    receipt = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date": "2026-11-20",
        "claim": ("One real counterexample in a fourth repository narrows a PROVISIONAL "
                  "rule through its recorded support facts, without re-buying the "
                  "condition, while a previously repaired action stays intact."),
        "oracle": "each real program's own exit status; support facts come from real positive states",
        "summary": summary,
        "support_rows": support,
        "counterexample": counterexample,
        "repair_result": repair_result,
        "before_rows": before_rows,
        "after_rows": after_rows,
        "dynamic_shift": dynamic,
    }
    if args.receipt:
        path = pathlib.Path(args.receipt)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="/tmp/provisional-refutation")
    parser.add_argument("--source-repo", default="https://github.com/pallets/click.git")
    parser.add_argument("--target-repo", default="https://github.com/pallets/flask.git")
    parser.add_argument("--source-commit",
                        default="08b803cf32ceb2ae6a772c62d5da42757a897d44")
    parser.add_argument("--target-commit",
                        default="49943b5a94413a530761350f04e896f76e8d620e")
    parser.add_argument("--source-seed", type=int, default=41)
    parser.add_argument("--target-seed", type=int, default=43)
    parser.add_argument("--per-class", type=int, default=8)
    parser.add_argument("--store", default=str(STORE.DEFAULT_STORE))
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--fresh", action="store_true", default=True)
    args = parser.parse_args(argv)
    print(json.dumps(measure(args)["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
