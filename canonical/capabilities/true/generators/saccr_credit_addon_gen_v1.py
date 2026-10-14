"""Fresh-instance generator for SACCR_CREDIT_ADDON_V1.

Separate from the solver by law: this file must not import the kernel.
Instances cover the kernel's declared scope: linear single-name and index
credit derivatives, 1-8 trades, 1-4 reference entities with consistent
rating per entity, mixed directions, margined and unmargined trades,
maturities from the 10-business-day floor to 30 years, notionals from 1e4
to 1e10 (log-uniform), start dates up to 3 years forward.
"""
from __future__ import annotations

import math
import random

SINGLE_RATINGS = ("AAA", "AA", "A", "BBB", "BB", "B", "CCC")
INDEX_RATINGS = ("IG", "SG")


def generate(rng: random.Random, n: int) -> list[dict]:
    out = []
    for _ in range(n):
        n_entities = rng.randint(1, 4)
        entities = []
        for e in range(n_entities):
            is_index = rng.random() < 0.3
            entities.append({
                "reference": f"ENT_{e}_{rng.randrange(10**6)}",
                "is_index": is_index,
                "credit_rating": rng.choice(INDEX_RATINGS if is_index else SINGLE_RATINGS),
            })
        trades = []
        for _t in range(rng.randint(1, 8)):
            ent = rng.choice(entities)
            start = 0.0 if rng.random() < 0.6 else round(rng.uniform(0.0, 3.0), 4)
            tenor = math.exp(rng.uniform(math.log(10.0 / 250.0), math.log(30.0)))
            margined = rng.random() < 0.4
            trades.append({
                "notional": round(10 ** rng.uniform(4, 10), 2),
                "start": start,
                "end": round(start + tenor, 6),
                "direction": rng.choice((1, -1)),
                "reference": ent["reference"],
                "credit_rating": ent["credit_rating"],
                "is_index": ent["is_index"],
                "margined_mpor": (round(rng.uniform(10.0 / 250.0, 0.5), 4) if margined else None),
            })
        out.append({"trades": trades})
    return out
