"""Collision-total hidden generator V3 for the two Unknown-Domain direct leaves.

V3 preserves V2's numeric/task semantics and the frozen visible/hidden packet
schemas. It changes only identifier construction: every finite identifier scope
is assigned by a secret-dependent permutation onto unique ordinal slots.

The permutation ordering is HMAC-derived, but uniqueness does NOT depend on HMAC
collision resistance. Even if every ranking digest ties, the deterministic
label tie-break still assigns distinct ranks. Domain A/B feature vocabularies
remain independently permuted and disjoint.

No production case is generated on import or verification. Production generation
still requires the exact V1 predicate-local one-use authority gate.
"""
from __future__ import annotations

import hashlib
import hmac
from typing import Any, Mapping, Sequence

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as v1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as v2

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_HIDDEN_GENERATOR_V3"


def _rank_digest(secret: bytes, beacon: str, scope: str, label: str) -> bytes:
    msg = "|".join((beacon, "UDIR_V3_PERM", scope, label)).encode()
    return hmac.new(secret, msg, hashlib.sha256).digest()


def _opaque_bijection(
    secret: bytes,
    beacon: str,
    *,
    scope: str,
    labels: Sequence[str],
    prefix: str,
) -> dict[str, str]:
    rows = [str(x) for x in labels]
    if not rows or len(rows) != len(set(rows)):
        raise v1.UnknownDomainGeneratorError("V3_BIJECTION_LABEL_SET_INVALID")
    ranked = sorted(rows, key=lambda x: (_rank_digest(secret, beacon, scope, x), x))
    width = max(2, len(str(len(ranked) - 1)))
    out = {label: f"{prefix}{rank:0{width}d}" for rank, label in enumerate(ranked)}
    if len(set(out.values())) != len(rows):
        raise AssertionError("V3_BIJECTION_INTERNAL_NONINJECTIVE")
    return out


def _case_id_map(secret: bytes, beacon: str, namespace: str) -> dict[tuple[str, int], str]:
    labels = [
        *(f"T:{i}" for i in range(v1.PRODUCTION_CASE_COUNTS[v1.TRANSFER])),
        *(f"A:{i}" for i in range(v1.PRODUCTION_CASE_COUNTS[v1.ABSTAIN])),
    ]
    perm = _opaque_bijection(
        secret,
        beacon,
        scope=namespace + "|CASES",
        labels=labels,
        prefix=f"{namespace}-C-",
    )
    return {
        (v1.TRANSFER if label.startswith("T:") else v1.ABSTAIN, int(label.split(":")[1])): cid
        for label, cid in perm.items()
    }


def _surface_ids_total(
    secret: bytes,
    beacon: str,
    index: int,
    domain: str,
    roles: list[str],
) -> tuple[dict[str, str], list[str]]:
    role_labels = [f"ROLE:{r}" for r in roles]
    distractor_labels = ["DISTRACTOR:0", "DISTRACTOR:1"]
    labels = role_labels + distractor_labels
    perm = _opaque_bijection(
        secret,
        beacon,
        scope=f"{domain}|CASE:{index}|FEATURES",
        labels=labels,
        prefix=f"{domain.lower()}_f",
    )
    mapping = {role: perm[f"ROLE:{role}"] for role in roles}
    distractors = [perm[f"DISTRACTOR:{i}"] for i in range(2)]
    if len(set(mapping.values()) | set(distractors)) != len(roles) + 2:
        raise AssertionError("V3_SURFACE_ID_TOTALITY_BROKEN")
    return mapping, distractors


def _local_ids(
    secret: bytes,
    beacon: str,
    *,
    case_id: str,
    kind: str,
    labels: Sequence[str],
) -> dict[str, str]:
    tag = case_id.rsplit("-", 1)[-1]
    return _opaque_bijection(
        secret,
        beacon,
        scope=f"{case_id}|{kind}",
        labels=labels,
        prefix=f"{kind}-{tag}-",
    )


def _transfer_case(
    secret: bytes,
    beacon: str,
    index: int,
    *,
    namespace: str,
    case_id: str,
):
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
        raise AssertionError("V3_DOMAIN_VOCABULARY_DISJOINTNESS_BROKEN")

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

    receipt_id = "R-" + case_id.rsplit("-", 1)[-1]
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

    probe_ids = _local_ids(
        secret,
        beacon,
        case_id=case_id,
        kind="P",
        labels=("0", "1"),
    )
    probes = []
    probe_hidden = {}
    for j, row in enumerate(target_rows[3:5]):
        pid = probe_ids[str(j)]
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
    }
    return visible, hidden


