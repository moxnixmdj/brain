"""Collision-totalized hidden generator V3 for Unknown-Domain direct evaluation.

V3 preserves the V2 numeric/program semantics but removes every probabilistic
identifier-uniqueness assumption. Opaque identifiers are assigned by keyed
permutations over fixed finite slot sets. A permutation may vary with the
secret/beacon, but it is bijective for every possible HMAC output, so semantic
roles, distractors, hypotheses, actions, probes, receipts, and case IDs cannot
collapse through token collisions.

No production case is generated on import. Production generation retains the
exact V1 predicate-local one-use authority gate.
"""
from __future__ import annotations

import hashlib
import hmac
from typing import Any, Mapping

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as v1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as v2

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_HIDDEN_GENERATOR_V3"
IDENTIFIER_CONSTRUCTION = "KEYED_FISHER_YATES_PERMUTATION_OVER_FIXED_OPAQUE_SLOTS"
IDENTIFIER_TOTALITY = "DETERMINISTIC_BIJECTION_FOR_EVERY_SECRET_BEACON__NO_HASH_UNIQUENESS_ASSUMPTION"


def _draw(secret: bytes, beacon: str, label: str, step: int) -> int:
    msg = f"{beacon}|V3PERM|{label}|{step}".encode()
    return int.from_bytes(hmac.new(secret, msg, hashlib.sha256).digest(), "big")


def _perm(secret: bytes, beacon: str, label: str, n: int) -> tuple[int, ...]:
    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        raise v1.UnknownDomainGeneratorError("PERMUTATION_SIZE_INVALID")
    out = list(range(n))
    for i in range(n - 1, 0, -1):
        j = _draw(secret, beacon, label, i) % (i + 1)
        out[i], out[j] = out[j], out[i]
    result = tuple(out)
    if len(result) != n or set(result) != set(range(n)):
        raise v1.UnknownDomainGeneratorError("PERMUTATION_BIJECTION_BROKEN")
    return result


def _case_tag(secret: bytes, beacon: str, namespace: str, kind: str, index: int, total: int) -> int:
    if index < 0 or index >= total:
        raise v1.UnknownDomainGeneratorError("CASE_INDEX_INVALID")
    return _perm(secret, beacon, f"{namespace}|case|{kind}", total)[index]


def _surface_ids(
    secret: bytes,
    beacon: str,
    *,
    namespace: str,
    domain: str,
    case_index: int,
    case_tag: int,
    roles: list[str],
) -> tuple[dict[str, str], list[str]]:
    semantic_slots = list(roles) + ["__d0", "__d1"]
    perm = _perm(
        secret,
        beacon,
        f"{namespace}|surface|{domain}|{case_index}|{','.join(semantic_slots)}",
        len(semantic_slots),
    )
    prefix = f"{namespace.lower()}_{domain.lower()}_c{case_tag:02d}"
    opaque = [f"{prefix}_q{i}" for i in range(len(semantic_slots))]
    assigned = {slot: opaque[perm[pos]] for pos, slot in enumerate(semantic_slots)}
    mapping = {role: assigned[role] for role in roles}
    distractors = [assigned["__d0"], assigned["__d1"]]
    all_ids = list(mapping.values()) + distractors
    if len(all_ids) != len(set(all_ids)):
        raise v1.UnknownDomainGeneratorError("V3_SURFACE_IDENTIFIER_NONINJECTIVE")
    return mapping, distractors


def _two_unique_ids(secret: bytes, beacon: str, *, label: str, prefix: str) -> tuple[str, str]:
    p = _perm(secret, beacon, label, 2)
    a = f"{prefix}-q{p[0]}"
    b = f"{prefix}-q{p[1]}"
    if a == b:
        raise v1.UnknownDomainGeneratorError("V3_PAIR_IDENTIFIER_NONINJECTIVE")
    return a, b


def _transfer_case(secret: bytes, beacon: str, index: int, *, namespace: str):
    family, program, roles = v2._program_for(secret, beacon, index)
    fingerprint = v1._sha256(program)
    source_rows = v2._role_rows(secret, beacon, index, program, domain="A")
    target_rows = v2._role_rows(secret, beacon, index, program, domain="B")
    tag = _case_tag(secret, beacon, namespace, "TRANSFER", index, v1.PRODUCTION_CASE_COUNTS[v1.TRANSFER])

    a_map, a_distractors = _surface_ids(
        secret, beacon, namespace=namespace, domain="A", case_index=index, case_tag=tag, roles=roles
    )
    b_map, b_distractors = _surface_ids(
        secret, beacon, namespace=namespace, domain="B", case_index=index, case_tag=tag, roles=roles
    )
    if (set(a_map.values()) | set(a_distractors)) & (set(b_map.values()) | set(b_distractors)):
        raise v1.UnknownDomainGeneratorError("DOMAIN_VOCABULARY_OVERLAP")

    source_observations = []
    for j, row in enumerate(source_rows[:3]):
        source_observations.append({
            "inputs": v1._surface_row(row, a_map, a_distractors, mimic_visible=False, probe_variant=j),
            "terminal_consequence": v1._eval(program, row),
        })

    target_observations = []
    for j, row in enumerate(target_rows[:3]):
        target_observations.append({
            "inputs": v1._surface_row(row, b_map, b_distractors, mimic_visible=True, probe_variant=j),
            "terminal_consequence": v1._eval(program, row),
        })

    receipt_id = f"R-{namespace}-c{tag:02d}"
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

    probe_slots = _perm(secret, beacon, f"{namespace}|transfer-probes|{index}", 2)
    probes = []
    probe_hidden = {}
    for j, row in enumerate(target_rows[3:5]):
        pid = f"P-{namespace}-c{tag:02d}-q{probe_slots[j]}"
        public = {
            "probe_id": pid,
            "argument_schema": {"type": "OBSERVE_PRECOMMITTED_ROW", "row_slot": j},
            "cost": j + 1,
        }
        result = {
            "inputs": v1._surface_row(row, b_map, b_distractors, mimic_visible=False, probe_variant=j),
            "terminal_consequence": v1._eval(program, row),
        }
        probes.append(public)
        probe_hidden[pid] = result
    if len({p["probe_id"] for p in probes}) != 2:
        raise v1.UnknownDomainGeneratorError("V3_TRANSFER_PROBE_ID_NONINJECTIVE")

    query_roles = target_rows[5]
    query_inputs = v1._surface_row(query_roles, b_map, b_distractors, mimic_visible=False, probe_variant=9)
    case_id = f"{namespace}-T-c{tag:02d}"
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
    if len(relevant) != len(set(relevant)) or len(b_distractors) != len(set(b_distractors)):
        raise v1.UnknownDomainGeneratorError("V3_HIDDEN_SUPPORT_IDENTIFIER_NONINJECTIVE")
    return visible, hidden


