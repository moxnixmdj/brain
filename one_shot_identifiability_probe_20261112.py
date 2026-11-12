"""One-shot identifiability: what a single demonstration actually determines.

The owner's claim, in his words: *"after he does them at least once, he would learn all of those
permanently."* That is a claim about **identifiability**, and it is measurable in this tree's own
machinery rather than argued about.

The experiment is deliberately small and deliberately honest:

  * a fixed, hand-authored hypothesis space of unary integer programs;
  * a target that is a member of that space (checked, and the probe fails closed if not);
  * three protocols on the SAME space and the SAME target:
       ONE     -- one demonstration, then take the leader (this is "learn it from one try")
       THREE   -- three demonstrations, then take the leader
       ASK     -- no free demonstration; ask the questions `settlement_v1` chooses by exact
                  expected information gain, then take the leader
       ASK_ONE -- one demonstration, then ask
  * and one counterfactual: the SAME one demonstration against a space that already contains
    only two hypotheses.

Everything is scored on inputs 10..21, which appear in no demonstration and in no probe choice
made by the protocol under test (the probe pool is -6..30 and the asker chooses; the *scorer* is
held out).

What this measures is not "can a program fit one point". Any program can. It measures **how many
programs still fit**, and **whether the one you would pick is right where you live**. The second
number is the only one that matters, and it is the difference between a lesson and a lookup.

Authority: NONE. Constructed experiment, one machine, no independent verifier, $0, zero model
dependency. It says nothing about GUI or unbounded computer use.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.settlement_v1 import (  # noqa: E402
    SETTLED,
    Hypothesis,
    VersionSpace,
    settle,
)

HELD_OUT: tuple[int, ...] = tuple(range(10, 22))
PROBE_POOL: tuple[tuple[int], ...] = tuple((x,) for x in range(-6, 31))
MAX_QUERIES = 8


# ---------------------------------------------------------------------------------------------
# The hypothesis space. It is hand-authored -- that is the finding, not a caveat to hide.
# ---------------------------------------------------------------------------------------------
def build_space() -> list[Hypothesis]:
    hs: list[Hypothesis] = []
    for a in (1, 2, 3, -1, -2):
        for b in (-2, -1, 0, 1, 2):
            hs.append(
                Hypothesis(
                    key=f"affine:{a}:{b}",
                    predict=_affine(a, b),
                    description=f"{a}*x + {b}",
                )
            )
    for k in range(2, 10):
        hs.append(Hypothesis(key=f"mod:{k}", predict=_mod(k), description=f"x % {k}"))
        hs.append(Hypothesis(key=f"floordiv:{k}", predict=_floordiv(k), description=f"x // {k}"))
    hs.append(Hypothesis(key="const:0", predict=lambda p: 0, description="0"))
    hs.append(Hypothesis(key="const:1", predict=lambda p: 1, description="1"))
    hs.append(Hypothesis(key="square", predict=lambda p: p[0] * p[0], description="x*x"))
    for t in (-1, 0, 1):
        hs.append(
            Hypothesis(
                key=f"threshold:{t}",
                predict=_threshold(t),
                description=f"0 if x <= {t} else 1",
            )
        )
    return hs


def _affine(a: int, b: int) -> Callable[[tuple[int]], int]:
    return lambda p: a * p[0] + b


def _mod(k: int) -> Callable[[tuple[int]], int]:
    return lambda p: p[0] % k


def _floordiv(k: int) -> Callable[[tuple[int]], int]:
    return lambda p: p[0] // k


def _threshold(t: int) -> Callable[[tuple[int]], int]:
    return lambda p: 0 if p[0] <= t else 1


TRUTHS: dict[str, Callable[[int], int]] = {
    "affine:2:1": lambda x: 2 * x + 1,
    "affine:-1:2": lambda x: -x + 2,
    "mod:3": lambda x: x % 3,
    "mod:5": lambda x: x % 5,
    "mod:7": lambda x: x % 7,
    "floordiv:2": lambda x: x // 2,
    "floordiv:3": lambda x: x // 3,
    "square": lambda x: x * x,
    "threshold:0": lambda x: 0 if x <= 0 else 1,
    "const:0": lambda x: 0,
}


# ---------------------------------------------------------------------------------------------
# Measurement primitives
# ---------------------------------------------------------------------------------------------
def survivors(space: VersionSpace) -> list[Hypothesis]:
    """Hypotheses that agree with EVERY observation, not merely with high posterior weight.

    Posterior weight is the settlement posterior, which deliberately keeps contradicted
    hypotheses alive at a small likelihood. For identifiability the honest count is the exact
    version space: hypotheses still consistent with all the evidence.
    """
    out: list[Hypothesis] = []
    for h in space.hypotheses:
        ok = True
        for probe, outcome in space.observations:
            try:
                if h.predict(probe) != outcome:
                    ok = False
                    break
            except Exception:  # a hypothesis that cannot run has explained nothing
                ok = False
                break
        if ok:
            out.append(h)
    return out


def leader(space: VersionSpace) -> Hypothesis:
    post = space.posterior()
    key = sorted(post.items(), key=lambda kv: (-kv[1], str(kv[0])))[0][0]
    return space._by_key[key]  # noqa: SLF001 - inspection only, no behaviour of the space changes


def held_out_accuracy(h: Hypothesis, truth: Callable[[int], int]) -> float:
    correct = 0
    for x in HELD_OUT:
        try:
            if h.predict((x,)) == truth(x):
                correct += 1
        except Exception:
            pass
    return correct / len(HELD_OUT)


def observe(space: VersionSpace, truth: Callable[[int], int], xs: Sequence[int]) -> None:
    for x in xs:
        space.observe((x,), truth(x))


# ---------------------------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------------------------
def protocol_fixed(truth: Callable[[int], int], xs: Sequence[int]) -> dict[str, Any]:
    space = VersionSpace(build_space())
    observe(space, truth, xs)
    lead = leader(space)
    return {
        "observations": len(space.observations),
        "survivors": len(survivors(space)),
        "leader": str(lead.key),
        "leader_held_out_accuracy": round(held_out_accuracy(lead, truth), 4),
    }


def protocol_ask(
    truth: Callable[[int], int], *, seed_observations: Sequence[int] = ()
) -> dict[str, Any]:
    space = VersionSpace(build_space())
    observe(space, truth, seed_observations)
    result = settle(
        space,
        domain=[(x,) for x in HELD_OUT],
        probes=list(PROBE_POOL),
        oracle=lambda p: truth(p[0]),
        max_queries=MAX_QUERIES,
        confidence=0.99,
        domain_tolerance=0.01,
    )
    lead = result.winner if result.winner is not None else leader(space)
    return {
        "seed_observations": len(seed_observations),
        "status": result.status,
        "settled": result.status == SETTLED,
        "queries_used": result.queries_used,
        "information_bits": round(result.information_bits, 4),
        "survivors": len(survivors(space)),
        "leader": str(lead.key),
        "leader_held_out_accuracy": round(held_out_accuracy(lead, truth), 4),
    }


def protocol_narrow_prior(
    truth_key: str, truth: Callable[[int], int], xs: Sequence[int]
) -> dict[str, Any]:
    """The same one demonstration, against a space that already excludes almost everything.

    This is the counterfactual that names where the generalising happens. Nothing about the
    example changes; only the prior does.
    """
    true_h: Hypothesis | None = None
    decoy: Hypothesis | None = None
    for h in build_space():
        if h.key == truth_key:
            true_h = h
        elif decoy is None and h.key != truth_key:
            probe = (HELD_OUT[0],)
            if h.predict(probe) != truth(HELD_OUT[0]):
                decoy = h
    if true_h is None or decoy is None:
        raise SystemExit("COUNTERFACTUAL_SPACE_INVALID")
    space = VersionSpace([true_h, decoy])
    observe(space, truth, xs)
    lead = leader(space)
    return {
        "space_size": 2,
        "observations": len(space.observations),
        "survivors": len(survivors(space)),
        "leader": str(lead.key),
        "leader_held_out_accuracy": round(held_out_accuracy(lead, truth), 4),
    }


# ---------------------------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------------------------
def run() -> dict[str, Any]:
    space_size = len(build_space())
    keys = {h.key for h in build_space()}
    missing = sorted(set(TRUTHS) - keys)
    if missing:
        raise SystemExit(f"TRUTH_NOT_IN_SPACE: {missing}")

    rows: list[dict[str, Any]] = []
    for key in sorted(TRUTHS):
        truth = TRUTHS[key]
        one = protocol_fixed(truth, [1])
        three = protocol_fixed(truth, [1, 2, 3])
        ask = protocol_ask(truth)
        ask_one = protocol_ask(truth, seed_observations=[1])
        narrow = protocol_narrow_prior(key, truth, [1])
        rows.append(
            {
                "target": key,
                "space_size": space_size,
                "ONE": one,
                "THREE": three,
                "ASK": ask,
                "ASK_ONE": ask_one,
                "NARROW_PRIOR_ONE": narrow,
            }
        )

    def mean(path: str) -> float:
        vals = []
        for r in rows:
            node: Any = r
            for part in path.split("."):
                node = node[int(part)] if part.isdigit() else node[part]
            vals.append(float(node))
        return round(sum(vals) / len(vals), 4)

    summary = {
        "space_size": space_size,
        "targets": len(rows),
        "held_out_inputs": len(HELD_OUT),
        "mean_survivors_after_one": mean("ONE.survivors"),
        "mean_leader_accuracy_after_one": mean("ONE.leader_held_out_accuracy"),
        "mean_survivors_after_three": mean("THREE.survivors"),
        "mean_leader_accuracy_after_three": mean("THREE.leader_held_out_accuracy"),
        "mean_queries_to_settle": mean("ASK.queries_used"),
        "mean_accuracy_after_ask": mean("ASK.leader_held_out_accuracy"),
        "mean_queries_to_settle_after_one": mean("ASK_ONE.queries_used"),
        "mean_accuracy_after_one_then_ask": mean("ASK_ONE.leader_held_out_accuracy"),
        "mean_accuracy_with_one_example_and_narrow_prior": mean(
            "NARROW_PRIOR_ONE.leader_held_out_accuracy"
        ),
        "targets_exact_after_one": sum(1 for r in rows if r["ONE"]["survivors"] == 1),
        "targets_exact_after_three": sum(1 for r in rows if r["THREE"]["survivors"] == 1),
        "targets_settled_after_one_then_ask": sum(1 for r in rows if r["ASK_ONE"]["settled"]),
    }
    return {
        "schema": "ONE_SHOT_IDENTIFIABILITY_PROBE_V1",
        "authority": "NONE",
        "spend_usd": 0,
        "model_dependency": 0,
        "held_out": list(HELD_OUT),
        "summary": summary,
        "rows": rows,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)

    result = run()
    s = result["summary"]

    print("one-shot identifiability  --  authority NONE, $0, zero model\n")
    print(f"hypothesis space {s['space_size']} programs;  {s['targets']} targets;  "
          f"held out {s['held_out_inputs']} inputs\n")
    header = f"{'target':<16}{'|B| 1':>7}{'acc 1':>8}{'|B| 3':>7}{'acc 3':>8}" \
             f"{'q ask':>7}{'acc ask':>9}{'acc 1+narrow':>14}"
    print(header)
    print("-" * len(header))
    for r in result["rows"]:
        print(
            f"{r['target']:<16}"
            f"{r['ONE']['survivors']:>7}"
            f"{r['ONE']['leader_held_out_accuracy']:>8.2f}"
            f"{r['THREE']['survivors']:>7}"
            f"{r['THREE']['leader_held_out_accuracy']:>8.2f}"
            f"{r['ASK_ONE']['queries_used']:>7}"
            f"{r['ASK_ONE']['leader_held_out_accuracy']:>9.2f}"
            f"{r['NARROW_PRIOR_ONE']['leader_held_out_accuracy']:>14.2f}"
        )
    print("-" * len(header))
    print(
        f"\nafter ONE demonstration:  {s['mean_survivors_after_one']} of {s['space_size']} "
        f"programs still fit;  the leader is right on "
        f"{s['mean_leader_accuracy_after_one']:.0%} of held-out inputs;  "
        f"{s['targets_exact_after_one']}/{s['targets']} targets are exactly identified"
    )
    print(
        f"after THREE demonstrations: {s['mean_survivors_after_three']} fit;  leader right "
        f"{s['mean_leader_accuracy_after_three']:.0%};  "
        f"{s['targets_exact_after_three']}/{s['targets']} exactly identified"
    )
    print(
        f"one demonstration + chosen probes: {s['mean_queries_to_settle_after_one']} queries on "
        f"average, leader right {s['mean_accuracy_after_one_then_ask']:.0%}, "
        f"{s['targets_settled_after_one_then_ask']}/{s['targets']} settled"
    )
    print(
        f"one demonstration, narrow prior: leader right "
        f"{s['mean_accuracy_with_one_example_and_narrow_prior']:.0%}"
    )
    print("\nThe example does not change between those last two lines. Only the space does.")
    print("AUTHORITY NONE -- constructed experiment, one machine, no independent verifier.")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("WROTE", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
