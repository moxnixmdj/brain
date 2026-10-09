"""Bounded cross-filing comparability for SEC issuer-extension numeric facts.

V1 proves a source-native REPORTED numeric relation only when:
- both extracted XBRL instance semantic documents independently rederive from raw bytes;
- the two issuer-extension concept contracts pass the existing same-issuer
  cross-filing semantic-contract stability verifier;
- each selected fact uses the corresponding stable concept QName;
- entity, unit, and dimensions are exactly equal;
- both periods are instants and left instant is earlier than right instant;
- both values are finite non-nil normalized decimals.

The relation concerns the reported normalized decimal values. It does not claim
the same relation for unknown unrounded economic values, accounting-policy
comparability, standard-taxonomy equivalence, policy adequacy, or terminal truth.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import pathlib
import urllib.parse
from typing import Any, Mapping

from canonical.runtime import sec_extracted_xbrl_instance_source_native_verify_v1 as instance_verify
from canonical.runtime import sec_issuer_extension_cross_filing_stability_v1 as concept_stability

SCHEMA="PROJECT_BRAIN_SEC_ISSUER_EXTENSION_CROSS_FILING_FACT_COMPARABILITY_V1"
INSTANCE_SCHEMA="PROJECT_BRAIN_SEC_EXTRACTED_XBRL_INSTANCE_SOURCE_NATIVE_V1"

def _base(status:str,passed:bool=False,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":status,
        "pass":passed,
        "cross_filing_fact_measurement_contract_compatible":False,
        "reported_value_relation_authority":False,
        "underlying_unrounded_value_relation_claimed":False,
        "accounting_policy_comparability_claimed":False,
        "standard_taxonomy_equivalence_authority":False,
        "semantic_truth_authority":False,
        "policy_adequacy_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        **extra,
    }

def _safe(root:pathlib.Path,raw:Any)->pathlib.Path:
    root=root.resolve()
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p

def _load(path:pathlib.Path)->dict[str,Any]:
    obj=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj,Mapping):
        raise ValueError("SEMANTIC_DOCUMENT_NOT_OBJECT")
    return dict(obj)

def _filing_directory(url:Any)->tuple[str,str]:
    p=urllib.parse.urlsplit(str(url or ""))
    if (
        p.scheme!="https" or p.hostname!="www.sec.gov" or p.username or p.password
        or p.port not in (None,443) or p.query or p.fragment
        or not p.path.startswith("/Archives/edgar/data/")
    ):
        raise ValueError("SEC_ARCHIVE_URL_REQUIRED")
    parts=p.path.split("/")
    if len(parts)<7 or not parts[4] or not parts[5]:
        raise ValueError("SEC_ARCHIVE_PATH_INVALID")
    cik=(parts[4].lstrip("0") or "0")
    return cik,parts[5]

def _fact(doc:Mapping[str,Any],ordinal:Any)->dict[str,Any]:
    if doc.get("schema")!=INSTANCE_SCHEMA:
        raise ValueError("INSTANCE_SEMANTIC_SCHEMA_INVALID")
    if isinstance(ordinal,bool) or not isinstance(ordinal,int) or ordinal<0:
        raise ValueError("FACT_ORDINAL_INVALID")
    rows=[
        row for row in (doc.get("facts") or [])
        if isinstance(row,Mapping) and row.get("ordinal")==ordinal
    ]
    if len(rows)!=1:
        raise ValueError("FACT_ORDINAL_NOT_UNIQUE")
    return dict(rows[0])

def _decimal(value:Any)->Decimal:
    if not isinstance(value,str) or not value.strip():
        raise ValueError("NORMALIZED_DECIMAL_REQUIRED")
    try:
        d=Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("NORMALIZED_DECIMAL_INVALID") from exc
    if not d.is_finite():
        raise ValueError("NORMALIZED_DECIMAL_NOT_FINITE")
    return d

def _instant(context:Mapping[str,Any])->date:
    period=context.get("period")
    if not isinstance(period,Mapping) or period.get("kind")!="instant":
        raise ValueError("ONLY_INSTANT_PERIOD_COMPARABILITY_SUPPORTED_V1")
    raw=str(period.get("instant") or "")
    try:
        return date.fromisoformat(raw)
    except Exception as exc:
        raise ValueError("INSTANT_DATE_INVALID") from exc

def _sha(value:Any)->str:
    return sha256(json.dumps(
        value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False
    ).encode("utf-8")).hexdigest()

def verify_comparable_facts(
    *,
    root:Any,
    left_instance_raw_path:Any,
    left_instance_semantic_path:Any,
    right_instance_raw_path:Any,
    right_instance_semantic_path:Any,
    left_concept_xsd_path:Any,
    left_concept_label_path:Any,
    left_concept_semantic_path:Any,
    right_concept_xsd_path:Any,
    right_concept_label_path:Any,
    right_concept_semantic_path:Any,
    left_fact_ordinal:int,
    right_fact_ordinal:int,
)->dict[str,Any]:
    try:
        root=pathlib.Path(root).resolve()
        lp={
            "raw":_safe(root,left_instance_raw_path),
            "sem":_safe(root,left_instance_semantic_path),
        }
        rp={
            "raw":_safe(root,right_instance_raw_path),
            "sem":_safe(root,right_instance_semantic_path),
        }

        lv=instance_verify.verify(
            root=root,
            raw_path=str(lp["raw"].relative_to(root)),
            semantic_path=str(lp["sem"].relative_to(root)),
        )
        rv=instance_verify.verify(
            root=root,
            raw_path=str(rp["raw"].relative_to(root)),
            semantic_path=str(rp["sem"].relative_to(root)),
        )
        if lv.get("verified") is not True or rv.get("verified") is not True:
            return _base(
                "FAIL_CLOSED",
                reason="UPSTREAM_INSTANCE_SEMANTICS_REDERIVATION_FAILED",
                left_instance_verification=lv,
                right_instance_verification=rv,
            )

        stable=concept_stability.verify_pair(
            root=root,
            left_xsd_path=left_concept_xsd_path,
            left_label_path=left_concept_label_path,
            left_semantic_path=left_concept_semantic_path,
            right_xsd_path=right_concept_xsd_path,
            right_label_path=right_concept_label_path,
            right_semantic_path=right_concept_semantic_path,
        )
        if stable.get("pass") is not True:
            return _base(
                "FAIL_CLOSED",
                reason="UPSTREAM_CONCEPT_STABILITY_PROOF_FAILED",
                concept_stability=stable,
            )
        if stable.get("cross_filing_semantic_contract_stable") is not True:
            return _base(
                "OPEN__CONCEPT_SEMANTIC_CONTRACT_NOT_STABLE",
                concept_stability=stable,
            )

        left=_load(lp["sem"])
        right=_load(rp["sem"])
        lcik,lfiling=_filing_directory(left.get("source_url"))
        rcik,rfiling=_filing_directory(right.get("source_url"))
        if lcik!=stable.get("issuer_cik") or rcik!=stable.get("issuer_cik"):
            return _base("FAIL_CLOSED",reason="INSTANCE_AND_CONCEPT_ISSUER_MISMATCH")
        if lfiling!=stable.get("left_filing_directory") or rfiling!=stable.get("right_filing_directory"):
            return _base("FAIL_CLOSED",reason="INSTANCE_AND_CONCEPT_FILING_DIRECTORY_MISMATCH")

        lf=_fact(left,left_fact_ordinal)
        rf=_fact(right,right_fact_ordinal)
        if lf.get("concept_qname")!=stable.get("left_concept_qname"):
            return _base("FAIL_CLOSED",reason="LEFT_FACT_CONCEPT_QNAME_MISMATCH")
        if rf.get("concept_qname")!=stable.get("right_concept_qname"):
            return _base("FAIL_CLOSED",reason="RIGHT_FACT_CONCEPT_QNAME_MISMATCH")
        if lf.get("nil") is True or rf.get("nil") is True:
            return _base("OPEN__NIL_FACT_NOT_NUMERICALLY_COMPARABLE")
        if lf.get("unit") is None or rf.get("unit") is None:
            return _base("OPEN__UNIT_REQUIRED_FOR_NUMERIC_COMPARABILITY")

        lc=lf.get("context")
        rc=rf.get("context")
        if not isinstance(lc,Mapping) or not isinstance(rc,Mapping):
            return _base("FAIL_CLOSED",reason="FACT_CONTEXT_INVALID")
        if lc.get("entity")!=rc.get("entity"):
            return _base("OPEN__ENTITY_MISMATCH")
        if lc.get("dimensions")!=rc.get("dimensions"):
            return _base("OPEN__DIMENSION_MISMATCH")
        if lf.get("unit")!=rf.get("unit"):
            return _base("OPEN__UNIT_MISMATCH")

        ldate=_instant(lc)
        rdate=_instant(rc)
        if not ldate<rdate:
            return _base("OPEN__CHRONOLOGICAL_ORDER_NOT_LEFT_BEFORE_RIGHT")

        lval=_decimal(lf.get("normalized_decimal"))
        rval=_decimal(rf.get("normalized_decimal"))
        relation=(
            "RIGHT_REPORTED_VALUE_GT_LEFT"
            if rval>lval else
            "RIGHT_REPORTED_VALUE_LT_LEFT"
            if rval<lval else
            "RIGHT_REPORTED_VALUE_EQ_LEFT"
        )
        change=rval-lval

        material={
            "issuer_cik":stable.get("issuer_cik"),
            "left_filing_directory":lfiling,
            "right_filing_directory":rfiling,
            "left_concept_qname":lf.get("concept_qname"),
            "right_concept_qname":rf.get("concept_qname"),
            "concept_stability_receipt_sha256":stable.get("stability_receipt_sha256"),
            "entity":lc.get("entity"),
            "dimensions":lc.get("dimensions"),
            "unit":lf.get("unit"),
            "left_instant":ldate.isoformat(),
            "right_instant":rdate.isoformat(),
            "left_reported_normalized_decimal":format(lval,"f"),
            "right_reported_normalized_decimal":format(rval,"f"),
            "reported_value_relation":relation,
            "reported_decimal_change":format(change,"f"),
            "left_instance_source_sha256":left.get("source_sha256"),
            "right_instance_source_sha256":right.get("source_sha256"),
        }
        return _base(
            "PASS__CROSS_FILING_REPORTED_NUMERIC_FACT_COMPARABILITY_PROVED",
            passed=True,
            cross_filing_fact_measurement_contract_compatible=True,
            reported_value_relation_authority=True,
            reported_value_relation=relation,
            reported_decimal_change=format(change,"f"),
            left_reported_normalized_decimal=format(lval,"f"),
            right_reported_normalized_decimal=format(rval,"f"),
            left_instant=ldate.isoformat(),
            right_instant=rdate.isoformat(),
            entity=lc.get("entity"),
            dimensions=lc.get("dimensions"),
            unit=lf.get("unit"),
            concept_stability_receipt_sha256=stable.get("stability_receipt_sha256"),
            comparison_receipt_sha256=_sha(material),
            left_instance_source_sha256=left.get("source_sha256"),
            right_instance_source_sha256=right.get("source_sha256"),
            underlying_unrounded_value_relation_claimed=False,
            accounting_policy_comparability_claimed=False,
            semantic_truth_authority=False,
            boundary=(
                "PAIRWISE_REPORTED_NORMALIZED_DECIMAL_RELATION_ONLY__"
                "REQUIRES_INDEPENDENT_RAW_INSTANCE_REDERIVATION_AND_STABLE_CONCEPT_CONTRACT__"
                "EXACT_ENTITY_UNIT_DIMENSIONS_AND_CHRONOLOGICAL_INSTANT_PERIOD_SHAPE__"
                "NO_UNROUNDED_ECONOMIC_VALUE_ACCOUNTING_POLICY_OR_TERMINAL_CLAIM"
            ),
        )
    except ValueError as exc:
        msg=str(exc)
        if msg in {
            "ONLY_INSTANT_PERIOD_COMPARABILITY_SUPPORTED_V1",
            "NORMALIZED_DECIMAL_REQUIRED",
            "NORMALIZED_DECIMAL_INVALID",
            "NORMALIZED_DECIMAL_NOT_FINITE",
        }:
            return _base("OPEN__"+msg)
        return _base("FAIL_CLOSED",reason="ValueError:"+msg)
    except Exception as exc:
        return _base("FAIL_CLOSED",reason=type(exc).__name__+":"+str(exc))

def run(args:Mapping[str,Any],root:Any)->dict[str,Any]:
    return verify_comparable_facts(
        root=root,
        left_instance_raw_path=args.get("left_instance_raw_path"),
        left_instance_semantic_path=args.get("left_instance_semantic_path"),
        right_instance_raw_path=args.get("right_instance_raw_path"),
        right_instance_semantic_path=args.get("right_instance_semantic_path"),
        left_concept_xsd_path=args.get("left_concept_xsd_path"),
        left_concept_label_path=args.get("left_concept_label_path"),
        left_concept_semantic_path=args.get("left_concept_semantic_path"),
        right_concept_xsd_path=args.get("right_concept_xsd_path"),
        right_concept_label_path=args.get("right_concept_label_path"),
        right_concept_semantic_path=args.get("right_concept_semantic_path"),
        left_fact_ordinal=args.get("left_fact_ordinal"),
        right_fact_ordinal=args.get("right_fact_ordinal"),
    )
