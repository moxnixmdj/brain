"""Fail-closed typed minimum certificate-basis solver.

A certificate may close a predicate only when its declared proof type is
explicitly admitted by that predicate.  The solver finds the minimum total
declared critical-path cost over the supplied candidate set.  It is a
zero-reality planning primitive and grants no acceptance credit.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_TYPED_MINIMUM_CERTIFICATE_BASIS_V1"


@dataclass(frozen=True)
class Predicate:
    predicate_id: str
    admissible_proof_types: frozenset[str]


@dataclass(frozen=True)
class Certificate:
    certificate_id: str
    proof_type: str
    closes: frozenset[str]
    critical_path_cost: float


def _cost(x: object) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise ValueError("INVALID_COST")
    v = float(x)
    if not isfinite(v) or v < 0:
        raise ValueError("INVALID_COST")
    return v


def compile_inputs(
    predicates: Sequence[Mapping[str, object]],
    certificates: Sequence[Mapping[str, object]],
) -> tuple[list[Predicate], list[Certificate]]:
    ps: list[Predicate] = []
    seen_p: set[str] = set()
    for raw in predicates:
        pid = raw.get("predicate_id")
        types = raw.get("admissible_proof_types")
        if not isinstance(pid, str) or not pid or pid in seen_p:
            raise ValueError("INVALID_OR_DUPLICATE_PREDICATE")
        if not isinstance(types, (list, tuple, set, frozenset)) or not types:
            raise ValueError("PREDICATE_WITHOUT_ADMISSIBLE_TYPE")
        st = frozenset(str(x) for x in types if isinstance(x, str) and x)
        if len(st) != len(types):
            raise ValueError("INVALID_PROOF_TYPE")
        seen_p.add(pid)
        ps.append(Predicate(pid, st))

    cs: list[Certificate] = []
    seen_c: set[str] = set()
    for raw in certificates:
        cid = raw.get("certificate_id")
        ptype = raw.get("proof_type")
        closes = raw.get("closes")
        if not isinstance(cid, str) or not cid or cid in seen_c:
            raise ValueError("INVALID_OR_DUPLICATE_CERTIFICATE")
        if not isinstance(ptype, str) or not ptype:
            raise ValueError("INVALID_CERTIFICATE_TYPE")
        if not isinstance(closes, (list, tuple, set, frozenset)) or not closes:
            raise ValueError("CERTIFICATE_WITHOUT_TARGET")
        target = frozenset(str(x) for x in closes if isinstance(x, str) and x)
        if len(target) != len(closes) or not target <= seen_p:
            raise ValueError("UNKNOWN_CERTIFICATE_TARGET")
        seen_c.add(cid)
        cs.append(Certificate(cid, ptype, target, _cost(raw.get("critical_path_cost"))))
    return ps, cs


def solve(
    predicates: Sequence[Mapping[str, object]],
    certificates: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    ps, cs = compile_inputs(predicates, certificates)
    index = {p.predicate_id: i for i, p in enumerate(ps)}
    admissible = {p.predicate_id: p.admissible_proof_types for p in ps}
    full = (1 << len(ps)) - 1

    prepared: list[tuple[Certificate, int]] = []
    rejected: list[dict[str, object]] = []
    for c in cs:
        invalid = sorted(pid for pid in c.closes if c.proof_type not in admissible[pid])
        if invalid:
            rejected.append({
                "certificate_id": c.certificate_id,
                "reason": "PROOF_TYPE_NOT_ADMISSIBLE",
                "predicates": invalid,
            })
            continue
        mask = 0
        for pid in c.closes:
            mask |= 1 << index[pid]
        prepared.append((c, mask))

    # mask -> (cost, action_count, tuple(ids))
    best: dict[int, tuple[float, int, tuple[str, ...]]] = {0: (0.0, 0, ())}
    for c, cmask in prepared:
        nxt = dict(best)
        for mask, state in best.items():
            nm = mask | cmask
            cand = (state[0] + c.critical_path_cost, state[1] + 1, state[2] + (c.certificate_id,))
            old = nxt.get(nm)
            if old is None or cand < old:
                nxt[nm] = cand
        best = nxt

    state = best.get(full)
    uncovered: list[str] = []
    if state is None:
        cover = 0
        for _, m in prepared:
            cover |= m
        uncovered = [p.predicate_id for p in ps if not (cover & (1 << index[p.predicate_id]))]

    return {
        "schema": SCHEMA,
        "predicate_count": len(ps),
        "candidate_count": len(cs),
        "admissible_candidate_count": len(prepared),
        "rejected_candidates": rejected,
        "complete_basis_exists": state is not None,
        "minimum_total_declared_cost": None if state is None else state[0],
        "minimum_action_count_at_minimum_cost": None if state is None else state[1],
        "selected_certificate_ids": [] if state is None else list(state[2]),
        "structurally_uncoverable_predicates": uncovered,
        "acceptance_credit_authorized": False,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
