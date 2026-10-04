"""Unknown-Domain direct hidden generator V4: full structural identifier totality.

V4 preserves V2's program, numeric-row, perturbation, evaluation, class-balance,
probe-budget, and authority semantics. It changes only opaque identifier
construction so no correctness property depends on truncated-HMAC uniqueness.

Every load-bearing identifier contains a structural discriminator:
* feature IDs: domain + case index + secret-permuted unique slot;
* receipt IDs: transfer case index;
* transfer probe IDs: transfer case index + probe ordinal;
* case IDs: leaf kind + case index;
* hypothesis/action IDs: abstention case index + local ordinal;
* abstention probe IDs: abstention marker + case index + probe ordinal.

HMAC material remains only for opacity/randomization. Even if every HMAC token
collides, required semantic identities remain injective by construction.
"""
from __future__ import annotations

import hashlib
import hmac
from typing import Any, Mapping

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as v1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as v2

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_HIDDEN_GENERATOR_V4"
IDENTIFIER_TOTALITY = (
    "STRUCTURAL_DISCRIMINATORS_PLUS_SECRET_PERMUTED_FEATURE_SLOTS__"
    "NO_IDENTIFIER_CORRECTNESS_DEPENDS_ON_HMAC_COLLISION_FREEDOM"
)


def _permutation(
    secret: bytes,
    beacon: str,
    case_index: int,
    domain: str,
    count: int,
) -> tuple[int, ...]:
    if count not in (3, 4):
        raise v1.UnknownDomainGeneratorError("V4_SLOT_COUNT_UNSUPPORTED")
    msg = f"{beacon}|V4-slot-permutation|{case_index}|{domain}|{count}".encode()
    seed = int.from_bytes(hmac.new(secret, msg, hashlib.sha256).digest(), "big")
    values = list(range(count))
    for i in range(count - 1, 0, -1):
        j = seed % (i + 1)
        values[i], values[j] = values[j], values[i]
        seed //= i + 1
    result = tuple(values)
    if len(result) != count or set(result) != set(range(count)):
        raise AssertionError("V4_PERMUTATION_BIJECTION_BROKEN")
    return result


def _surface_ids_total(
    secret: bytes,
    beacon: str,
    case_index: int,
    domain: str,
    roles: list[str],
) -> tuple[dict[str, str], list[str]]:
    items = [("role", role) for role in roles] + [
        ("distractor", str(i)) for i in range(2)
    ]
    perm = _permutation(secret, beacon, case_index, domain, len(items))
    ids: list[str] = []
    for semantic_index, (kind, label) in enumerate(items):
        slot = perm[semantic_index]
        token = v1._token(
            secret,
            beacon,
            "feature-v4",
            case_index,
            domain,
            kind,
            label,
        )
        ids.append(f"{domain.lower()}_t{case_index:02d}_u{slot}_{token}")

    if len(ids) != len(set(ids)):
        raise AssertionError("V4_STRUCTURAL_FEATURE_ID_TOTALITY_BROKEN")
    mapping = {role: ids[i] for i, role in enumerate(roles)}
    distractors = ids[len(roles):]
    if set(mapping.values()) & set(distractors):
        raise AssertionError("V4_STRUCTURAL_ROLE_DISTRACTOR_DISJOINTNESS_BROKEN")
    return mapping, distractors


