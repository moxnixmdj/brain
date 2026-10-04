"""Zero-learned candidate for the two frozen Unknown-Domain direct leaves.

The candidate consumes only the visible projection.  It never imports the hidden
case generator or scorer.  Cross-domain transfer is performed by exact
enumeration of surface renamings/inversions over independently verified source
primitive tables.  If the query is not identified, the existing verified V3
decision discriminator selects a safe decision-relevant probe; otherwise the
candidate abstains.

No persistent learned state or external learned capability is used.
"""
from __future__ import annotations

import itertools
from fractions import Fraction
from typing import Any, Mapping

from canonical.runtime import decision_discriminator_v3 as decision

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_CANDIDATE_RESULT_V1"


class DirectCandidateError(ValueError):
    pass


def _validate_receipt(source: Mapping[str, Any]) -> str:
    rec = source.get("verification_receipt")
    if not isinstance(rec, Mapping):
        raise DirectCandidateError("SOURCE_RECEIPT_REQUIRED")
    if rec.get("independent_verified") is not True:
        raise DirectCandidateError("SOURCE_RECEIPT_NOT_INDEPENDENT")
    if rec.get("exact_byte_bound") is not True:
        raise DirectCandidateError("SOURCE_RECEIPT_NOT_EXACT_BYTE_BOUND")
    if rec.get("conclusion") != "success":
        raise DirectCandidateError("SOURCE_RECEIPT_NOT_SUCCESS")
    sid = str(source.get("id") or "")
    if rec.get("primitive_id") != sid:
        raise DirectCandidateError("SOURCE_RECEIPT_PRIMITIVE_MISMATCH")
    rid = str(rec.get("receipt_id") or "")
    if not rid:
        raise DirectCandidateError("SOURCE_RECEIPT_ID_REQUIRED")
    return rid


def _parse_table(source: Mapping[str, Any]):
    table_raw = source.get("canonical_table")
    if not isinstance(table_raw, Mapping):
        raise DirectCandidateError("SOURCE_TABLE_INVALID")
    table = {}
    for key, value in table_raw.items():
        parts = str(key).split(",")
        if len(parts) != 2 or any(x not in {"0", "1"} for x in parts):
            raise DirectCandidateError("SOURCE_TABLE_KEY_INVALID")
        if value not in (0, 1):
            raise DirectCandidateError("SOURCE_TABLE_VALUE_INVALID")
        table[(int(parts[0]), int(parts[1]))] = int(value)
    if set(table) != set(itertools.product((0, 1), repeat=2)):
        raise DirectCandidateError("SOURCE_TABLE_INCOMPLETE")
    return table


def _all_transforms():
    for swap, inv0, inv1, out_inv in itertools.product((0, 1), repeat=4):
        yield (swap, inv0, inv1, out_inv)


def _predict(table, tr, bits):
    swap, inv0, inv1, out_inv = tr
    raw = [bits[0] ^ inv0, bits[1] ^ inv1]
    s0, s1 = (raw[1], raw[0]) if swap else (raw[0], raw[1])
    return int(table[(s0, s1)]) ^ out_inv


def _parse_surface(visible: Mapping[str, Any]):
    surface = visible.get("target_surface")
    if not isinstance(surface, Mapping):
        raise DirectCandidateError("TARGET_SURFACE_INVALID")
    features = surface.get("features")
    outputs = surface.get("output_tokens")
    if not isinstance(features, list) or len(features) != 2:
        raise DirectCandidateError("TARGET_FEATURES_INVALID")
    if not isinstance(outputs, list) or len(outputs) != 2 or len(set(outputs)) != 2:
        raise DirectCandidateError("TARGET_OUTPUT_TOKENS_INVALID")
    names = []
    maps = []
    for feature in features:
        if not isinstance(feature, Mapping):
            raise DirectCandidateError("TARGET_FEATURE_INVALID")
        name = str(feature.get("name") or "")
        tokens = feature.get("tokens")
        if not name or not isinstance(tokens, list) or len(tokens) != 2 or len(set(tokens)) != 2:
            raise DirectCandidateError("TARGET_FEATURE_TOKENS_INVALID")
        names.append(name)
        maps.append({str(tokens[0]): 0, str(tokens[1]): 1})
    if len(set(names)) != 2:
        raise DirectCandidateError("TARGET_FEATURE_NAMES_DUPLICATE")
    out_map = {str(outputs[0]): 0, str(outputs[1]): 1}
    return names, maps, [str(outputs[0]), str(outputs[1])], out_map


def _input_bits(input_row: Mapping[str, Any], names, token_maps):
    if not isinstance(input_row, Mapping):
        raise DirectCandidateError("INPUT_ROW_INVALID")
    bits = []
    for i, name in enumerate(names):
        token = str(input_row.get(name) or "")
        if token not in token_maps[i]:
            raise DirectCandidateError("INPUT_TOKEN_UNKNOWN:" + name)
        bits.append(token_maps[i][token])
    return tuple(bits)


