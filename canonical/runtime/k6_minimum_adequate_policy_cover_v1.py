from __future__ import annotations

from itertools import combinations
from math import ceil, log2
from typing import Mapping, Sequence


class PolicyCoverError(ValueError):
    pass


def _normalize(
    worlds: Sequence[str],
    policies: Sequence[str],
    adequate: Mapping[str, Sequence[str]],
) -> tuple[tuple[str, ...], tuple[str, ...], dict[str, frozenset[str]]]:
    ws = tuple(str(x) for x in worlds)
    ps = tuple(str(x) for x in policies)
    if not ws or len(set(ws)) != len(ws):
        raise PolicyCoverError("WORLD_DOMAIN_INVALID")
    if not ps or len(set(ps)) != len(ps):
        raise PolicyCoverError("POLICY_DOMAIN_INVALID")
    pset = set(ps)
    out: dict[str, frozenset[str]] = {}
    for w in ws:
        if w not in adequate:
            raise PolicyCoverError("ADEQUATE_SET_MISSING:" + w)
        aset = frozenset(str(p) for p in adequate[w])
        if not aset:
            raise PolicyCoverError("NO_ADEQUATE_POLICY:" + w)
        if not aset <= pset:
            raise PolicyCoverError("UNKNOWN_POLICY_IN_ADEQUATE_SET:" + w)
        out[w] = aset
    return ws, ps, out


def policy_cover_sets(
    worlds: Sequence[str],
    policies: Sequence[str],
    adequate: Mapping[str, Sequence[str]],
) -> dict[str, frozenset[str]]:
    ws, ps, a = _normalize(worlds, policies, adequate)
    return {p: frozenset(w for w in ws if p in a[w]) for p in ps}


def minimum_policy_cover(
    worlds: Sequence[str],
    policies: Sequence[str],
    adequate: Mapping[str, Sequence[str]],
) -> tuple[str, ...]:
    ws, ps, a = _normalize(worlds, policies, adequate)
    covers = {p: {w for w in ws if p in a[w]} for p in ps}
    target = set(ws)
    for k in range(1, len(ps) + 1):
        for combo in combinations(ps, k):
            if set().union(*(covers[p] for p in combo)) == target:
                return combo
    raise PolicyCoverError("NO_POLICY_COVER")


def assignment_from_cover(
    worlds: Sequence[str],
    adequate: Mapping[str, Sequence[str]],
    cover: Sequence[str],
) -> dict[str, str]:
    out: dict[str, str] = {}
    for w in worlds:
        aset = set(adequate[w])
        chosen = next((p for p in cover if p in aset), None)
        if chosen is None:
            raise PolicyCoverError("COVER_DOES_NOT_COVER_WORLD:" + str(w))
        out[str(w)] = str(chosen)
    return out


def verify_assignment(
    worlds: Sequence[str],
    adequate: Mapping[str, Sequence[str]],
    assignment: Mapping[str, str],
) -> bool:
    if set(assignment) != set(worlds):
        return False
    return all(assignment[w] in set(adequate[w]) for w in worlds)


def minimum_fixed_length_bits(label_count: int) -> int:
    if label_count <= 0:
        raise PolicyCoverError("LABEL_COUNT_INVALID")
    if label_count == 1:
        return 0
    return ceil(log2(label_count))


def universal_policy_case() -> dict[str, object]:
    worlds = ("w0", "w1", "w2")
    policies = ("common", "p0", "p1")
    adequate = {
        "w0": ("common", "p0"),
        "w1": ("common", "p1"),
        "w2": ("common",),
    }
    cover = minimum_policy_cover(worlds, policies, adequate)
    assignment = assignment_from_cover(worlds, adequate, cover)
    return {
        "cover": cover,
        "tau": len(cover),
        "bits": minimum_fixed_length_bits(len(cover)),
        "assignment_valid": verify_assignment(worlds, adequate, assignment),
    }


def disjoint_separator_case() -> dict[str, object]:
    worlds = ("w0", "w1")
    policies = ("a0", "a1")
    adequate = {"w0": ("a0",), "w1": ("a1",)}
    cover = minimum_policy_cover(worlds, policies, adequate)
    return {
        "cover": cover,
        "tau": len(cover),
        "bits": minimum_fixed_length_bits(len(cover)),
    }


def pairwise_compatibility_trap() -> dict[str, object]:
    worlds = ("w0", "w1", "w2")
    policies = ("p1", "p2", "p3")
    adequate = {
        "w0": ("p1", "p2"),
        "w1": ("p2", "p3"),
        "w2": ("p1", "p3"),
    }
    intersections = {
        "w0_w1": bool(set(adequate["w0"]) & set(adequate["w1"])),
        "w0_w2": bool(set(adequate["w0"]) & set(adequate["w2"])),
        "w1_w2": bool(set(adequate["w1"]) & set(adequate["w2"])),
    }
    global_common = set(adequate["w0"]) & set(adequate["w1"]) & set(adequate["w2"])
    cover = minimum_policy_cover(worlds, policies, adequate)
    return {
        "pairwise_intersections_all_nonempty": all(intersections.values()),
        "global_common_policy_exists": bool(global_common),
        "tau": len(cover),
        "cover": cover,
    }


def compile_falsifiers() -> dict[str, object]:
    universal = universal_policy_case()
    disjoint = disjoint_separator_case()
    trap = pairwise_compatibility_trap()

    if not (
        universal["tau"] == 1
        and universal["bits"] == 0
        and universal["assignment_valid"] is True
    ):
        return {"status": "FAIL_CLOSED", "error": "UNIVERSAL_POLICY_CASE"}

    if not (disjoint["tau"] == 2 and disjoint["bits"] == 1):
        return {"status": "FAIL_CLOSED", "error": "DISJOINT_SEPARATOR_CASE"}

    if not (
        trap["pairwise_intersections_all_nonempty"] is True
        and trap["global_common_policy_exists"] is False
        and trap["tau"] == 2
    ):
        return {"status": "FAIL_CLOSED", "error": "PAIRWISE_COMPATIBILITY_TRAP"}

    return {
        "status": "PASS__FINITE_K6_MINIMUM_POLICY_COVER_FALSIFIERS",
        "full_world_identification_not_necessary": True,
        "separator_lower_bound_recovered": True,
        "pairwise_compatibility_insufficient": True,
        "terminal_credit": False,
        "classification": "TRUTH_REPAIR_CANDIDATE",
    }
