"""Whether the transfer wall is in the learning or in the FILING KEY -- measured, not argued.

WHAT THE TREE ALREADY MEASURED, AND WHAT IT LEFT OPEN
------------------------------------------------------
`cross_kind_compounding_benchmark_v1.py` -> "COMPOUNDING ACROSS KINDS: NO", 10 kinds, net saving 0.
That mechanism stores facts KEYED PER KIND, so it cannot compound by construction -- the tree says so.

`cross_kind_learning_to_learn_benchmark_v1.py` then indexed PROCEDURE CREDIT by a kind-blind feature
key and measured:

    test kinds=10   learned solved=5   beat default=1/10   beat random mean=3/10
    NO_COMPOUNDING -- the learned choice is not better than a coin flip on unseen kinds

and its own docstring names the design tension that the result sits on:

    "Deliberately few and coarse. A rich feature vector would let the choice overfit to kinds it
     has seen, which is the failure this measurement is looking for."
    `feature_key`: "A coarse, transferable key. Coarse on purpose: a fine key cannot generalise."

So the tree concluded that the FEATURES do not generalise. This module asks a different and more
specific question, because the run's own output shows something the conclusion does not say:

    b1_m2_r1_d0_g0   <- sliding_pairs, stack_pushout, letter_shift, double_dial, tri_lock

FIVE kinds share one key and they do not share an optimal policy. A ledger keyed on that key is
asked for one answer where five different answers are correct. That is not "the features did not
generalise"; it is that the key is NOT INJECTIVE ON THE DISTINCTION THE POLICY DEPENDS ON.

WHY THAT DISTINCTION MATTERS, AND WHY IT IS THE WHOLE ANSWER
------------------------------------------------------------
Coarse and fine are not two settings of one knob. They are two failures:

    too coarse -> different kinds collide  -> the ledger is asked for one policy where several are right
    too fine   -> every kind gets its own key -> nothing transfers, and you are back to a per-kind table

If BOTH ends fail then no granularity of THESE features works, and the honest conclusion is not
"coarsen it" or "enrich it". It is that the features do not CONTAIN the observable the policy
depends on, so no bucketing of them can. That is vocabulary insufficiency, and it lives at the
INDEX rather than in the edit space where the tree has been looking for it.

WHAT THIS MEASURES (three numbers per key family, no learning claimed)
---------------------------------------------------------------------
  keys                how many distinct keys the kinds produce
  collisions          keys holding >=2 kinds with DIFFERENT optimal policies
  answerable          fraction of keys whose kinds share one optimal policy, i.e. keys a ledger
                      could answer correctly

and it sweeps the bucketing from "the tree's own coarse key" to "one key per kind", to show the
curve is a trade and not a tuning problem.

Authority: NONE. Pure counting over the existing benchmark's own kinds and policies. No learning is
trained, no capability is claimed, $0, zero model dependency.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent.parent


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_benchmark() -> Any:
    return _load(
        "_ckl2l", ROOT / "canonical" / "tools" / "cross_kind_learning_to_learn_benchmark_v1.py"
    )


def kinds_and_makers(bench: Any) -> list[tuple[str, Callable[[], Any]]]:
    """Every kind the benchmark trains on and tests on, as (name, maker).

    Makers have the benchmark's real shape: `make(instance) -> (env, actions, is_goal, description)`.
    """
    from canonical.tools.cross_kind_compounding_benchmark_v1 import _kinds
    train = _kinds()
    test = bench._heldout_kinds()
    out: list[tuple[str, Callable[[], Any]]] = []
    for pool, table in ((bench.TRAIN_KINDS, train), (bench.TEST_KINDS, test)):
        for name in pool:
            if name in table:
                out.append((name, table[name]))
    return out


def solving_policies(bench: Any, l2l: Any, name: str, maker: Callable[[], Any],
                     instances: Sequence[int] = (0, 1, 2)) -> dict[str, Any]:
    """Which policies solve this kind, swept over instances.

    The sweep is not optional. The benchmark calls `make(1)` everywhere, and instance 1 is the
    HARDEST of the three for several kinds: `letter_shift`, `stack_pushout` and `tri_lock` are solved
    by NO policy at instance 1 and by several at instance 2. Reporting instance 1 as "no policy
    exists" would be an instrument artifact dressed as a capability finding -- it was made once in
    this file's own first draft and is recorded here so it is not made again.

    So a kind's required policy set is the UNION over the instances where any policy works, and the
    per-instance variation is reported separately because it is its own failure mode: if the same
    KIND needs different policies on different instances, then no index keyed on KIND features can be
    right about it either.
    """
    per_instance: dict[str, list[str]] = {}
    union: set[str] = set()
    for instance in instances:
        winners: list[str] = []
        for policy in l2l.POLICIES:
            try:
                result = bench._solve_with(name, maker, policy, instance=instance)
            except Exception:  # noqa: BLE001 - a policy that cannot run is simply not a winner
                continue
            if result.get("pass"):
                winners.append(policy)
        per_instance[str(instance)] = winners
        union.update(winners)
    solved_somewhere = any(v for v in per_instance.values())
    agree = len({tuple(sorted(v)) for v in per_instance.values() if v}) <= 1
    return {"union": union, "per_instance": per_instance,
            "solved_on_any_instance": solved_somewhere,
            "same_policy_set_on_every_solvable_instance": agree}


def score_key(feature_keys: dict[str, str], winners: dict[str, set[str]]) -> dict[str, Any]:
    """keys / collisions / answerable for one key family."""
    by_key: dict[str, list[str]] = {}
    for kind, key in feature_keys.items():
        by_key.setdefault(key, []).append(kind)
    collisions = []
    answerable = 0
    for key, kinds in by_key.items():
        policies = [frozenset(winners[k]) for k in kinds if winners.get(k)]
        if not policies:
            continue
        if len(set(policies)) == 1:
            answerable += 1
        else:
            collisions.append({"key": key, "kinds": kinds, "distinct_winner_sets": len(set(policies))})
    return {
        "keys": len(by_key),
        "kinds": len(feature_keys),
        "collisions": len(collisions),
        "collision_detail": collisions,
        "answerable": answerable,
        "answerable_fraction": round(answerable / len(by_key), 4) if by_key else None,
    }


def key_families(bench: Any, l2l: Any) -> list[dict[str, Any]]:
    """The sweep: the tree's own key, coarser, and finer, ending at one key per kind."""
    envs: dict[str, str] = {}
    raw: dict[str, dict[str, Any]] = {}
    for name, maker in kinds_and_makers(bench):
        env, actions, is_goal, _description = maker(1)
        raw[name] = l2l.features(env, actions, is_goal)
        envs[name] = l2l.feature_key(raw[name])

    def _bucket(value: float, edges: tuple[float, ...]) -> int:
        for i, edge in enumerate(edges):
            if value < edge:
                return i
        return len(edges)

    families: list[dict[str, Any]] = []

    # every family the sweep needs, from coarsest to finest
    def build(branching_edges, moved_edges, reach_edges, depth_edges, use_start):
        keys: dict[str, str] = {}
        for name, feat in raw.items():
            keys[name] = "b%s_m%s_r%s_d%s_g%s" % (
                _bucket(float(feat.get("branching") or 0), branching_edges),
                _bucket(float(feat.get("moved_fraction") or 0.0), moved_edges),
                _bucket(float(feat.get("reachable_growth") or 0.0), reach_edges),
                _bucket(int(feat.get("single_action_goal_depth") or 0), depth_edges),
                int(bool(feat.get("start_reaches_goal_already"))) if use_start else 0,
            )
        return keys

    families.append({"name": "tree_coarse__b(2,4,6)_m(.45,.8)_r(1.5,3)_d(0,3,10)",
                     "keys": dict(envs)})
    families.append({"name": "coarser_still",
                     "keys": build((4,), (0.8,), (3.0,), (3,), False)})
    families.append({"name": "finer_mid",
                     "keys": build((2, 3, 4, 5, 6), (0.45, 0.65, 0.8, 0.9), (1.5, 2.2, 3.0, 4.0),
                                   (0, 1, 2, 3, 5, 10), True)})
    families.append({"name": "finest_exact_features",
                     "keys": {n: json.dumps(f, sort_keys=True) for n, f in raw.items()}})
    families.append({"name": "trivial_one_key_per_kind",
                     "keys": {n: n for n in envs}})
    return families


