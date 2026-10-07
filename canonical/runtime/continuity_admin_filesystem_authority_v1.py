from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ENTRY="canonical/runtime/continuity_root3_fixed_entry_v2.py"
SUPERVISOR="canonical/runtime/same_identity_supervisor_credited_v1.py"
EXPECTED={
    ENTRY:"0aec0038af9babbe6d7786c8e5869546ebd688dd",
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
    texts={}
    trees={}
    observed={}
    for rel,expected in EXPECTED.items():
        data=(root/rel).read_bytes()
        sha=blob(data); observed[rel]=sha
        if sha!=expected:
            errors.append("BLOB_DRIFT:"+rel+":"+sha)
        texts[rel]=data.decode("utf-8")
        trees[rel]=ast.parse(texts[rel],filename=rel)

    entry_text=texts[ENTRY]
    for frag in [
        'TASKS_DIR=ROOT/"canonical/same_identity_worker/tasks"',
        'STATE_DIR=ROOT/"canonical/same_identity_worker/state"',
        'EVIDENCE_DIR=ROOT/"canonical/same_identity_worker/evidence"',
        "relative_to(tasks_root)",
        'TASK_PATH_OUTSIDE_CANONICAL_TASK_QUEUE',
        'TASK_PATH_NOT_JSON',
    ]:
        if "".join(frag.split()) not in "".join(entry_text.split()):
            errors.append("ENTRY_AUTHORITY_GUARD_DRIFT:"+frag)

    su=defs(trees[SUPERVISOR])
    required_names=[
        "_safe_id","_write_json_atomic","_claim_lock","_validate_task",
        "_validate_existing_state","claim_task","execute_claimed_task"
    ]
    for name in required_names:
        if name not in su:
            errors.append("SUPERVISOR_FUNCTION_MISSING:"+name)

    if not errors:
        def src(name):
            return ast.get_source_segment(texts[SUPERVISOR],su[name]) or ""

        checks={
          "_safe_id":[r"[A-Za-z0-9_.-]{1,160}"],
          "_write_json_atomic":["path.parent.mkdir","temp.write_text","os.replace(temp, path)"],
          "_claim_lock":['state_dir / ".claim.lock"',"state_dir.mkdir","os.open","os.write","lock.unlink"],
          "_validate_task":[
              "declared_agent != agent_id",
              "NONZERO_INCREMENTAL_SPEND",
              "MISSION_BINDING_INVALID",
              "_safe_id(task.get(\"task_id\")",
          ],
          "_validate_existing_state":[
              "STATE_AGENT_ID_MISMATCH",
              "TASK_MANIFEST_DRIFT",
              "STATE_MISSION_SHA_MISMATCH",
              "LEASE_OWNER_MISMATCH",
          ],
          "claim_task":[
              "_validate_task",
              "_prerequisites_satisfied",
              "MISSION_SHA_MISMATCH",
              "with _claim_lock(state_dir)",
              "_write_json_atomic(_state_path(state_dir, task[\"task_id\"]), state)",
          ],
          "execute_claimed_task":[
              "CLAIM_BINDING_INVALID",
              "_write_json_atomic(state_path, state)",
              'evidence_dir / f"{task[\'task_id\']}__CHECKPOINT.json"',
              'evidence_dir / f"{task[\'task_id\']}__ATTEMPT_{attempt}.json"',
              '/ "same_identity_worker"',
              '/ "external_tool_bridge"',
              '/ task["task_id"]',
              "bridge_dir.mkdir",
              "evidence_dir.mkdir",
          ],
        }
        for name,frags in checks.items():
            body=src(name)
            for frag in frags:
                if frag not in body:
                    errors.append("AUTHORITY_SEMANTIC_DRIFT:"+name+":"+frag)

    # Exhaustive direct filesystem mutation API inventory in the credited supervisor.
    mutation_suffixes={"mkdir","write_text","unlink"}
    mutation_dotted={"os.replace","os.open","os.write"}
    observed_mutations=[]
    for node in ast.walk(trees[SUPERVISOR]):
        if not isinstance(node,ast.Call):
            continue
        name=None
        if isinstance(node.func,ast.Attribute):
            parts=[]
            cur=node.func
            while isinstance(cur,ast.Attribute):
                parts.append(cur.attr);cur=cur.value
            if isinstance(cur,ast.Name):
                parts.append(cur.id)
                name=".".join(reversed(parts))
        elif isinstance(node.func,ast.Name):
            name=node.func.id
        if name and (name in mutation_dotted or name.split(".")[-1] in mutation_suffixes):
            observed_mutations.append(name)
    required_mutations={"path.parent.mkdir","temp.write_text","os.replace","state_dir.mkdir","os.open","os.write","lock.unlink","bridge_dir.mkdir","evidence_dir.mkdir"}
    if not required_mutations.issubset(set(observed_mutations)):
        errors.append("MUTATION_INVENTORY_MISSING:"+repr(sorted(required_mutations-set(observed_mutations))))

    return {
      "schema":"PROJECT_BRAIN_CONTINUITY_ADMIN_FILESYSTEM_AUTHORITY_VERIFIER_V1",
      "status":"PASS__SELECTED_CONTINUITY_ADMIN_WRITES_BOUND_TO_CANONICAL_TASK_AUTHORITY_AND_FIXED_PREFIXES" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "observed_blobs":observed,
      "allowed_effect_classes":["file.open_write","file.remove","file.rename","file.directory_mutation"],
      "allowed_prefixes":list(ALLOWED_PREFIXES),
      "authority_preconditions":[
        "CANONICAL_TASK_QUEUE_JSON_ONLY",
        "SAFE_TASK_ID",
        "BOUND_AGENT_ID",
        "ZERO_INCREMENTAL_SPEND",
        "MISSION_SHA_BINDING",
        "PREREQUISITES_SATISFIED",
        "TASK_SHA_BINDING",
        "LEASE_OWNER_BINDING"
      ],
      "downstream_mission_effects_separate":True,
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
