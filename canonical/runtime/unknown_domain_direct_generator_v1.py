"""Information-safe generator for the two frozen Unknown-Domain direct leaves.

The generator family is frozen before candidate requalification.  Actual case
instances require a post-freeze beacon that is never passed to the candidate.
The candidate receives only source-domain verified primitive tables, target
public observations, an opaque target query, and allowed safe probes.

This module does not execute the candidate and grants no fresh-reality authority.
"""
from __future__ import annotations

import hashlib
import itertools
import random
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_CASESET_V1"

PRIMITIVES = {
    "P_X": {(0, 0): 0, (0, 1): 1, (1, 0): 1, (1, 1): 0},
    "P_A": {(0, 0): 0, (0, 1): 0, (1, 0): 0, (1, 1): 1},
}

_FEATURE_TOKEN_BANK = [
    (("amber", "cobalt"), ("moss", "quartz"), ("quiet", "loud")),
    (("lumen", "vanta"), ("cedar", "opal"), ("dry", "wet")),
    (("north", "south"), ("dawn", "dusk"), ("open", "closed")),
    (("ivory", "onyx"), ("reed", "stone"), ("low", "high")),
]


class DirectCaseError(ValueError):
    pass


def _seed(beacon: str) -> int:
    if not isinstance(beacon, str) or len(beacon) < 16:
        raise DirectCaseError("POST_FREEZE_BEACON_INVALID")
    digest = hashlib.sha256(("UNKNOWN_DOMAIN_DIRECT_V1|" + beacon).encode()).digest()
    return int.from_bytes(digest[:16], "big")


def _target_table(source_table: Mapping[tuple[int, int], int], *, swap: int, inv0: int, inv1: int, out_inv: int):
    out = {}
    for t0, t1 in itertools.product((0, 1), repeat=2):
        raw = [t0 ^ inv0, t1 ^ inv1]
        s0, s1 = (raw[1], raw[0]) if swap else (raw[0], raw[1])
        out[(t0, t1)] = int(source_table[(s0, s1)]) ^ out_inv
    return out


def _render_input(surface: Mapping[str, Any], bits: tuple[int, int]) -> dict[str, str]:
    return {
        surface["features"][0]["name"]: surface["features"][0]["tokens"][bits[0]],
        surface["features"][1]["name"]: surface["features"][1]["tokens"][bits[1]],
    }


def _render_output(surface: Mapping[str, Any], bit: int) -> str:
    return surface["output_tokens"][int(bit)]


def _all_transforms():
    for swap, inv0, inv1, out_inv in itertools.product((0, 1), repeat=4):
        yield {"swap": swap, "inv0": inv0, "inv1": inv1, "out_inv": out_inv}


def _predict(source_table, transform, bits):
    table = _target_table(source_table, **transform)
    return table[bits]


def _survivors(source_primitives, observations):
    survivors = []
    for source in source_primitives:
        table = {tuple(map(int, k.split(","))): int(v) for k, v in source["canonical_table"].items()}
        for tr in _all_transforms():
            good = True
            for bits, out_bit in observations:
                if _predict(table, tr, bits) != out_bit:
                    good = False
                    break
            if good:
                survivors.append((source["id"], tr, table))
    return survivors


def _probe_gain(survivors, query, probe):
    if not survivors:
        return False
    before = {_predict(table, tr, query) for _, tr, table in survivors}
    if len(before) <= 1:
        return False
    groups = {}
    for sid, tr, table in survivors:
        p = _predict(table, tr, probe)
        groups.setdefault(p, []).append((sid, tr, table))
    if len(groups) <= 1:
        return False
    for group in groups.values():
        after = {_predict(table, tr, query) for _, tr, table in group}
        if len(after) > 1:
            return False
    return True


def _source_rows(relevant_id: str):
    distractor_id = "P_A" if relevant_id == "P_X" else "P_X"
    rows = []
    for sid in (relevant_id, distractor_id):
        table = PRIMITIVES[sid]
        rows.append({
            "id": sid,
            "canonical_table": {f"{a},{b}": int(table[(a, b)]) for a, b in itertools.product((0, 1), repeat=2)},
            "verification_receipt": {
                "receipt_id": "source-receipt-" + sid,
                "independent_verified": True,
                "exact_byte_bound": True,
                "conclusion": "success",
                "primitive_id": sid,
            },
        })
    return rows


