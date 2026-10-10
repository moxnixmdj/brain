"""Professional-quality declared-system dependency closure compiler V2.

Reuses the verified transitive-runtime closure mechanism, but computes subject
identity from the declared system itself, never from external root-verification
tooling. Root-specific compilers/receipts remain evidence inputs unless the
declared system's runtime/config dependency cone actually includes them.

Diagnostic only: no root, quality, acceptance, promotion, ownership, or
terminal authority.
"""
from __future__ import annotations

import ast
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.python_transitive_runtime_closure_v1 import (
    ClosureError,
    compute_closure,
)

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_SUBJECT_DEPENDENCY_CLOSURE_V2"
REGISTRY_PATH="canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json"
WORKLIST_PATH="canonical/governance/PROFESSIONAL_QUALITY_SUBJECT_DEPENDENCY_CLOSURE_WORKLIST_20261010_V1.json"
EXPECTED_ROOTS=(
    "R1_TARGET_SPECIFICATION","R2_CANDIDATE_SEARCH","R3_REALIZATION_OBSERVATION",
    "R4_MEASUREMENT_CONSTRUCT","R5_EVALUATOR_REFERENCE",
    "R6_EVIDENCE_GROUNDING_DEPENDENCE","R7_CAUSAL_PRESCRIPTIVE",
    "R8_POPULATION_CONTEXT_OPERATOR","R9_TEMPORAL_DEPLOYMENT",
    "R10_ANALYSIS_DECISION","R11_ADAPTIVE_INTEGRITY_SECURITY",
    "R12_META_COMPOSITION_CLOSURE",
)

def _blob(path:Path)->str:
    raw=path.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _base(status:str,*,passed:bool=False,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,"status":status,"pass":passed,
        "dependency_classification_authority":False,
        "root_subject_binding_authority":False,
        "quality_authority":False,"acceptance_authority":False,
        "promotion_authority":False,"terminal_authority":False,
        "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
    }

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return _base("FAIL_CLOSED",reason=reason,**extra)

def _resolve(root:Path,rel:str)->Path|None:
    if not isinstance(rel,str) or not rel.startswith("canonical/"):
        return None
    p=(root/rel).resolve()
    try:p.relative_to(root.resolve())
    except ValueError:return None
    return p

def _json(root:Path,rel:str)->dict[str,Any]|None:
    p=_resolve(root,rel)
    if p is None or not p.is_file() or p.is_symlink():return None
    try:o=json.loads(p.read_text(encoding="utf-8"))
    except Exception:return None
    return o if isinstance(o,dict) else None

def _literal_refs(root:Path,rel:str)->dict[str,list[str]]:
    p=_resolve(root,rel)
    if p is None or not p.is_file():return {"governance":[],"external":[]}
    try:tree=ast.parse(p.read_text(encoding="utf-8"),filename=rel)
    except Exception:return {"governance":[],"external":[]}
    gov=set(); ext=set()
    for node in ast.walk(tree):
        if not isinstance(node,ast.Constant) or not isinstance(node.value,str):
            continue
        raw=node.value
        if not raw.startswith("canonical/") or not raw.endswith((".json",".py")):
            continue
        rp=_resolve(root,raw)
        if rp is None or not rp.is_file() or rp.is_symlink():
            continue
        if raw.startswith("canonical/governance/"):
            gov.add(raw)
        elif raw.startswith(("canonical/verification/","canonical/evidence/","canonical/action_intents/")):
            ext.add(raw)
    return {"governance":sorted(gov),"external":sorted(ext)}