def _abstention_case(secret: bytes, beacon: str, index: int, *, namespace: str):
    cls = v1.ABSTAIN_CLASSES[index // 5]
    tag = _case_tag(secret, beacon, namespace, "ABSTAIN", index, v1.PRODUCTION_CASE_COUNTS[v1.ABSTAIN])
    h1, h2 = _two_unique_ids(
        secret, beacon,
        label=f"{namespace}|abstain-hyp|{index}",
        prefix=f"H-{namespace}-c{tag:02d}",
    )
    action1, action2 = _two_unique_ids(
        secret, beacon,
        label=f"{namespace}|abstain-action|{index}",
        prefix=f"A-{namespace}-c{tag:02d}",
    )
    a = action1
    b = a if cls == "IDENTIFIABLE" else action2
    hypotheses = [
        {"hypothesis_id": h1, "plausible": True, "terminal_consequence": a, "evidence": ["OBS-0"]},
        {"hypothesis_id": h2, "plausible": True, "terminal_consequence": b, "evidence": ["OBS-0"]},
    ]

    probes = []
    table = {}
    minimum = None
    if cls == "UNDERSPECIFIED":
        p0, p1 = _two_unique_ids(
            secret, beacon,
            label=f"{namespace}|abstain-disc|{index}",
            prefix=f"P-{namespace}-c{tag:02d}",
        )
        probes = [
            {"probe_id": p0, "argument_schema": {"type": "SAFE_BINARY_DISCRIMINATOR"}, "cost": 1},
            {"probe_id": p1, "argument_schema": {"type": "SAFE_BINARY_DISCRIMINATOR"}, "cost": 2},
        ]
        table = {p0: {h1: "LEFT", h2: "RIGHT"}, p1: {h1: "LEFT", h2: "RIGHT"}}
        minimum = p0
    elif cls == "NONIDENTIFIABLE":
        p0 = f"P-{namespace}-c{tag:02d}-obs"
        probes = [{"probe_id": p0, "argument_schema": {"type": "SAFE_OBSERVATION"}, "cost": 1}]
        table = {p0: {h1: "SAME", h2: "SAME"}}

    case_id = f"{namespace}-A-c{tag:02d}"
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
    if h1 == h2:
        raise v1.UnknownDomainGeneratorError("V3_HYPOTHESIS_ID_NONINJECTIVE")
    if cls != "IDENTIFIABLE" and a == b:
        raise v1.UnknownDomainGeneratorError("V3_DISTINCT_ACTIONS_COLLAPSED")
    if len({p["probe_id"] for p in probes}) != len(probes):
        raise v1.UnknownDomainGeneratorError("V3_ABSTENTION_PROBE_ID_NONINJECTIVE")
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
        a, b = _abstention_case(secret, beacon, i, namespace=namespace)
        visible.append(a)
        hidden.append(b)
    ids = [x["case_id"] for x in visible]
    if len(ids) != 27 or len(ids) != len(set(ids)):
        raise v1.UnknownDomainGeneratorError("V3_CASE_ID_SET_INVALID")
    return {
        "schema": SCHEMA,
        "case_count": 27,
        "visible_cases": visible,
        "hidden_records": hidden,
        "visible_packet_digest": v1._sha256(visible),
        "hidden_packet_digest": v1._sha256(hidden),
        "identifier_construction": IDENTIFIER_CONSTRUCTION,
        "identifier_totality": IDENTIFIER_TOTALITY,
    }


def generate_production_population(*, beacon: str, evaluator_secret: Any, authority: Mapping[str, Any]):
    v1._production_authorized(authority)
    out = _generate(beacon=beacon, evaluator_secret=evaluator_secret, namespace="UDIRV3")
    out["authority_claim_id"] = str(authority["one_use_claim_id"])
    out["production"] = True
    return out


def generate_qualification_fixture_population(*, beacon: str):
    if not isinstance(beacon, str) or len(beacon.strip()) < 16:
        raise v1.UnknownDomainGeneratorError("QUALIFICATION_BEACON_INVALID")
    out = _generate(
        beacon="QUALIFICATION-ONLY|V3|"+beacon,
        evaluator_secret=b"QUALIFICATION-ONLY-V3-SECRET-0123456789-ABCDEFG",
        namespace="QUALV3",
    )
    out["production"] = False
    out["hard_nonclaim"] = "QUALIFICATION_FIXTURES_ARE_NOT_PRODUCTION_OR_TERMINAL_CASES"
    return out
