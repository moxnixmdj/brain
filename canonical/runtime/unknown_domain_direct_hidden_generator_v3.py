"""Unknown-Domain direct hidden generator V3.

V3 preserves the V2 task family, parameter ranges, row distributions, authority
gate, case counts, probe budget, and abstention semantics while repairing two
non-semantic defects discovered before production:

1. ADD2 uses the canonical permutation-invariant V3 numeric semantics.
2. Every load-bearing opaque identifier is unique by construction.  HMAC is
   used only to choose a secret permutation and opaque suffix, never as the
   sole uniqueness mechanism.

No production case is generated on import or verification.
"""
from __future__ import annotations

import hashlib
import hmac
from typing import Any, Mapping

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as v1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as v2
from canonical.runtime import unknown_domain_direct_v3_semantics_v1 as sem

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_HIDDEN_GENERATOR_V3"
TRANSFER = v1.TRANSFER
ABSTAIN = v1.ABSTAIN


def _rank(secret: bytes, beacon: str, tag: str, index: int, count: int) -> int:
    if not 0 <= index < count:
        raise v1.UnknownDomainGeneratorError("RANK_INDEX_OUT_OF_RANGE")
    keyed = []
    for i in range(count):
        msg = f"{beacon}|V3-RANK|{tag}|{i}".encode()
        keyed.append((hmac.new(secret, msg, hashlib.sha256).digest(), i))
    ordered = [i for _, i in sorted(keyed)]
    return ordered.index(index)


def _opaque_suffix(secret: bytes, beacon: str, *parts: Any) -> str:
    msg = "|".join([beacon, "V3-ID"] + [str(x) for x in parts]).encode()
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()[:14]


def _surface_ids_total(
    secret: bytes,
    beacon: str,
    case_index: int,
    domain: str,
    roles: list[str],
) -> tuple[dict[str, str], list[str]]:
    logical = [("ROLE", role) for role in roles] + [("DIST", str(i)) for i in range(2)]
    keyed = []
    for kind, label in logical:
        msg = f"{beacon}|V3-SURFACE-RANK|{case_index}|{domain}|{kind}|{label}".encode()
        keyed.append((hmac.new(secret, msg, hashlib.sha256).digest(), kind, label))
    ordered = [(kind, label) for _, kind, label in sorted(keyed)]
    alias = {}
    for rank, (kind, label) in enumerate(ordered):
        # rank makes equality impossible inside the domain even if every HMAC
        # suffix collides.  The rank-to-role assignment is secret-permuted.
        alias[(kind, label)] = (
            f"{domain.lower()}_f{rank}_"
            + _opaque_suffix(secret, beacon, case_index, domain, kind, label)
        )
    mapping = {role: alias[("ROLE", role)] for role in roles}
    distractors = [alias[("DIST", str(i))] for i in range(2)]
    assert len(set(mapping.values()) | set(distractors)) == len(roles) + 2
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
        raise v1.UnknownDomainGeneratorError("DOMAIN_VOCABULARY_OVERLAP")

    source_observations = []
    for j, row in enumerate(source_rows[:3]):
        source_observations.append({
            "inputs": v1._surface_row(
                row, a_map, a_distractors, mimic_visible=False, probe_variant=j
            ),
            "terminal_consequence": sem.eval_program(program, row),
        })

    target_observations = []
    for j, row in enumerate(target_rows[:3]):
        target_observations.append({
            "inputs": v1._surface_row(
                row, b_map, b_distractors, mimic_visible=True, probe_variant=j
            ),
            "terminal_consequence": sem.eval_program(program, row),
        })

    case_rank = _rank(secret, beacon, "TRANSFER_CASE", index, v1.PRODUCTION_CASE_COUNTS[TRANSFER])
    receipt_id = (
        f"R3-{case_rank}-"
        + _opaque_suffix(secret, beacon, "receipt", index, namespace)
    )
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
        pid = (
            f"P3-{case_rank}-{j}-"
            + _opaque_suffix(secret, beacon, "probe", index, j, namespace)
        )
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
            "terminal_consequence": sem.eval_program(program, row),
        }

    query_roles = target_rows[5]
    query_inputs = v1._surface_row(
        query_roles, b_map, b_distractors, mimic_visible=False, probe_variant=9
    )
    case_id = (
        f"{namespace}-T3-{case_rank}-"
        + _opaque_suffix(secret, beacon, "case", TRANSFER, index, namespace)
    )
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
        "decision_requirement": (
            "PREDICT_TERMINAL_CONSEQUENCE_AND_PROVIDE_TRANSFER_PROOF_TRACE"
        ),
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
        "gold_terminal_consequence": sem.eval_program(program, query_roles),
        "full_rediscovery_probe_floor": 3,
        "surface_label_permutation_verified": True,
        "domain_vocabularies_disjoint": True,
        "allowed_probe_outcome_table": probe_hidden,
    }
    return visible, hidden


