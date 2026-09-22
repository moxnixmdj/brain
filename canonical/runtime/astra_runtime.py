#!/usr/bin/env python3
import argparse, hashlib, json, os, pathlib, shlex, subprocess, sys, time, urllib.request
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parents[2]
STATE_DIR=ROOT/"canonical"/"astra_runtime"/"state"
EVID_DIR=ROOT/"canonical"/"astra_runtime"/"evidence"

def utc(): return datetime.now(timezone.utc).isoformat()
def writej(p,x):
    p=pathlib.Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def readj(p): return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
def sha_file(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

class Blocker(RuntimeError):
    pass

def run_shell(step):
    cmd=step["command"]
    t=time.monotonic()
    p=subprocess.run(cmd,shell=True,cwd=ROOT,text=True,capture_output=True)
    return {
      "adapter":"shell","command":cmd,"returncode":p.returncode,
      "stdout":p.stdout[-12000:],"stderr":p.stderr[-12000:],
      "duration_s":round(time.monotonic()-t,3)
    }

def run_http(step):
    req=urllib.request.Request(step["url"],headers={"User-Agent":"ProjectBrain-ASTRA_RUNTIME/1"})
    t=time.monotonic()
    with urllib.request.urlopen(req,timeout=step.get("timeout_s",20)) as r:
        body=r.read(step.get("max_bytes",200000))
        return {
          "adapter":"http","url":r.geturl(),"status":r.status,
          "body_sha256":hashlib.sha256(body).hexdigest(),
          "body_excerpt":body[:12000].decode("utf-8","replace"),
          "duration_s":round(time.monotonic()-t,3)
        }

def verify(step,result):
    v=step.get("verify",{})
    typ=v.get("type","returncode_zero")
    if typ=="returncode_zero":
        return result.get("returncode")==0
    if typ=="stdout_contains":
        return v["text"] in result.get("stdout","")
    if typ=="file_exists":
        return (ROOT/v["path"]).exists()
    if typ=="json_field_equals":
        x=readj(ROOT/v["path"])
        cur=x
        for k in v["field"].split("."): cur=cur[k]
        return cur==v["value"]
    if typ=="http_status":
        return result.get("status")==v["value"]
    raise Blocker("UNKNOWN_VERIFIER:"+typ)

def main():
    STATE_DIR.mkdir(parents=True,exist_ok=True)
    EVID_DIR.mkdir(parents=True,exist_ok=True)
    ap=argparse.ArgumentParser()
    ap.add_argument("mission")
    a=ap.parse_args()
    mission_path=(ROOT/a.mission).resolve()
    if ROOT.resolve() not in mission_path.parents:
        raise Blocker("MISSION_PATH_OUTSIDE_ROOT")
    mission=readj(mission_path)
    mid=mission["mission_id"]
    mission_sha256=sha_file(mission_path)
    state_path=STATE_DIR/f"{mid}.json"
    state=readj(state_path) if state_path.exists() else {
      "schema":"PROJECT_BRAIN_ASTRA_RUNTIME_STATE_V1",
      "mission_id":mid,"mission_path":a.mission,"mission_sha256":mission_sha256,
      "runtime_id":"ASTRA_RUNTIME_V1_SHARED",
      "status":"RUNNING","next_step":0,"history":[],"created_at_utc":utc()
    }
    if state.get("mission_id") != mid:
        raise Blocker("STATE_MISSION_ID_MISMATCH")
    if state.get("mission_path", a.mission) != a.mission:
        raise Blocker("STATE_MISSION_PATH_MISMATCH")
    state["mission_path"]=a.mission
    state["mission_sha256"]=mission_sha256
    for i in range(state["next_step"],len(mission["steps"])):
        step=mission["steps"][i]
        adapter=step["adapter"]
        try:
            if adapter=="shell": result=run_shell(step)
            elif adapter=="http": result=run_http(step)
            else: raise Blocker("MISSING_ADAPTER:"+adapter)
            ok=verify(step,result)
        except Exception as e:
            blocker={
              "schema":"PROJECT_BRAIN_ASTRA_RUNTIME_BLOCKER_V1",
              "mission_id":mid,"step_index":i,"step_id":step["id"],
              "adapter":adapter,"error":type(e).__name__+":"+str(e),
              "observed_at_utc":utc()
            }
            writej(EVID_DIR/f"{mid}__BLOCKER.json",blocker)
            state["status"]="BLOCKED"; state["blocker"]=blocker; state["updated_at_utc"]=utc()
            writej(state_path,state)
            print(json.dumps(blocker)); return 3
        rec={"step_index":i,"step_id":step["id"],"ok":bool(ok),"result":result,"completed_at_utc":utc()}
        state["history"].append(rec)
        if not ok:
            blocker={
              "schema":"PROJECT_BRAIN_ASTRA_RUNTIME_BLOCKER_V1",
              "mission_id":mid,"step_index":i,"step_id":step["id"],
              "adapter":adapter,"error":"VERIFICATION_FAILED",
              "result":result,"observed_at_utc":utc()
            }
            writej(EVID_DIR/f"{mid}__BLOCKER.json",blocker)
            state["status"]="BLOCKED"; state["blocker"]=blocker; state["updated_at_utc"]=utc()
            writej(state_path,state)
            print(json.dumps(blocker)); return 4
        state["next_step"]=i+1; state["updated_at_utc"]=utc()
        writej(state_path,state)
    state["status"]="COMPLETE"; state["completed_at_utc"]=utc()
    writej(state_path,state)
    receipt={
      "schema":"PROJECT_BRAIN_ASTRA_RUNTIME_RECEIPT_V1",
      "mission_id":mid,"mission_path":a.mission,"mission_sha256":mission_sha256,
      "runtime_id":"ASTRA_RUNTIME_V1_SHARED",
      "status":"COMPLETE","steps_completed":len(state["history"]),
      "state_sha256":sha_file(state_path),"completed_at_utc":utc()
    }
    writej(EVID_DIR/f"{mid}__RECEIPT.json",receipt)
    print(json.dumps(receipt)); return 0

if __name__=="__main__":
    raise SystemExit(main())