def _transfer_case(secret: bytes, beacon: str, index: int, *, namespace: str):
    family, program, roles = v2._program_for(secret, beacon, index)
    fingerprint = v1._sha256(program)
    source_rows = v2._role_rows(secret, beacon, index, program, domain="A")
    target_rows = v2._role_rows(secret, beacon, index, program, domain="B")

    a_map, a_distractors = _surface_ids_total(
        secret, beacon, index, namespace + "_A", roles
    )
    b_map, b_distractors = _surface_ids_total(
        secret, beacon, index, namespace + "_B", roles
    )
    if (set(a_map.values()) | set(a_distractors)) & (
        set(b_map.values()) | set(b_distractors)
    ):
        raise AssertionError("V4_STRUCTURAL_DOMAIN_VOCABULARY_DISJOINTNESS_BROKEN")

    source_observations = []
    for j, row in enumerate(source_rows[:3]):
        source_observations.append({
            "inputs": v1._surface_row(
                row, a_map, a_distractors, mimic_visible=False, probe_variant=j
            ),
            "terminal_consequence": v1._eval(program, row),
        })

    target_observations = []
    for j, row in enumerate(target_rows[:3]):
        target_observations.append({
            "inputs": v1._surface_row(
                row, b_map, b_distractors, mimic_visible=True, probe_variant=j
            ),
            "terminal_consequence": v1._eval(program, row),
        })

    receipt_token = v1._token(secret, beacon, "receipt-v4", index, namespace)
    receipt_id = f"R-{namespace}-T-{index:02d}-{receipt_token}"
    receipt = {
        "receipt_id": receipt_id,
        "normalized_primitive_program": program,
        "primitive_fingerprint": fingerprint,
        "source_role_binding": dict(a_map),
        "source_evidence_digest": v1._sha256(source_observations),
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
    }

    probes = []
    probe_hidden = {}
    for j, row in enumerate(target_rows[3:5]):
        token = v1._token(secret, beacon, "probe-v4", index, j, namespace)
        pid = f"P-{namespace}-T-{index:02d}-{j}-{token}"
        probes.append({
            "probe_id": pid,
            "argument_schema": {
                "type": "OBSERVE_PRECOMMITTED_ROW",
                "row_slot": j,
            },
            "cost": j + 1,
        })
        probe_hidden[pid] = {
            "inputs": v1._surface_row(
                row, b_map, b_distractors, mimic_visible=False, probe_variant=j
            ),
            "terminal_consequence": v1._eval(program, row),
        }

    query_roles = target_rows[5]
    query_inputs = v1._surface_row(
        query_roles, b_map, b_distractors, mimic_visible=False, probe_variant=9
    )
    case_token = v1._token(
        secret, beacon, "case-v4", v1.TRANSFER, index, namespace, width=20
    )
    case_id = f"{namespace}-T-{index:02d}-{case_token}"

    visible = {
        "case_id": case_id,
        "leaf_id": v1.TRANSFER,
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
        "decision_requirement": (
            "PREDICT_TERMINAL_CONSEQUENCE_AND_PROVIDE_TRANSFER_PROOF_TRACE"
        ),
    }
    relevant = [b_map[r] for r in roles]
    hidden = {
        "case_id": case_id,
        "leaf_id": v1.TRANSFER,
        "primitive_family": family,
        "latent_primitive_program": program,
        "latent_primitive_fingerprint": fingerprint,
        "domain_mapping": dict(b_map),
        "domain_a_earned_receipt_ids": [receipt_id],
        "domain_a_receipt_primitive_bindings": {receipt_id: fingerprint},
        "transfer_relevant_feature_ids": relevant,
        "distractor_feature_ids": list(b_distractors),
        "gold_terminal_consequence": v1._eval(program, query_roles),
        "full_rediscovery_probe_floor": 3,
        "surface_label_permutation_verified": True,
        "domain_vocabularies_disjoint": True,
        "allowed_probe_outcome_table": probe_hidden,
        "opaque_identifier_scheme": IDENTIFIER_TOTALITY,
    }
    return visible, hidden