def _abstention_case(
    secret: bytes,
    beacon: str,
    index: int,
    *,
    namespace: str,
    case_id: str,
):
    cls = v1.ABSTAIN_CLASSES[index // 5]
    ids = _local_ids(
        secret,
        beacon,
        case_id=case_id,
        kind="H",
        labels=("0", "1"),
    )
    h1, h2 = ids["0"], ids["1"]

    action_ids = _local_ids(
        secret,
        beacon,
        case_id=case_id,
        kind="A",
        labels=("0", "1"),
    )
    a = action_ids["0"]
    b = a if cls == "IDENTIFIABLE" else action_ids["1"]

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
    probe_ids = _local_ids(
        secret,
        beacon,
        case_id=case_id,
        kind="D",
        labels=("0", "1"),
    )
    if cls == "UNDERSPECIFIED":
        p0, p1 = probe_ids["0"], probe_ids["1"]
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
        p0 = probe_ids["0"]
        probes = [
            {
                "probe_id": p0,
                "argument_schema": {"type": "SAFE_OBSERVATION"},
                "cost": 1,
            }
        ]
        table = {p0: {h1: "SAME", h2: "SAME"}}

    visible = {
        "case_id": case_id,
        "leaf_id": v1.ABSTAIN,
        "hypotheses": hypotheses,
        "public_observations": {"OBS-0": "VISIBLE"},
        "allowed_probes": probes,
        "decision_requirement": (
            "CONCLUDE_OR_ABSTAIN_OR_REQUEST_DISCRIMINATOR"
        ),
    }
    hidden = {
        "case_id": case_id,
        "leaf_id": v1.ABSTAIN,
        "identifiability_status": cls,
        "equivalence_classes": [[h1, h2]] if a == b else [[h1], [h2]],
        "gold_terminal_consequence": a if cls == "IDENTIFIABLE" else None,
        "minimum_discriminator_id": minimum,
        "allowed_probe_outcome_table": table,
    }
    return visible, hidden


def _validate_totality(visible: Sequence[Mapping[str, Any]], hidden: Sequence[Mapping[str, Any]]) -> None:
    case_ids = [str(x["case_id"]) for x in visible]
    if len(case_ids) != len(set(case_ids)):
        raise AssertionError("V3_CASE_ID_NONINJECTIVE")
    if [str(x["case_id"]) for x in hidden] != case_ids:
        raise AssertionError("V3_VISIBLE_HIDDEN_CASE_ID_ALIGNMENT_BROKEN")

    for v, h in zip(visible, hidden):
        if v["leaf_id"] == v1.TRANSFER:
            roles = list(h["latent_primitive_program"]["roles"])
            relevant = list(h["transfer_relevant_feature_ids"])
            distractors = list(h["distractor_feature_ids"])
            if len(relevant) != len(roles) or len(relevant) != len(set(relevant)):
                raise AssertionError("V3_RELEVANT_FEATURE_ID_TOTALITY_BROKEN")
            if len(distractors) != 2 or len(distractors) != len(set(distractors)):
                raise AssertionError("V3_DISTRACTOR_ID_TOTALITY_BROKEN")
            if set(relevant) & set(distractors):
                raise AssertionError("V3_RELEVANT_DISTRACTOR_DISJOINTNESS_BROKEN")
            pids = [str(x["probe_id"]) for x in v["domain_b"]["allowed_probes"]]
            if len(pids) != len(set(pids)):
                raise AssertionError("V3_TRANSFER_PROBE_ID_TOTALITY_BROKEN")
            if set(pids) != set(h["allowed_probe_outcome_table"]):
                raise AssertionError("V3_TRANSFER_PROBE_TABLE_ALIGNMENT_BROKEN")
        else:
            hids = [str(x["hypothesis_id"]) for x in v["hypotheses"]]
            if len(hids) != len(set(hids)):
                raise AssertionError("V3_HYPOTHESIS_ID_TOTALITY_BROKEN")
            pids = [str(x["probe_id"]) for x in v["allowed_probes"]]
            if len(pids) != len(set(pids)):
                raise AssertionError("V3_ABSTENTION_PROBE_ID_TOTALITY_BROKEN")
            status = str(h["identifiability_status"])
            consequences = [str(x["terminal_consequence"]) for x in v["hypotheses"]]
            if status == "IDENTIFIABLE" and len(set(consequences)) != 1:
                raise AssertionError("V3_IDENTIFIABLE_ACTION_EQUIVALENCE_BROKEN")
            if status != "IDENTIFIABLE" and len(set(consequences)) != 2:
                raise AssertionError("V3_DISTINCT_ACTION_TOTALITY_BROKEN")


def _generate(*, beacon: str, evaluator_secret: Any, namespace: str):
    if not isinstance(beacon, str) or len(beacon.strip()) < 16:
        raise v1.UnknownDomainGeneratorError("POST_FREEZE_BEACON_INVALID")
    secret = v1._secret_bytes(evaluator_secret)
    case_ids = _case_id_map(secret, beacon, namespace)

    visible = []
    hidden = []
    for i in range(v1.PRODUCTION_CASE_COUNTS[v1.TRANSFER]):
        a, b = _transfer_case(
            secret,
            beacon,
            i,
            namespace=namespace,
            case_id=case_ids[(v1.TRANSFER, i)],
        )
        visible.append(a)
        hidden.append(b)
    for i in range(v1.PRODUCTION_CASE_COUNTS[v1.ABSTAIN]):
        a, b = _abstention_case(
            secret,
            beacon,
            i,
            namespace=namespace,
            case_id=case_ids[(v1.ABSTAIN, i)],
        )
        visible.append(a)
        hidden.append(b)

    _validate_totality(visible, hidden)
    return {
        "schema": SCHEMA,
        "case_count": 27,
        "visible_cases": visible,
        "hidden_records": hidden,
        "visible_packet_digest": v1._sha256(visible),
        "hidden_packet_digest": v1._sha256(hidden),
        "identifier_construction": (
            "SECRET_DEPENDENT_FINITE_BIJECTION__UNIQUENESS_INDEPENDENT_OF_HASH_COLLISION"
        ),
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


def generate_qualification_fixture_population(*, beacon: str):
    if not isinstance(beacon, str) or len(beacon.strip()) < 16:
        raise v1.UnknownDomainGeneratorError("QUALIFICATION_BEACON_INVALID")
    out = _generate(
        beacon="QUALIFICATION-ONLY|" + beacon,
        evaluator_secret=b"QUALIFICATION-ONLY-SECRET-0123456789-ABCDEFG",
        namespace="QUALONLY3",
    )
    out["production"] = False
    out["hard_nonclaim"] = (
        "QUALIFICATION_FIXTURES_ARE_NOT_PRODUCTION_OR_TERMINAL_CASES"
    )
    return out
