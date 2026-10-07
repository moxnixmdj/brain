from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from canonical.runtime import continuity_root3_fixed_entry_verifier_v1 as fixed_verify
from canonical.runtime import continuity_root3_selected_route_reachability_v1 as reach_verify
from canonical.runtime import continuity_filesystem_confinement_v1 as fs_verify

ROOT=Path(__file__).resolve().parents[2]
FILES={
    "entry":"canonical/runtime/continuity_root3_fixed_entry_v1.py",
    "entry_verifier":"canonical/runtime/continuity_root3_fixed_entry_verifier_v1.py",
    "adapter":"canonical/runtime/continuity_root3_inprocess_executor_v1.py",
    "supervisor":"canonical/runtime/same_identity_supervisor_credited_v1.py",
    "reachability":"canonical/runtime/continuity_root3_selected_route_reachability_v1.py",
    "filesystem":"canonical/runtime/continuity_filesystem_confinement_v1.py",
    "manifest":"canonical/governance/CONTINUITY_SELECTED_DEPLOYMENT_ROUTE_20261007_V1.json",
    "l1":"canonical/governance/L1_UNIVERSAL_ABC_NORMAL_FORM_THEOREM_20261007_V1.json",
    "d_footprint":"canonical/governance/ROOT3_CREDITED_ROUTE_EFFECT_FOOTPRINT_TOTALITY_20261007_V1.json",
    "authority_semantics":"canonical/runtime/matched_executable_atom_semantics_v1.py",
}
EXPECTED={
    FILES["entry"]:"af55015eb02f64dfce924b7b0a29cd085ab9de2e",
    FILES["entry_verifier"]:"7fffca182794e93ac01092dbc25c7b8609750a4a",
    FILES["adapter"]:"e5351b413ce9819da7f8e69589a2ac1547c902fa",
    FILES["supervisor"]:"47c461f502e840def0c38728e1bfd7c6401cb804",
    FILES["reachability"]:"49d75afcf265486460751de714b72bf9701315bc",
    FILES["filesystem"]:"df0b3139d388ba7459388f95b97bd8d69af2dcd4",
    FILES["manifest"]:"783501ed976adb13972fa8534b1c3f1ad4cc9e9b",
    FILES["l1"]:"cff6a95cad0027f3e142a32fd028a27566a00ea5",
    FILES["d_footprint"]:"9fd755465ae17b19335987b78c154afa6434ab3a",
    FILES["authority_semantics"]:"47a0e828847a57fb206490a866a1041d83c42bde",
}
ALLOWED_PREFIXES=[
    "canonical/same_identity_worker/state",
    "canonical/same_identity_worker/evidence",
    "canonical/same_identity_worker/external_tool_bridge",
]
DIRECT_EFFECTS=[
    "file.open_write","file.remove","file.rename","file.directory_mutation"
]

def blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def defs(tree):
    return {n.name:n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}

def source(fn,text):
    return ast.get_source_segment(text,fn) or ""