def _surface(rng: random.Random, case_index: int):
    bank = _FEATURE_TOKEN_BANK[case_index % len(_FEATURE_TOKEN_BANK)]
    suffix = hashlib.sha256(f"{case_index}|{rng.random()}".encode()).hexdigest()[:6]
    return {
        "features": [
            {"name": "f_" + suffix + "_a", "tokens": list(bank[0])},
            {"name": "f_" + suffix + "_b", "tokens": list(bank[1])},
        ],
        "output_tokens": list(bank[2]),
    }


def _select_layout(source_rows, target_table, mode):
    points = list(itertools.product((0, 1), repeat=2))
    obs_sizes = (1, 2, 3) if mode == "IDENTIFIABLE_TRANSFER" else (1, 2)
    for n in obs_sizes:
        for obs_points in itertools.combinations(points, n):
            observations = [(p, target_table[p]) for p in obs_points]
            survivors = _survivors(source_rows, observations)
            if not survivors:
                continue
            for query in points:
                if query in obs_points:
                    continue
                preds = {_predict(table, tr, query) for _, tr, table in survivors}
                source_ids = {sid for sid, _, _ in survivors}
                remaining = [p for p in points if p not in obs_points and p != query]
                valid_probes = [p for p in remaining if _probe_gain(survivors, query, p)]
                if mode == "IDENTIFIABLE_TRANSFER":
                    relevant = source_rows[0]["id"]
                    if len(preds) == 1 and source_ids == {relevant}:
                        return observations, query, []
                elif mode == "NONIDENTIFIABLE_ABSTAIN":
                    if len(preds) > 1:
                        return observations, query, []
                elif mode == "UNDERSPECIFIED_REQUEST_DISCRIMINATOR":
                    if len(preds) > 1 and valid_probes:
                        return observations, query, valid_probes
    raise DirectCaseError("NO_LAYOUT_FOR_MODE:" + mode)


def _make_case(rng: random.Random, case_index: int, mode: str):
    relevant_id = rng.choice(["P_X", "P_A"])
    sources = _source_rows(relevant_id)
    tr = {
        "swap": rng.randrange(2),
        "inv0": rng.randrange(2),
        "inv1": rng.randrange(2),
        "out_inv": rng.randrange(2),
    }
    table = _target_table(PRIMITIVES[relevant_id], **tr)
    observations, query, valid_probes = _select_layout(sources, table, mode)
    surface = _surface(rng, case_index)

    def obs_row(item):
        bits, out_bit = item
        return {"input": _render_input(surface, bits), "output": _render_output(surface, out_bit)}

    visible = {
        "source_primitives": sources,
        "target_surface": surface,
        "target_observations": [obs_row(x) for x in observations],
        "query": {"input": _render_input(surface, query)},
        "allowed_safe_probes": [
            {"probe_id": f"probe-{case_index}-{i}", "input": _render_input(surface, bits)}
            for i, bits in enumerate(valid_probes)
        ],
    }
    hidden = {
        "mode": mode,
        "relevant_source_id": relevant_id,
        "distractor_source_id": "P_A" if relevant_id == "P_X" else "P_X",
        "target_transform": tr,
        "gold_query_output": _render_output(surface, table[query]),
        "valid_discriminator_probe_ids": [f"probe-{case_index}-{i}" for i in range(len(valid_probes))],
        "target_only_baseline_ambiguous": True,
    }
    case_digest = hashlib.sha256(repr((case_index, mode, visible, hidden)).encode()).hexdigest()
    return {
        "case_id": "UDD-" + case_digest[:16],
        "visible": visible,
        "hidden_evaluator": hidden,
    }


def generate(beacon: str) -> dict[str, Any]:
    rng = random.Random(_seed(beacon))
    modes = (
        ["IDENTIFIABLE_TRANSFER"] * 24
        + ["NONIDENTIFIABLE_ABSTAIN"] * 12
        + ["UNDERSPECIFIED_REQUEST_DISCRIMINATOR"] * 12
    )
    rng.shuffle(modes)
    cases = [_make_case(rng, i, mode) for i, mode in enumerate(modes)]
    ids = [c["case_id"] for c in cases]
    if len(ids) != len(set(ids)):
        raise DirectCaseError("CASE_ID_COLLISION")
    return {
        "schema": SCHEMA,
        "beacon_commitment": hashlib.sha256(beacon.encode()).hexdigest(),
        "case_count": len(cases),
        "cases": cases,
        "candidate_visible_projection": [
            {"case_id": c["case_id"], "visible": c["visible"]} for c in cases
        ],
        "accounting": {
            "persistent_learned_bytes": 0,
            "external_frontier_model_calls": 0,
            "external_learned_capability_calls": 0,
        },
    }
