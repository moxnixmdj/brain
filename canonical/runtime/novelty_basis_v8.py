"""Exact finite novelty-basis discovery for Universal Learning V8.

Given independently verified primitives and a finite, independently verified
target corpus, compute the exact minimum-cost primitive subset covering every
required atom in that corpus. The result is deliberately NOT an open-world
basis theorem.
"""
from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from itertools import combinations
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_NOVELTY_BASIS_V8"
MAX_EXACT_PRIMITIVES = 18


class NoveltyBasisError(ValueError):
    pass


def _s(x: Any) -> str:
    return " ".join(str(x or "").split())


def _items(xs) -> list[str]:
    return sorted({_s(x) for x in (xs or []) if _s(x)})


def _f(x: Any, name: str) -> Fraction:
    if isinstance(x, bool):
        raise NoveltyBasisError(name.upper() + "_INVALID")
    try:
        out = x if isinstance(x, Fraction) else Fraction(str(x))
    except Exception as exc:
        raise NoveltyBasisError(name.upper() + "_INVALID") from exc
    if out < 0:
        raise NoveltyBasisError(name.upper() + "_NEGATIVE")
    return out


def primitive_digest(*, primitive_id: str, covers_atoms, description_cost: Any) -> str:
    pid = _s(primitive_id)
    atoms = _items(covers_atoms)
    cost = _f(description_cost, "description_cost")
    if not pid or not atoms:
        raise NoveltyBasisError("PRIMITIVE_INVALID")
    body = json.dumps(
        {"primitive_id": pid, "covers_atoms": atoms, "description_cost": str(cost)},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return "sha256:" + hashlib.sha256(body).hexdigest()


def target_digest(*, target_id: str, required_atoms) -> str:
    tid = _s(target_id)
    atoms = _items(required_atoms)
    if not tid or not atoms:
        raise NoveltyBasisError("TARGET_INVALID")
    body = json.dumps(
        {"target_id": tid, "required_atoms": atoms},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return "sha256:" + hashlib.sha256(body).hexdigest()


def _primitive(raw: Mapping[str, Any]) -> dict[str, Any]:
    pid = _s(raw.get("primitive_id"))
    atoms = _items(raw.get("covers_atoms"))
    cost = _f(raw.get("description_cost", 0), "description_cost")
    digest = primitive_digest(primitive_id=pid, covers_atoms=atoms, description_cost=cost)
    r = raw.get("verification_receipt")
    if not isinstance(r, Mapping):
        raise NoveltyBasisError("PRIMITIVE_RECEIPT_REQUIRED:" + pid)
    if r.get("independent_verified") is not True or r.get("exact_byte_bound") is not True or r.get("conclusion") != "success":
        raise NoveltyBasisError("PRIMITIVE_RECEIPT_INVALID:" + pid)
    if r.get("primitive_sha256") != digest or _s(r.get("primitive_id")) != pid:
        raise NoveltyBasisError("PRIMITIVE_RECEIPT_BINDING_MISMATCH:" + pid)
    rid = _s(r.get("receipt_id"))
    if not rid:
        raise NoveltyBasisError("PRIMITIVE_RECEIPT_ID_REQUIRED:" + pid)
    return {"primitive_id": pid, "covers_atoms": atoms, "description_cost": cost, "primitive_sha256": digest, "verification_receipt": rid}


def _target(raw: Mapping[str, Any]) -> dict[str, Any]:
    tid = _s(raw.get("target_id"))
    atoms = _items(raw.get("required_atoms"))
    digest = target_digest(target_id=tid, required_atoms=atoms)
    r = raw.get("verification_receipt")
    if not isinstance(r, Mapping):
        raise NoveltyBasisError("TARGET_RECEIPT_REQUIRED:" + tid)
    if (
        r.get("independent_verified") is not True
        or r.get("exact_byte_bound") is not True
        or r.get("conclusion") != "success"
        or r.get("required_atom_set_complete") is not True
    ):
        raise NoveltyBasisError("TARGET_RECEIPT_INVALID:" + tid)
    if r.get("target_sha256") != digest or _s(r.get("target_id")) != tid:
        raise NoveltyBasisError("TARGET_RECEIPT_BINDING_MISMATCH:" + tid)
    rid = _s(r.get("receipt_id"))
    if not rid:
        raise NoveltyBasisError("TARGET_RECEIPT_ID_REQUIRED:" + tid)
    return {"target_id": tid, "required_atoms": atoms, "target_sha256": digest, "verification_receipt": rid}


def exact_basis(*, primitives: Sequence[Mapping[str, Any]], targets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ps = [_primitive(x) for x in primitives]
    ts = [_target(x) for x in targets]
    if not ps or not ts:
        raise NoveltyBasisError("PRIMITIVES_AND_TARGETS_REQUIRED")
    if len(ps) > MAX_EXACT_PRIMITIVES:
        raise NoveltyBasisError("EXACT_BASIS_BOUND_EXCEEDED")
    if len({x["primitive_id"] for x in ps}) != len(ps):
        raise NoveltyBasisError("PRIMITIVE_ID_DUPLICATE")
    if len({x["target_id"] for x in ts}) != len(ts):
        raise NoveltyBasisError("TARGET_ID_DUPLICATE")

    required = set()
    for t in ts:
        required |= set(t["required_atoms"])
    available = set()
    for p in ps:
        available |= set(p["covers_atoms"])
    missing = sorted(required - available)
    if missing:
        raise NoveltyBasisError("UNCOVERED_REQUIRED_ATOMS:" + ",".join(missing))

    best = None
    for size in range(1, len(ps) + 1):
        for subset in combinations(ps, size):
            covered = set()
            total = Fraction(0)
            ids = []
            for p in subset:
                covered |= set(p["covers_atoms"])
                total += p["description_cost"]
                ids.append(p["primitive_id"])
            if required <= covered:
                key = (total, size, tuple(sorted(ids)))
                if best is None or key < best[0]:
                    best = (key, subset)
    if best is None:
        raise NoveltyBasisError("NO_FINITE_BASIS")

    key, subset = best
    selected = sorted(x["primitive_id"] for x in subset)
    return {
        "schema": SCHEMA,
        "status": "EXACT_MINIMUM_COST_BASIS_FOR_VERIFIED_FINITE_CORPUS",
        "selected_primitive_ids": selected,
        "total_description_cost": str(key[0]),
        "primitive_count": key[1],
        "required_atoms": sorted(required),
        "target_ids": sorted(x["target_id"] for x in ts),
        "optimality": "EXHAUSTIVE_FINITE_SUBSET_SEARCH",
        "declared_finite_corpus_only": True,
        "open_world_basis_claimed": False,
        "universal_primitive_vocabulary_claimed": False,
        "acceptance_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
