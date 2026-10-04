"""Collision-total Unknown-Domain direct hidden generator V3.

V3 preserves V2 task semantics, numeric generation, task counts, authority gate,
and visible decision contract.  Its only semantic-independent change is the
opaque identifier constructor: every finite identifier group is assigned a
keyed permutation rank, and that explicit rank is part of the identifier.

Therefore identifier uniqueness does not depend on collision resistance of a
truncated HMAC.  HMAC still randomizes the permutation and group decoration, but
even adversarially identical HMAC outputs cannot collapse two semantic slots.
"""
from __future__ import annotations

import hashlib
import hmac
from typing import Any, Mapping, Sequence

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as v1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as v2

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_HIDDEN_GENERATOR_V3_COLLISION_TOTAL"


def _draw(secret: bytes, beacon: str, *parts: Any) -> int:
    msg = "|".join([beacon] + [str(x) for x in parts]).encode()
    return int.from_bytes(hmac.new(secret, msg, hashlib.sha256).digest(), "big")


def _rank_from_swaps(labels: Sequence[str], swaps: Sequence[int]) -> dict[str, int]:
    """Pure Fisher-Yates core. Every legal swap sequence yields a permutation."""
    arr = [str(x) for x in labels]
    if len(arr) != len(set(arr)):
        raise v1.UnknownDomainGeneratorError("V3_PERMUTATION_LABELS_NOT_UNIQUE")
    if len(swaps) != max(0, len(arr) - 1):
        raise v1.UnknownDomainGeneratorError("V3_SWAP_COUNT_INVALID")
    for k, i in enumerate(range(len(arr) - 1, 0, -1)):
        j = swaps[k]
        if isinstance(j, bool) or not isinstance(j, int) or not (0 <= j <= i):
            raise v1.UnknownDomainGeneratorError("V3_SWAP_INDEX_INVALID")
        arr[i], arr[j] = arr[j], arr[i]
    return {label: rank for rank, label in enumerate(arr)}


def _keyed_ranks(
    secret: bytes,
    beacon: str,
    labels: Sequence[str],
    *context: Any,
) -> dict[str, int]:
    n = len(labels)
    swaps = []
    for i in range(n - 1, 0, -1):
        swaps.append(_draw(secret, beacon, "V3_PERM", *context, i) % (i + 1))
    return _rank_from_swaps(labels, swaps)


def _group_token(secret: bytes, beacon: str, *parts: Any) -> str:
    return v1._token(secret, beacon, "V3_GROUP", *parts, width=14)


def _surface_ids(
    secret: bytes,
    beacon: str,
    case_index: int,
    domain: str,
    roles: Sequence[str],
) -> tuple[dict[str, str], list[str]]:
    role_labels = [f"ROLE:{r}" for r in roles]
    distractor_labels = ["DISTRACTOR:0", "DISTRACTOR:1"]
    labels = role_labels + distractor_labels
    ranks = _keyed_ranks(secret, beacon, labels, "SURFACE", case_index, domain)
    group = _group_token(secret, beacon, "SURFACE", case_index, domain)

    def oid(label: str) -> str:
        # domain + case index give cross-group disjointness; rank gives
        # within-group injectivity independently of HMAC collision behavior.
        return f"{domain.lower()}_{case_index:02d}_{group}_{ranks[label]:02d}"

    mapping = {str(r): oid(f"ROLE:{r}") for r in roles}
    distractors = [oid("DISTRACTOR:0"), oid("DISTRACTOR:1")]
    vals = list(mapping.values()) + distractors
    if len(vals) != len(set(vals)):
        raise v1.UnknownDomainGeneratorError("V3_SURFACE_ID_INJECTIVITY_BROKEN")
    return mapping, distractors


def _case_token(secret: bytes, beacon: str, namespace: str, leaf: str, index: int) -> str:
    return _group_token(secret, beacon, "CASE", namespace, leaf, index)


