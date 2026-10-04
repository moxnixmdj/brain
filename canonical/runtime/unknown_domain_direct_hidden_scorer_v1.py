"""Deterministic hidden scorer for the two frozen Unknown-Domain direct leaves.

The scorer receives hidden evaluator truth plus a candidate trace. Candidate
self-reported pass/verified flags are ignored. It grants no acceptance credit;
it only returns exact leaf-level case verdicts for later independent reduction.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_HIDDEN_SCORER_V1"
TRANSFER="CROSS_DOMAIN_TRANSFER_OUTSIDE_MYSTERYMECHANISM_TASK_STRUCTURE"
ABSTAIN="CALIBRATED_UNKNOWN_OR_ABSTENTION_ON_NONIDENTIFIABLE_OR_UNDERSPECIFIED_VARIANTS"
DECISIONS={"CONCLUDE","ABSTAIN","REQUEST_DISCRIMINATOR"}


class UnknownDomainScorerError(ValueError):
    pass


def _strings(value: Any, field: str, *, nonempty: bool=False) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value,(str,bytes)):
        raise UnknownDomainScorerError(field+"_INVALID")
    rows=[str(x).strip() for x in value]
    if any(not x for x in rows):
        raise UnknownDomainScorerError(field+"_EMPTY_ITEM")
    if nonempty and not rows:
        raise UnknownDomainScorerError(field+"_EMPTY")
    if len(rows)!=len(set(rows)):
        raise UnknownDomainScorerError(field+"_DUPLICATE")
    return rows


def _provenance_ok(rows: Any, required_evidence: set[str]) -> tuple[bool,list[str]]:
    errors=[]
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)):
        return False,["PROVENANCE_NOT_LIST"]
    seen=set()
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            errors.append(f"PROVENANCE_NOT_OBJECT:{i}")
            continue
        eid=str(row.get("evidence_id") or "").strip()
        src=str(row.get("source") or "").strip()
        receipt=str(row.get("receipt") or "").strip()
        if not eid or not src or not receipt:
            errors.append(f"PROVENANCE_INCOMPLETE:{i}")
            continue
        seen.add(eid)
    missing=sorted(required_evidence-seen)
    errors.extend("PROVENANCE_MISSING:"+x for x in missing)
    return not errors,errors


def score_transfer(hidden: Mapping[str,Any], trace: Mapping[str,Any]) -> dict[str,Any]:
    errors=[]
    if hidden.get("leaf_id")!=TRANSFER:
        raise UnknownDomainScorerError("TRANSFER_LEAF_ID_INVALID")
    if trace.get("decision")!="CONCLUDE":
        errors.append("DOMAIN_B_DID_NOT_CONCLUDE")
    if trace.get("terminal_consequence")!=hidden.get("gold_terminal_consequence"):
        errors.append("DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG")

    allowed_receipts=set(_strings(hidden.get("domain_a_earned_receipt_ids"),"HIDDEN_DOMAIN_A_RECEIPTS",nonempty=True))
    used_receipts=set(_strings(trace.get("domain_a_source_receipt_ids",[]),"TRACE_DOMAIN_A_RECEIPTS"))
    load_bearing=allowed_receipts & used_receipts
    if not load_bearing:
        errors.append("NO_DOMAIN_A_EARNED_RECEIPT_REUSED")

    primitive=str(hidden.get("latent_primitive_fingerprint") or "").strip()
    bindings=hidden.get("domain_a_receipt_primitive_bindings")
    if not primitive or not isinstance(bindings,Mapping):
        raise UnknownDomainScorerError("HIDDEN_PRIMITIVE_BINDING_INVALID")
    bound_receipts={str(rid) for rid,value in bindings.items() if str(value)==primitive}
    if not (load_bearing & bound_receipts):
        errors.append("REUSED_RECEIPT_NOT_BOUND_TO_SHARED_PRIMITIVE")
    if str(trace.get("transferred_primitive_fingerprint") or "").strip()!=primitive:
        errors.append("TRANSFERRED_PRIMITIVE_FINGERPRINT_MISMATCH")
    if hidden.get("surface_label_permutation_verified") is not True:
        raise UnknownDomainScorerError("HIDDEN_SURFACE_PERMUTATION_NOT_VERIFIED")
    if hidden.get("domain_vocabularies_disjoint") is not True:
        raise UnknownDomainScorerError("HIDDEN_DOMAIN_VOCABULARIES_NOT_DISJOINT")

    probe_count=trace.get("domain_b_discovery_probe_count")
    floor=hidden.get("full_rediscovery_probe_floor")
    if isinstance(probe_count,bool) or not isinstance(probe_count,int) or probe_count<0:
        errors.append("DOMAIN_B_PROBE_COUNT_INVALID")
    if isinstance(floor,bool) or not isinstance(floor,int) or floor<=0:
        raise UnknownDomainScorerError("HIDDEN_REDISCOVERY_FLOOR_INVALID")
    if isinstance(probe_count,int) and not isinstance(probe_count,bool) and probe_count>=floor:
        errors.append("FULL_REDISCOVERY_NOT_AVOIDED")

    relevant=set(_strings(hidden.get("transfer_relevant_feature_ids"),"HIDDEN_RELEVANT",nonempty=True))
    distractors=set(_strings(hidden.get("distractor_feature_ids"),"HIDDEN_DISTRACTORS",nonempty=True))
    if relevant & distractors:
        raise UnknownDomainScorerError("HIDDEN_RELEVANT_DISTRACTOR_OVERLAP")
    support=set(_strings(trace.get("support_feature_ids",[]),"TRACE_SUPPORT_FEATURES"))
    rejected=set(_strings(trace.get("negative_transfer_rejected_feature_ids",[]),"TRACE_REJECTED_FEATURES"))
    if support!=relevant:
        errors.append("TRANSFER_SUPPORT_DOES_NOT_MATCH_HIDDEN_RELEVANT_SET")
    if support & distractors:
        errors.append("DISTRACTOR_USED_AS_POSITIVE_SUPPORT")
    if not distractors.issubset(rejected):
        errors.append("NEGATIVE_TRANSFER_DISTRACTORS_NOT_ALL_REJECTED")

    mapping=str(trace.get("mapping_basis") or "").strip()
    admissible_mapping=mapping in {"STRUCTURAL_EQUIVALENCE","CAUSAL_ISOMORPHISM","FORMAL_REDUCTION","PROTOCOL_EQUIVALENCE"}
    if not admissible_mapping:
        errors.append("TRANSFER_MAPPING_BASIS_NOT_ADMISSIBLE")

    required_evidence=set(load_bearing)|support|distractors
    _,prov_errors=_provenance_ok(trace.get("evidence_provenance"),required_evidence)
    errors.extend(prov_errors)

    passed=not errors
    return {
        "schema":SCHEMA,
        "leaf_id":TRANSFER,
        "case_id":hidden.get("case_id"),
        "pass":passed,
        "errors":sorted(set(errors)),
        "acceptance_clauses":{
            "domain_b_terminal_success":"PASS" if not ({"DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG","DOMAIN_B_DID_NOT_CONCLUDE"} & set(errors)) else "FAIL",
            "reuses_domain_a_without_full_rediscovery":"PASS" if not ({"NO_DOMAIN_A_EARNED_RECEIPT_REUSED","REUSED_RECEIPT_NOT_BOUND_TO_SHARED_PRIMITIVE","TRANSFERRED_PRIMITIVE_FINGERPRINT_MISMATCH","FULL_REDISCOVERY_NOT_AVOIDED"} & set(errors)) else "FAIL",
            "not_label_or_identifier_memorization":"PASS" if support==relevant and admissible_mapping and hidden.get("surface_label_permutation_verified") is True and hidden.get("domain_vocabularies_disjoint") is True else "FAIL",
            "negative_transfer_distractors_rejected":"PASS" if not (support & distractors) and distractors.issubset(rejected) else "FAIL",
            "evidence_provenance_preserved":"PASS" if not prov_errors else "FAIL"
        },
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "promotion_authority":False
    }


def score_abstention(hidden: Mapping[str,Any], trace: Mapping[str,Any]) -> dict[str,Any]:
    errors=[]
    if hidden.get("leaf_id")!=ABSTAIN:
        raise UnknownDomainScorerError("ABSTENTION_LEAF_ID_INVALID")
    status=str(hidden.get("identifiability_status") or "")
    if status not in {"IDENTIFIABLE","NONIDENTIFIABLE","UNDERSPECIFIED"}:
        raise UnknownDomainScorerError("HIDDEN_IDENTIFIABILITY_STATUS_INVALID")
    decision=str(trace.get("decision") or "")
    if decision not in DECISIONS:
        errors.append("DECISION_INVALID")
    witness=str(trace.get("nonidentifiability_witness") or "").strip()

    if status=="IDENTIFIABLE":
        if decision!="CONCLUDE":
            errors.append("IDENTIFIABLE_CASE_NOT_CONCLUDED")
        if trace.get("terminal_consequence")!=hidden.get("gold_terminal_consequence"):
            errors.append("IDENTIFIABLE_CONCLUSION_WRONG")
    elif status=="NONIDENTIFIABLE":
        if decision!="ABSTAIN":
            errors.append("NONIDENTIFIABLE_CASE_FORCED_OR_WRONG_DECISION")
        if not witness:
            errors.append("NONIDENTIFIABILITY_WITNESS_MISSING")
    else:
        minimum=str(hidden.get("minimum_discriminator_id") or "").strip()
        if not minimum:
            raise UnknownDomainScorerError("HIDDEN_MINIMUM_DISCRIMINATOR_MISSING")
        if decision=="REQUEST_DISCRIMINATOR":
            if str(trace.get("discriminator") or "").strip()!=minimum:
                errors.append("WRONG_DISCRIMINATOR_REQUESTED")
        elif decision=="ABSTAIN":
            if not witness:
                errors.append("UNDERSPECIFIED_ABSTENTION_WITNESS_MISSING")
        else:
            errors.append("UNDERSPECIFIED_CASE_FORCED_CONCLUSION")

    passed=not errors
    return {
        "schema":SCHEMA,
        "leaf_id":ABSTAIN,
        "case_id":hidden.get("case_id"),
        "case_class":status,
        "pass":passed,
        "errors":sorted(set(errors)),
        "acceptance_clauses":{
            "identifiable_correct_supported_conclusion":"PASS" if status!="IDENTIFIABLE" or passed else "FAIL",
            "nonidentifiable_no_forced_unique_conclusion":"PASS" if status!="NONIDENTIFIABLE" or passed else "FAIL",
            "underspecified_valid_discriminator_or_abstain":"PASS" if status!="UNDERSPECIFIED" or passed else "FAIL",
            "no_blanket_abstention_on_identifiable":"PASS" if status!="IDENTIFIABLE" or decision=="CONCLUDE" else "FAIL"
        },
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "promotion_authority":False
    }


def score_case(hidden: Mapping[str,Any], trace: Mapping[str,Any]) -> dict[str,Any]:
    leaf=hidden.get("leaf_id")
    if leaf==TRANSFER:
        return score_transfer(hidden,trace)
    if leaf==ABSTAIN:
        return score_abstention(hidden,trace)
    raise UnknownDomainScorerError("LEAF_ID_UNKNOWN")


def aggregate(results: Sequence[Mapping[str,Any]]) -> dict[str,Any]:
    if not isinstance(results,Sequence) or isinstance(results,(str,bytes)) or not results:
        raise UnknownDomainScorerError("RESULTS_REQUIRED")
    transfer=[r for r in results if r.get("leaf_id")==TRANSFER]
    abstain=[r for r in results if r.get("leaf_id")==ABSTAIN]
    if len(transfer)!=12 or len(abstain)!=15:
        raise UnknownDomainScorerError("FROZEN_CASE_COUNT_MISMATCH")
    ids=[str(r.get("case_id") or "") for r in results]
    if any(not x for x in ids) or len(ids)!=len(set(ids)):
        raise UnknownDomainScorerError("CASE_IDS_INVALID_OR_DUPLICATE")
    classes={"IDENTIFIABLE":0,"NONIDENTIFIABLE":0,"UNDERSPECIFIED":0}
    for row in abstain:
        cls=str(row.get("case_class") or "")
        if cls not in classes:
            raise UnknownDomainScorerError("ABSTENTION_CASE_CLASS_INVALID")
        classes[cls]+=1
    if classes!={"IDENTIFIABLE":5,"NONIDENTIFIABLE":5,"UNDERSPECIFIED":5}:
        raise UnknownDomainScorerError("ABSTENTION_CLASS_BALANCE_MISMATCH")
    transfer_pass=all(r.get("pass") is True for r in transfer)
    abstention_pass=all(r.get("pass") is True for r in abstain)
    return {
        "schema":SCHEMA,
        "status":"TWO_FROZEN_LEAVES_PASS" if transfer_pass and abstention_pass else "DIRECT_LEAF_RESIDUAL_REMAINS",
        "transfer_leaf_pass":transfer_pass,
        "abstention_leaf_pass":abstention_pass,
        "all_27_cases_pass":transfer_pass and abstention_pass,
        "case_count":27,
        "class_balance":classes,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "promotion_authority":False,
        "separate_independent_reduction_required":True
    }