def _abstention_case(secret: bytes, beacon: str, index: int, *, namespace: str):
    cls = v1.ABSTAIN_CLASSES[index // 5]

    h1 = (
        f"H-{namespace}-A-{index:02d}-0-"
        f"{v1._token(secret, beacon, 'hyp-v4', index, 0, namespace)}"
    )
    h2 = (
        f"H-{namespace}-A-{index:02d}-1-"
        f"{v1._token(secret, beacon, 'hyp-v4', index, 1, namespace)}"
    )
    a = (
        f"A-{namespace}-A-{index:02d}-0-"
        f"{v1._token(secret, beacon, 'action-v4', index, 0, namespace)}"
    )
    b = (
        a
        if cls == "IDENTIFIABLE"
        else (
            f"A-{namespace}-A-{index:02d}-1-"
            f"{v1._token(secret, beacon, 'action-v4', index, 1, namespace)}"
        )
    )

    if h1 == h2:
        raise AssertionError("V4_STRUCTURAL_HYPOTHESIS_ID_TOTALITY_BROKEN")
    if cls != "IDENTIFIABLE" and a == b:
        raise AssertionError("V4_STRUCTURAL_ACTION_ID_TOTALITY_BROKEN")

    hypotheses = [
        {
            "hypothesis_id": h1,
            "plausible": True,
            "terminal_consequence": a,
            "evidence": ["OBS-0"],
        },
        {
            "hypothesis_id": h2,
            "plausible": True,
            "terminal_consequence": b,
            "evidence": ["OBS-0"],
        },
    ]
    probes = []
    table = {}
    minimum = None

    if cls == "UNDERSPECIFIED":
        p0 = (
            f"P-{namespace}-A-{index:02d}-0-"
            f"{v1._token(secret, beacon, 'disc-v4', index, 0, namespace)}"
        )
        p1 = (
            f"P-{namespace}-A-{index:02d}-1-"
            f"{v1._token(secret, beacon, 'disc-v4', index, 1, namespace)}"
        )
        probes = [
            {
                "probe_id": p0,
                "argument_schema": {"type": "SAFE_BINARY_DISCRIMINATOR"},
                "cost": 1,
            },
            {
                "probe_id": p1,
                "argument_schema": {"type": "SAFE_BINARY_DISCRIMINATOR"},
                "cost": 2,
            },
        ]
        table = {
            p0: {h1: "LEFT", h2: "RIGHT"},
            p1: {h1: "LEFT", h2: "RIGHT"},
        }
        minimum = p0
    elif cls == "NONIDENTIFIABLE":
        p0 = (
            f"P-{namespace}-A-{index:02d}-0-"
            f"{v1._token(secret, beacon, 'nondisc-v4', index, 0, namespace)}"
        )
        probes = [{
            "probe_id": p0,
            "argument_schema": {"type": "SAFE_OBSERVATION"},
            "cost": 1,
        }]
        table = {p0: {h1: "SAME", h2: "SAME"}}

    case_token = v1._token(
        secret, beacon, "case-v4", v1.ABSTAIN, index, namespace, width=20
    )
    case_id = f"{namespace}-A-{index:02d}-{case_token}"
    visible = {
        "case_id": case_id,
        "leaf_id": v1.ABSTAIN,
        "hypotheses": hypotheses,
        "public_observations": {"OBS-0": "VISIBLE"},
        "allowed_probes": probes,
        "decision_requirement": "CONCLUDE_OR_ABSTAIN_OR_REQUEST_DISCRIMINATOR",
    }
    hidden = {
        "case_id": case_id,
        "leaf_id": v1.ABSTAIN,
        "identifiability_status": cls,
        "equivalence_classes": [[h1, h2]] if a == b else [[h1], [h2]],
        "gold_terminal_consequence": a if cls == "IDENTIFIABLE" else None,
        "minimum_discriminator_id": minimum,
        "allowed_probe_outcome_table": table,
        "opaque_identifier_scheme": IDENTIFIER_TOTALITY,
    }
    return visible, hidden


def _generate(*, beacon: str, evaluator_secret: Any, namespace: str):
    if not isinstance(beacon, str) or len(beacon.strip()) < 16:
        raise v1.UnknownDomainGeneratorError("POST_FREEZE_BEACON_INVALID")
    secret = v1._secret_bytes(evaluator_secret)
    visible = []
    hidden = []
    for i in range(v1.PRODUCTION_CASE_COUNTS[v1.TRANSFER]):
        v, h = _transfer_case(secret, beacon, i, namespace=namespace)
        visible.append(v)
        hidden.append(h)
    for i in range(v1.PRODUCTION_CASE_COUNTS[v1.ABSTAIN]):
        v, h = _abstention_case(secret, beacon, i, namespace=namespace)
        visible.append(v)
        hidden.append(h)

    ids = [x["case_id"] for x in visible]
    if len(ids) != 27 or len(ids) != len(set(ids)):
        raise AssertionError("V4_STRUCTURAL_CASE_ID_TOTALITY_BROKEN")
    return {
        "schema": SCHEMA,
        "case_count": 27,
        "visible_cases": visible,
        "hidden_records": hidden,
        "visible_packet_digest": v1._sha256(visible),
        "hidden_packet_digest": v1._sha256(hidden),
        "identifier_totality": IDENTIFIER_TOTALITY,
    }


def generate_production_population(
    *,
    beacon: str,
    evaluator_secret: Any,
    authority: Mapping[str, Any],
):
    v1._production_authorized(authority)
    out = _generate(
        beacon=beacon,
        evaluator_secret=evaluator_secret,
        namespace="UDIR4",
    )
    out["authority_claim_id"] = str(authority["one_use_claim_id"])
    out["production"] = True
    return out


def generate_qualification_fixture_population(*, beacon: str):
    if not isinstance(beacon, str) or len(beacon.strip()) < 16:
        raise v1.UnknownDomainGeneratorError("QUALIFICATION_BEACON_INVALID")
    out = _generate(
        beacon="QUALIFICATION-ONLY|V4|" + beacon,
        evaluator_secret=b"QUALIFICATION-ONLY-V4-SECRET-0123456789-ABCDEFG",
        namespace="QUALONLY4",
    )
    out["production"] = False
    out["hard_nonclaim"] = (
        "QUALIFICATION_FIXTURES_ARE_NOT_PRODUCTION_OR_TERMINAL_CASES"
    )
    return out