def compile_closure(*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    registry=_json(root,REGISTRY_PATH); worklist=_json(root,WORKLIST_PATH)
    if registry is None or worklist is None:
        return _fail("CURRENT_REGISTRY_OR_WORKLIST_INVALID")

    cand=worklist.get("candidate_subject")
    if not isinstance(cand,Mapping) or not isinstance(cand.get("path"),str):
        return _fail("CANDIDATE_SUBJECT_INVALID")
    subject_path=str(cand["path"]); subject=_json(root,subject_path)
    if subject is None:return _fail("CANDIDATE_SUBJECT_INVALID")
    material=subject.get("system_material")
    components=material.get("components") if isinstance(material,Mapping) else None
    if not isinstance(components,list):return _fail("CANDIDATE_SUBJECT_COMPONENTS_INVALID")
    subject_components={
        str(r["path"]) for r in components
        if isinstance(r,Mapping) and isinstance(r.get("path"),str)
    }
    runtime_roots=sorted(
        p for p in subject_components
        if p.startswith("canonical/runtime/") and p.endswith(".py")
    )
    if not runtime_roots:return _fail("SUBJECT_RUNTIME_ROOTS_EMPTY")

    try:closure=compute_closure(root,runtime_roots)
    except ClosureError as exc:return _fail("TRANSITIVE_RUNTIME_CLOSURE_FAILED",detail=str(exc))
    if closure.get("pass") is not True:
        return _fail("TRANSITIVE_RUNTIME_CLOSURE_OPEN",closure=closure)

    runtime_closure={str(r["path"]) for r in closure.get("files",[]) if isinstance(r,Mapping)}
    governance_refs=set(); external_runtime_refs=set()
    for rel in sorted(runtime_closure):
        refs=_literal_refs(root,rel)
        governance_refs.update(refs["governance"])
        external_runtime_refs.update(refs["external"])

    required_system_material=runtime_closure|governance_refs
    missing=sorted(required_system_material-subject_components)

    entries=registry.get("entries")
    if not isinstance(entries,list):return _fail("SCOPED_REGISTRY_ENTRIES_INVALID")
    by_root={r:[] for r in EXPECTED_ROOTS}
    for entry in entries:
        if isinstance(entry,Mapping) and entry.get("root_id") in by_root:
            by_root[str(entry["root_id"])].append(entry)
    for rid,rows in by_root.items():
        if not rows:return _fail("ROOT_SCOPED_SUPPORT_MISSING",root_id=rid)

    root_rows=[]
    for rid in EXPECTED_ROOTS:
        mechanisms=set(); evidence=set(); scope_inputs=set()
        for row in by_root[rid]:
            comp=row.get("reusable_compiler")
            if isinstance(comp,Mapping) and isinstance(comp.get("path"),str):
                mechanisms.add(str(comp["path"]))
            rec=row.get("source_receipt")
            if isinstance(rec,Mapping) and isinstance(rec.get("path"),str):
                evidence.add(str(rec["path"]))
            sg=row.get("scope_governance")
            if isinstance(sg,Mapping) and isinstance(sg.get("path"),str):
                scope_inputs.add(str(sg["path"]))
        live_mechanisms=sorted(mechanisms & runtime_closure)
        external_mechanisms=sorted(mechanisms-runtime_closure)
        root_rows.append({
            "root_id":rid,
            "scoped_support_count":len(by_root[rid]),
            "system_material_mechanisms":live_mechanisms,
            "external_verification_mechanisms":external_mechanisms,
            "external_evidence_inputs":sorted(evidence|scope_inputs),
            "classification_status":"CLASSIFIED",
        })

    complete=not missing
    return _base(
        "PASS__DECLARED_SYSTEM_DEPENDENCY_CLASSIFICATION_COMPLETE__SUBJECT_CLOSED"
        if complete else
        "PASS__DECLARED_SYSTEM_DEPENDENCY_CLASSIFICATION_COMPLETE__SUBJECT_EXPANSION_REQUIRED",
        passed=True,
        candidate_subject_path=subject_path,
        candidate_subject_git_blob_sha=_blob(_resolve(root,subject_path)),
        current_subject_component_count=len(subject_components),
        subject_runtime_root_count=len(runtime_roots),
        subject_runtime_roots=runtime_roots,
        transitive_runtime_closure_file_count=len(runtime_closure),
        transitive_runtime_closure_files=sorted(runtime_closure),
        governance_configuration_dependencies=sorted(governance_refs),
        runtime_external_evidence_references=sorted(external_runtime_refs),
        required_system_material=sorted(required_system_material),
        missing_subject_components=missing,
        missing_subject_component_count=len(missing),
        subject_dependency_closure_complete=complete,
        roots_total=len(root_rows),
        roots_dependency_classified=len(root_rows),
        roots=root_rows,
        classification_law=(
            "SYSTEM_IDENTITY_IS_DERIVED_FROM_THE_DECLARED_SYSTEM_RUNTIME_AND_CONFIGURATION_"
            "DEPENDENCY_CONE__ROOT_VERIFIERS_AND_RECEIPTS_REMAIN_EXTERNAL_UNLESS_THE_"
            "DECLARED_SYSTEM_ACTUALLY_IMPORTS_OR_READS_THEM"
        ),
    )

if __name__=="__main__":
    print(json.dumps(compile_closure(),indent=2,sort_keys=True))
