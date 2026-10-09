"""Bounded cross-filing semantic-contract stability for SEC issuer extensions.

This module proves only that two independently rederived issuer-extension
concept snapshots from the SAME SEC issuer have the same Brain-owned semantic
contract after removing filing-specific identity/provenance fields.

It does not prove eternal concept identity, standard-taxonomy equivalence,
ontology equivalence, or future stability.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import pathlib
import re
import urllib.parse
from typing import Any, Mapping

from canonical.runtime import sec_issuer_extension_concept_semantics_verify_v1 as concept_verify

SCHEMA="PROJECT_BRAIN_SEC_ISSUER_EXTENSION_CROSS_FILING_STABILITY_V1"
PRODUCER_SCHEMA="PROJECT_BRAIN_SEC_ISSUER_EXTENSION_CONCEPT_SEMANTICS_V1"
_CIK_RE=re.compile(r"^[0-9]+$")
_STABLE_METADATA_FIELDS=(
    "xsd_type","substitution_group","period_type","balance","abstract","nillable",
)

def _base(status:str,passed:bool=False,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,"status":status,"pass":passed,
        "cross_filing_semantic_contract_stable":False,
        "cross_filing_semantic_stability_authority":False,
        "concept_identity_authority":False,
        "standard_taxonomy_equivalence_authority":False,
        "future_stability_claimed":False,
        "open_world_finance_semantics_complete":False,
        "policy_adequacy_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        **extra,
    }

def _safe(root: pathlib.Path, raw:Any)->pathlib.Path:
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p

def _load(path:pathlib.Path)->dict[str,Any]:
    obj=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj,Mapping):
        raise ValueError("SEMANTIC_DOCUMENT_NOT_OBJECT")
    return dict(obj)

def _filing(url:Any)->tuple[str,str]:
    p=urllib.parse.urlsplit(str(url or ""))
    if (
        p.scheme!="https" or p.hostname!="www.sec.gov" or p.username or p.password
        or p.port not in (None,443) or p.query or p.fragment
        or not p.path.startswith("/Archives/edgar/data/")
    ):
        raise ValueError("SEC_ARCHIVE_URL_REQUIRED")
    parts=p.path.split("/")
    # ["", "Archives", "edgar", "data", cik, accession, file]
    if len(parts)<7 or not _CIK_RE.fullmatch(parts[4] or "") or not parts[5]:
        raise ValueError("SEC_ARCHIVE_PATH_INVALID")
    return parts[4].lstrip("0") or "0",parts[5]

def _signature(doc:Mapping[str,Any])->dict[str,Any]:
    if doc.get("schema")!=PRODUCER_SCHEMA:
        raise ValueError("CONCEPT_SCHEMA_INVALID")
    local=str(doc.get("local_name") or "").strip()
    documentation=str(doc.get("documentation_label") or "").strip()
    standard=doc.get("standard_label")
    if standard is not None:
        standard=str(standard).strip()
    md=doc.get("concept_metadata")
    if not local or not documentation or not isinstance(md,Mapping):
        raise ValueError("CONCEPT_SEMANTICS_INCOMPLETE")
    semantic_md={
        key:deepcopy(md[key])
        for key in _STABLE_METADATA_FIELDS
        if key in md
    }
    return {
        "local_name":local,
        "standard_label":standard,
        "documentation_label":documentation,
        "semantic_metadata":semantic_md,
    }

def _sha(value:Any)->str:
    return sha256(json.dumps(
        value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False
    ).encode("utf-8")).hexdigest()

def verify_pair(
    *,
    root:Any,
    left_xsd_path:Any,
    left_label_path:Any,
    left_semantic_path:Any,
    right_xsd_path:Any,
    right_label_path:Any,
    right_semantic_path:Any,
)->dict[str,Any]:
    try:
        root=pathlib.Path(root).resolve()
        paths={
            "left_xsd":_safe(root,left_xsd_path),
            "left_label":_safe(root,left_label_path),
            "left_semantic":_safe(root,left_semantic_path),
            "right_xsd":_safe(root,right_xsd_path),
            "right_label":_safe(root,right_label_path),
            "right_semantic":_safe(root,right_semantic_path),
        }
        left_v=concept_verify.verify(
            root=root,
            xsd_path=str(paths["left_xsd"].relative_to(root)),
            label_path=str(paths["left_label"].relative_to(root)),
            semantic_path=str(paths["left_semantic"].relative_to(root)),
        )
        right_v=concept_verify.verify(
            root=root,
            xsd_path=str(paths["right_xsd"].relative_to(root)),
            label_path=str(paths["right_label"].relative_to(root)),
            semantic_path=str(paths["right_semantic"].relative_to(root)),
        )
        if left_v.get("verified") is not True or right_v.get("verified") is not True:
            return _base(
                "FAIL_CLOSED",
                reason="UPSTREAM_CONCEPT_SEMANTICS_REDERIVATION_FAILED",
                left_verification=left_v,
                right_verification=right_v,
            )

        left=_load(paths["left_semantic"])
        right=_load(paths["right_semantic"])
        lcik,lfiling=_filing(left.get("xsd_url"))
        rcik,rfiling=_filing(right.get("xsd_url"))
        if lcik!=rcik:
            return _base("FAIL_CLOSED",reason="CROSS_ISSUER_COMPARISON_FORBIDDEN")
        if lfiling==rfiling:
            return _base("FAIL_CLOSED",reason="DISTINCT_FILING_DIRECTORIES_REQUIRED")

        lsig=_signature(left)
        rsig=_signature(right)
        if lsig["local_name"]!=rsig["local_name"]:
            return _base("FAIL_CLOSED",reason="LOCAL_NAME_MISMATCH")
        differences=[
            key for key in sorted(set(lsig)|set(rsig))
            if lsig.get(key)!=rsig.get(key)
        ]
        if differences:
            return _base(
                "PASS__CROSS_FILING_SEMANTIC_CONTRACT_DIFFERENCE_DETECTED",
                passed=True,
                issuer_cik=lcik,
                left_filing_directory=lfiling,
                right_filing_directory=rfiling,
                left_concept_qname=left.get("concept_qname"),
                right_concept_qname=right.get("concept_qname"),
                left_signature=lsig,
                right_signature=rsig,
                differing_fields=differences,
                semantic_contract_equality_proved=True,
                cross_filing_semantic_contract_stable=False,
                cross_filing_semantic_stability_authority=True,
                relation="SEMANTIC_CONTRACT_DIFFERS_ACROSS_FILINGS",
                boundary=(
                    "EXACT_PAIRWISE_COMPARISON_OF_BRAIN_OWNED_ISSUER_EXTENSION_SEMANTIC_"
                    "FIELDS_ONLY__NO_CONCEPT_IDENTITY_OR_GENERAL_INSTABILITY_CLAIM"
                ),
            )

        material={
            "issuer_cik":lcik,
            "left_filing_directory":lfiling,
            "right_filing_directory":rfiling,
            "left_concept_qname":left.get("concept_qname"),
            "right_concept_qname":right.get("concept_qname"),
            "semantic_signature":lsig,
            "left_xsd_sha256":left.get("xsd_sha256"),
            "left_label_sha256":left.get("label_sha256"),
            "right_xsd_sha256":right.get("xsd_sha256"),
            "right_label_sha256":right.get("label_sha256"),
        }
        return _base(
            "PASS__CROSS_FILING_SEMANTIC_CONTRACT_STABILITY_PROVED",
            passed=True,
            cross_filing_semantic_contract_stable=True,
            cross_filing_semantic_stability_authority=True,
            semantic_contract_equality_proved=True,
            issuer_cik=lcik,
            left_filing_directory=lfiling,
            right_filing_directory=rfiling,
            left_concept_qname=left.get("concept_qname"),
            right_concept_qname=right.get("concept_qname"),
            semantic_signature=lsig,
            stability_receipt_sha256=_sha(material),
            relation="SAME_BRAIN_OWNED_SEMANTIC_CONTRACT_ACROSS_TWO_FILINGS",
            boundary=(
                "PAIRWISE_SAME_ISSUER_EXACT_LOCAL_NAME_LABEL_DOCUMENTATION_AND_"
                "SEMANTIC_XSD_FIELDS_ONLY__NAMESPACE_PROVENANCE_AND_FILING_ID_MAY_DIFFER__"
                "NO_ETERNAL_IDENTITY_STANDARD_TAXONOMY_EQUIVALENCE_OR_FUTURE_STABILITY"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED",reason=type(exc).__name__+":"+str(exc))

def run(args:Mapping[str,Any],root:Any)->dict[str,Any]:
    return verify_pair(
        root=root,
        left_xsd_path=args.get("left_xsd_path"),
        left_label_path=args.get("left_label_path"),
        left_semantic_path=args.get("left_semantic_path"),
        right_xsd_path=args.get("right_xsd_path"),
        right_label_path=args.get("right_label_path"),
        right_semantic_path=args.get("right_semantic_path"),
    )
