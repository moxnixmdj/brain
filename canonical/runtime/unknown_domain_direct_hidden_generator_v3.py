"""Unknown-Domain hidden generator V3 with structurally total opaque IDs.

V2 truncated HMAC labels could collide for some valid secret/beacon values. V3
keeps every semantic task distribution unchanged but assigns each semantic
feature to a secret-randomized *slot*. The slot ordinal is unique by
construction and its semantic assignment is hidden by an HMAC ranking. Opaque
suffixes remain for unlinkability; uniqueness no longer depends on them.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as v1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as v2

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_HIDDEN_GENERATOR_V3"


def _surface_ids_total(
    secret: bytes,
    beacon: str,
    case_index: int,
    domain: str,
    roles: list[str],
) -> tuple[dict[str, str], list[str]]:
    semantic = [("role", role) for role in roles] + [("distractor", str(i)) for i in range(2)]

    ranked = []
    for kind, key in semantic:
        rank = v1._token(
            secret, beacon, "opaque-slot-rank", case_index, domain, kind, key, width=64
        )
        ranked.append((rank, kind, key))
    # The semantic key is a deterministic tie-breaker. Even a full-HMAC tie
    # therefore cannot collapse identifiers; it only selects a stable slot order.
    ranked.sort()

    label_by_semantic = {}
    for slot, (_, kind, key) in enumerate(ranked):
        opaque = v1._token(
            secret, beacon, "opaque-label", case_index, domain, slot, width=14
        )
        label_by_semantic[(kind, key)] = f"{domain.lower()}_f{slot}_{opaque}"

    mapping = {role: label_by_semantic[("role", role)] for role in roles}
    distractors = [label_by_semantic[("distractor", str(i))] for i in range(2)]

    all_ids = list(mapping.values()) + distractors
    if len(all_ids) != len(set(all_ids)):
        raise AssertionError("STRUCTURAL_OPAQUE_ID_TOTALITY_BROKEN")
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
        raise AssertionError("STRUCTURAL_CROSS_DOMAIN_ID_TOTALITY_BROKEN")

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

    receipt_id = f"R-{v1._token(secret, beacon, 'receipt', index, namespace)}"
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
        pid = f"P-{v1._token(secret, beacon, 'probe', index, j, namespace)}"
        probes.append({
            "probe_id": pid,
            "argument_schema": {"type": "OBSERVE_PRECOMMITTED_ROW", "row_slot": j},
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
    case_id = (
        f"{namespace}-T-"
        f"{v1._token(secret, beacon, 'case', v1.TRANSFER, index, namespace, width=20)}"
    )
    visible = {
        "case_id": case_id,
        "leaf_id": v1.TRANSFER,
        "domain_a": {"tasks": source_observations, "earned_receipts": [receipt]},
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
        "opaque_identifier_scheme": "SECRET_RANDOMIZED_STRUCTURALLY_UNIQUE_SLOT_V3",
    }
    return visible, hidden


def _generate(*, beacon: str, evaluator_secret: Any, namespace: str):
    if not isinstance(beacon, str) or len(beacon.strip()) < 16:
        raise v1.UnknownDomainGeneratorError("POST_FREEZE_BEACON_INVALID")
    secret = v1._secret_bytes(evaluator_secret)
    visible = []
    hidden = []
    for i in range(v1.PRODUCTION_CASE_COUNTS[v1.TRANSFER]):
        a, b = _transfer_case(secret, beacon, i, namespace=namespace)
        visible.append(a)
        hidden.append(b)
    for i in range(v1.PRODUCTION_CASE_COUNTS[v1.ABSTAIN]):
        a, b = v1._abstention_case(secret, beacon, i, namespace=namespace)
        visible.append(a)
        hidden.append(b)

    ids = [x["case_id"] for x in visible]
    if len(ids) != 27 or len(ids) != len(set(ids)):
        raise v1.UnknownDomainGeneratorError("CASE_ID_SET_INVALID")
    return {
        "schema": SCHEMA,
        "case_count": 27,
        "visible_cases": visible,
        "hidden_records": hidden,
        "visible_packet_digest": v1._sha256(visible),
        "hidden_packet_digest": v1._sha256(hidden),
    }


def generate_production_population(
    *, beacon: str, evaluator_secret: Any, authority: Mapping[str, Any]
):
    v1._production_authorized(authority)
    out = _generate(beacon=beacon, evaluator_secret=evaluator_secret, namespace="UDIR3")
    out["authority_claim_id"] = str(authority["one_use_claim_id"])
    out["production"] = True
    return out


def generate_qualification_fixture_population(*, beacon: str):
    if not isinstance(beacon, str) or len(beacon.strip()) < 16:
        raise v1.UnknownDomainGeneratorError("QUALIFICATION_BEACON_INVALID")
    out = _generate(
        beacon="QUALIFICATION-ONLY|" + beacon,
        evaluator_secret=b"QUALIFICATION-ONLY-SECRET-0123456789-ABCDEFG",
        namespace="QUALONLY3",
    )
    out["production"] = False
    out["hard_nonclaim"] = "QUALIFICATION_FIXTURES_ARE_NOT_PRODUCTION_OR_TERMINAL_CASES"
    return out
