"""Fail-closed verifier for final CAD T0 oracle extraction/population binding."""
from __future__ import annotations
import hashlib,json
from pathlib import Path

CAD="canonical/governance/CAD_T0_MULTIPLEX_TERMINAL_BINDING_V1.json"
ORACLE="canonical/governance/CAD_T0_ORACLE_EXTRACTION_POPULATION_BINDING_V1.json"
SCHEMA="canonical/governance/CAD_T0_EVALUATOR_OBSERVATION_SCHEMA_V1.json"
SCORER_RECEIPT="canonical/verification/CAD_T0_MULTIPLEX_SCORER_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
PROTOCOL="canonical/governance/GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json"

def _load(root:Path,rel:str):
    return json.loads((root/rel).read_text(encoding="utf-8"))

def verify(root:Path)->dict:
    errors=[]
    try:
        cad=_load(root,CAD); oracle=_load(root,ORACLE); schema=_load(root,SCHEMA)
        scorer=_load(root,SCORER_RECEIPT); protocol=_load(root,PROTOCOL)
    except Exception as exc:
        return {"schema":"PROJECT_BRAIN_CAD_T0_FINAL_PREWAVE_VERDICT_V1","pass":False,"errors":["UNREADABLE:"+type(exc).__name__],"execution_authority":False}

    if cad.get("behavior_id")!="CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001":
        errors.append("CAD_BEHAVIOR")
    if cad.get("oracle_extraction_population_binding")!=ORACLE:
        errors.append("ORACLE_BINDING_NOT_ATTACHED")
    if cad.get("remaining_prequalification")!=["INDEPENDENT_CAD_T0_ORACLE_EXTRACTION_BINDING_VERIFICATION_PENDING"]:
        errors.append("CAD_REMAINING_BLOCKERS")
    if "INDEPENDENT_PASS" not in str(scorer.get("status","")):
        errors.append("SCORER_NOT_INDEPENDENT_PASS")
    if scorer.get("incremental_spend_usd")!=0:
        errors.append("SCORER_NONZERO_SPEND")

    if oracle.get("behavior_id")!=cad.get("behavior_id") or oracle.get("portfolio")!="T0_CODING_SEMANTIC_GEOMETRY_PORTFOLIO":
        errors.append("ORACLE_SCOPE")
    src=oracle.get("source_rule") or {}
    for key in ("pre_beacon_case_selection","adaptive_case_selection","case_replacement","tuning_replay"):
        if src.get(key) is not False:
            errors.append("SOURCE_SELECTION:"+key)
    if "POST_FREEZE" not in str(src.get("selection","")):
        errors.append("POST_FREEZE_SELECTOR_NOT_BOUND")

    ex=oracle.get("oracle_extraction") or {}
    if ex.get("runtime")!="canonical/runtime/cad_t0_oracle_extractor.py":
        errors.append("EXTRACTOR_RUNTIME")
    if ex.get("scorer")!="canonical/runtime/cad_t0_multiplex_scorer.py":
        errors.append("SCORER_RUNTIME")
    if ex.get("observation_schema")!=SCHEMA:
        errors.append("OBSERVATION_SCHEMA")
    if ex.get("candidate_self_report_as_oracle") is not False:
        errors.append("CANDIDATE_SELF_REPORT_AUTHORITY")
    if ex.get("immutable_candidate_output_digest_required") is not True:
        errors.append("OUTPUT_DIGEST_NOT_REQUIRED")
    if ex.get("producer_id_and_version_or_blob_required") is not True:
        errors.append("PRODUCER_PROVENANCE_NOT_REQUIRED")

    fields=schema.get("observation_fields") or {}
    required={
      "candidate_solid_valid","geometry_class_covered","candidate_geometry_metrics",
      "ambiguity_witness_valid","end_to_end_final_geometry_correct",
      "cross_stage_state_loss","failure_localization_consistent",
    }
    if set(fields)!=required:
        errors.append("OBSERVATION_FIELD_SET")
    for name,row in fields.items():
        if row.get("candidate_may_supply") is not False:
            errors.append("CANDIDATE_MAY_SUPPLY:"+name)

    deps=oracle.get("dependencies") or []
    for rel in deps:
        if not isinstance(rel,str) or not (root/rel).is_file():
            errors.append("DEPENDENCY_MISSING:"+str(rel))
    if not (root/"canonical/runtime/cad_t0_oracle_extractor.py").is_file():
        errors.append("EXTRACTOR_MISSING")

    rp=protocol.get("route_specific_requirements") or {}
    if "open-domain" not in str(rp.get("scope","")).lower() and "OPEN_DOMAIN" not in str(rp.get("scope","")):
        errors.append("OPEN_DOMAIN_SCOPE_LAW_MISSING")
    if oracle.get("execution_authority") is not False or oracle.get("terminal_results_observed")!=0:
        errors.append("ORACLE_OVERCLAIM")
    if cad.get("execution_authority") is not False or cad.get("terminal_results_observed")!=0:
        errors.append("CAD_OVERCLAIM")

    return {
      "schema":"PROJECT_BRAIN_CAD_T0_FINAL_PREWAVE_VERDICT_V1",
      "pass":not errors,"errors":sorted(set(errors)),
      "execution_authority":False,"terminal_results_observed":0,
      "capability_credit_delta":0,"family_credit_delta":0,"incremental_spend_usd":0,
    }
