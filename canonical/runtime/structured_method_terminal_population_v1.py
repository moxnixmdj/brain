"""Post-freeze population generator for STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001.

Generated cases stay exactly inside the frozen contract boundary: applicable rules
are already normalized and carry their semantic signatures. The generator varies
graph topology, rule order, requirement source kinds, type/dimension signatures,
exclusions, invariants, and opaque operator identities. It does not supply any
hidden graph solution to the candidate.
"""
from __future__ import annotations

import random
from typing import Any

BEHAVIOR_ID = "STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001"
SOURCE_KINDS = ("formula", "constraint", "schema", "standard", "feature_callout")
TYPES = ("number", "integer", "boolean", "string")
DIMS = ("dimensionless", "USD", "mass", "length", "time")


def _meta(r: random.Random) -> tuple[str, str]:
    typ = r.choice(TYPES)
    dim = "dimensionless" if typ in {"boolean", "string"} else r.choice(DIMS)
    return typ, dim


def generate_case(seed: int, index: int) -> dict[str, Any]:
    r = random.Random((int(seed) << 32) ^ int(index))
    input_count = 2 + r.randrange(4)
    rule_count = 2 + r.randrange(10)
    req_count = 2 + r.randrange(5)

    inputs = []
    node_meta: dict[str, tuple[str, str]] = {}
    for i in range(input_count):
        typ, dim = _meta(r)
        nid = f"in_{i}"
        inputs.append({"id": nid, "type": typ, "dimension": dim})
        node_meta[nid] = (typ, dim)

    requirements = []
    applicable_ids: list[str] = []
    for i in range(req_count):
        rid = f"REQ_{i}"
        kind = SOURCE_KINDS[(i + r.randrange(len(SOURCE_KINDS))) % len(SOURCE_KINDS)]
        if i == req_count - 1 and req_count > 2 and index % 3 == 0:
            requirements.append({
                "id": rid,
                "source_kind": kind,
                "status": "excluded",
                "exclusion_reason": f"NORMALIZED_NOT_APPLICABLE_{seed}_{index}_{i}",
            })
        else:
            requirements.append({"id": rid, "source_kind": kind, "status": "applicable"})
            applicable_ids.append(rid)

    rules = []
    available = list(node_meta)
    req_consumers: dict[str, int] = {rid: 0 for rid in applicable_ids}

    for i in range(rule_count):
        arity = 1 if len(available) == 1 else 1 + r.randrange(min(3, len(available)))
        ins = r.sample(available, arity)
        out = f"v_{i}"
        out_type, out_dim = _meta(r)
        consume: list[str] = []
        remaining_slots = rule_count - i
        unconsumed = [rid for rid, n in req_consumers.items() if n == 0]
        must_take = unconsumed[:max(0, len(unconsumed) - (remaining_slots - 1))]
        consume.extend(must_take)
        if applicable_ids and r.random() < 0.7:
            consume.append(r.choice(applicable_ids))
        consume = sorted(set(consume))
        for rid in consume:
            req_consumers[rid] += 1

        inv = []
        if r.random() < 0.6:
            inv.append({
                "kind": f"normalized_invariant_{r.randrange(7)}",
                "statement": f"I({out})::{seed}:{index}:{i}",
            })

        rules.append({
            "id": f"RULE_{i}",
            "operator": f"opaque::normalized::{seed}::{index}::{r.randrange(10**12)}",
            "inputs": ins,
            "input_contracts": [
                {"type": node_meta[n][0], "dimension": node_meta[n][1]} for n in ins
            ],
            "output": out,
            "type": out_type,
            "dimension": out_dim,
            "consumes_requirements": consume,
            "invariants": inv,
        })
        node_meta[out] = (out_type, out_dim)
        available.append(out)

    for rid, n in req_consumers.items():
        if n == 0:
            rules[-1]["consumes_requirements"] = sorted(
                set(rules[-1]["consumes_requirements"] + [rid])
            )

    r.shuffle(rules)
    derived = [f"v_{i}" for i in range(rule_count)]
    output_count = 1 + r.randrange(min(3, len(derived)))
    required_outputs = sorted(r.sample(derived, output_count))

    return {
        "behavior_id": BEHAVIOR_ID,
        "task": {
            "inputs": inputs,
            "requirements": requirements,
            "normalized_rules": rules,
            "required_outputs": required_outputs,
        },
    }


def generate_population(seed: int, count: int) -> list[dict[str, Any]]:
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        raise ValueError("COUNT_MUST_BE_POSITIVE_INTEGER")
    return [generate_case(seed, i) for i in range(count)]
