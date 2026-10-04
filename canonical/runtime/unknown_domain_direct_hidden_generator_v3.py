"""Fail-closed namespace-total wrapper for Unknown-Domain hidden generator V2.

Generator V2 uses truncated opaque HMAC surface identifiers.  Its semantic case
construction is sound, but the V2 code does not itself reject every local
identifier collision that can make a packet structurally invalid (for example
role-role, distractor-distractor, duplicate probe IDs, or a nonidentifiable
action-token collision).

V3 changes no successful V2 case semantics.  It validates the fully constructed
packet and refuses to emit any population whose opaque namespace is not
structurally injective for the frozen evaluator contract.  This removes a
probabilistic collision-freeness assumption from universal proofs: every packet
that V3 *emits* has the exact uniqueness invariants consumed by the candidate,
harness, and scorer.

No production population is generated on import or by this module's tests.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as v1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as v2

SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_HIDDEN_GENERATOR_V3_NAMESPACE_TOTAL"


class UnknownDomainGeneratorV3Error(ValueError):
    pass


def _seq(value: Any, field: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise UnknownDomainGeneratorV3Error(field+"_INVALID")
    return list(value)


def _unique_strings(value: Any, field: str, *, expected: int | None=None) -> list[str]:
    rows=_seq(value,field)
    out=[str(x).strip() for x in rows]
    if any(not x for x in out):
        raise UnknownDomainGeneratorV3Error(field+"_EMPTY")
    if expected is not None and len(out)!=expected:
        raise UnknownDomainGeneratorV3Error(field+"_COUNT")
    if len(out)!=len(set(out)):
        raise UnknownDomainGeneratorV3Error(field+"_DUPLICATE")
    return out


def _input_width(row: Any, field: str, expected: int) -> None:
    if not isinstance(row, Mapping) or not isinstance(row.get("inputs"), Mapping):
        raise UnknownDomainGeneratorV3Error(field+"_INVALID")
    keys=[str(k) for k in row["inputs"].keys()]
    if len(keys)!=expected or len(keys)!=len(set(keys)):
        raise UnknownDomainGeneratorV3Error(field+"_FEATURE_NAMESPACE_NOT_INJECTIVE")


def _validate_transfer(visible: Mapping[str,Any], hidden: Mapping[str,Any]) -> None:
    relevant=_unique_strings(hidden.get("transfer_relevant_feature_ids"),"TRANSFER_RELEVANT",expected=len(hidden.get("domain_mapping") or {}))
    distractors=_unique_strings(hidden.get("distractor_feature_ids"),"TRANSFER_DISTRACTORS",expected=2)
    if set(relevant) & set(distractors):
        raise UnknownDomainGeneratorV3Error("TRANSFER_RELEVANT_DISTRACTOR_OVERLAP")

    mapping=hidden.get("domain_mapping")
    if not isinstance(mapping,Mapping) or set(map(str,mapping.values()))!=set(relevant):
        raise UnknownDomainGeneratorV3Error("TRANSFER_DOMAIN_MAPPING_INVALID")

    domain_a=visible.get("domain_a")
    domain_b=visible.get("domain_b")
    if not isinstance(domain_a,Mapping) or not isinstance(domain_b,Mapping):
        raise UnknownDomainGeneratorV3Error("TRANSFER_DOMAIN_PACKET_INVALID")

    receipts=_seq(domain_a.get("earned_receipts"),"TRANSFER_RECEIPTS")
    if len(receipts)!=1 or not isinstance(receipts[0],Mapping):
        raise UnknownDomainGeneratorV3Error("TRANSFER_RECEIPT_SHAPE")
    receipt=receipts[0]
    program=receipt.get("normalized_primitive_program")
    source_binding=receipt.get("source_role_binding")
    if not isinstance(program,Mapping) or not isinstance(source_binding,Mapping):
        raise UnknownDomainGeneratorV3Error("TRANSFER_RECEIPT_PROGRAM_OR_BINDING_INVALID")
    roles=[str(x) for x in (program.get("roles") or [])]
    if roles not in (["r0"],["r0","r1"]):
        raise UnknownDomainGeneratorV3Error("TRANSFER_ROLES_INVALID")
    source_ids=[str(source_binding.get(role) or "") for role in roles]
    if any(not x for x in source_ids) or len(source_ids)!=len(set(source_ids)):
        raise UnknownDomainGeneratorV3Error("SOURCE_ROLE_NAMESPACE_NOT_INJECTIVE")

    expected_width=len(roles)+2
    source_tasks=_seq(domain_a.get("tasks"),"SOURCE_TASKS")
    target_tasks=_seq(domain_b.get("tasks"),"TARGET_TASKS")
    if len(source_tasks)!=3 or len(target_tasks)!=3:
        raise UnknownDomainGeneratorV3Error("TRANSFER_PUBLIC_TASK_COUNT")
    for i,row in enumerate(source_tasks):
        _input_width(row,f"SOURCE_TASK_{i}",expected_width)
    for i,row in enumerate(target_tasks):
        _input_width(row,f"TARGET_TASK_{i}",expected_width)
    _input_width({"inputs":domain_b.get("query_inputs")}, "TRANSFER_QUERY", expected_width)

    probes=_seq(domain_b.get("allowed_probes"),"TRANSFER_PROBES")
    if len(probes)!=2 or any(not isinstance(x,Mapping) for x in probes):
        raise UnknownDomainGeneratorV3Error("TRANSFER_PROBE_SHAPE")
    probe_ids=_unique_strings([x.get("probe_id") for x in probes],"TRANSFER_PROBE_IDS",expected=2)
    table=hidden.get("allowed_probe_outcome_table")
    if not isinstance(table,Mapping) or set(map(str,table.keys()))!=set(probe_ids):
        raise UnknownDomainGeneratorV3Error("TRANSFER_PROBE_TABLE_KEYS")
    for i,pid in enumerate(probe_ids):
        _input_width(table[pid],f"TRANSFER_PROBE_RESULT_{i}",expected_width)


def _validate_abstention(visible: Mapping[str,Any], hidden: Mapping[str,Any]) -> None:
    status=str(hidden.get("identifiability_status") or "")
    if status not in {"IDENTIFIABLE","NONIDENTIFIABLE","UNDERSPECIFIED"}:
        raise UnknownDomainGeneratorV3Error("ABSTENTION_STATUS_INVALID")

    hypotheses=_seq(visible.get("hypotheses"),"ABSTENTION_HYPOTHESES")
    if len(hypotheses)!=2 or any(not isinstance(x,Mapping) for x in hypotheses):
        raise UnknownDomainGeneratorV3Error("ABSTENTION_HYPOTHESIS_SHAPE")
    hypothesis_ids=_unique_strings([x.get("hypothesis_id") for x in hypotheses],"ABSTENTION_HYPOTHESIS_IDS",expected=2)
    consequences=[str(x.get("terminal_consequence") or "").strip() for x in hypotheses]
    if any(not x for x in consequences):
        raise UnknownDomainGeneratorV3Error("ABSTENTION_CONSEQUENCE_EMPTY")
    if status=="IDENTIFIABLE":
        if len(set(consequences))!=1:
            raise UnknownDomainGeneratorV3Error("IDENTIFIABLE_CONSEQUENCE_NOT_EQUAL")
    elif len(set(consequences))!=2:
        raise UnknownDomainGeneratorV3Error("NONIDENTIFIABLE_CONSEQUENCE_COLLISION")

    probes=_seq(visible.get("allowed_probes"),"ABSTENTION_PROBES")
    expected_probe_count={"IDENTIFIABLE":0,"NONIDENTIFIABLE":1,"UNDERSPECIFIED":2}[status]
    if len(probes)!=expected_probe_count or any(not isinstance(x,Mapping) for x in probes):
        raise UnknownDomainGeneratorV3Error("ABSTENTION_PROBE_COUNT_OR_SHAPE")
    probe_ids=_unique_strings([x.get("probe_id") for x in probes],"ABSTENTION_PROBE_IDS",expected=expected_probe_count) if probes else []

    table=hidden.get("allowed_probe_outcome_table")
    if not isinstance(table,Mapping) or set(map(str,table.keys()))!=set(probe_ids):
        raise UnknownDomainGeneratorV3Error("ABSTENTION_PROBE_TABLE_KEYS")
    for pid in probe_ids:
        row=table[pid]
        if not isinstance(row,Mapping) or set(map(str,row.keys()))!=set(hypothesis_ids):
            raise UnknownDomainGeneratorV3Error("ABSTENTION_PROBE_OUTCOME_KEYS")

    minimum=hidden.get("minimum_discriminator_id")
    if status=="UNDERSPECIFIED":
        if str(minimum or "") not in set(probe_ids):
            raise UnknownDomainGeneratorV3Error("UNDERSPECIFIED_MINIMUM_DISCRIMINATOR_INVALID")
    elif minimum is not None:
        raise UnknownDomainGeneratorV3Error("NON_UNDERSPECIFIED_MINIMUM_DISCRIMINATOR_PRESENT")


def validate_packet(packet: Mapping[str,Any]) -> dict[str,Any]:
    if not isinstance(packet,Mapping):
        raise UnknownDomainGeneratorV3Error("PACKET_INVALID")
    visible=_seq(packet.get("visible_cases"),"VISIBLE_CASES")
    hidden=_seq(packet.get("hidden_records"),"HIDDEN_RECORDS")
    if len(visible)!=27 or len(hidden)!=27 or len(visible)!=len(hidden):
        raise UnknownDomainGeneratorV3Error("PACKET_CASE_COUNT")

    visible_ids=_unique_strings([x.get("case_id") if isinstance(x,Mapping) else None for x in visible],"VISIBLE_CASE_IDS",expected=27)
    hidden_ids=_unique_strings([x.get("case_id") if isinstance(x,Mapping) else None for x in hidden],"HIDDEN_CASE_IDS",expected=27)
    if visible_ids!=hidden_ids:
        raise UnknownDomainGeneratorV3Error("VISIBLE_HIDDEN_CASE_ID_ORDER_MISMATCH")

    for i,(v,h) in enumerate(zip(visible,hidden)):
        if not isinstance(v,Mapping) or not isinstance(h,Mapping):
            raise UnknownDomainGeneratorV3Error(f"CASE_{i}_NOT_OBJECT")
        if v.get("leaf_id")!=h.get("leaf_id"):
            raise UnknownDomainGeneratorV3Error(f"CASE_{i}_LEAF_MISMATCH")
        if v.get("leaf_id")==v1.TRANSFER:
            _validate_transfer(v,h)
        elif v.get("leaf_id")==v1.ABSTAIN:
            _validate_abstention(v,h)
        else:
            raise UnknownDomainGeneratorV3Error(f"CASE_{i}_LEAF_UNKNOWN")

    return dict(packet)


def _generate(*, beacon:str, evaluator_secret:Any, namespace:str) -> dict[str,Any]:
    return validate_packet(v2._generate(beacon=beacon,evaluator_secret=evaluator_secret,namespace=namespace))


def generate_production_population(*, beacon:str, evaluator_secret:Any, authority:Mapping[str,Any]) -> dict[str,Any]:
    v1._production_authorized(authority)
    out=_generate(beacon=beacon,evaluator_secret=evaluator_secret,namespace="UDIR")
    out["authority_claim_id"]=str(authority["one_use_claim_id"])
    out["production"]=True
    out["namespace_integrity"]="V3_FAIL_CLOSED_TOTALITY_GUARD"
    return out


def generate_qualification_fixture_population(*, beacon:str) -> dict[str,Any]:
    if not isinstance(beacon,str) or len(beacon.strip())<16:
        raise v1.UnknownDomainGeneratorError("QUALIFICATION_BEACON_INVALID")
    out=_generate(
        beacon="QUALIFICATION-ONLY|"+beacon,
        evaluator_secret=b"QUALIFICATION-ONLY-SECRET-0123456789-ABCDEFG",
        namespace="QUALONLY",
    )
    out["production"]=False
    out["hard_nonclaim"]="QUALIFICATION_FIXTURES_ARE_NOT_PRODUCTION_OR_TERMINAL_CASES"
    out["namespace_integrity"]="V3_FAIL_CLOSED_TOTALITY_GUARD"
    return out
