"""Fail-closed checker for synthesis quality-wake subsumption.

This checker proves no raw-language semantics. It tests a narrower structural claim:
the frozen synthesis target scope is exhausted by six load-bearing dimensions and,
once those dimensions are soundly bound into the explicit V2/V3 synthesis contract,
the existing Brain-owned policy reaches the objective ceiling without a target
comparator. Contexts lacking that binding remain unresolved on the shared semantic
admission frontier rather than constituting a distinct synthesis-quality wake.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_SYNTHESIS_QUALITY_WAKE_SUBSUMPTION_CHECKER_V1"

BOUND={
 "scope":("canonical/governance/SYNTHESIS_SCOPE_CERTIFICATE_V1.json","dea9028f92f111ee3c8be71615fa4b02e8a8bfb6"),
 "metric_truth":("canonical/governance/SYNTHESIS_MATCHED_QUALITY_NECESSITY_TRUTH_REPAIR_20261007_V1.json","688d78a0b39f519a279d9d248c07f31db5292609"),
 "v2":("canonical/governance/SYNTHESIS_EXPLICIT_SELECTION_ORDER_TOP_LAW_CELL_20261007_V2.json","70f5796d77b79e96ffcc706918410da77dd4d653"),
 "v3":("canonical/governance/SYNTHESIS_EXPLICIT_UNCERTAINTY_TOP_LAW_CELL_20261007_V3.json","afcedff26c361938526fa1aa8ddc17f140d19967"),
 "v3_verify":("canonical/verification/SYNTHESIS_EXPLICIT_UNCERTAINTY_V3_SPRITE_VERIFICATION_20261007_V1.json","cb34f78a3789258656f2907d8b8d16a3c14daf7c"),
 "metric":("canonical/governance/SYNTHESIS_MATCHED_QUALITY_METRIC_CONTRACT_V1.json","0886f7592875a5b750cdd401aa783351ab2f0854"),
}

TARGET_DIMS={
 "CLAIM_TO_SOURCE_FIDELITY",
 "REQUIRED_EVIDENCE_COVERAGE",
 "UNCERTAINTY_DISAGREEMENT_PRESERVATION",
 "AUDIENCE_ADAPTATION",
 "FORMAT_STYLE_CONSTRAINTS",
 "COMPRESSION_WITHOUT_DECISION_RELEVANT_LOSS",
}

DIMENSION_TO_WITNESS={
 "CLAIM_TO_SOURCE_FIDELITY":"selected_claim_to_source_fidelity",
 "REQUIRED_EVIDENCE_COVERAGE":"selected_required_claim_coverage",
 "UNCERTAINTY_DISAGREEMENT_PRESERVATION":"uncertainty_and_disagreement_preservation",
 "AUDIENCE_ADAPTATION":"audience_adaptation",
 "FORMAT_STYLE_CONSTRAINTS":"format_and_style_constraints",
 "COMPRESSION_WITHOUT_DECISION_RELEVANT_LOSS":"compression_without_decision_relevant_loss",
}

def _git_blob(raw:bytes)->str:
 return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _load()->dict[str,Mapping[str,Any]]:
 out={}
 for key,(rel,expected) in BOUND.items():
  raw=(ROOT/rel).read_bytes()
  actual=_git_blob(raw)
  if actual!=expected:
   raise ValueError("BOUND_BLOB_DRIFT:"+key+":"+actual)
  doc=json.loads(raw)
  if not isinstance(doc,Mapping):
   raise ValueError("BOUND_JSON_INVALID:"+key)
  out[key]=doc
 return out

def verify_documents(docs:Mapping[str,Mapping[str,Any]])->dict[str,Any]:
 errors=[]
 if not isinstance(docs,Mapping) or not set(BOUND).issubset(docs):
  return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":["BOUND_DOCUMENT_SET_INCOMPLETE"],"terminal_authority":False}

 scope=docs["scope"]
 children=scope.get("children") or []
 scope_dims={str(x.get("target_scope_id") or "").split("/")[-1].replace("-","_").replace(" ","_").upper() for x in children if isinstance(x,Mapping)}
 # Use exact target labels from the independently verified child certificates.
 expected_scope_ids={
  "scope://opus55/synthesis/claim-to-source fidelity",
  "scope://opus55/synthesis/required evidence coverage",
  "scope://opus55/synthesis/uncertainty/disagreement preservation",
  "scope://opus55/synthesis/audience adaptation",
  "scope://opus55/synthesis/format/style constraints",
  "scope://opus55/synthesis/compression without decision-relevant loss",
 }
 got_scope_ids={x.get("target_scope_id") for x in children if isinstance(x,Mapping)}
 if scope.get("coverage_complete") is not True or scope.get("coverage_relation")!="EXACT_UNION":
  errors.append("SYNTHESIS_SCOPE_NOT_COMPLETE_EXACT_UNION")
 if got_scope_ids!=expected_scope_ids:
  errors.append("SYNTHESIS_SCOPE_DIMENSION_SET_DRIFT")
 for row in children:
  if not isinstance(row,Mapping) or row.get("verified") is not True or row.get("formal_completeness") is not True or row.get("all_admissible_target_inputs_proved") is not True:
   errors.append("SYNTHESIS_SCOPE_CHILD_NOT_FORMALLY_COMPLETE")
   break

 truth=docs["metric_truth"]
 established=set((truth.get("established_scope") or {}).get("dimensions") or [])
 if established!=TARGET_DIMS:
  errors.append("TRUTH_REPAIR_TARGET_DIMENSION_SET_DRIFT")
 tr=truth.get("truth_repair") or {}
 if tr.get("delete_only")!="MATCHED_QUALITY_METRIC_IDENTITY_AS_UNCONDITIONAL_TERMINAL_AXIOM":
  errors.append("MATCHED_QUALITY_IDENTITY_STILL_TREATED_AS_AXIOM")
 if "ADDITIONAL_USEFUL_QUALITY_DIMENSION" not in str(tr.get("reopen_if") or ""):
  errors.append("ADDITIONAL_USEFUL_QUALITY_REOPEN_BOUNDARY_MISSING")

 v2=docs["v2"]
 q2=(v2.get("theorem") or {}).get("quality_coordinates") or {}
 if q2.get("selected_claim_to_source_fidelity")!=1:
  errors.append("V2_CLAIM_SOURCE_CEILING_MISSING")
 if q2.get("selected_required_claim_coverage")!=1:
  errors.append("V2_REQUIRED_COVERAGE_CEILING_MISSING")
 if q2.get("typed_audience_adaptation")!=1:
  errors.append("V2_AUDIENCE_CEILING_MISSING")
 if q2.get("typed_format_and_style_constraints")!=1:
  errors.append("V2_FORMAT_STYLE_CEILING_MISSING")
 if q2.get("decision_relevant_selected_content_drop")!=0:
  errors.append("V2_COMPRESSION_LOSS_NOT_ZERO")
 if q2.get("unsupported_new_material_claims")!=0:
  errors.append("V2_UNSUPPORTED_MATERIAL_NOT_ZERO")
 if (v2.get("theorem") or {}).get("comparator_required") is not False:
  errors.append("V2_COMPARATOR_STILL_REQUIRED")

 v3=docs["v3"]
 q3=(v3.get("theorem") or {}).get("matched_quality_coordinates") or {}
 if q3.get("uncertainty_and_disagreement_preservation")!=1:
  errors.append("V3_UNCERTAINTY_CEILING_MISSING")
 for key in ("claim_to_source_fidelity","audience_adaptation","format_and_style_constraints","compression_without_decision_relevant_loss"):
  if q3.get(key)!=1:
   errors.append("V3_QUALITY_COORDINATE_NOT_CEILING:"+key)
 if (v3.get("theorem") or {}).get("comparator_required") is not False:
  errors.append("V3_COMPARATOR_STILL_REQUIRED")
 if (v3.get("selected_class") or {}).get("fail_closed_outside_class") is not True:
  errors.append("V3_OUTSIDE_CLASS_NOT_FAIL_CLOSED")

 vv=docs["v3_verify"]
 if "PASS" not in str(vv.get("status") or ""):
  errors.append("V3_INDEPENDENT_REPLAY_NOT_PASS")
 direct=((vv.get("replay") or {}).get("direct_function_replay") or {})
 if direct.get("tests_run")!=7 or direct.get("tests_passed")!=7 or direct.get("failures")!=0:
  errors.append("V3_REPLAY_COUNT_DRIFT")

 metric=docs["metric"]
 mc=metric.get("metric_contract") or {}
 comps=set(mc.get("quality_components") or [])
 expected_components={
  "claim_to_source_fidelity",
  "uncertainty_and_disagreement_preservation",
  "audience_adaptation",
  "format_and_style_constraints",
  "compression_without_decision_relevant_loss",
 }
 if comps!=expected_components:
  errors.append("MATCHED_QUALITY_COMPONENT_SET_DRIFT")
 if mc.get("excluded_separate_metric")!="required_claim_coverage":
  errors.append("REQUIRED_COVERAGE_NOT_SEPARATE")
 if "MINIMUM" not in str(mc.get("aggregation") or ""):
  errors.append("MATCHED_QUALITY_AGGREGATION_DRIFT")

 # Explicitly verify every load-bearing target dimension has a ceiling witness.
 witness_ok={
  "CLAIM_TO_SOURCE_FIDELITY":q2.get("selected_claim_to_source_fidelity")==1 and q3.get("claim_to_source_fidelity")==1,
  "REQUIRED_EVIDENCE_COVERAGE":q2.get("selected_required_claim_coverage")==1,
  "UNCERTAINTY_DISAGREEMENT_PRESERVATION":q3.get("uncertainty_and_disagreement_preservation")==1,
  "AUDIENCE_ADAPTATION":q2.get("typed_audience_adaptation")==1 and q3.get("audience_adaptation")==1,
  "FORMAT_STYLE_CONSTRAINTS":q2.get("typed_format_and_style_constraints")==1 and q3.get("format_and_style_constraints")==1,
  "COMPRESSION_WITHOUT_DECISION_RELEVANT_LOSS":q2.get("decision_relevant_selected_content_drop")==0 and q3.get("compression_without_decision_relevant_loss")==1,
 }
 if set(witness_ok)!=TARGET_DIMS or not all(witness_ok.values()):
  errors.append("TARGET_DIMENSION_TO_CEILING_WITNESS_INCOMPLETE")

 return {
  "schema":SCHEMA,
  "pass":not errors,
  "status":"PASS__SYNTHESIS_QUALITY_WAKE_SUBSUMED_BY_SCOPE_COMPLETE_DIMENSIONAL_TOP_LAW" if not errors else "FAIL_CLOSED",
  "errors":sorted(set(errors)),
  "target_dimensions":sorted(TARGET_DIMS),
  "dimension_ceiling_witness":witness_ok,
  "separate_synthesis_quality_target_wake_required":False if not errors else None,
  "semantic_admission_required":True,
  "outside_explicit_contract_disposition":"SHARED_ABC_SEMANTIC_ADMISSION_FRONTIER",
  "terminal_authority":False,
  "terminal_credit_delta":0,
 }

def verify_repository()->dict[str,Any]:
 try:return verify_documents(_load())
 except Exception as exc:
  return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":[type(exc).__name__+":"+str(exc)],"terminal_authority":False}
