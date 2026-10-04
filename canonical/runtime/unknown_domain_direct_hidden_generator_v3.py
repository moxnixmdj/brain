"""Unknown-Domain direct hidden generator V3.

V3 is an additive totality guard over the frozen V2 semantic generator.  V2 uses
truncated HMAC-derived opaque identifiers but did not reject every intra-packet
collision class.  V3 emits exactly the same packet when identifiers are
injective and fails closed before returning a population otherwise.

No production population is created by import or qualification.  Production
still requires the V1 predicate-local one-use authority gate.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as v1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as v2

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_HIDDEN_GENERATOR_V3"


def _require_unique(values, code: str) -> None:
    rows = [str(x) for x in values]
    if not rows or len(rows) != len(set(rows)):
        raise v1.UnknownDomainGeneratorError(code)


def _validate_transfer_packet(visible: Mapping[str, Any], hidden: Mapping[str, Any]) -> None:
    mapping = hidden.get("domain_mapping")
    relevant = hidden.get("transfer_relevant_feature_ids")
    distractors = hidden.get("distractor_feature_ids")
    if not isinstance(mapping, Mapping) or not isinstance(relevant, list) or not isinstance(distractors, list):
        raise v1.UnknownDomainGeneratorError("V3_IDENTIFIER_METADATA_INVALID")

    _require_unique(mapping.values(), "V3_DOMAIN_MAPPING_NOT_INJECTIVE")
    _require_unique(relevant, "V3_RELEVANT_IDS_NOT_INJECTIVE")
    _require_unique(distractors, "V3_DISTRACTOR_IDS_NOT_INJECTIVE")
    if set(map(str, relevant)) & set(map(str, distractors)):
        raise v1.UnknownDomainGeneratorError("V3_RELEVANT_DISTRACTOR_OVERLAP")

    receipt_rows = visible.get("domain_a", {}).get("earned_receipts", [])
    if not isinstance(receipt_rows, list) or len(receipt_rows) != 1 or not isinstance(receipt_rows[0], Mapping):
        raise v1.UnknownDomainGeneratorError("V3_RECEIPT_SHAPE_INVALID")
    source_binding = receipt_rows[0].get("source_role_binding")
    if not isinstance(source_binding, Mapping):
        raise v1.UnknownDomainGeneratorError("V3_SOURCE_BINDING_INVALID")
    _require_unique(source_binding.values(), "V3_SOURCE_MAPPING_NOT_INJECTIVE")

    arity = len(mapping)
    expected_feature_count = arity + 2

    def check_inputs(row: Mapping[str, Any], code: str) -> None:
        inputs = row.get("inputs") if isinstance(row, Mapping) else None
        if not isinstance(inputs, Mapping) or len(inputs) != expected_feature_count:
            raise v1.UnknownDomainGeneratorError(code)

    for row in visible.get("domain_a", {}).get("tasks", []):
        check_inputs(row, "V3_SOURCE_SURFACE_IDENTIFIER_COLLISION")
    for row in visible.get("domain_b", {}).get("tasks", []):
        check_inputs(row, "V3_TARGET_SURFACE_IDENTIFIER_COLLISION")
    query = visible.get("domain_b", {}).get("query_inputs")
    if not isinstance(query, Mapping) or len(query) != expected_feature_count:
        raise v1.UnknownDomainGeneratorError("V3_QUERY_SURFACE_IDENTIFIER_COLLISION")
    table = hidden.get("allowed_probe_outcome_table")
    if not isinstance(table, Mapping):
        raise v1.UnknownDomainGeneratorError("V3_PROBE_TABLE_INVALID")
    for row in table.values():
        check_inputs(row, "V3_PROBE_SURFACE_IDENTIFIER_COLLISION")


def _transfer_case(secret: bytes, beacon: str, index: int, *, namespace: str):
    visible, hidden = v2._transfer_case(secret, beacon, index, namespace=namespace)
    _validate_transfer_packet(visible, hidden)
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
