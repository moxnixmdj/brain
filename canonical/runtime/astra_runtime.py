#!/usr/bin/env python3
import argparse, gzip, hashlib, json, os, pathlib, shlex, subprocess, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parents[2]
STATE_DIR=ROOT/"canonical"/"astra_runtime"/"state"
EVID_DIR=ROOT/"canonical"/"astra_runtime"/"evidence"

def utc(): return datetime.now(timezone.utc).isoformat()
def writej(p,x):
    p=pathlib.Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def readj(p): return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))

def context_results(state):
    latest={}
    for rec in state.get("history",[]):
        if rec.get("ok"):
            latest[rec["step_index"]]=rec["result"]
    for batch in state.get("rehydrations",[]):
        for rec in batch.get("steps",[]):
            if rec.get("ok"):
                latest[rec["step_index"]]=rec["result"]
    return [latest[i] for i in sorted(latest)]

def sha_file(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

class Blocker(RuntimeError):
    pass

def run_shell(step, prior_results=None):
    cmd=step["command"]
    env=os.environ.copy()
    for i, result in enumerate(prior_results or []):
        prefix=f"ASTRA_STEP_{i}_"
        env[prefix+"RESULT_JSON"]=json.dumps(result, sort_keys=True)
        if "body_excerpt" in result:
            env[prefix+"BODY"]=result["body_excerpt"]
        if "stdout" in result:
            env[prefix+"STDOUT"]=result["stdout"]
    t=time.monotonic()
    p=subprocess.run(cmd,shell=True,executable="/bin/bash",cwd=ROOT,text=True,capture_output=True,env=env)
    return {
      "adapter":"shell","command":cmd,"returncode":p.returncode,
      "stdout":p.stdout[-12000:],"stderr":p.stderr[-12000:],
      "duration_s":round(time.monotonic()-t,3)
    }

def run_http(step):
    req=urllib.request.Request(step["url"],headers={"User-Agent":"ProjectBrain-ASTRA_RUNTIME/1"})
    t=time.monotonic()
    with urllib.request.urlopen(req,timeout=step.get("timeout_s",20)) as r:
        raw=r.read(step.get("max_bytes",200000))
        body=gzip.decompress(raw) if r.headers.get("Content-Encoding","").lower()=="gzip" else raw
        return {
          "adapter":"http","url":r.geturl(),"status":r.status,
          "body_sha256":hashlib.sha256(body).hexdigest(),
          "body_excerpt":body[:12000].decode("utf-8","replace"),
          "duration_s":round(time.monotonic()-t,3)
        }

def _safe_repo_path(raw):
    p=(ROOT/str(raw or "")).resolve()
    if p != ROOT.resolve() and ROOT.resolve() not in p.parents:
        raise Blocker("PATH_OUTSIDE_REPOSITORY")
    return p

def _goal_action(action):
    typ=action.get("type")
    args=action.get("args") or {}
    if typ=="list_tree":
        base=_safe_repo_path(args.get("prefix",""))
        if not base.exists(): return {"type":typ,"error":"PATH_NOT_FOUND","path":str(args.get("prefix",""))}
        items=[]
        if base.is_file():
            items=[str(base.relative_to(ROOT))]
        else:
            for p in sorted(base.rglob("*")):
                if p.is_file():
                    items.append(str(p.relative_to(ROOT)))
                    if len(items)>=80: break
        return {"type":typ,"items":items,"truncated":len(items)>=80}
    if typ=="read_file":
        p=_safe_repo_path(args.get("path",""))
        if not p.is_file(): return {"type":typ,"error":"FILE_NOT_FOUND","path":str(args.get("path",""))}
        text=p.read_text(encoding="utf-8",errors="replace")
        return {"type":typ,"path":str(p.relative_to(ROOT)),"content":text[:6000],"truncated":len(text)>6000}
    if typ=="search_text":
        q=str(args.get("query",""))
        if not q: return {"type":typ,"error":"EMPTY_QUERY"}
        hits=[]
        for p in sorted((ROOT/"canonical").rglob("*")):
            if not p.is_file() or p.suffix.lower() not in {".json",".md",".py",".txt",".yml",".yaml"}: continue
            try: text=p.read_text(encoding="utf-8",errors="replace")
            except Exception: continue
            if q.lower() in text.lower():
                hits.append(str(p.relative_to(ROOT)))
                if len(hits)>=80: break
        return {"type":typ,"query":q,"hits":hits,"truncated":len(hits)>=80}
    if typ=="http_get":
        url=str(args.get("url",""))
        if not url.startswith(("https://","http://")): return {"type":typ,"error":"UNSUPPORTED_URL"}
        return run_http({"url":url,"timeout_s":20,"max_bytes":60000})
    if typ=="finish":
        return {"type":typ,"summary":str(args.get("summary",""))[:12000]}
    raise Blocker("GOAL_ACTION_NOT_ALLOWED:"+str(typ))

def _extract_json_object(text):
    text=str(text).strip()
    try: return json.loads(text)
    except Exception: pass
    a=text.find("{"); b=text.rfind("}")
    if a<0 or b<a: raise Blocker("PLANNER_NO_JSON")
    return json.loads(text[a:b+1])

def _planner_post(prompt, timeout_s=20):
    endpoint="https://text.pollinations.ai/"
    models=("openai-fast","openai","mistral")
    errors=[]
    for model in models:
        body=json.dumps({
          "messages":[{"role":"user","content":prompt}],
          "model":model,
          "jsonMode":True
        }).encode("utf-8")
        req=urllib.request.Request(
          endpoint,
          data=body,
          headers={"Content-Type":"application/json","User-Agent":"ProjectBrain/1.0"},
          method="POST"
        )
        t=time.monotonic()
        try:
            with urllib.request.urlopen(req,timeout=timeout_s) as r:
                raw=r.read(30000).decode("utf-8","replace")
            return {"text":raw,"model":model,"duration_s":round(time.monotonic()-t,3),"errors":errors}
        except Exception as e:
            errors.append({"model":model,"error":type(e).__name__+":"+str(e),"duration_s":round(time.monotonic()-t,3)})
    raise Blocker("PLANNER_ALL_ROUTES_FAILED:"+json.dumps(errors,sort_keys=True)[:1800])

def run_goal(step, mission):
    goal=mission.get(step.get("goal_ref","goal"), mission.get("goal"))
    if isinstance(goal,(dict,list)): goal=json.dumps(goal,sort_keys=True)
    goal=str(goal or "").strip()
    if not goal: raise Blocker("GOAL_REQUIRED")
    observations=[]
    trace=[]
    max_cycles=max(1,min(int(step.get("max_cycles",6)),8))
    allowed="read_file(path), list_tree(prefix), search_text(query), http_get(url), finish(summary)"
    for cycle in range(max_cycles):
        compact=[]
        for item in observations[-6:]:
            a=item.get("action",{})
            r=item.get("result",{})
            rr=dict(r) if isinstance(r,dict) else {"value":str(r)}
            if isinstance(rr.get("items"),list):
                rr["items"]=rr["items"][:40]
            if isinstance(rr.get("hits"),list):
                rr["hits"]=rr["hits"][:30]
            if isinstance(rr.get("content"),str):
                rr["content"]=rr["content"][:2500]
            if isinstance(rr.get("body_excerpt"),str):
                rr["body_excerpt"]=rr["body_excerpt"][:2500]
            compact.append({"action":a,"result":rr})
        obs=json.dumps(compact,sort_keys=True)[:5000]
        prompt=(
          "You are an OPTIONAL planning source, not the controller. "
          "DO NOT invoke tools or function calls. DO NOT return tool_calls. Emit JSON text only. "
          "Goal: "+goal+"\nAllowed action types: "+allowed+". "
          "Choose the smallest next evidence action only. No writes, no shell, no secrets. "
          "If evidence is sufficient, use finish. Return exactly this schema: "
          '{"actions":[{"type":"...","args":{},"why":"..."}],"stop_after_evidence":true}. '
          "Observations so far: "+obs
        )
        planned=_planner_post(prompt, timeout_s=20)
        obj=_extract_json_object(planned.get("text",""))
        action=obj.get("action")
        if not isinstance(action,dict):
            actions=obj.get("actions")
            if isinstance(actions,list) and actions and isinstance(actions[0],dict):
                action=actions[0]
        if not isinstance(action,dict) and isinstance(obj.get("next_action"),dict):
            action=obj["next_action"]
        if not isinstance(action,dict):
            tc=obj.get("tool_calls")
            if isinstance(tc,list) and tc and isinstance(tc[0],dict):
                call=tc[0]
                fn=call.get("function") if isinstance(call.get("function"),dict) else call
                name=fn.get("name")
                raw_args=fn.get("arguments",{})
                if isinstance(raw_args,str):
                    try: raw_args=json.loads(raw_args)
                    except Exception: raw_args={}
                if isinstance(name,str) and isinstance(raw_args,dict):
                    action={"type":name,"args":raw_args,"why":str(obj.get("reasoning","tool_call"))}
        if not isinstance(action,dict) and isinstance(obj.get("type"),str):
            action=obj
        if not isinstance(action,dict) and isinstance(obj.get("reasoning"),str) and obj["reasoning"].strip():
            normalize_prompt=(
              "Convert this planner intent into ONE allowed action. Return JSON text only, no reasoning, no tool_calls. "
              "Allowed action types: "+allowed+". Schema exactly: "
              '{"actions":[{"type":"...","args":{},"why":"normalized planner intent"}]}. '
              "Planner intent: "+obj["reasoning"][:5000]
            )
            normalized=_planner_post(normalize_prompt, timeout_s=20)
            nobj=_extract_json_object(normalized.get("text",""))
            na=nobj.get("action")
            if not isinstance(na,dict):
                nas=nobj.get("actions")
                if isinstance(nas,list) and nas and isinstance(nas[0],dict):
                    na=nas[0]
            if isinstance(na,dict):
                action=na
        if not isinstance(action,dict):
            diag=json.dumps(obj,sort_keys=True)[:2200].replace("\n"," ")
            raise Blocker("PLANNER_ACTION_MISSING_OBJECT:"+diag)
        typ=action.get("type")
        # Some optional planner providers return a free-form `commentary`
        # pseudo-action even when instructed to emit one typed action. Treat
        # that as untrusted intent and normalize it through the same bounded
        # second-pass path already used for free-form reasoning. The runtime
        # still executes only its existing allowlisted action types.
        if typ=="commentary":
            args=action.get("args") if isinstance(action.get("args"),dict) else {}
            intent=""
            for key in ("text","content","message","commentary","value"):
                if isinstance(args.get(key),str) and args[key].strip():
                    intent=args[key].strip(); break
            if not intent and isinstance(action.get("why"),str):
                intent=action["why"].strip()
            if not intent:
                intent=json.dumps(action,sort_keys=True)[:5000]
            normalize_prompt=(
              "Convert this planner commentary into ONE allowed action. Return JSON text only, no reasoning, no tool_calls. "
              "Allowed action types: "+allowed+". Schema exactly: "
              '{"actions":[{"type":"...","args":{},"why":"normalized planner commentary"}]}. '
              "Planner commentary: "+intent[:5000]
            )
            normalized=_planner_post(normalize_prompt, timeout_s=20)
            nobj=_extract_json_object(normalized.get("text",""))
            na=nobj.get("action")
            if not isinstance(na,dict):
                nas=nobj.get("actions")
                if isinstance(nas,list) and nas and isinstance(nas[0],dict):
                    na=nas[0]
            if not isinstance(na,dict):
                raise Blocker("PLANNER_COMMENTARY_NORMALIZATION_FAILED")
            action=na
            typ=action.get("type")
        allowed_types={"read_file","list_tree","search_text","http_get","finish"}
        if isinstance(typ,str) and "." in typ:
            suffix=typ.rsplit(".",1)[-1]
            if suffix in allowed_types:
                typ=suffix
                action=dict(action)
                action["type"]=suffix
        if typ not in allowed_types:
            raise Blocker("PLANNER_ACTION_REJECTED:"+str(typ))
        if not isinstance(action.get("args"),dict): raise Blocker("PLANNER_ARGS_INVALID")
        result=_goal_action(action)
        trace.append({"cycle":cycle,"plan":action,"result":result})
        if typ=="finish":
            summary=result.get("summary","")
            if not summary.strip(): raise Blocker("PLANNER_EMPTY_FINISH")
            return {
              "adapter":"goal","returncode":0,
              "stdout":summary,
              "planner_source":"https://text.pollinations.ai/",
              "planner_transport":"POST_BOUNDED_FAILOVER",
              "planner_model_last":planned.get("model"),
              "cycles":cycle+1,"trace":trace,
              "final_summary":summary
            }
        observations.append({"action":action,"result":result})
    raise Blocker("GOAL_MAX_CYCLES_WITHOUT_FINISH")

def execute_step(step, prior_results=None, mission=None):
    adapter=step["adapter"]
    if adapter=="shell":
        return run_shell(step, prior_results)
    if adapter=="http":
        return run_http(step)
    if adapter=="goal":
        return run_goal(step, mission or {})
    raise Blocker("MISSING_ADAPTER:"+adapter)

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
    # A durable checkpoint can outlive its executor, while filesystem/process
    # effects often cannot. Rehydrate explicitly marked prior steps before
    # resuming the first unfinished causal step on a fresh invocation.
    if state["next_step"] > 0:
        rehydrated=[]
        for j, prior in enumerate(mission["steps"][:state["next_step"]]):
            if not prior.get("replay_on_resume", False):
                continue
            try:
                result=execute_step(prior, context_results(state), mission)
                ok=verify(prior,result)
            except Exception as e:
                blocker={
                  "schema":"PROJECT_BRAIN_ASTRA_RUNTIME_BLOCKER_V1",
                  "mission_id":mid,"step_index":j,"step_id":prior["id"],
                  "adapter":prior["adapter"],
                  "phase":"REHYDRATION",
                  "error":type(e).__name__+":"+str(e),
                  "observed_at_utc":utc()
                }
                writej(EVID_DIR/f"{mid}__BLOCKER.json",blocker)
                state["status"]="BLOCKED"; state["blocker"]=blocker; state["updated_at_utc"]=utc()
                writej(state_path,state)
                print(json.dumps(blocker)); return 3
            rec={"step_index":j,"step_id":prior["id"],"ok":bool(ok),"result":result,
                 "rehydration":True,"completed_at_utc":utc()}
            rehydrated.append(rec)
            if not ok:
                blocker={
                  "schema":"PROJECT_BRAIN_ASTRA_RUNTIME_BLOCKER_V1",
                  "mission_id":mid,"step_index":j,"step_id":prior["id"],
                  "adapter":prior["adapter"],"phase":"REHYDRATION",
                  "error":"VERIFICATION_FAILED","result":result,"observed_at_utc":utc()
                }
                writej(EVID_DIR/f"{mid}__BLOCKER.json",blocker)
                state["status"]="BLOCKED"; state["blocker"]=blocker; state["updated_at_utc"]=utc()
                writej(state_path,state)
                print(json.dumps(blocker)); return 4
        if rehydrated:
            state.setdefault("rehydrations",[]).append({
              "at_utc":utc(),"before_step":state["next_step"],"steps":rehydrated
            })
            state["updated_at_utc"]=utc()
            writej(state_path,state)

    for i in range(state["next_step"],len(mission["steps"])):
        step=mission["steps"][i]
        adapter=step["adapter"]
        try:
            result=execute_step(step, context_results(state), mission)
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
