#!/usr/bin/env python3
"""Verify a frozen plan, atomically admit this Actions run, then start the child."""
import argparse,hashlib,json,os,pathlib,subprocess,urllib.error,urllib.request
from actions_admission import FrozenExecution,admit_current_run_once,problem_sha256
from github_ref_store_live import GitHubRefStore
from v22_prewrite_admission import ACTIVE_POINTER_PATH, admission_errors as v22_admission_errors, referenced_receipt_paths

def request_factory(token,api="https://api.github.com"):
    def req(method,path,payload=None):
        data=None if payload is None else json.dumps(payload,separators=(",",":")).encode()
        r=urllib.request.Request(api+path,data=data,method=method,headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"project-brain-execution-guard-v1"})
        try:
            with urllib.request.urlopen(r,timeout=20) as x: raw=x.read(); return x.status,(json.loads(raw) if raw else {}),dict(x.headers.items())
        except urllib.error.HTTPError as e:
            raw=e.read()
            try: body=json.loads(raw) if raw else {}
            except Exception: body={"message":"non-json HTTP error"}
            return e.code,body,dict(e.headers.items())
    return req

def blob_sha(p):
    raw=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def sha256(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def verify_pins(root,pins):
    if not isinstance(pins,list) or not pins: raise ValueError("PLAN_PINS_REQUIRED")
    checked=[]; root=root.resolve()
    for x in pins:
        rel=x.get("path"); p=(root/str(rel)).resolve()
        if not isinstance(rel,str) or rel.startswith("/") or ".." in pathlib.PurePosixPath(rel).parts or (p!=root and root not in p.parents): raise ValueError("PIN_PATH_INVALID")
        if not p.is_file(): raise RuntimeError("PIN_FILE_MISSING:"+rel)
        if x.get("git_blob_sha1") and blob_sha(p)!=x["git_blob_sha1"]: raise RuntimeError("PIN_GIT_BLOB_MISMATCH:"+rel)
        if x.get("sha256") and sha256(p)!=x["sha256"]: raise RuntimeError("PIN_SHA256_MISMATCH:"+rel)
        checked.append(rel)
    return checked


def _safe_pinned_json(root,rel,checked):
    if not isinstance(rel,str) or not rel or rel not in checked:
        raise RuntimeError("V22_REQUIRED_PIN_MISSING:"+str(rel))
    pure=pathlib.PurePosixPath(rel)
    if rel.startswith("/") or ".." in pure.parts:
        raise RuntimeError("V22_PIN_PATH_INVALID:"+rel)
    p=(root/rel).resolve()
    if p!=root and root not in p.parents:
        raise RuntimeError("V22_PIN_PATH_ESCAPE:"+rel)
    return json.loads(p.read_text(encoding="utf-8"))

def verify_v22_prewrite(root,plan,checked):
    required={"execution_guard/v22_prewrite_admission.py",ACTIVE_POINTER_PATH}
    missing=sorted(required-set(checked))
    if missing:
        raise RuntimeError("V22_GUARD_PINS_MISSING:"+",".join(missing))
    pointer=_safe_pinned_json(root,ACTIVE_POINTER_PATH,checked)
    pointer_blob=blob_sha(root/ACTIVE_POINTER_PATH)
    authority=plan.get("authority") or {}
    intent_rel=authority.get("brain_action_intent")
    intent=_safe_pinned_json(root,intent_rel,checked)
    plan_admission=plan.get("v22_prewrite_admission")
    intent_admission=intent.get("v22_prewrite_admission")
    if plan_admission!=intent_admission:
        raise RuntimeError("V22_PLAN_INTENT_ADMISSION_MISMATCH")
    receipt_blobs={}
    for rel in referenced_receipt_paths(plan_admission):
        _safe_pinned_json(root,rel,checked)
        receipt_blobs[rel]=blob_sha(root/rel)
    errors=v22_admission_errors(
        plan_admission,pointer,pointer_blob_sha=pointer_blob,
        action_kind=str(intent.get("action_kind") or ""),
        receipt_blobs=receipt_blobs,
    )
    if errors:
        raise RuntimeError("V22_PREWRITE_ADMISSION_DENIED:"+"|".join(errors))
    return {"status":"PASS","mode":plan_admission.get("mode"),"active_pointer_git_blob_sha":pointer_blob}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--plan",required=True); ap.add_argument("--workspace",default="."); ap.add_argument("--receipt",default="execution-guard-launch-receipt.json"); a=ap.parse_args()
    plan=json.loads(pathlib.Path(a.plan).read_text())
    if plan.get("schema")!="BRAIN_GUARDED_LAUNCH_PLAN_V1": raise ValueError("PLAN_SCHEMA_INVALID")
    frozen=dict(plan.get("frozen") or {}); goal=plan.get("goal_text"); observed=problem_sha256(goal)
    if frozen.get("problem_sha256")!=observed: raise ValueError("PROBLEM_IDENTITY_MISMATCH")
    spec=FrozenExecution(**frozen); spec.validate(); command=plan.get("command")
    if not isinstance(command,list) or not command or not all(isinstance(x,str) and x for x in command): raise ValueError("PLAN_COMMAND_INVALID")
    workspace=pathlib.Path(a.workspace).resolve()
    checked=verify_pins(workspace,plan.get("pinned_files"))
    v22_admission=verify_v22_prewrite(workspace,plan,checked)
    repo=os.environ.get("GITHUB_REPOSITORY",""); token=os.environ.get("GITHUB_TOKEN",""); run=os.environ.get("GITHUB_RUN_ID",""); job=os.environ.get("GITHUB_JOB",""); sha=os.environ.get("GITHUB_SHA","")
    if not all((repo,token,run,job)) or len(sha)!=40: raise RuntimeError("GITHUB_ACTIONS_IDENTITY_REQUIRED")
    req=request_factory(token); st,commit,_=req("GET",f"/repos/{repo}/git/commits/{sha}")
    tree=(commit.get("tree") or {}).get("sha") if st==200 and isinstance(commit,dict) else None
    if not isinstance(tree,str) or len(tree)!=40: raise RuntimeError("GITHUB_BASE_TREE_UNCONFIRMED")
    store=GitHubRefStore(req,repo,sha,tree,"live-v1")
    run_ref=f"{os.environ.get('GITHUB_SERVER_URL','https://github.com')}/{repo}/actions/runs/{run}"
    admission=admit_current_run_once(store,spec,f"{job}:{run}:{os.environ.get('GITHUB_RUN_ATTEMPT','1')}",run_ref)
    env=os.environ.copy()
    for k in list(env):
        if k in {"GITHUB_TOKEN","GH_TOKEN"} or (k.startswith("GITHUB") and k.endswith("_TOKEN")): env.pop(k,None)
    receipt={"schema":"BRAIN_GUARDED_LAUNCH_LOCAL_RECEIPT_V1","admission":admission,"v22_prewrite_admission":v22_admission,"checked_files":checked,"command":command,"child_started":False,"child_returncode":None}
    rp=pathlib.Path(a.receipt); rp.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    p=subprocess.run(command,cwd=pathlib.Path(a.workspace),env=env); receipt.update(child_started=True,child_returncode=p.returncode); rp.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n"); return p.returncode
if __name__=="__main__": raise SystemExit(main())
