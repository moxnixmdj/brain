"""Fail-closed pre-wave verifier for native artifact T1 multiplex binding."""
from __future__ import annotations
import json
from pathlib import Path
BINDING="canonical/governance/NATIVE_ARTIFACT_T1_MULTIPLEX_TERMINAL_BINDING_V1.json"
FORMATS={"docx":"XML_SET_TEXT","xlsx":"XML_SET_TEXT","pptx":"XML_SET_TEXT","pdf":"PDF_REPLACE_UNIQUE_TEXT"}
def evaluate(root:Path)->dict:
    errors=[]
    try:d=json.loads((root/BINDING).read_text(encoding="utf-8"))
    except Exception as exc:return {"pass":False,"errors":["BINDING_UNREADABLE:"+type(exc).__name__]}
    if d.get("behavior_id")!="NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001":errors.append("BEHAVIOR_ID")
    if d.get("proof_mode")!="T1_MULTIPLEXED_MECHANICAL_GATE_PLUS_PUBLIC_PROFESSIONAL_BAR":errors.append("PROOF_MODE")
    dec=d.get("decomposition") or {}
    if dec.get("adjacent_behavior_id")!="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001":errors.append("ADJACENT_BEHAVIOR")
    if "SEMANTIC_TARGET_SELECTION" not in str(dec.get("excluded_adjacent_behavior") or ""):errors.append("SEMANTIC_SPLIT")
    fs=d.get("format_scope") or {}
    if set(fs)!=set(FORMATS):errors.append("FORMAT_SCOPE")
    for fmt,kind in FORMATS.items():
        if (fs.get(fmt) or {}).get("edit_kind")!=kind:errors.append("EDIT_KIND:"+fmt)
    vis=set(d.get("candidate_visible_information") or [])
    if "EXPECTED_POST_EDIT_STRUCTURAL_SNAPSHOT" in vis or "RENDER_PIXEL_DIFF_ORACLE" in vis:errors.append("ORACLE_LEAK")
    if len(d.get("independent_preflights") or [])!=2:errors.append("INDEPENDENT_PREFLIGHTS")
    ts=d.get("terminal_surface") or {}
    if ts.get("portfolio")!="T1" or ts.get("synthetic_whole_domain_superset_required") is not False:errors.append("TERMINAL_SURFACE")
    ab=d.get("abstention") or {}
    if ab.get("silent_fallback") is not False:errors.append("SILENT_FALLBACK")
    for k,v in (d.get("contamination") or {}).items():
        if v is not False:errors.append("CONTAMINATION:"+k)
    if d.get("execution_authority") is not False or d.get("terminal_results_observed")!=0:errors.append("AUTHORITY_OR_RESULT")
    for rel in ["canonical/runtime/native_artifact_cross_format_candidate_v1.py","canonical/runtime/native_artifact_cross_format_proof_v1.py","canonical/runtime/native_artifact_render_preservation_proof_v1.py"]:
        if not (root/rel).is_file():errors.append("DEPENDENCY_MISSING:"+rel)
    return {"schema":"PROJECT_BRAIN_NATIVE_ARTIFACT_T1_MULTIPLEX_PREFLIGHT_VERDICT_V1","pass":not errors,"errors":sorted(set(errors)),"execution_authority":False,"capability_credit_delta":0}
