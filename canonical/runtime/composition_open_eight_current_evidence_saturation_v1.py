"""Fail-closed zero-reality saturation audit for the eight open Composition components.

This proves only that the CURRENT EXPLICIT AUTHORITATIVE CANDIDATE SURFACE
contains no new admissible scoped-acceptance receipt. It makes no global
nonexistence claim about unpublished, inaccessible, or unindexed evidence.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CAND="canonical/governance/COMPOSITION_OPEN_EIGHT_CURRENT_EVIDENCE_SATURATION_V1.json"

EXPECTED={
"canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json":"5bb089582a5bc2ee4a44143c8d3a11e919fecdff",
"canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json":"9efbf3e81e67fbd15e34be2fcd86fbfc626b246d",
"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json":"ee187f611a0e82b2de495ee377682f39bc31dd31",
"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":"4000854d577f7ab5f0146d21d16e91d017458431",
"canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_V1.json":"d6cb17f548493e64ca3d200d51b049412a939ef7",
"canonical/verification/COMPOSITION_BEHAVIORAL_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"bb9ecf9b34e3a41d8cd9a387fe70d9376accbccc",
"canonical/governance/COMPOSITION_RECOVERY_SCOPE_COMPLETE_BRIDGE_V1.json":"05f68ee39ebef0a9a1fe1cb0ac2df0cede0725f9",
"canonical/verification/COMPOSITION_RECOVERY_SCOPE_COMPLETE_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"2c18b5029b1a953488b2aefacb00f67b88d27659",
"canonical/verification/RESEARCH_CONTROL_INFORMATION_SAFE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"860cd929e3b7fdab6befec5bf052479dc4ae41ac",
"canonical/verification/BROWSER_T2_OBJECTIVE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"e9913dfb0f4fb3d9256f619c85e5ab072c7109c9",
"canonical/verification/BROWSER_GOAL_GROUNDING_RECOVERY_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"1ca40f09a29f36b16f10c4778adbf38405e630eb",
"canonical/verification/NATIVE_ARTIFACT_T1_MULTIPLEX_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"b8b214a33808ef75c9f5a70fe5f0eb376ea2341e",
"canonical/verification/NATIVE_ARTIFACT_CROSS_FORMAT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"34d8a3b7a99363902d6212759125ac71fa54a986",
"canonical/verification/CURRENT_BRAIN_CODING_CONTROL_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"ea2904e17cbbd353f1bf73364ea073460225ee38",
"canonical/verification/CODING_SUBSTRATE_MATERIALITY_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"8971df6936044eb62a09f7f711227fa85dcde840",
"canonical/verification/OPUS55_SYNTHESIS_PROOF_OBLIGATION_DELTA_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"dc3045403cabfc2adac373afb7089647bb971635",
"canonical/verification/OPUS55_SYNTHESIS_IMPLICATION_RESIDUAL_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json":"c9a3046dd5a409379d675051861600919c3017fb",
}
OPEN=[
"research","tool use","artifact creation","browser/computer action",
"coding","debugging","evidence synthesis","artifact production"
]

def blob(path:str)->str:
    b=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(path:str):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def has(xs, token):
    return token in (xs or [])

def evaluate():
    errors=[]
    drift={p:{"expected":h,"actual":blob(p)} for p,h in EXPECTED.items() if blob(p)!=h}
    if drift:
        return {"pass":False,"status":"FAIL_CLOSED__SOURCE_BLOB_DRIFT","errors":["SOURCE_BLOB_DRIFT"],"drift":drift}

    cand=load(CAND)
    auth=load("canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json")
    manifest=load("canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json")
    registry=load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json")
    bridge=load("canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_V1.json")
    bridge_v=load("canonical/verification/COMPOSITION_BEHAVIORAL_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
    rec_bridge=load("canonical/governance/COMPOSITION_RECOVERY_SCOPE_COMPLETE_BRIDGE_V1.json")
    rec_bridge_v=load("canonical/verification/COMPOSITION_RECOVERY_SCOPE_COMPLETE_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
    research=load("canonical/verification/RESEARCH_CONTROL_INFORMATION_SAFE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
    browser=load("canonical/verification/BROWSER_T2_OBJECTIVE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
    browser_ground=load("canonical/verification/BROWSER_GOAL_GROUNDING_RECOVERY_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
    art_bind=load("canonical/verification/NATIVE_ARTIFACT_T1_MULTIPLEX_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
    art=load("canonical/verification/NATIVE_ARTIFACT_CROSS_FORMAT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
    coding=load("canonical/verification/CURRENT_BRAIN_CODING_CONTROL_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
    coding_mat=load("canonical/verification/CODING_SUBSTRATE_MATERIALITY_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
    synth=load("canonical/verification/OPUS55_SYNTHESIS_PROOF_OBLIGATION_DELTA_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
    synth_res=load("canonical/verification/OPUS55_SYNTHESIS_IMPLICATION_RESIDUAL_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json")

    truth=auth.get("truth") or {}
    if truth.get("frozen_interface_count")!=12: errors.append("AUTH_INTERFACE_COUNT")
    if truth.get("current_admissible_scoped_proved")!=4: errors.append("AUTH_PROVED_COUNT")
    if truth.get("current_open")!=8: errors.append("AUTH_OPEN_COUNT")
    proved=set(truth.get("current_scoped_proved_components") or [])
    if proved!={"memory","recovery","delegation","tool discovery"}: errors.append("AUTH_PROVED_SET")

    manifest_components={x.get("component_id") for x in manifest.get("interfaces",[])}
    if not set(OPEN).issubset(manifest_components): errors.append("OPEN_COMPONENT_NOT_IN_FROZEN_MANIFEST")

    exact_bridge_components={x.get("component_id") for x in bridge.get("bindings",[])}
    if exact_bridge_components!={"tool discovery","delegation"}: errors.append("EXACT_BEHAVIORAL_BRIDGE_SET_DRIFT")
    if bridge_v.get("derived_binding_count")!=2: errors.append("BEHAVIORAL_BRIDGE_COUNT_DRIFT")

    contracts={x.get("behavior_id"):x for x in registry.get("active_contracted_residuals",[])}
    tool=contracts.get("TOOL_ROUTE_DISCOVERY_AND_SELECTION_001") or {}
    tool_semantic=" ".join(str(tool.get(k,"")) for k in (
      "inputs","required_output_or_action","success_condition","failure_condition",
      "terminal_consequence","dependency_boundary","scope"
    )).lower()
    if "tool use" in tool_semantic: errors.append("TOOL_USE_LITERAL_UNEXPECTEDLY_PRESENT_IN_TOOL_ROUTE_CONTRACT")

    research_limits=set(research.get("limitations") or [])
    if "WHOLE_OPEN_ENDED_RESEARCH_SCOPE_EQUIVALENCE_NOT_YET_ESTABLISHED" not in research_limits:
        errors.append("RESEARCH_SCOPE_LIMIT_MISSING")
    if "SCOPE_EQUIVALENT_PROOF_GATE_V2_NOT_YET_PASS" not in research_limits:
        errors.append("RESEARCH_SCOPE_GATE_LIMIT_MISSING")

    browser_limits=set(browser.get("limitations") or [])
    ground_limits=set(browser_ground.get("limitations") or [])
    if "NO_TERMINAL_BROWSER_RESULT" not in browser_limits: errors.append("BROWSER_TERMINAL_LIMIT_MISSING")
    if "SCOPE_EQUIVALENCE_GATE_V2_FOR_WHOLE_BROWSER_VISUAL_CONTRACT_STILL_REQUIRED" not in ground_limits:
        errors.append("BROWSER_SCOPE_LIMIT_MISSING")

    art_limits=set(art.get("limitations") or [])
    if "NO_WHOLE_CONTRACT_SCOPE_EQUIVALENCE" not in art_limits: errors.append("ARTIFACT_SCOPE_LIMIT_MISSING")
    if "NO_TERMINAL_ACCEPTANCE_OR_CAPABILITY_CREDIT" not in art_limits: errors.append("ARTIFACT_CREDIT_LIMIT_MISSING")
    if art_bind.get("terminal_results_observed")!=0: errors.append("ARTIFACT_PREWAVE_TERMINAL_RESULT_UNEXPECTED")

    if "DOES_NOT_PROVE_TERMINAL_BENCH_SCORE_OR_CARRIER_COMPATIBILITY_BY_ITSELF" not in str(coding.get("scope_limit","")):
        errors.append("CODING_SCOPE_LIMIT_MISSING")
    if "NOT_TERMINAL_BENCH_PERFORMANCE" not in str(coding_mat.get("scope_limit","")):
        errors.append("CODING_MATERIALITY_LIMIT_MISSING")

    excluded=set((rec_bridge.get("scope_guard") or {}).get("excluded_scope") or [])
    if "GENERAL_DEBUGGING_COMPONENT" not in excluded: errors.append("RECOVERY_DEBUGGING_EXCLUSION_MISSING")
    if "NO_GENERAL_DEBUGGING_COMPONENT_CREDIT" not in set(rec_bridge_v.get("hard_nonclaims") or []):
        errors.append("RECOVERY_VERIFIER_DEBUGGING_NONCLAIM_MISSING")

    sr=synth.get("result") or {}
    rr=synth_res.get("result") or {}
    if sr.get("acceptance_predicate_closed") is not False: errors.append("SYNTHESIS_DELTA_CLOSED_UNEXPECTEDLY")
    if rr.get("missing_scope_relation") is not True: errors.append("SYNTHESIS_SCOPE_NOT_OPEN")
    if "metric:matched_quality" not in set(rr.get("missing_atoms") or []): errors.append("SYNTHESIS_QUALITY_ATOM_NOT_OPEN")
    need={"matched_quality_noninferiority","required_claim_coverage_noninferiority"}
    if not need.issubset(set(rr.get("missing_metric_bounds") or [])): errors.append("SYNTHESIS_METRIC_BOUNDS_NOT_OPEN")

    expected=list(cand.get("expected_assessments") or [])
    if [x.get("component") for x in expected] != OPEN: errors.append("CANDIDATE_COMPONENT_ORDER_OR_SET_DRIFT")
    if any(x.get("admissible_current_receipt") is not False for x in expected): errors.append("CANDIDATE_INVENTS_ADMISSIBLE_RECEIPT")

    ok=not errors
    return {
      "schema":"PROJECT_BRAIN_COMPOSITION_OPEN_EIGHT_CURRENT_EVIDENCE_SATURATION_VERDICT_V1",
      "status":"PASS__CURRENT_AUTHORITATIVE_CANDIDATE_SURFACE_SATURATED__ZERO_NEW_ADMISSIBLE_RECEIPTS__8_EXACT_RESIDUALS_FROZEN__ZERO_CREDIT" if ok else "FAIL_CLOSED",
      "pass":ok,
      "errors":sorted(set(errors)),
      "current_scoped_proved":4 if ok else None,
      "current_open":8 if ok else None,
      "newly_admissible_receipts":[] if ok else None,
      "newly_closed_components":[] if ok else None,
      "open_components_after_audit":OPEN if ok else None,
      "minimum_missing_conditions":{x["component"]:x["minimum_missing_condition"] for x in expected} if ok else {},
      "slicer_rerun_useful":False if ok else None,
      "bounded_surface_only":True,
      "global_nonexistence_claim":False,
      "new_reality_units_consumed":0,
      "terminal_results_replayed":0,
      "incremental_spend_usd":0,
      "acceptance_credit_delta":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "ownership_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
      "fresh_reality_authority":False,
    }

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