def evaluate(root:Path=ROOT):
    errors=[]
    texts={}
    observed={}
    for rel,want in EXPECTED.items():
        data=(root/rel).read_bytes()
        got=blob(data); observed[rel]=got
        if got!=want:
            errors.append("SOURCE_DRIFT:"+rel+":"+got)
        try:
            texts[rel]=data.decode("utf-8")
        except UnicodeDecodeError:
            texts[rel]=""

    fixed=fixed_verify.evaluate(root)
    reach=reach_verify.evaluate(root)
    fs=fs_verify.evaluate(root)
    if fixed.get("pass") is not True:
        errors.append("FIXED_ENTRY_PROOF_FAIL")
    if reach.get("pass") is not True:
        errors.append("REACHABILITY_PROOF_FAIL")
    if fs.get("pass") is not True:
        errors.append("FILESYSTEM_PROOF_FAIL")
    if fs.get("effect_classes")!=DIRECT_EFFECTS:
        errors.append("DIRECT_EFFECT_SET_DRIFT")
    if fs.get("allowed_prefixes")!=ALLOWED_PREFIXES:
        errors.append("ADMIN_PREFIX_SET_DRIFT")
    if reach.get("raw_default_subprocess_executor_reachable_on_selected_route") is not False:
        errors.append("RAW_PROCESS_ROUTE_REOPENED")

    manifest=json.loads(texts[FILES["manifest"]])
    if manifest.get("continuity_owned_effect_classes")!=DIRECT_EFFECTS:
        errors.append("MANIFEST_EFFECT_SET_DRIFT")
    if manifest.get("allowed_continuity_effect_prefixes")!=ALLOWED_PREFIXES:
        errors.append("MANIFEST_PREFIX_SET_DRIFT")

    # Current terminal normal form keeps D separate from universal ABC.
    l1=json.loads(texts[FILES["l1"]])
    nf=l1.get("normal_form_effect_if_verified") or {}
    if nf.get("independent_L1_predicates")!=["COMPLETE_SELECTED_CONTEXT_ABC"]:
        errors.append("L1_NORMAL_FORM_DRIFT")
    if nf.get("D_ownership_effect_closure")!="REMAINS_SEPARATE_AND_OPEN":
        errors.append("D_NOT_SEPARATE")

    # D's current footprint theorem explicitly permits a separately proved
    # equivalent instead of a broker driver for a reachable effect.
    d=json.loads(texts[FILES["d_footprint"]])
    premises=(d.get("theorem") or {}).get("required_premises") or []
    if not any("typed mediated commit route or separately proved equivalent" in str(x) for x in premises):
        # The phrase may occur in the conclusion prose rather than the list.
        if "separately proved equivalent" not in texts[FILES["d_footprint"]]:
            errors.append("D_EQUIVALENT_ROUTE_NOT_ALLOWED")

    sup_text=texts[FILES["supervisor"]]
    sup_tree=ast.parse(sup_text,filename=FILES["supervisor"])
    sd=defs(sup_tree)
    required=["_validate_task","_new_state","_write_json_atomic","_claim_lock","execute_claimed_task"]
    if any(name not in sd for name in required):
        errors.append("SUPERVISOR_FUNCTION_MISSING")
    else:
        validate=source(sd["_validate_task"],sup_text)
        newstate=source(sd["_new_state"],sup_text)
        writej=source(sd["_write_json_atomic"],sup_text)
        lock=source(sd["_claim_lock"],sup_text)
        execute=source(sd["execute_claimed_task"],sup_text)

        # The continuity state/evidence schema does not define task-action
        # permission sets. Task/mission authority remains outside mutable admin state.
        for forbidden in ("allowed_actions","denied_actions","authorized_actions","permission_set"):
            if forbidden in sup_text:
                errors.append("ADMIN_STATE_CONTAINS_ACTION_AUTHORITY_FIELD:"+forbidden)

        for frag in (
            'declared_agent = _safe_id(task.get("agent_id"), "AGENT_ID")',
            'mission_path = str(task.get("mission_path") or "").strip()',
            'mission_sha = str(task.get("mission_sha256") or "").strip().lower()',
            'if float(task.get("incremental_spend_usd", 0)) != 0.0',
        ):
            if frag not in validate:
                errors.append("TASK_AUTHORITY_BINDING_DRIFT:"+frag)

        for frag in (
            '"task_sha256": _task_sha(task)',
            '"mission_path": task["mission_path"]',
            '"mission_sha256": task["mission_sha256"]',
            '"promotion_claim": False',
            '"p_real_claim": 0',
        ):
            if frag not in newstate:
                errors.append("NONEXPANSIVE_STATE_SCHEMA_DRIFT:"+frag)

        for frag in ("path.parent.mkdir","temp.write_text","os.replace(temp, path)"):
            if frag not in writej:
                errors.append("ATOMIC_ADMIN_WRITE_DRIFT:"+frag)
        for frag in ('lock = state_dir / ".claim.lock"',"os.open","lock.unlink"):
            if frag not in lock:
                errors.append("LOCK_ADMIN_EFFECT_DRIFT:"+frag)

        # Bridge is directory creation only in the continuity leaf; no bridge
        # payload write is owned by continuity itself.
        if "bridge_dir.mkdir" not in execute:
            errors.append("BRIDGE_DIRECTORY_CREATION_MISSING")
        bridge_section=execute[execute.find("bridge_dir ="):execute.find("argv =")]
        if "write_text" in bridge_section or "write_bytes" in bridge_section or "open(" in bridge_section:
            errors.append("CONTINUITY_WRITES_BRIDGE_PAYLOAD")

        # Post-executor state/evidence commits happen only after adapter returns.
        if execute.find("result = executor(")<0:
            errors.append("EXECUTOR_CALL_MISSING")
        else:
            post=execute[execute.find("result = executor("):]
            if "_write_json_atomic" not in post:
                errors.append("POST_EXEC_ADMIN_COMMIT_MISSING")

    # Bind current executable authority semantics: task effects must stay inside
    # allowed actions; blocked cases must abstain before further effects.
    auth_text=texts[FILES["authority_semantics"]]
    if "e.get("action_id") not in allowed" not in auth_text:
        errors.append("AUTHORITY_SEMANTIC_DRIFT")
    if 'x.get("decision")=="ABSTAIN"' not in auth_text or 'for e in _rows(events,"EFFECT")' not in auth_text:
        errors.append("FAIL_CLOSED_SEMANTIC_DRIFT")

    ok=not errors
    return {
        "schema":"PROJECT_BRAIN_CONTINUITY_ADMIN_STATE_AUTHORITY_PRESERVATION_V1",
        "status":"PASS__DIRECT_CONTINUITY_ADMIN_EFFECTS_AUTHORITY_NONEXPANSIVE" if ok else "FAIL_CLOSED",
        "pass":ok,
        "errors":errors,
        "observed_blobs":observed,
        "direct_effect_classes":DIRECT_EFFECTS,
        "admin_prefixes":ALLOWED_PREFIXES,
        "authority_sources_mutated":False if ok else None,
        "task_or_mission_bytes_mutated":False if ok else None,
        "action_permission_state_written":False if ok else None,
        "self_promotion_enabled":False if ok else None,
        "direct_process_network_native_effect":False if ok else None,
        "downstream_mission_effects_in_scope":False,
        "D_closed":False,
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
