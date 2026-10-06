from __future__ import annotations

from itertools import combinations
from math import ceil, log2
from typing import Mapping, Sequence


class ConditionalPolicyCoverError(ValueError):
    pass


def _normalize(
    worlds: Sequence[str],
    policies: Sequence[str],
    adequate: Mapping[str, Sequence[str]],
    transcript: Mapping[str, str],
):
    ws = tuple(str(w) for w in worlds)
    ps = tuple(str(p) for p in policies)
    if not ws or len(set(ws)) != len(ws):
        raise ConditionalPolicyCoverError("WORLD_DOMAIN_INVALID")
    if not ps or len(set(ps)) != len(ps):
        raise ConditionalPolicyCoverError("POLICY_DOMAIN_INVALID")
    pset = set(ps)
    a = {}
    t = {}
    for w in ws:
        if w not in adequate:
            raise ConditionalPolicyCoverError("ADEQUATE_SET_MISSING:" + w)
        aset = frozenset(str(p) for p in adequate[w])
        if not aset:
            raise ConditionalPolicyCoverError("NO_ADEQUATE_POLICY:" + w)
        if not aset <= pset:
            raise ConditionalPolicyCoverError("UNKNOWN_POLICY:" + w)
        if w not in transcript:
            raise ConditionalPolicyCoverError("TRANSCRIPT_MISSING:" + w)
        a[w] = aset
        t[w] = str(transcript[w])
    return ws, ps, a, t


def _minimum_cover(
    cell: Sequence[str],
    policies: Sequence[str],
    adequate: Mapping[str, frozenset[str]],
) -> tuple[str, ...]:
    target = set(cell)
    covers = {p: {w for w in cell if p in adequate[w]} for p in policies}
    for k in range(1, len(policies) + 1):
        for combo in combinations(policies, k):
            if set().union(*(covers[p] for p in combo)) == target:
                return combo
    raise ConditionalPolicyCoverError("NO_POLICY_COVER")


def conditional_policy_covers(
    worlds: Sequence[str],
    policies: Sequence[str],
    adequate: Mapping[str, Sequence[str]],
    transcript: Mapping[str, str],
) -> dict[str, tuple[str, ...]]:
    ws, ps, a, t = _normalize(worlds, policies, adequate, transcript)
    states = sorted(set(t.values()))
    out = {}
    for state in states:
        cell = tuple(w for w in ws if t[w] == state)
        out[state] = _minimum_cover(cell, ps, a)
    return out


def minimum_persistent_message_states(
    worlds: Sequence[str],
    policies: Sequence[str],
    adequate: Mapping[str, Sequence[str]],
    transcript: Mapping[str, str],
) -> int:
    covers = conditional_policy_covers(worlds, policies, adequate, transcript)
    return max(len(c) for c in covers.values())


def minimum_persistent_message_bits(
    worlds: Sequence[str],
    policies: Sequence[str],
    adequate: Mapping[str, Sequence[str]],
    transcript: Mapping[str, str],
) -> int:
    r = minimum_persistent_message_states(worlds, policies, adequate, transcript)
    return 0 if r == 1 else ceil(log2(r))


def construct_encoder_decoder(
    worlds: Sequence[str],
    policies: Sequence[str],
    adequate: Mapping[str, Sequence[str]],
    transcript: Mapping[str, str],
):
    ws, ps, a, t = _normalize(worlds, policies, adequate, transcript)
    covers = conditional_policy_covers(ws, ps, a, t)
    R = max(len(c) for c in covers.values())
    decoder = {}
    encoder = {}
    for state, cover in covers.items():
        for r, p in enumerate(cover):
            decoder[(state, r)] = p
        for w in (x for x in ws if t[x] == state):
            chosen = next((r for r, p in enumerate(cover) if p in a[w]), None)
            if chosen is None:
                raise ConditionalPolicyCoverError("COVER_ASSIGNMENT_FAILED:" + w)
            encoder[w] = chosen
    return {
        "persistent_states": R,
        "persistent_bits": 0 if R == 1 else ceil(log2(R)),
        "encoder": encoder,
        "decoder": decoder,
    }


def verify_construction(
    worlds: Sequence[str],
    policies: Sequence[str],
    adequate: Mapping[str, Sequence[str]],
    transcript: Mapping[str, str],
) -> bool:
    built = construct_encoder_decoder(worlds, policies, adequate, transcript)
    for w in worlds:
        p = built["decoder"][(str(transcript[w]), built["encoder"][w])]
        if p not in set(adequate[w]):
            return False
    return True


def zero_persistence_exact(
    worlds: Sequence[str],
    policies: Sequence[str],
    adequate: Mapping[str, Sequence[str]],
    transcript: Mapping[str, str],
) -> bool:
    return minimum_persistent_message_states(worlds, policies, adequate, transcript) == 1


def global_cardinality_false_sufficiency_counterexample():
    worlds = ("w00", "w01", "w10", "w11")
    policies = ("p0", "p1")
    adequate = {
        "w00": ("p0",),
        "w01": ("p1",),
        "w10": ("p0",),
        "w11": ("p1",),
    }
    transcript = {
        "w00": "t0",
        "w01": "t0",
        "w10": "t1",
        "w11": "t1",
    }
    global_cover = _minimum_cover(worlds, policies, {w: frozenset(v) for w, v in adequate.items()})
    S = len(set(transcript.values()))
    return {
        "global_tau": len(global_cover),
        "S": S,
        "global_cardinality_zero_lower_bound_trigger": S >= len(global_cover),
        "exact_conditional_states": minimum_persistent_message_states(worlds, policies, adequate, transcript),
        "exact_conditional_bits": minimum_persistent_message_bits(worlds, policies, adequate, transcript),
        "construction_valid": verify_construction(worlds, policies, adequate, transcript),
    }