def solve(visible: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(visible, Mapping):
        raise DirectCandidateError("VISIBLE_CASE_INVALID")
    names, token_maps, output_tokens, out_map = _parse_surface(visible)

    sources = visible.get("source_primitives")
    if not isinstance(sources, list) or len(sources) < 1:
        raise DirectCandidateError("SOURCE_PRIMITIVES_INVALID")

    parsed_sources = []
    for source in sources:
        if not isinstance(source, Mapping):
            raise DirectCandidateError("SOURCE_PRIMITIVE_NOT_OBJECT")
        sid = str(source.get("id") or "")
        if not sid:
            raise DirectCandidateError("SOURCE_ID_REQUIRED")
        parsed_sources.append({
            "id": sid,
            "table": _parse_table(source),
            "receipt_id": _validate_receipt(source),
        })

    obs_raw = visible.get("target_observations")
    if not isinstance(obs_raw, list) or not obs_raw:
        raise DirectCandidateError("TARGET_OBSERVATIONS_INVALID")
    observations = []
    for row in obs_raw:
        if not isinstance(row, Mapping):
            raise DirectCandidateError("TARGET_OBSERVATION_NOT_OBJECT")
        bits = _input_bits(row.get("input"), names, token_maps)
        token = str(row.get("output") or "")
        if token not in out_map:
            raise DirectCandidateError("TARGET_OUTPUT_TOKEN_UNKNOWN")
        observations.append((bits, out_map[token]))

    query_raw = visible.get("query")
    if not isinstance(query_raw, Mapping):
        raise DirectCandidateError("QUERY_INVALID")
    query = _input_bits(query_raw.get("input"), names, token_maps)

    survivors = []
    for source in parsed_sources:
        for tr in _all_transforms():
            if all(_predict(source["table"], tr, bits) == out_bit for bits, out_bit in observations):
                survivors.append({
                    "source_id": source["id"],
                    "receipt_id": source["receipt_id"],
                    "table": source["table"],
                    "transform": tr,
                })

    base = {
        "schema": SCHEMA,
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "survivor_count": len(survivors),
        "surviving_source_ids": sorted({x["source_id"] for x in survivors}),
        "source_receipt_ids": sorted({x["receipt_id"] for x in survivors}),
    }

    if not survivors:
        return {
            **base,
            "verdict": "ABSTAIN",
            "answer": None,
            "probe_id": None,
            "reason": "NO_VERIFIED_SOURCE_TRANSFER_HYPOTHESIS_SURVIVES",
        }

    query_predictions = {
        output_tokens[_predict(x["table"], x["transform"], query)]
        for x in survivors
    }
    if len(query_predictions) == 1:
        return {
            **base,
            "verdict": "ANSWER",
            "answer": next(iter(query_predictions)),
            "probe_id": None,
            "reason": "ALL_VERIFIED_TRANSFER_HYPOTHESES_AGREE_ON_QUERY",
        }

    hypotheses = []
    probability = str(Fraction(1, len(survivors)))
    for i, survivor in enumerate(survivors):
        hypotheses.append({
            "id": f"h{i}",
            "plausible": True,
            "best_action": output_tokens[_predict(survivor["table"], survivor["transform"], query)],
            "probability": probability,
        })

    actions = []
    probes = visible.get("allowed_safe_probes") or []
    if not isinstance(probes, list):
        raise DirectCandidateError("ALLOWED_PROBES_INVALID")
    for probe in probes:
        if not isinstance(probe, Mapping):
            raise DirectCandidateError("PROBE_NOT_OBJECT")
        pid = str(probe.get("probe_id") or "")
        if not pid:
            raise DirectCandidateError("PROBE_ID_REQUIRED")
        bits = _input_bits(probe.get("input"), names, token_maps)
        outcomes = {}
        for i, survivor in enumerate(survivors):
            outcomes[f"h{i}"] = output_tokens[_predict(survivor["table"], survivor["transform"], bits)]
        actions.append({
            "id": pid,
            "safe": True,
            "outcome_by_hypothesis": outcomes,
            "transfer_gain": 0,
            "proof_gain": 0,
            "time": 1,
            "cost": 0,
            "risk": 0,
        })

    ranked = decision.rank(hypotheses=hypotheses, actions=actions)
    if ranked:
        return {
            **base,
            "verdict": "REQUEST_DISCRIMINATOR",
            "answer": None,
            "probe_id": ranked[0]["id"],
            "reason": "SAFE_POSITIVE_DECISION_GAIN_DISCRIMINATOR_AVAILABLE",
            "ranked_discriminators": ranked,
        }

    return {
        **base,
        "verdict": "ABSTAIN",
        "answer": None,
        "probe_id": None,
        "reason": "QUERY_NONIDENTIFIABLE_WITH_NO_SAFE_POSITIVE_DECISION_GAIN_DISCRIMINATOR",
    }
