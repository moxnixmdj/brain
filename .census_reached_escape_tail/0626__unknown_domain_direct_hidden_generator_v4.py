"""Unknown-Domain hidden generator V4 with total evaluator-visible identifiers.

V4 preserves V2 numeric/task semantics and V3 structural feature labels, while
making every evaluator-visible identifier collision-proof by construction.
Secret HMAC ranks only permute unique slot ordinals; uniqueness comes from the
ordinal, never from a truncated digest.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as v1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as v2

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_HIDDEN_GENERATOR_V4"


def _ranked_labels(
    secret: bytes,
    beacon: str,
    *,
    scope: str,
    keys: Sequence[str],
    prefix: str,
) -> dict[str, str]:
    ks = [str(x) for x in keys]
    if len(ks) != len(set(ks)):
        raise v1.UnknownDomainGeneratorError("STRUCTURAL_LABEL_KEYS_DUPLICATE")
    ranked = sorted(
        (
            v1._token(secret, beacon, "rank", scope, key, width=64),
            key,
        )
        for key in ks
    )
    out: dict[str, str] = {}
    for slot, (_, key) in enumerate(ranked):
        suffix = v1._token(secret, beacon, "label", scope, slot, width=14)
        out[key] = f"{prefix}{slot}_{suffix}"
    if len(set(out.values())) != len(out):
        raise AssertionError("STRUCTURAL_LABEL_TOTALITY_BROKEN")
    return out


def _surface_ids_total(
    secret: bytes,
    beacon: str,
    case_index: int,
    domain: str,
    roles: list[str],
) -> tuple[dict[str, str], list[str]]:
    keys = ["role:" + r for r in roles] + ["distractor:0", "distractor:1"]
    labels = _ranked_labels(
        secret,
        beacon,
        scope=f"surface|{case_index}|{domain}",
        keys=keys,
        prefix=f"{domain.lower()}_f",
    )
    mapping = {r: labels["role:" + r] for r in roles}
    distractors = [labels["distractor:0"], labels["distractor:1"]]
    return mapping, distractors


def _case_ids(secret: bytes, beacon: str, namespace: str) -> dict[str, str]:
    keys = [f"T:{i}" for i in range(v1.PRODUCTION_CASE_COUNTS[v1.TRANSFER])]
    keys += [f"A:{i}" for i in range(v1.PRODUCTION_CASE_COUNTS[v1.ABSTAIN])]
    return _ranked_labels(
        secret,
        beacon,
        scope=f"caseids|{namespace}",
        keys=keys,
        prefix=f"{namespace}-C-",
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
        raise AssertionError("STRUCTURAL_CROSS_DOMAIN_ID_TOTALITY_BROKEN")

    source_observations = [
        {
            "inputs": v1._surface_row(
                row, a_map, a_distractors, mimic_visible=False, probe_variant=j
            ),
            "terminal_consequence": v1._eval(program, row),
        }
        for j, row in enumerate(source_rows[:3])
    ]
    target_observations = [
        {
            "inputs": v1._surface_row(
                row, b_map, b_distractors, mimic_visible=True, probe_variant=j
            ),
            "terminal_consequence": v1._eval(program, row),
        }
        for j, row in enumerate(target_rows[:3])
    ]

    receipt_id = _ranked_labels(
        secret,
        beacon,
        scope=f"receipt|{namespace}|{index}",
        keys=["receipt"],
        prefix="R-",
    )["receipt"]
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

    probe_ids = _ranked_labels(
        secret,
        beacon,
        scope=f"transfer-probes|{namespace}|{index}",
        keys=["p0", "p1"],
        prefix="P-",
    )
    probes = []
    probe_hidden = {}
    for j, row in enumerate(target_rows[3:5]):
        pid = probe_ids[f"p{j}"]
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
        "identifier_scheme": "SECRET_RANKED_STRUCTURALLY_UNIQUE_SLOTS_V4",
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
    hypothesis_ids = _ranked_labels(
        secret,
        beacon,
        scope=f"hypotheses|{namespace}|{index}",
        keys=["h0", "h1"],
        prefix="H-",
    )
    action_ids = _ranked_labels(
        secret,
        beacon,
        scope=f"actions|{namespace}|{index}",
        keys=["a0", "a1"],
        prefix="A-",
    )
    h1 = hypothesis_ids["h0"]
    h2 = hypothesis_ids["h1"]
    a = action_ids["a0"]
    b = a if cls == "IDENTIFIABLE" else action_ids["a1"]

    hypotheses = [
        {"hypothesis_id": h1, "plausible": True, "terminal_consequence": a, "evidence": ["OBS-0"]},
        {"hypothesis_id": h2, "plausible": True, "terminal_consequence": b, "evidence": ["OBS-0"]},
    ]

    probes = []
    table = {}
    minimum = None
    if cls == "UNDERSPECIFIED":
        pids = _ranked_labels(
            secret,
            beacon,
            scope=f"abstain-probes|{namespace}|{index}",
            keys=["p0", "p1"],
            prefix="P-",
        )
        p0, p1 = pids["p0"], pids["p1"]
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
        p0 = _ranked_labels(
            secret,
            beacon,
            scope=f"abstain-probes|{namespace}|{index}",
            keys=["p0"],
            prefix="P-",
        )["p0"]
        probes = [{"probe_id": p0, "argument_schema": {"type": "SAFE_OBSERVATION"}, "cost": 1}]
        table = {p0: {h1: "SAME", h2: "SAME"}}

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
        "identifier_scheme": "SECRET_RANKED_STRUCTURALLY_UNIQUE_SLOTS_V4",
    }
    return visible, hidden


def _generate(*, beacon: str, evaluator_secret: Any, namespace: str):
    if not isinstance(beacon, str) or len(beacon.strip()) < 16:
        raise v1.UnknownDomainGeneratorError("POST_FREEZE_BEACON_INVALID")
    secret = v1._secret_bytes(evaluator_secret)
    ids = _case_ids(secret, beacon, namespace)
    visible = []
    hidden = []
    for i in range(v1.PRODUCTION_CASE_COUNTS[v1.TRANSFER]):
        a, b = _transfer_case(
            secret, beacon, i, namespace=namespace, case_id=ids[f"T:{i}"]
        )
        visible.append(a)
        hidden.append(b)
    for i in range(v1.PRODUCTION_CASE_COUNTS[v1.ABSTAIN]):
        a, b = _abstention_case(
            secret, beacon, i, namespace=namespace, case_id=ids[f"A:{i}"]
        )
        visible.append(a)
        hidden.append(b)

    case_ids = [x["case_id"] for x in visible]
    if len(case_ids) != 27 or len(case_ids) != len(set(case_ids)):
        raise AssertionError("STRUCTURAL_CASE_ID_TOTALITY_BROKEN")
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
    out = _generate(beacon=beacon, evaluator_secret=evaluator_secret, namespace="UDIR4")
    out["authority_claim_id"] = str(authority["one_use_claim_id"])
    out["production"] = True
    return out


def generate_qualification_fixture_population(*, beacon: str):
    if not isinstance(beacon, str) or len(beacon.strip()) < 16:
        raise v1.UnknownDomainGeneratorError("QUALIFICATION_BEACON_INVALID")
    out = _generate(
        beacon="QUALIFICATION-ONLY|" + beacon,
        evaluator_secret=b"QUALIFICATION-ONLY-SECRET-0123456789-ABCDEFG",
        namespace="QUALONLY4",
    )
    out["production"] = False
    out["hard_nonclaim"] = "QUALIFICATION_FIXTURES_ARE_NOT_PRODUCTION_OR_TERMINAL_CASES"
    return out
