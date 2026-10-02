"""Deterministic Brain-owned control kernel for configured Harbor coding runs.

The cognition model is an untrusted proposal source. Terminal completion is
authorized only by this module after objective trace checks derived from the
Brain-owned mini-SWE + Superpowers completion contract.
"""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT=Path(__file__).resolve().parents[2]
MANIFEST_PATH=ROOT/"canonical/capabilities/internalized/software_engineering/mini_swe_superpowers_v1/COMPOSED_CONFIGURATION_V1.json"
RULE_MARKERS=(
("KNOWN_FAILURE_GATE","Do not submit while a known relevant failure remains."),
("REQUIREMENT_TRACEABILITY_GATE","Every validation requirement, rejection condition, and mandatory field"),
("ACCEPTANCE_COVERAGE_GATE","Enumerate every explicit acceptance criterion"),
("RUNTIME_ORACLE_GATE","For any criterion whose truth depends on a concrete runtime engine"),
("BROWSER_ORACLE_RULE","For browser, UI, or web-security behavior"),
("ARTIFACT_DEPENDENCY_CLOSURE_GATE","ARTIFACT DEPENDENCY CLOSURE:"),
("CLEAN_ROOM_REPLAY_GATE","CLEAN-ROOM ARTIFACT REPLAY:"),
("FAIL_CLOSED_PORTABILITY_RULE","FAIL-CLOSED PORTABILITY:"),
("CONSTRAINT_ROLE_SEPARATION_GATE","CONSTRAINT ROLE SEPARATION:"),
("BOUNDARY_SATURATION_ORACLE","BOUNDARY SATURATION ORACLE:"),
("ACTUAL_STATE_COUPLING_RULE","ACTUAL-STATE COUPLING:"),
("SINGLE_TERMINAL_AUTHORITY","Only the designated central completion authority"),
)
_VERIFICATION_RE=re.compile(r"(?:^|[;&| ]|python\s+-m\s+)(?:pytest|unittest|test|tests|ruff|mypy|pyright|eslint|tsc|npm\s+test|pnpm\s+test|yarn\s+test|cargo\s+test|go\s+test|mvn\s+test|gradle\s+test|make\s+test|ctest|git\s+diff\s+--check)(?:$|[ ;&|])",re.I)
_DIFF_RE=re.compile(r"(?:^|[;&| ])git\s+(?:diff|status)(?:$|[ ;&|])",re.I)

def _manifest()->dict[str,Any]:
    data=json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if data.get("capability_candidate_id")!="ADVANCED_AGENTIC_SOFTWARE_ENGINEERING_MINI_SWE_SUPERPOWERS_V1":
        raise RuntimeError("CODING_CONFIGURATION_IDENTITY_MISMATCH")
    if data.get("underlying_capability_invention") is not False:
        raise RuntimeError("CODING_CONFIGURATION_INVENTION_FLAG_INVALID")
    return data

def operative_rules()->list[dict[str,str]]:
    req=_manifest()["components"]["brain_completion_gate"]["requirements"]
    if not isinstance(req,list): raise RuntimeError("CODING_CONFIGURATION_REQUIREMENTS_INVALID")
    out=[]
    for rid,marker in RULE_MARKERS:
        matches=[str(x) for x in req if marker in str(x)]
        if len(matches)!=1: raise RuntimeError(f"CODING_CONFIGURATION_RULE_BINDING_INVALID:{rid}:{len(matches)}")
        out.append({"rule_id":rid,"text":matches[0]})
    return out

def render_policy_block()->str:
    data=_manifest(); skills=sorted(data["components"]["methodology"]["skill_pins"])
    lines=["BRAIN-OWNED OPERATIVE CODING CONFIGURATION","candidate_id="+data["capability_candidate_id"],"methodology_modules="+",".join(skills),"The cognition model proposes actions; Brain-owned control alone decides terminal authority."]
    lines += [f'{r["rule_id"]}: {r["text"]}' for r in operative_rules()]
    return "\n".join(lines)

def configuration_fingerprint()->str:
    raw=MANIFEST_PATH.read_bytes()+b"\0"+render_policy_block().encode()
    return hashlib.sha256(raw).hexdigest()