def _transfer_case(secret: bytes, beacon: str, index: int, *, namespace: str):
    family, program, roles = v2._program_for(secret, beacon, index)
    fingerprint = v1._sha256(program)
    source_rows = v2._role_rows(secret, beacon, index, program, domain="A")
    target_rows = v2._role_rows(secret, beacon, index, program, domain="B")
    a_map, a_distractors = _surface_ids(secret, beacon, index, namespace + "_A", roles)
    b_map, b_distractors = _surface_ids(secret, beacon, index, namespace + "_B", roles)

    a_ids = set(a_map.values()) | set(a_distractors)
    b_ids = set(b_map.values()) | set(b_distractors)
    if a_ids & b_ids:
        raise v1.UnknownDomainGeneratorError("V3_DOMAIN_VOCABULARY_OVERLAP")

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

    receipt_id = (
        f"R-{namespace}-{index:02d}-"
        f"{_group_token(secret, beacon, 'RECEIPT', namespace, index)}"
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
            f"P-{namespace}-{index:02d}-{j}-"
            f"{_group_token(secret, beacon, 'PROBE', namespace, index, j)}"
        )
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

    if len({p["probe_id"] for p in probes}) != 2:
        raise v1.UnknownDomainGeneratorError("V3_TRANSFER_PROBE_ID_INJECTIVITY_BROKEN")

    query_roles = target_rows[5]
    query_inputs = v1._surface_row(
        query_roles, b_map, b_distractors, mimic_visible=False, probe_variant=9
    )
    case_id = (
        f"{namespace}-T-{index:02d}-"
        f"{_case_token(secret, beacon, namespace, 'T', index)}"
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
    }
    return visible, hidden


def _abstention_case(secret: bytes, beacon: str, index: int, *, namespace: str):
    cls = v1.ABSTAIN_CLASSES[index // 5]
    labels = ("H1", "H2", "A1", "A2", "D0", "D1", "N0")
    ranks = _keyed_ranks(secret, beacon, labels, "ABSTAIN", namespace, index)
    group = _group_token(secret, beacon, "ABSTAIN", namespace, index)

    def oid(prefix: str, label: str) -> str:
        return f"{prefix}-{namespace}-{index:02d}-{group}-{ranks[label]:02d}"

    h1, h2 = oid("H", "H1"), oid("H", "H2")
    a = oid("A", "A1")
    b = a if cls == "IDENTIFIABLE" else oid("A", "A2")
    if h1 == h2:
        raise v1.UnknownDomainGeneratorError("V3_HYPOTHESIS_ID_INJECTIVITY_BROKEN")
    if cls != "IDENTIFIABLE" and a == b:
        raise v1.UnknownDomainGeneratorError("V3_ACTION_ID_INJECTIVITY_BROKEN")

    hypotheses = [
        {"hypothesis_id": h1, "plausible": True, "terminal_consequence": a, "evidence": ["OBS-0"]},
        {"hypothesis_id": h2, "plausible": True, "terminal_consequence": b, "evidence": ["OBS-0"]},
    ]
    probes = []
    table = {}
    minimum = None
    if cls == "UNDERSPECIFIED":
        p0, p1 = oid("P", "D0"), oid("P", "D1")
        probes = [
            {"probe_id": p0, "argument_schema": {"type": "SAFE_BINARY_DISCRIMINATOR"}, "cost": 1},
            {"probe_id": p1, "argument_schema": {"type": "SAFE_BINARY_DISCRIMINATOR"}, "cost": 2},
        ]
        table = {p0: {h1: "LEFT", h2: "RIGHT"}, p1: {h1: "LEFT", h2: "RIGHT"}}
        minimum = p0
        if p0 == p1:
            raise v1.UnknownDomainGeneratorError("V3_DISCRIMINATOR_ID_INJECTIVITY_BROKEN")
    elif cls == "NONIDENTIFIABLE":
        p0 = oid("P", "N0")
        probes = [
            {"probe_id": p0, "argument_schema": {"type": "SAFE_OBSERVATION"}, "cost": 1}
        ]
        table = {p0: {h1: "SAME", h2: "SAME"}}

    case_id = (
        f"{namespace}-A-{index:02d}-"
        f"{_case_token(secret, beacon, namespace, 'A', index)}"
    )
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
    }
    return visible, hidden


