"""Post-freeze hidden-case generator for the two Unknown-Domain direct leaves.

No production case is generated merely by importing or testing this module.
Production generation requires an explicit predicate-local fresh-reality
authorization object, a post-freeze beacon, and an evaluator-only secret.

The generator returns candidate-visible packets and evaluator-only hidden records
separately. Surface names are HMAC-derived and disjoint across domains. Test
fixtures use a separate TEST_ONLY namespace and cannot satisfy production
authorization.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
from typing import Any, Mapping, Sequence

TRANSFER = "CROSS_DOMAIN_TRANSFER_OUTSIDE_MYSTERYMECHANISM_TASK_STRUCTURE"
ABSTAIN = "CALIBRATED_UNKNOWN_OR_ABSTENTION_ON_NONIDENTIFIABLE_OR_UNDERSPECIFIED_VARIANTS"
SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_HIDDEN_GENERATOR_V1"
TARGET_PREDICATE = "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
PRODUCTION_CASE_COUNTS = {TRANSFER: 12, ABSTAIN: 15}
ABSTAIN_CLASSES = ("IDENTIFIABLE", "NONIDENTIFIABLE", "UNDERSPECIFIED")
PRIMITIVE_FAMILIES = (
    "ORDER_PRESERVING_TRANSFORM",
    "PARITY_OR_SIGN_INVARIANT",
    "CONSERVATION_RELATION",
    "MONOTONE_CAUSAL_EDGE",
    "COMPOSITIONAL_REWRITE",
    "THRESHOLD_OR_PARTITION_INVARIANT",
)


class UnknownDomainGeneratorError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _sha256(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canon(value)).hexdigest()


def _secret_bytes(secret: Any) -> bytes:
    if isinstance(secret, bytes):
        out = secret
    elif isinstance(secret, str):
        out = secret.encode()
    else:
        raise UnknownDomainGeneratorError("EVALUATOR_SECRET_INVALID")
    if len(out) < 32:
        raise UnknownDomainGeneratorError("EVALUATOR_SECRET_TOO_SHORT")
    return out


def _token(secret: bytes, beacon: str, *parts: Any, width: int = 14) -> str:
    msg = "|".join([beacon] + [str(x) for x in parts]).encode()
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()[:width]


def _production_authorized(authority: Mapping[str, Any]) -> None:
    if not isinstance(authority, Mapping):
        raise UnknownDomainGeneratorError("AUTHORITY_INVALID")
    if authority.get("active") is not True:
        raise UnknownDomainGeneratorError("PREDICATE_LOCAL_AUTHORITY_NOT_ACTIVE")
    if authority.get("target_predicate") != TARGET_PREDICATE:
        raise UnknownDomainGeneratorError("AUTHORITY_PREDICATE_MISMATCH")
    leaves = authority.get("authorized_leaves")
    if not isinstance(leaves, Sequence) or isinstance(leaves, (str, bytes)):
        raise UnknownDomainGeneratorError("AUTHORIZED_LEAVES_INVALID")
    if set(map(str, leaves)) != {TRANSFER, ABSTAIN}:
        raise UnknownDomainGeneratorError("AUTHORIZED_LEAF_SET_MISMATCH")
    if authority.get("predicate_local_fresh_reality") is not True:
        raise UnknownDomainGeneratorError("PREDICATE_LOCAL_FRESH_REALITY_FALSE")
    if authority.get("global_fresh_reality") is not False:
        raise UnknownDomainGeneratorError("GLOBAL_FRESH_REALITY_MUST_REMAIN_FALSE")
    if authority.get("one_use_claim_created") is not True:
        raise UnknownDomainGeneratorError("ONE_USE_CLAIM_REQUIRED")
    claim = str(authority.get("one_use_claim_id") or "").strip()
    if not claim:
        raise UnknownDomainGeneratorError("ONE_USE_CLAIM_ID_REQUIRED")
    if authority.get("incremental_spend_usd") != 0:
        raise UnknownDomainGeneratorError("ZERO_INCREMENTAL_SPEND_REQUIRED")


def _program_for(index: int) -> tuple[str, dict[str, Any], list[str]]:
    family = PRIMITIVE_FAMILIES[index % len(PRIMITIVE_FAMILIES)]
    variant = index // len(PRIMITIVE_FAMILIES)
    if family == "ORDER_PRESERVING_TRANSFORM":
        program = {"dsl": "UDIR_V1", "op": "AFFINE_POS", "roles": ["r0"], "params": {"bias": 1.25 + 0.3*variant, "gain": 1.5 + 0.2*variant}}
    elif family == "PARITY_OR_SIGN_INVARIANT":
        program = {"dsl": "UDIR_V1", "op": "SIGN", "roles": ["r0"], "params": {}}
    elif family == "CONSERVATION_RELATION":
        program = {"dsl": "UDIR_V1", "op": "COMPLEMENT", "roles": ["r0"], "params": {"total": 4.0 + variant}}
    elif family == "MONOTONE_CAUSAL_EDGE":
        program = {"dsl": "UDIR_V1", "op": "SAT_MONO", "roles": ["r0"], "params": {"bias": -0.25 + 0.1*variant, "gain": 2.0 + 0.25*variant}}
    elif family == "COMPOSITIONAL_REWRITE":
        program = {"dsl": "UDIR_V1", "op": "ADD2", "roles": ["r0", "r1"], "params": {"bias": 0.5 - 0.2*variant}}
    else:
        program = {"dsl": "UDIR_V1", "op": "STEP", "roles": ["r0"], "params": {"threshold": -0.5 + 0.75*variant, "low": -1.0 - 0.2*variant, "high": 1.0 + 0.3*variant}}
    return family, program, list(program["roles"])


def _eval(program: Mapping[str, Any], role_values: Mapping[str, float]) -> float:
    op = program["op"]
    p = program["params"]
    x = float(role_values.get("r0", 0.0))
    if op == "AFFINE_POS":
        return float(p["bias"]) + float(p["gain"]) * x
    if op == "SIGN":
        return -1.0 if x < 0 else 1.0
    if op == "COMPLEMENT":
        return float(p["total"]) - x
    if op == "SAT_MONO":
        return float(p["bias"]) + float(p["gain"]) * (x / (1.0 + abs(x)))
    if op == "ADD2":
        return float(p["bias"]) + float(role_values["r0"]) + float(role_values["r1"])
    if op == "STEP":
        return float(p["high"]) if x >= float(p["threshold"]) else float(p["low"])
    raise UnknownDomainGeneratorError("PROGRAM_OP_UNKNOWN")


def _role_rows(arity: int) -> list[dict[str, float]]:
    r0 = [-2.4, -1.1, 0.35, 1.4, 2.7, -0.45]
    r1 = [1.6, -0.7, 2.2, -1.4, 0.55, 3.1]
    rows = []
    for i in range(len(r0)):
        row = {"r0": r0[i]}
        if arity == 2:
            row["r1"] = r1[i]
        rows.append(row)
    return rows


def _surface_ids(secret: bytes, beacon: str, case_index: int, domain: str, roles: list[str]) -> tuple[dict[str, str], list[str]]:
    mapping = {
        role: f"{domain.lower()}_{_token(secret, beacon, 'feature', case_index, domain, role)}"
        for role in roles
    }
    distractors = [
        f"{domain.lower()}_{_token(secret, beacon, 'distractor', case_index, domain, i)}"
        for i in range(2)
    ]
    if set(mapping.values()) & set(distractors):
        raise UnknownDomainGeneratorError("OPAQUE_FEATURE_COLLISION")
    return mapping, distractors


def _surface_row(
    role_row: Mapping[str, float],
    mapping: Mapping[str, str],
    distractors: Sequence[str],
    *,
    mimic_visible: bool,
    probe_variant: int,
) -> dict[str, float]:
    out = {mapping[r]: float(v) for r, v in role_row.items()}
    roles = list(role_row)
    for i, did in enumerate(distractors):
        role = roles[i % len(roles)]
        if mimic_visible:
            out[did] = float(role_row[role])
        else:
            delta = 4.75 + 1.5*i + 0.25*probe_variant
            out[did] = float(role_row[role]) + delta
    return out


def _transfer_case(secret: bytes, beacon: str, index: int, *, namespace: str) -> tuple[dict[str, Any], dict[str, Any]]:
    family, program, roles = _program_for(index)
    fingerprint = _sha256(program)
    rows = _role_rows(len(roles))
    a_map, a_distractors = _surface_ids(secret, beacon, index, namespace + "_A", roles)
    b_map, b_distractors = _surface_ids(secret, beacon, index, namespace + "_B", roles)
    if (set(a_map.values()) | set(a_distractors)) & (set(b_map.values()) | set(b_distractors)):
        raise UnknownDomainGeneratorError("DOMAIN_VOCABULARY_OVERLAP")

    source_observations = []
    target_observations = []
    for j in range(3):
        source_observations.append({
            "inputs": _surface_row(rows[j], a_map, a_distractors, mimic_visible=False, probe_variant=j),
            "terminal_consequence": _eval(program, rows[j]),
        })
        target_observations.append({
            "inputs": _surface_row(rows[j], b_map, b_distractors, mimic_visible=True, probe_variant=j),
            "terminal_consequence": _eval(program, rows[j]),
        })

    receipt_id = f"R-{_token(secret, beacon, 'receipt', index, namespace)}"
    receipt = {
        "receipt_id": receipt_id,
        "normalized_primitive_program": program,
        "primitive_fingerprint": fingerprint,
        "source_role_binding": dict(a_map),
        "source_evidence_digest": _sha256(source_observations),
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
    }

    probes = []
    probe_hidden = {}
    for j, row in enumerate(rows[3:5]):
        pid = f"P-{_token(secret, beacon, 'probe', index, j, namespace)}"
        public = {
            "probe_id": pid,
            "argument_schema": {"type": "OBSERVE_PRECOMMITTED_ROW", "row_slot": j},
            "cost": j + 1,
        }
        result = {
            "inputs": _surface_row(row, b_map, b_distractors, mimic_visible=False, probe_variant=j),
            "terminal_consequence": _eval(program, row),
        }
        probes.append(public)
        probe_hidden[pid] = result

    query_roles = rows[5]
    query_inputs = _surface_row(query_roles, b_map, b_distractors, mimic_visible=False, probe_variant=9)
    case_id = f"{namespace}-T-{_token(secret, beacon, 'case', TRANSFER, index, namespace, width=20)}"
    visible = {
        "case_id": case_id,
        "leaf_id": TRANSFER,
        "domain_a": {
            "tasks": source_observations,
            "earned_receipts": [receipt],
        },
        "domain_b": {
            "tasks": target_observations,
            "query_inputs": query_inputs,
            "allowed_probes": probes,
            "tool_metadata": {
                "input_shape": "OPAQUE_FEATURE_VALUE_MAP",
                "output_shape": "SCALAR_TERMINAL_CONSEQUENCE",
            },
        },
        "decision_requirement": "PREDICT_TERMINAL_CONSEQUENCE_AND_PROVIDE_TRANSFER_PROOF_TRACE",
    }
    relevant = [b_map[r] for r in roles]
    hidden = {
        "case_id": case_id,
        "leaf_id": TRANSFER,
        "primitive_family": family,
        "latent_primitive_program": program,
        "latent_primitive_fingerprint": fingerprint,
        "domain_mapping": dict(b_map),
        "domain_a_earned_receipt_ids": [receipt_id],
        "domain_a_receipt_primitive_bindings": {receipt_id: fingerprint},
        "transfer_relevant_feature_ids": relevant,
        "distractor_feature_ids": list(b_distractors),
        "gold_terminal_consequence": _eval(program, query_roles),
        "full_rediscovery_probe_floor": 3,
        "surface_label_permutation_verified": True,
        "domain_vocabularies_disjoint": True,
        "allowed_probe_outcome_table": probe_hidden,
    }
    return visible, hidden


def _abstention_case(secret: bytes, beacon: str, index: int, *, namespace: str) -> tuple[dict[str, Any], dict[str, Any]]:
    cls = ABSTAIN_CLASSES[index // 5]
    local = index % 5
    h1 = f"H-{_token(secret, beacon, 'hyp', index, 1, namespace)}"
    h2 = f"H-{_token(secret, beacon, 'hyp', index, 2, namespace)}"
    a = f"A-{_token(secret, beacon, 'action', index, 1, namespace)}"
    b = a if cls == "IDENTIFIABLE" else f"A-{_token(secret, beacon, 'action', index, 2, namespace)}"
    hypotheses = [
        {"hypothesis_id": h1, "plausible": True, "terminal_consequence": a, "evidence": ["OBS-0"]},
        {"hypothesis_id": h2, "plausible": True, "terminal_consequence": b, "evidence": ["OBS-0"]},
    ]
    probes = []
    table = {}
    minimum = None
    if cls == "UNDERSPECIFIED":
        p0 = f"P-{_token(secret, beacon, 'disc', index, 0, namespace)}"
        p1 = f"P-{_token(secret, beacon, 'disc', index, 1, namespace)}"
        probes = [
            {"probe_id": p0, "argument_schema": {"type": "SAFE_BINARY_DISCRIMINATOR"}, "cost": 1},
            {"probe_id": p1, "argument_schema": {"type": "SAFE_BINARY_DISCRIMINATOR"}, "cost": 2},
        ]
        table = {
            p0: {h1: "LEFT", h2: "RIGHT"},
            p1: {h1: "LEFT", h2: "RIGHT"},
        }
        minimum = p0
    elif cls == "NONIDENTIFIABLE":
        p0 = f"P-{_token(secret, beacon, 'nondisc', index, 0, namespace)}"
        probes = [{"probe_id": p0, "argument_schema": {"type": "SAFE_OBSERVATION"}, "cost": 1}]
        table = {p0: {h1: "SAME", h2: "SAME"}}

    case_id = f"{namespace}-A-{_token(secret, beacon, 'case', ABSTAIN, index, namespace, width=20)}"
    visible = {
        "case_id": case_id,
        "leaf_id": ABSTAIN,
        "hypotheses": hypotheses,
        "public_observations": {"OBS-0": "VISIBLE"},
        "allowed_probes": probes,
        "decision_requirement": "CONCLUDE_OR_ABSTAIN_OR_REQUEST_DISCRIMINATOR",
    }
    hidden = {
        "case_id": case_id,
        "leaf_id": ABSTAIN,
        "identifiability_status": cls,
        "equivalence_classes": [[h1, h2]] if a == b else [[h1], [h2]],
        "gold_terminal_consequence": a if cls == "IDENTIFIABLE" else None,
        "minimum_discriminator_id": minimum,
        "allowed_probe_outcome_table": table,
    }
    return visible, hidden


def _generate(*, beacon: str, evaluator_secret: Any, namespace: str) -> dict[str, Any]:
    if not isinstance(beacon, str) or len(beacon.strip()) < 16:
        raise UnknownDomainGeneratorError("POST_FREEZE_BEACON_INVALID")
    secret = _secret_bytes(evaluator_secret)
    visible = []
    hidden = []
    for i in range(PRODUCTION_CASE_COUNTS[TRANSFER]):
        v, h = _transfer_case(secret, beacon, i, namespace=namespace)
        visible.append(v)
        hidden.append(h)
    for i in range(PRODUCTION_CASE_COUNTS[ABSTAIN]):
        v, h = _abstention_case(secret, beacon, i, namespace=namespace)
        visible.append(v)
        hidden.append(h)
    ids = [x["case_id"] for x in visible]
    if len(ids) != 27 or len(ids) != len(set(ids)):
        raise UnknownDomainGeneratorError("CASE_ID_SET_INVALID")
    return {
        "schema": SCHEMA,
        "case_count": 27,
        "visible_cases": visible,
        "hidden_records": hidden,
        "visible_packet_digest": _sha256(visible),
        "hidden_packet_digest": _sha256(hidden),
    }


def generate_production_population(
    *,
    beacon: str,
    evaluator_secret: Any,
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    _production_authorized(authority)
    out = _generate(beacon=beacon, evaluator_secret=evaluator_secret, namespace="UDIR")
    out["authority_claim_id"] = str(authority["one_use_claim_id"])
    out["production"] = True
    return out


def generate_test_fixture_population() -> dict[str, Any]:
    out = _generate(
        beacon="TEST-ONLY-BEACON-DOES-NOT-AUTHORIZE-REALITY",
        evaluator_secret=b"TEST-ONLY-SECRET-0123456789-ABCDEFGHIJK",
        namespace="TESTONLY",
    )
    out["production"] = False
    out["hard_nonclaim"] = "TEST_FIXTURES_ARE_NOT_PRODUCTION_OR_TERMINAL_CASES"
    return out