def finish_schema_prompt()->str:
    return ('finish args MUST be {"summary":"...","known_relevant_failures":[],"verification_cycles":[0],"diff_inspection_cycles":[1],"acceptance_criteria":[{"criterion":"...","evidence_cycles":[0,1]}]}. Every referenced cycle must be an earlier successful environment_exec trace. At least one verification cycle must execute a recognized test/check command and at least one diff inspection cycle must execute git diff or git status.')

def _entry(trace:Sequence[Mapping[str,Any]],cycle:int)->Mapping[str,Any]|None:
    return next((r for r in trace if r.get("cycle")==cycle),None)

def _successful(row:Mapping[str,Any]|None)->bool:
    return bool(isinstance(row,Mapping) and isinstance(row.get("action"),Mapping) and row["action"].get("type")=="environment_exec" and isinstance(row.get("result"),Mapping) and row["result"].get("returncode")==0)

def _command(row:Mapping[str,Any]|None)->str:
    if not isinstance(row,Mapping) or not isinstance(row.get("action"),Mapping): return ""
    args=row["action"].get("args")
    return str(args.get("command") or "") if isinstance(args,Mapping) else ""

def validate_finish(args:Mapping[str,Any],trace:Sequence[Mapping[str,Any]])->dict[str,Any]:
    errors=[]
    if not isinstance(args.get("summary"),str) or not str(args.get("summary")).strip(): errors.append("SUMMARY_REQUIRED")
    failures=args.get("known_relevant_failures")
    if not isinstance(failures,list): errors.append("KNOWN_FAILURES_LIST_REQUIRED")
    elif failures: errors.append("KNOWN_RELEVANT_FAILURE_REMAINS")
    vcs=args.get("verification_cycles")
    if not isinstance(vcs,list) or not vcs: errors.append("VERIFICATION_CYCLES_REQUIRED"); vcs=[]
    valid_ver=False
    for raw in vcs:
        if type(raw) is not int: errors.append("VERIFICATION_CYCLE_INVALID"); continue
        row=_entry(trace,raw)
        if not _successful(row): errors.append(f"VERIFICATION_CYCLE_NOT_SUCCESSFUL:{raw}"); continue
        if _VERIFICATION_RE.search(_command(row)): valid_ver=True
    if not valid_ver: errors.append("RECOGNIZED_SUCCESSFUL_VERIFICATION_REQUIRED")
    dcs=args.get("diff_inspection_cycles")
    if not isinstance(dcs,list) or not dcs: errors.append("DIFF_INSPECTION_CYCLES_REQUIRED"); dcs=[]
    valid_diff=False
    for raw in dcs:
        if type(raw) is not int: errors.append("DIFF_INSPECTION_CYCLE_INVALID"); continue
        row=_entry(trace,raw)
        if not _successful(row): errors.append(f"DIFF_INSPECTION_CYCLE_NOT_SUCCESSFUL:{raw}"); continue
        if _DIFF_RE.search(_command(row)): valid_diff=True
    if not valid_diff: errors.append("SUCCESSFUL_DIFF_INSPECTION_REQUIRED")
    criteria=args.get("acceptance_criteria")
    if not isinstance(criteria,list) or not criteria: errors.append("ACCEPTANCE_CRITERIA_REQUIRED"); criteria=[]
    for i,item in enumerate(criteria):
        if not isinstance(item,Mapping): errors.append(f"ACCEPTANCE_CRITERION_INVALID:{i}"); continue
        if not isinstance(item.get("criterion"),str) or not item["criterion"].strip(): errors.append(f"ACCEPTANCE_CRITERION_TEXT_REQUIRED:{i}")
        cycles=item.get("evidence_cycles")
        if not isinstance(cycles,list) or not cycles: errors.append(f"ACCEPTANCE_CRITERION_EVIDENCE_REQUIRED:{i}"); continue
        for raw in cycles:
            if type(raw) is not int or not _successful(_entry(trace,raw)): errors.append(f"ACCEPTANCE_CRITERION_EVIDENCE_NOT_SUCCESSFUL:{i}:{raw}")
    ok=not errors
    return {"schema":"PROJECT_BRAIN_CODING_CONTROL_FINISH_GATE_V1","pass":ok,"status":"TERMINAL_AUTHORIZED" if ok else "TERMINAL_REJECTED","errors":sorted(set(errors)),"configuration_sha256":configuration_fingerprint(),"model_has_terminal_authority":False,"rule":"BRAIN_OWNED_CONTROL_KERNEL_IS_LOAD_BEARING__MODEL_IS_PROPOSAL_SOURCE_ONLY"}
