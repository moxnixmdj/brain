"""Collision-total hardening of the frozen Unknown-Domain V2 generator.

V3 preserves V2 numeric/task semantics and ordinary opaque identifiers.  The
only delta is deterministic disambiguation when truncated opaque HMAC labels
collide.  This removes a finite-namespace hole from universal reasoning without
reading or generating terminal/production reality on import.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as v1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as v2

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_HIDDEN_GENERATOR_V3_COLLISION_TOTAL"

TRANSFER = v1.TRANSFER
ABSTAIN = v1.ABSTAIN
TARGET_PREDICATE = v1.TARGET_PREDICATE
PRODUCTION_CASE_COUNTS = v1.PRODUCTION_CASE_COUNTS
ABSTAIN_CLASSES = v1.ABSTAIN_CLASSES
PRIMITIVE_FAMILIES = v1.PRIMITIVE_FAMILIES


def _disambiguate(prefix: str, rows: list[tuple[str, str, str]]) -> dict[str, str]:
    """Map semantic keys to injective public ids.

    rows are (semantic_key, raw_truncated_token, secret_rank_token).  Ordinary
    singleton tokens are byte-for-byte compatible with V2.  Only colliding raw
    tokens receive a suffix.  Rank-token ties fall back to the internal semantic
    key, so uniqueness does not depend on any cryptographic collision claim.
    """
    groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for key, raw, rank in rows:
        groups[str(raw)].append((str(key), str(rank)))

    out: dict[str, str] = {}
    for raw, members in groups.items():
        if len(members) == 1:
            key, _ = members[0]
            out[key] = prefix + raw
            continue
        ordered = sorted(members, key=lambda x: (x[1], x[0]))
        for i, (key, _) in enumerate(ordered):
            out[key] = f"{prefix}{raw}_c{i}"

    if len(out) != len(rows) or len(set(out.values())) != len(rows):
        raise v1.UnknownDomainGeneratorError("OPAQUE_ID_DISAMBIGUATION_FAILED")
    return out


def _opaque_ids(
    secret: bytes,
    beacon: str,
    *,
    prefix: str,
    context: tuple[Any, ...],
    specs: list[tuple[str, tuple[Any, ...]]],
    width: int = 14,
) -> dict[str, str]:
    rows = []
    for key, parts in specs:
        raw = v1._token(secret, beacon, *parts, width=width)
        rank = v1._token(
            secret,
            beacon,
            "collision-rank",
            *context,
            key,
            width=64,
        )
        rows.append((key, raw, rank))
    return _disambiguate(prefix, rows)


def _surface_ids(
    secret: bytes,
    beacon: str,
    case_index: int,
    domain: str,
    roles: list[str],
) -> tuple[dict[str, str], list[str]]:
    specs: list[tuple[str, tuple[Any, ...]]] = []
    for role in roles:
        specs.append((f"role:{role}", ("feature", case_index, domain, role)))
    for i in range(2):
        specs.append((f"distractor:{i}", ("distractor", case_index, domain, i)))
    ids = _opaque_ids(
        secret,
        beacon,
        prefix=domain.lower() + "_",
        context=("surface", case_index, domain),
        specs=specs,
    )
    mapping = {role: ids[f"role:{role}"] for role in roles}
    distractors = [ids[f"distractor:{i}"] for i in range(2)]
    if len(set(mapping.values())) != len(mapping):
        raise v1.UnknownDomainGeneratorError("OPAQUE_ROLE_ID_COLLISION")
    if len(set(distractors)) != len(distractors):
        raise v1.UnknownDomainGeneratorError("OPAQUE_DISTRACTOR_ID_COLLISION")
    if set(mapping.values()) & set(distractors):
        raise v1.UnknownDomainGeneratorError("OPAQUE_FEATURE_COLLISION")
    return mapping, distractors


def _transfer_case(secret: bytes, beacon: str, index: int, *, namespace: str):
    family, program, roles = v2._program_for(secret, beacon, index)
    fingerprint = v1._sha256(program)
    source_rows = v2._role_rows(secret, beacon, index, program, domain="A")
    target_rows = v2._role_rows(secret, beacon, index, program, domain="B")
    a_map, a_distractors = _surface_ids(secret, beacon, index, namespace + "_A", roles)
    b_map, b_distractors = _surface_ids(secret, beacon, index, namespace + "_B", roles)
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

    probe_ids = _opaque_ids(
        secret,
        beacon,
        prefix="P-",
        context=("transfer-probes", index, namespace),
        specs=[
            (str(j), ("probe", index, j, namespace))
            for j in range(2)
        ],
    )
    probes = []
    probe_hidden = {}
    for j, row in enumerate(target_rows[3:5]):
        pid = probe_ids[str(j)]
        probes.append({
            "probe_id": pid,
            "argument_schema": {"type": "OBSERVE_PRECOMMITTED_ROW", "row_slot": j},
            "cost": j + 1,
        })
        probe_hidden[pid] = {
            "inputs": v1._surface_row(row, b_map, b_distractors, mimic_visible=False, probe_variant=j),
            "terminal_consequence": v1._eval(program, row),
        }

    query_roles = target_rows[5]
    query_inputs = v1._surface_row(query_roles, b_map, b_distractors, mimic_visible=False, probe_variant=9)
    case_id = f"{namespace}-T-{v1._token(secret, beacon, 'case', v1.TRANSFER, index, namespace, width=20)}"
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
    hids = _opaque_ids(
        secret,
        beacon,
        prefix="H-",
        context=("hypotheses", index, namespace),
        specs=[
            ("h1", ("hyp", index, 1, namespace)),
            ("h2", ("hyp", index, 2, namespace)),
        ],
    )
    h1, h2 = hids["h1"], hids["h2"]

    if cls == "IDENTIFIABLE":
        a = f"A-{v1._token(secret, beacon, 'action', index, 1, namespace)}"
        b = a
    else:
        actions = _opaque_ids(
            secret,
            beacon,
            prefix="A-",
            context=("actions", index, namespace),
            specs=[
                ("a", ("action", index, 1, namespace)),
                ("b", ("action", index, 2, namespace)),
            ],
        )
        a, b = actions["a"], actions["b"]

    hypotheses = [
        {"hypothesis_id": h1, "plausible": True, "terminal_consequence": a, "evidence": ["OBS-0"]},
        {"hypothesis_id": h2, "plausible": True, "terminal_consequence": b, "evidence": ["OBS-0"]},
    ]
    probes = []
    table = {}
    minimum = None
    if cls == "UNDERSPECIFIED":
        pids = _opaque_ids(
            secret,
            beacon,
            prefix="P-",
            context=("abstention-discriminators", index, namespace),
            specs=[
                ("p0", ("disc", index, 0, namespace)),
                ("p1", ("disc", index, 1, namespace)),
            ],
        )
        p0, p1 = pids["p0"], pids["p1"]
        probes = [
            {"probe_id": p0, "argument_schema": {"type": "SAFE_BINARY_DISCRIMINATOR"}, "cost": 1},
            {"probe_id": p1, "argument_schema": {"type": "SAFE_BINARY_DISCRIMINATOR"}, "cost": 2},
        ]
        table = {p0: {h1: "LEFT", h2: "RIGHT"}, p1: {h1: "LEFT", h2: "RIGHT"}}
        minimum = p0
    elif cls == "NONIDENTIFIABLE":
        p0 = f"P-{v1._token(secret, beacon, 'nondisc', index, 0, namespace)}"
        probes = [{"probe_id": p0, "argument_schema": {"type": "SAFE_OBSERVATION"}, "cost": 1}]
        table = {p0: {h1: "SAME", h2: "SAME"}}

    case_id = f"{namespace}-A-{v1._token(secret, beacon, 'case', v1.ABSTAIN, index, namespace, width=20)}"
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


def _dedupe_case_ids(visible: list[dict[str, Any]], hidden: list[dict[str, Any]]) -> None:
    groups: dict[str, list[int]] = defaultdict(list)
    for i, row in enumerate(visible):
        groups[str(row["case_id"])].append(i)
    for raw, indexes in groups.items():
        if len(indexes) == 1:
            continue
        for rank, i in enumerate(indexes):
            new = f"{raw}_c{rank}"
            visible[i]["case_id"] = new
            hidden[i]["case_id"] = new
    ids = [str(x["case_id"]) for x in visible]
    if len(ids) != len(set(ids)):
        raise v1.UnknownDomainGeneratorError("CASE_ID_SET_INVALID_AFTER_DISAMBIGUATION")


def _generate(*, beacon: str, evaluator_secret: Any, namespace: str):
    if not isinstance(beacon, str) or len(beacon.strip()) < 16:
        raise v1.UnknownDomainGeneratorError("POST_FREEZE_BEACON_INVALID")
    secret = v1._secret_bytes(evaluator_secret)
    visible: list[dict[str, Any]] = []
    hidden: list[dict[str, Any]] = []
    for i in range(v1.PRODUCTION_CASE_COUNTS[v1.TRANSFER]):
        a, b = _transfer_case(secret, beacon, i, namespace=namespace)
        visible.append(a)
        hidden.append(b)
    for i in range(v1.PRODUCTION_CASE_COUNTS[v1.ABSTAIN]):
        a, b = _abstention_case(secret, beacon, i, namespace=namespace)
        visible.append(a)
        hidden.append(b)
    _dedupe_case_ids(visible, hidden)
    return {
        "schema": SCHEMA,
        "case_count": 27,
        "visible_cases": visible,
        "hidden_records": hidden,
        "visible_packet_digest": v1._sha256(visible),
        "hidden_packet_digest": v1._sha256(hidden),
    }


def generate_production_population(*, beacon: str, evaluator_secret: Any, authority: Mapping[str, Any]):
    v1._production_authorized(authority)
    out = _generate(beacon=beacon, evaluator_secret=evaluator_secret, namespace="UDIR")
    out["authority_claim_id"] = str(authority["one_use_claim_id"])
    out["production"] = True
    return out


def generate_qualification_fixture_population(*, beacon: str):
    if not isinstance(beacon, str) or len(beacon.strip()) < 16:
        raise v1.UnknownDomainGeneratorError("QUALIFICATION_BEACON_INVALID")
    out = _generate(
        beacon="QUALIFICATION-ONLY|" + beacon,
        evaluator_secret=b"QUALIFICATION-ONLY-SECRET-0123456789-ABCDEFG",
        namespace="QUALONLY",
    )
    out["production"] = False
    out["hard_nonclaim"] = "QUALIFICATION_FIXTURES_ARE_NOT_PRODUCTION_OR_TERMINAL_CASES"
    return out
