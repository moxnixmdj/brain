#!/usr/bin/env python3
"""Generator of unseen contract-violating Python instances.

TRUE_CAPABILITY_TEST_LAW_V1 scores a capability over "unseen instances of a
declared input class".  The Python repair cluster never had a generator, so
it could never be scored at all -- which is why ten capabilities sit at
"bound" and not "proven".

Declared input class:

    a single-module Python file declaring exactly one pure function with a
    postcondition, whose body has been moved away from that contract by
    exactly one operator/constant edit.

Every instance is:

  - deterministic from (seed, index): reproducible, no randomness at proving
    time, so a run can be replayed and checked by anyone
  - contract-violating by construction: a correct oracle MUST find a
    counterexample, which is what makes the oracle itself falsifiable
  - model-free: template plus mutation, with no model anywhere

The contract travels with the instance, so no external answer key is needed:
the oracle checks code against contract mechanically.
"""

from __future__ import annotations

import hashlib

SCHEMA = "PROJECT_BRAIN_PYTHON_CONTRACT_MUTATION_GENERATOR_V1"

# Every mutation is chosen so that the contract is genuinely violated -- a
# mutation that merely reformats the expression would make the oracle
# unfalsifiable, because "no counterexample found" would mean nothing.
FAMILIES = [
    {
        "name": "linear",
        "contract": "post: _ == x * {k}",
        "correct": "x * {k}",
        "mutations": ["x + {k}", "x - {k}", "x * {k1}", "x * {km1}"],
        "ks": list(range(2, 52)),  # 50
    },
    {
        "name": "nonneg",
        "contract": "post: _ >= {k}",
        "correct": "abs(x) + {k}",
        "mutations": ["x + {k}", "-x + {k}", "abs(x) + {km1}"],
        "ks": list(range(0, 30)),  # 30
    },
    {
        "name": "triangular",
        "contract": "post: _ == x * (x + 1) * {k} // 2",
        "correct": "x * (x + 1) * {k} // 2",
        "mutations": ["x * (x + 1) * {k} // 3", "x * (x - 1) * {k} // 2", "x * x * {k} // 2"],
        "ks": list(range(1, 11)),  # 10
    },
    {
        "name": "clamped",
        "contract": "post: _ >= 0 and _ <= {k}",
        "correct": "min(max(x, 0), {k})",
        "mutations": ["max(x, 0)", "min(x, {k})", "min(max(x, 0), {k1})"],
        "ks": list(range(3, 33)),  # 30
    },
    {
        "name": "square_nonneg",
        "contract": "post: _ >= {k}",
        "correct": "x * x + {k}",
        "mutations": ["x * x + {km1}", "-x * x + {k}", "x - x * x + {k}"],
        "ks": list(range(0, 30)),  # 30
    },
]


def _combinations() -> list[tuple]:
    """The full cross product of (family, parameter, mutation).

    Instances are enumerated over this rather than over a modulo cycle, so
    that every combination is reached before any is repeated.  A generator
    that cycles moduli silently repeats a handful of programs and reports
    them as fresh instances -- the defect this replaces.
    """
    combos = []
    for fam in FAMILIES:
        for k in fam["ks"]:
            for m_idx in range(len(fam["mutations"])):
                combos.append((fam, k, m_idx))
    return combos


_COMBINATIONS = _combinations()


def _render(template: str, k: int) -> str:
    return template.format(k=k, k1=k + 1, km1=k - 1)


def instance_at(index: int, seed: int = 0) -> dict:
    """Deterministic instance for `index`.  No randomness, ever."""
    fam, k, m_idx = _COMBINATIONS[(index + seed) % len(_COMBINATIONS)]
    mut = fam["mutations"][m_idx]

    contract = _render(fam["contract"], k)
    expr = _render(mut, k)
    source = (
        f"def f(x: int) -> int:\n"
        f'    """{contract}"""\n'
        f"    return {expr}\n"
    )
    instance_id = hashlib.sha256(f"{seed}:{index}:{source}".encode()).hexdigest()[:16]
    return {
        "schema": SCHEMA,
        "instance_id": instance_id,
        "index": index,
        "family": fam["name"],
        "params": {"k": k},
        "mutation": expr,
        "contract": contract,
        "source": source,
    }


def generate(count: int, seed: int = 0) -> list[dict]:
    """`count` unseen instances of the declared input class."""
    return [instance_at(i, seed) for i in range(count)]


if __name__ == "__main__":  # pragma: no cover
    import json

    for inst in generate(12):
        print(json.dumps(inst, sort_keys=True))
