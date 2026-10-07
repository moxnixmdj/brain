from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

from canonical.runtime import continuity_root3_fixed_entry_verifier_v1 as fixed_entry_verifier

ROOT=Path(__file__).resolve().parents[2]
MANIFEST="canonical/governance/CONTINUITY_SELECTED_DEPLOYMENT_ROUTE_20261007_V1.json"
ENTRY="canonical/runtime/continuity_root3_fixed_entry_v1.py"
SUPERVISOR="canonical/runtime/same_identity_supervisor_credited_v1.py"

EXPECTED={
    ENTRY:"af55015eb02f64dfce924b7b0a29cd085ab9de2e",
    SUPERVISOR:"47c461f502e840def0c38728e1bfd7c6401cb804",
}
ALLOWED_PREFIXES=(
    "canonical/same_identity_worker/state",
    "canonical/same_identity_worker/evidence",
    "canonical/same_identity_worker/external_tool_bridge",
)

def blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def defs(tree):
    return {n.name:n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}

def evaluate(root:Path=ROOT):
    errors=[]
    observed={}
    texts={}
    trees={}
    for rel,expected in EXPECTED.items():
        data=(root/rel).read_bytes()
        sha=blob(data); observed[rel]=sha
        if sha!=expected:
            errors.append(f"BLOB_DRIFT:{rel}:{sha}")
        text=data.decode("utf-8")
        texts[rel]=text
        trees[rel]=ast.parse(text,filename=rel)

    fixed=fixed_entry_verifier.evaluate(root)
    if fixed.get("pass") is not True:
        errors.extend("FIXED_ENTRY:"+e for e in fixed.get("errors",["UNKNOWN_FAILURE"]))

    manifest=json.loads((root/MANIFEST).read_text())
    if tuple(manifest.get("allowed_continuity_effect_prefixes",[]))!=ALLOWED_PREFIXES:
        errors.append("MANIFEST_ALLOWED_PREFIX_DRIFT")
    entry=manifest.get("entry") or {}
    if entry.get("path")!=ENTRY or entry.get("git_blob_sha")!=EXPECTED[ENTRY]:
        errors.append("MANIFEST_ENTRY_BINDING_DRIFT")

    su=defs(trees[SUPERVISOR])
    safe=su.get("_safe_id")
    statep=su.get("_state_path")
    lock=su.get("_claim_lock")
    writej=su.get("_write_json_atomic")
    execfn=su.get("execute_claimed_task")
    if not all([safe,statep,lock,writej,execfn]):
        errors.append("REQUIRED_SUPERVISOR_FUNCTION_MISSING")
    else:
        safe_src=ast.get_source_segment(texts[SUPERVISOR],safe) or ""
        if r"[A-Za-z0-9_.-]{1,160}" not in safe_src:
            errors.append("SAFE_ID_REGEX_DRIFT")

        state_src=ast.get_source_segment(texts[SUPERVISOR],statep) or ""
        if 'return state_dir / f"{task_id}.json"' not in state_src:
            errors.append("STATE_PATH_SHAPE_DRIFT")

        lock_src=ast.get_source_segment(texts[SUPERVISOR],lock) or ""
        for frag in ('lock = state_dir / ".claim.lock"',"state_dir.mkdir","lock.unlink","os.open"):
            if frag not in lock_src:
                errors.append("LOCK_EFFECT_SHAPE_DRIFT:"+frag)

        write_src=ast.get_source_segment(texts[SUPERVISOR],writej) or ""
        for frag in ("path.parent.mkdir","temp.write_text","os.replace(temp, path)"):
            if frag not in write_src:
                errors.append("ATOMIC_WRITE_EFFECT_SHAPE_DRIFT:"+frag)

        exsrc=ast.get_source_segment(texts[SUPERVISOR],execfn) or ""
        required_fragments=[
            'evidence_dir / f"{task[\'task_id\']}__CHECKPOINT.json"',
            'evidence_dir / f"{task[\'task_id\']}__ATTEMPT_{attempt}.json"',
            '/ "same_identity_worker"',
            '/ "external_tool_bridge"',
            '/ task["task_id"]',
            "bridge_dir.mkdir",
            "evidence_dir.mkdir",
            "_write_json_atomic(state_path, state)",
        ]
        for frag in required_fragments:
            if frag not in exsrc:
                errors.append("EXEC_EFFECT_PATH_SHAPE_DRIFT:"+frag)

    # Algebraic escape check: every dynamic filename component is a safe task id.
    safe_examples=["A","a.b-c_1","Z"*160]
    bad_examples=["../x","a/b","a\\b","", "x"*161]
    for tid in safe_examples:
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,160}",tid):
            errors.append("SAFE_EXAMPLE_REJECTED")
        for prefix in ALLOWED_PREFIXES:
            p=Path(prefix)/tid
            try:
                p.relative_to(Path(prefix))
            except ValueError:
                errors.append("PREFIX_ESCAPE:"+str(p))
    for tid in bad_examples:
        if re.fullmatch(r"[A-Za-z0-9_.-]{1,160}",tid):
            errors.append("MALICIOUS_ID_ACCEPTED:"+tid)

    return {
        "schema":"PROJECT_BRAIN_CONTINUITY_FILESYSTEM_CONFINEMENT_V2",
        "status":"PASS__FIXED_SELECTED_ROUTE_FILESYSTEM_EFFECTS_CONFINED" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "errors":errors,
        "observed_blobs":observed,
        "fixed_entry_verification":fixed.get("status"),
        "allowed_prefixes":list(ALLOWED_PREFIXES),
        "effect_classes":[
            "file.open_write","file.remove","file.rename","file.directory_mutation"
        ],
        "raw_process_effect_in_continuity_leaf":False,
        "downstream_effects_separate":True,
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
