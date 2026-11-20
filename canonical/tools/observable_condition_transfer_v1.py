#!/usr/bin/env python3
"""Turn latent preconditions into observable facts, then test transfer.

The prior measurement proved that successes never identify an action's
applicability condition and that tar/gzip/patch validity was outside the cheap
sensor vocabulary. This tool adds the smallest possible repair: three READ-ONLY
probes whose facts enter the same external condition store, then buys and
transfers those conditions to a third real repository with zero target learning
executions. No learner, model, weights or task answers are added.

Authority NONE. Producer-run measurement only.
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
from canonical.runtime import instant_condition_store_v1 as STORE  # noqa: E402
from canonical.runtime import observable_probe_v1 as PROBE  # noqa: E402
from canonical.tools.condition_transfer_across_environments_v1 import (  # noqa: E402
    _buy_condition, _resolved_commit, _score_target,
)
from canonical.tools.the_precondition_is_not_in_the_trace_v1 import (  # noqa: E402
    ACTIONS, APPLIES, build_base, build_states, verdict,
)

SCHEMA = "BRAIN_OBSERVABLE_CONDITION_TRANSFER_V1"
BY_NAME = {action.name: action for action in ACTIONS}

#: Actions whose deciding fact was previously unobservable.
LATENT_ACTIONS = ("tar_extract", "gzip_decompress", "patch_apply")
#: Actions already in the store from the previous measurement; re-scored here
#: to prove the new probe facts did not corrupt existing conditions.
PRESERVED_ACTIONS = ("git_stash_pop", "git_merge_abort", "git_checkout_feature")
#: Present in the target action set but absent from the store: must be refused.
UNSEEN_ACTIONS = ("git_rm_cached_tracked",)
TARGET_ACTIONS = (*LATENT_ACTIONS, *PRESERVED_ACTIONS, *UNSEEN_ACTIONS)

ACTION_PROBE = {
    "tar_extract": "archive_valid",
    "gzip_decompress": "gzip_valid",
    "patch_apply": "patch_applies",
}


def _augment_all(families: Mapping[str, Sequence[Any]]) -> dict[str, list[str]]:
    """Add probe facts only when the probe itself was proved read-only."""
    accepted: dict[str, list[str]] = {}
    for name, states in families.items():
        accepted[name] = []
        for state in states:
            before = set(getattr(state, "facts", ()))
            PROBE.augment(state)
            added = sorted(set(state.facts) - before)
            accepted[name].extend(added)
    return accepted


def _probe_agreement(action_name: str, states: Sequence[Any],
                     root: pathlib.Path) -> dict[str, Any]:
    probe = ACTION_PROBE.get(action_name)
    if not probe:
        return {"probe": None, "states": 0, "agreement": None}
    fact_true = probe + ".valid"
    correct = 0
    for state in states:
        truth, _note = verdict(state, BY_NAME[action_name], root)
        guess = fact_true in state.facts
        correct += int(guess == (truth == APPLIES))
    return {"probe": probe, "states": len(states),
            "agreement": round(correct / max(1, len(states)), 4)}


def measure(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    root = pathlib.Path(args.root)
    if root.exists() and args.fresh:
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "source").mkdir(exist_ok=True)
    (root / "target").mkdir(exist_ok=True)
    store_path = pathlib.Path(args.store)

    prior = STORE.load(store_path) if store_path.exists() else STORE.new_store()
    before_digest = STORE.digest(prior)
    preserved_before = {
        name: dict(prior["entries"].get(STORE.action_key(BY_NAME[name].argv), {}))
        for name in PRESERVED_ACTIONS
    }

    source_base = build_base(root / "source", args.source_repo, args.source_commit)
    source_commit = _resolved_commit(source_base)
    source_states = build_states(root / "source", source_base,
                                 per_class=args.per_class, seed=args.source_seed)
    source_probe_facts = _augment_all(source_states)

    source_rows: list[dict[str, Any]] = []
    learning_executions = 0
    for name in LATENT_ACTIONS:
        action = BY_NAME[name]
        learned = _buy_condition(root / "source", action, source_states[name],
                                 max_executions=args.max_contrasts)
        learning_executions += int(learned["executions"])
        if learned["stage"] == "MEASURED":
            STORE.record_one_success(prior, action.argv, source_states[name][0].facts,
                                     source={"environment": "observable-source",
                                             "repo": args.source_repo, "commit": source_commit})
            STORE.upsert_rule(
                prior, action.argv, required=learned["required"],
                condition_status=(STORE.IDENTIFIED if learned["boundary_status"] == APP.IDENTIFIED
                                  else STORE.PROVISIONAL),
                source={"environment": "observable-source", "repo": args.source_repo,
                        "commit": source_commit, "learned": learned,
                        "probes": sorted(set(source_probe_facts[name]))},
            )
        source_rows.append({"action": name, **learned})
    STORE.save(prior, store_path)
    after_digest = STORE.digest(prior)

    # The target uses only the store reloaded from disk.
    reloaded = STORE.load(store_path)
    if STORE.digest(reloaded) != after_digest:
        raise RuntimeError("STORE_RELOAD_DIGEST_MISMATCH")
    preserved_after = {
        name: dict(reloaded["entries"].get(STORE.action_key(BY_NAME[name].argv), {}))
        for name in PRESERVED_ACTIONS
    }
    preserved_unchanged = preserved_before == preserved_after

    target_base = build_base(root / "target", args.target_repo, args.target_commit)
    target_commit = _resolved_commit(target_base)
    target_states = build_states(root / "target", target_base,
                                 per_class=args.per_class, seed=args.target_seed)
    target_probe_facts = _augment_all(target_states)

    target_rows: list[dict[str, Any]] = []
    for name in TARGET_ACTIONS:
        row = _score_target(root / "target", BY_NAME[name], target_states[name], reloaded)
        row["probe_agreement"] = _probe_agreement(name, target_states[name], root / "target")
        row["probe_facts"] = sorted(set(target_probe_facts[name]))
        target_rows.append(row)

    latent_rows = [row for row in target_rows if row["action"] in LATENT_ACTIONS]
    preserved_rows = [row for row in target_rows if row["action"] in PRESERVED_ACTIONS]
    unseen_rows = [row for row in target_rows if row["action"] in UNSEEN_ACTIONS]
    summary = {
        "source_repo": args.source_repo,
        "source_commit": source_commit,
        "source_seed": args.source_seed,
        "source_latent_actions": len(LATENT_ACTIONS),
        "source_learning_executions": learning_executions,
        "source_exact_identifications": sum(
            1 for row in source_rows if row.get("boundary_status") == APP.IDENTIFIED),
        "target_repo": args.target_repo,
        "target_commit": target_commit,
        "target_seed": args.target_seed,
        "target_actions": len(target_rows),
        "target_learning_executions": 0,
        "target_evaluation_oracles": sum(row["states"] for row in target_rows),
        "latent_action_accuracy": round(
            sum(row["correct"] for row in latent_rows)
            / max(1, sum(row["states"] for row in latent_rows)), 4),
        "latent_false_applies": sum(row["false_applies"] for row in latent_rows),
        "preserved_action_accuracy": round(
            sum(row["correct"] for row in preserved_rows)
            / max(1, sum(row["states"] for row in preserved_rows)), 4),
        "preserved_entries_unchanged": preserved_unchanged,
        "unseen_false_applies": sum(row["false_applies"] for row in unseen_rows),
        "unseen_open_states": sum(row["decisions"].get(STORE.OPEN, 0)
                                  for row in unseen_rows),
        "unseen_states": sum(row["states"] for row in unseen_rows),
        "store_digest_before": before_digest,
        "store_digest_after": after_digest,
        "model_calls": 0,
        "parameters_stored": 0,
        "seconds": round(time.time() - started, 1),
    }
    receipt = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date": "2026-11-20",
        "claim": ("Read-only probes make previously unobservable action preconditions "
                  "observable; the existing external store then buys those conditions in "
                  "one real repository and transfers them to a third with zero target "
                  "learning executions."),
        "oracle": "each real program's own exit status; probes are read-only and digest-checked",
        "summary": summary,
        "source_rows": source_rows,
        "target_rows": target_rows,
    }
    if args.receipt:
        path = pathlib.Path(args.receipt)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="/tmp/observable-condition-transfer")
    parser.add_argument("--source-repo", default="https://github.com/pallets/click.git")
    parser.add_argument("--target-repo", default="https://github.com/psf/requests.git")
    parser.add_argument("--source-commit", default=None)
    parser.add_argument("--target-commit", default=None)
    parser.add_argument("--source-seed", type=int, default=23)
    parser.add_argument("--target-seed", type=int, default=31)
    parser.add_argument("--per-class", type=int, default=8)
    parser.add_argument("--max-contrasts", type=int, default=12)
    parser.add_argument("--store", default=str(STORE.DEFAULT_STORE))
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--fresh", action="store_true", default=True)
    args = parser.parse_args(argv)
    print(json.dumps(measure(args)["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