def _abstention_case(secret: bytes, beacon: str, index: int, *, namespace: str):
    cls = v1.ABSTAIN_CLASSES[index // 5]
    case_rank = _rank(secret, beacon, "ABSTAIN_CASE", index, v1.PRODUCTION_CASE_COUNTS[ABSTAIN])

    h1 = (
        f"H3-{case_rank}-0-"
        + _opaque_suffix(secret, beacon, "hyp", index, 0, namespace)
    )
    h2 = (
        f"H3-{case_rank}-1-"
        + _opaque_suffix(secret, beacon, "hyp", index, 1, namespace)
    )
    a = (
        f"A3-{case_rank}-0-"
        + _opaque_suffix(secret, beacon, "action", index, 0, namespace)
    )
    b = a if cls == "IDENTIFIABLE" else (
        f"A3-{case_rank}-1-"
        + _opaque_suffix(secret, beacon, "action", index, 1, namespace)
    )
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
            f"PD3-{case_rank}-0-"
            + _opaque_suffix(secret, beacon, "disc", index, 0, namespace)
        )
        p1 = (
            f"PD3-{case_rank}-1-"
            + _opaque_suffix(secret, beacon, "disc", index, 1, namespace)
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
            f"PN3-{case_rank}-0-"
            + _opaque_suffix(secret, beacon, "nondisc", index, 0, namespace)
        )
        probes = [{
            "probe_id": p0,
            "argument_schema": {"type": "SAFE_OBSERVATION"},
            "cost": 1,
        }]
        table = {p0: {h1: "SAME", h2: "SAME"}}

    case_id = (
        f"{namespace}-A3-{case_rank}-"
        + _opaque_suffix(secret, beacon, "case", ABSTAIN, index, namespace)
    )
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


def _generate(*, beacon: str, evaluator_secret: Any, namespace: str):
    if not isinstance(beacon, str) or len(beacon.strip()) < 16:
        raise v1.UnknownDomainGeneratorError("POST_FREEZE_BEACON_INVALID")
    secret = v1._secret_bytes(evaluator_secret)
    visible = []
    hidden = []
    for i in range(v1.PRODUCTION_CASE_COUNTS[TRANSFER]):
        a, b = _transfer_case(secret, beacon, i, namespace=namespace)
        visible.append(a)
        hidden.append(b)
    for i in range(v1.PRODUCTION_CASE_COUNTS[ABSTAIN]):
        a, b = _abstention_case(secret, beacon, i, namespace=namespace)
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
    *,
    beacon: str,
    evaluator_secret: Any,
    authority: Mapping[str, Any],
):
    v1._production_authorized(authority)
    out = _generate(
        beacon=beacon,
        evaluator_secret=evaluator_secret,
        namespace="UDIR3",
    )
    out["authority_claim_id"] = str(authority["one_use_claim_id"])
    out["production"] = True
    return out


def generate_test_fixture_population():
    out = _generate(
        beacon="TEST-ONLY-V3-BEACON-DOES-NOT-AUTHORIZE-REALITY",
        evaluator_secret=b"TEST-ONLY-V3-SECRET-0123456789-ABCDEFGHIJK",
        namespace="TESTONLYV3",
    )
    out["production"] = False
    out["hard_nonclaim"] = "TEST_FIXTURES_ARE_NOT_PRODUCTION_OR_TERMINAL_CASES"
    return out