def _validate_population(packet: Mapping[str, Any]) -> None:
    visible = packet.get("visible_cases")
    hidden = packet.get("hidden_records")
    if not isinstance(visible, list) or not isinstance(hidden, list) or len(visible) != 27 or len(hidden) != 27:
        raise v1.UnknownDomainGeneratorError("V3_PACKET_CARDINALITY_INVALID")
    case_ids = [str(x.get("case_id") or "") for x in visible]
    if any(not x for x in case_ids) or len(case_ids) != len(set(case_ids)):
        raise v1.UnknownDomainGeneratorError("V3_CASE_ID_INJECTIVITY_BROKEN")

    for v, h in zip(visible, hidden):
        if v.get("case_id") != h.get("case_id") or v.get("leaf_id") != h.get("leaf_id"):
            raise v1.UnknownDomainGeneratorError("V3_VISIBLE_HIDDEN_BINDING_INVALID")
        if h.get("leaf_id") == v1.TRANSFER:
            rel = [str(x) for x in h.get("transfer_relevant_feature_ids", [])]
            dist = [str(x) for x in h.get("distractor_feature_ids", [])]
            if len(rel) != len(set(rel)) or len(dist) != len(set(dist)) or set(rel) & set(dist):
                raise v1.UnknownDomainGeneratorError("V3_TRANSFER_FEATURE_PARTITION_INVALID")
            pids = [str(x.get("probe_id") or "") for x in v["domain_b"]["allowed_probes"]]
            if len(pids) != len(set(pids)):
                raise v1.UnknownDomainGeneratorError("V3_TRANSFER_PROBE_PARTITION_INVALID")
        else:
            hyps = v.get("hypotheses", [])
            hids = [str(x.get("hypothesis_id") or "") for x in hyps]
            if len(hids) != 2 or len(set(hids)) != 2:
                raise v1.UnknownDomainGeneratorError("V3_ABSTENTION_HYPOTHESES_INVALID")
            status = h.get("identifiability_status")
            consequences = [str(x.get("terminal_consequence") or "") for x in hyps]
            if status == "IDENTIFIABLE" and len(set(consequences)) != 1:
                raise v1.UnknownDomainGeneratorError("V3_IDENTIFIABLE_CONSEQUENCE_PARTITION_INVALID")
            if status in {"NONIDENTIFIABLE", "UNDERSPECIFIED"} and len(set(consequences)) != 2:
                raise v1.UnknownDomainGeneratorError("V3_NONUNIQUE_CONSEQUENCE_PARTITION_INVALID")


def _generate(*, beacon: str, evaluator_secret: Any, namespace: str) -> dict[str, Any]:
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
    out = {
        "schema": SCHEMA,
        "case_count": 27,
        "visible_cases": visible,
        "hidden_records": hidden,
        "visible_packet_digest": v1._sha256(visible),
        "hidden_packet_digest": v1._sha256(hidden),
    }
    _validate_population(out)
    return out


def generate_production_population(
    *,
    beacon: str,
    evaluator_secret: Any,
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    v1._production_authorized(authority)
    out = _generate(beacon=beacon, evaluator_secret=evaluator_secret, namespace="UDIR3")
    out["authority_claim_id"] = str(authority["one_use_claim_id"])
    out["production"] = True
    return out


def generate_qualification_fixture_population(*, beacon: str) -> dict[str, Any]:
    if not isinstance(beacon, str) or len(beacon.strip()) < 16:
        raise v1.UnknownDomainGeneratorError("QUALIFICATION_BEACON_INVALID")
    out = _generate(
        beacon="QUALIFICATION-ONLY|"+beacon,
        evaluator_secret=b"QUALIFICATION-ONLY-SECRET-0123456789-ABCDEFG",
        namespace="QUALONLY3",
    )
    out["production"] = False
    out["hard_nonclaim"] = "QUALIFICATION_FIXTURES_ARE_NOT_PRODUCTION_OR_TERMINAL_CASES"
    return out
