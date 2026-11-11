"""Authority-reconciled witness-target hole totalization v2.

V2 reuses the fail-closed V1 hole-totalizer over the independently verified
13-target normalization. It grants no positive semantic, scope, acceptance, or
family credit. Every target/witness pair is explicit so downstream proof
compilers can work on exact holes rather than stale 11-target bookkeeping.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.witness_target_binding_totalizer_v1 import totalize

ROOT=Path(__file__).resolve().parents[2]
TARGETS=ROOT/"canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V2.json"
TARGET_VERIFY=ROOT/"canonical/verification/OPUS55_MATCHED_TARGET_NORMALIZATION_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json"
WITNESSES=ROOT/"canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json"
TARGETS_REL="canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V2.json"
SCHEMA="PROJECT_BRAIN_WITNESS_TARGET_BINDING_TOTALIZATION_V2"

def _blob(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def _fail(*errors:str)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":"FAIL_CLOSED",
        "pass":False,
        "errors":sorted(set(errors)),
        "binding_surface_totalized":False,
        "semantic_implication_verified":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "new_reality_units_consumed":0,
    }

def evaluate(
    target_doc:Mapping[str,Any],
    target_verification:Mapping[str,Any],
    witness_doc:Mapping[str,Any],
    target_provenance_sha:str,
)->dict[str,Any]:
    errors:list[str]=[]
    status=str(target_verification.get("status",""))
    if not status.startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__13_OF_13_TARGETS"):
        errors.append("TARGET_NORMALIZATION_V2_NOT_INDEPENDENT_PASS")

    exact=target_verification.get("exact_brain_blobs")
    if not isinstance(exact,Mapping) or exact.get(TARGETS_REL)!=target_provenance_sha:
        errors.append("TARGET_PROVENANCE_BLOB_NOT_INDEPENDENTLY_VERIFIED")

    projection=target_verification.get("projection")
    if not isinstance(projection,Mapping) or (
        projection.get("verified_target_count")!=13
        or projection.get("verified_atom_count")!=62
        or projection.get("verified_metric_requirement_count")!=13
        or projection.get("semantic_implication_verified") is not False
    ):
        errors.append("TARGET_VERIFICATION_COUNT_MISMATCH")

    if target_doc.get("schema")!="PROJECT_BRAIN_OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V2":
        errors.append("TARGET_PROVENANCE_SCHEMA_MISMATCH")
    if witness_doc.get("witness_normalization_verified") is not True or witness_doc.get("witness_count")!=9:
        errors.append("WITNESS_CATALOG_NOT_VERIFIED_9")

    if errors:
        return _fail(*errors)

    base=totalize(target_doc,witness_doc)
    if base.get("pass") is not True:
        out=_fail(*(base.get("errors") or ["V1_TOTALIZER_FAILED"]))
        out["upstream_v1_status"]=base.get("status")
        return out

    expected=(13,9,117,62,13,0,0)
    observed=(
        base.get("target_count"),
        base.get("witness_count"),
        base.get("pair_count"),
        base.get("target_atom_occurrence_count"),
        base.get("target_metric_occurrence_count"),
        base.get("direct_atom_binding_count"),
        base.get("direct_metric_binding_count"),
    )
    if observed!=expected:
        return _fail("AUTHORITY_RECONCILED_TOTALIZATION_COUNT_MISMATCH")

    return {
        **base,
        "schema":SCHEMA,
        "status":"PASS__13_TARGET_9_WITNESS_SURFACE_TOTALIZED__117_PAIRS__EXPLICIT_HOLES_ONLY__ZERO_SEMANTIC_CREDIT",
        "target_normalization_verification":"canonical/verification/OPUS55_MATCHED_TARGET_NORMALIZATION_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json",
        "target_provenance_git_blob_sha":target_provenance_sha,
        "rule":(
            "V2_REUSES_VERIFIED_V1_HOLE_TOTALIZATION_ONLY__"
            "13_TARGETS_X_9_WITNESSES_MUST_EQUAL_117_EXPLICIT_PAIRS__"
            "ALL_POSITIVE_SEMANTICS_REMAIN_FORBIDDEN_HERE__"
            "SEPARATE_INDEPENDENT_ATOM_METRIC_AND_SCOPE_CERTIFICATES_REQUIRED"
        ),
    }

def evaluate_live()->dict[str,Any]:
    return evaluate(
        json.loads(TARGETS.read_text(encoding="utf-8")),
        json.loads(TARGET_VERIFY.read_text(encoding="utf-8")),
        json.loads(WITNESSES.read_text(encoding="utf-8")),
        _blob(TARGETS),
    )

def main()->int:
    out=evaluate_live()
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out.get("pass") else 1

if __name__=="__main__":
    raise SystemExit(main())
