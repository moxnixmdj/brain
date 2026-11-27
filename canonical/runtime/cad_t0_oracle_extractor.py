"""Evaluator-only CAD T0 case/oracle binding and observation extractor.

No terminal case is opened by this module. It validates the frozen post-beacon
selection metadata and transforms evaluator-side hidden reference plus independent
measurement records into the exact hidden case/orservation objects consumed by
cad_t0_multiplex_scorer.py.

Candidate self-report is never accepted as geometry or oracle authority.
"""
from __future__ import annotations
import hashlib
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_CAD_T0_ORACLE_EXTRACTION_V1"
PORTFOLIO="T0_CODING_SEMANTIC_GEOMETRY_PORTFOLIO"
BEHAVIOR="CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001"

_HIDDEN_REQUIRED={
    "reference_constraint_graph","identifiable","required_geometry_metrics",
    "reference_geometry_metrics","metric_tolerances","geometry_class_label",
}
_MEASURE_REQUIRED={
    "producer_id","producer_version_or_blob","input_artifact_digest",
    "candidate_output_digest","candidate_solid_valid","geometry_class_covered",
    "candidate_geometry_metrics","ambiguity_witness_valid",
    "end_to_end_final_geometry_correct","cross_stage_state_loss",
    "failure_localization_consistent",
}
_FORBIDDEN_CANDIDATE={
    "_oracle","reference_constraint_graph","reference_geometry_metrics",
    "reference_solid","gold","mutation_identity","expected_failure_reason",
    "candidate_geometry_metrics","geometry_class_covered",
}

def _digest_bytes(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def bind_case(
    case_meta:Mapping[str,Any],
    hidden_oracle:Mapping[str,Any],
    candidate:Mapping[str,Any],
    measurement:Mapping[str,Any],
    *,
    candidate_output_bytes:bytes,
)->dict[str,Any]:
    errors:list[str]=[]
    if not all(isinstance(x,Mapping) for x in (case_meta,hidden_oracle,candidate,measurement)):
        return {"schema":SCHEMA,"pass":False,"errors":["INPUT_NOT_MAPPING"]}

    if case_meta.get("portfolio")!=PORTFOLIO:
        errors.append("WRONG_PORTFOLIO")
    if case_meta.get("behavior_id")!=BEHAVIOR:
        errors.append("WRONG_BEHAVIOR")
    if case_meta.get("m1_load_bearing") is not True:
        errors.append("M1_NOT_PREDECLARED_LOAD_BEARING")
    if case_meta.get("selected_after_post_freeze_beacon") is not True:
        errors.append("PREBEACON_OR_UNFROZEN_SELECTION")
    for key in ("case_id","selector_commitment","post_freeze_beacon"):
        if not isinstance(case_meta.get(key),str) or not case_meta.get(key):
            errors.append("CASE_META_MISSING:"+key)

    missing_hidden=sorted(_HIDDEN_REQUIRED-set(hidden_oracle))
    if missing_hidden:
        errors.append("HIDDEN_ORACLE_MISSING:"+",".join(missing_hidden))
    identifiable=hidden_oracle.get("identifiable")
    if identifiable not in (True,False):
        errors.append("IDENTIFIABILITY_INVALID")
    required=hidden_oracle.get("required_geometry_metrics")
    refs=hidden_oracle.get("reference_geometry_metrics")
    tols=hidden_oracle.get("metric_tolerances")
    if not isinstance(required,list) or not required or any(not isinstance(x,str) or not x for x in required):
        errors.append("REQUIRED_METRICS_INVALID")
    elif not isinstance(refs,Mapping) or not isinstance(tols,Mapping):
        errors.append("REFERENCE_METRICS_OR_TOLERANCES_INVALID")
    else:
        for name in required:
            if name not in refs or name not in tols:
                errors.append("REFERENCE_METRIC_UNBOUND:"+name)

    leaked=sorted(_FORBIDDEN_CANDIDATE & set(candidate))
    if leaked:
        errors.append("CANDIDATE_ORACLE_SELF_REPORT:"+",".join(leaked))

    missing_measure=sorted(_MEASURE_REQUIRED-set(measurement))
    if missing_measure:
        errors.append("MEASUREMENT_MISSING:"+",".join(missing_measure))
    for key in ("producer_id","producer_version_or_blob","input_artifact_digest","candidate_output_digest"):
        if not isinstance(measurement.get(key),str) or not measurement.get(key):
            errors.append("MEASUREMENT_PROVENANCE_INVALID:"+key)

    expected=_digest_bytes(candidate_output_bytes)
    if measurement.get("candidate_output_digest")!=expected:
        errors.append("CANDIDATE_OUTPUT_DIGEST_MISMATCH")
    if measurement.get("producer_id") in {"candidate","self","candidate_stdout","candidate_json"}:
        errors.append("CANDIDATE_MEASUREMENT_PRODUCER_FORBIDDEN")
    if not isinstance(measurement.get("candidate_geometry_metrics"),Mapping):
        errors.append("CANDIDATE_GEOMETRY_METRICS_INVALID")

    if errors:
        return {"schema":SCHEMA,"pass":False,"errors":sorted(set(errors))}

    scorer_case=dict(case_meta.get("public_case") or {})
    scorer_case["_oracle"]={
        "reference_constraint_graph":hidden_oracle["reference_constraint_graph"],
        "identifiable":identifiable,
        "required_geometry_metrics":list(required),
        "reference_geometry_metrics":dict(refs),
        "metric_tolerances":dict(tols),
        "geometry_class_label":hidden_oracle["geometry_class_label"],
        "mutation_identity":hidden_oracle.get("mutation_identity"),
    }
    observation={
        key:measurement[key] for key in (
            "candidate_solid_valid","geometry_class_covered","candidate_geometry_metrics",
            "ambiguity_witness_valid","end_to_end_final_geometry_correct",
            "cross_stage_state_loss","failure_localization_consistent"
        )
    }
    provenance={
        "producer_id":measurement["producer_id"],
        "producer_version_or_blob":measurement["producer_version_or_blob"],
        "input_artifact_digest":measurement["input_artifact_digest"],
        "candidate_output_digest":measurement["candidate_output_digest"],
        "case_id":case_meta["case_id"],
        "selector_commitment":case_meta["selector_commitment"],
        "post_freeze_beacon":case_meta["post_freeze_beacon"],
    }
    return {
        "schema":SCHEMA,"pass":True,"errors":[],
        "scorer_case":scorer_case,"observation":observation,
        "measurement_provenance":provenance,
        "terminal_authority":False,
    }