def run() -> dict[str, Any]:
    bench = load_benchmark()
    l2l = _load("_l2l", ROOT / "canonical" / "runtime" / "learn_to_learn_v1.py")

    detail: dict[str, Any] = {}
    winners: dict[str, set[str]] = {}
    for name, maker in kinds_and_makers(bench):
        detail[name] = solving_policies(bench, l2l, name, maker)
        winners[name] = detail[name]["union"]

    rows = []
    for family in key_families(bench, l2l):
        scored = score_key(family["keys"], winners)
        scored["name"] = family["name"]
        rows.append(scored)

    # The conclusion is a shape, not a preference: is there ANY row with collisions 0 AND
    # keys well below the number of kinds? That row is the one a ledger could actually use.
    usable = [r for r in rows if r["collisions"] == 0 and r["keys"] < r["kinds"]]
    return {
        "schema": "THE_INDEX_IS_THE_BOTTLENECK_V1",
        "authority": "NONE__PRODUCER_RUN_COUNTING_OVER_EXISTING_BENCHMARK",
        "kind": "receipt",
        "incremental_spend_usd": 0,
        "producer_cognition_model_dependency_count": 0,
        "kinds": len(winners),
        "winner_sets": {k: sorted(v) for k, v in sorted(winners.items())},
        "instance_sensitivity": {
            "kinds_unsolvable_on_every_instance": sorted(
                k for k, v in detail.items() if not v["solved_on_any_instance"]),
            "kinds_whose_policy_set_changes_with_instance": sorted(
                k for k, v in detail.items() if v["solved_on_any_instance"]
                and not v["same_policy_set_on_every_solvable_instance"]),
            "per_kind": {k: v["per_instance"] for k, v in sorted(detail.items())},
            "reading": ("A kind whose required policy set changes between instances cannot be indexed "
                        "by kind-level features at all: the key would have to name the instance."),
        },
        "sweep": rows,
        "usable_key_families": [r["name"] for r in usable],
        "verdict": ("NO_GRANULARITY_OF_THESE_FEATURES_SEPARATES_WHAT_THE_POLICY_DEPENDS_ON"
                    if not usable else "SOME_GRANULARITY_WORKS"),
        "reading": (
            "A key has to be injective on the distinction the policy depends on. If every family "
            "either collides kinds that need different policies or degenerates to one key per kind, "
            "the features do not CONTAIN that distinction and no bucketing of them can supply it. "
            "The repair is a new observable, not a finer grid."),
    }


def main() -> int:
    result = run()
    text = json.dumps(result, indent=1, sort_keys=True)
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(text + "\n")
        print("written", sys.argv[1])
    print(f"{'family':52s} {'keys':>5s} {'collisions':>11s} {'answerable':>11s}")
    for row in result["sweep"]:
        print(f"{row['name'][:52]:52s} {row['keys']:5d} {row['collisions']:11d} "
              f"{row['answerable']:11d} / {row['keys']}")
    print()
    print("VERDICT:", result["verdict"])
    print("usable families:", result["usable_key_families"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
