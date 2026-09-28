#!/usr/bin/env python3
"""Run one frozen orthogonal tool-learning probe without changing runtime code."""
from __future__ import annotations
import gzip, json, pathlib, sqlite3, subprocess, sys, time, traceback
import xml.etree.ElementTree as ET

ROOT=pathlib.Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"canonical"/"runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0,str(RUNTIME))

import capability_discovery
import auto_capability_acquisition

PROBES={
  "ORTHO-GZIP-001":"canonical/astra_runtime/missions/ORTHO_GZIP_001.json",
  "ORTHO-SQLITE-001":"canonical/astra_runtime/missions/ORTHO_SQLITE_001.json",
  "ORTHO-XML-001":"canonical/astra_runtime/missions/ORTHO_XML_001.json",
}

def blocker_class(text):
    s=str(text or "")
    if "CLI_OUTPUT_FORMAT_UNVERIFIABLE" in s:
        return "GENERIC_CONTRACT_OUTPUT_FORMAT_COVERAGE"
    if "CLI_OUTPUT_FORMAT_UNSUPPORTED" in s:
        return "GENERIC_CONTRACT_OUTPUT_FORMAT_SEMANTICS"
    if "CLI_TEXT_INPUT_UNRESOLVED" in s or "CLI_OUTPUT_FLAG_UNRESOLVED" in s or "CLI_HELP_CONTRACT_TEXT_REQUIRED" in s:
        return "GENERIC_CONTRACT_INFERENCE_SHAPE"
    if "NO_COMPATIBLE_APT_CLI_CONTRACT" in s or "NO_COMPATIBLE_SUPPLIER_CONTRACT" in s:
        return "NO_COMPATIBLE_DISCOVERED_CONTRACT"
    if "SEMANTIC_VERIFIER_ACQUISITION_FAILED" in s:
        return "AUTONOMOUS_INDEPENDENT_VERIFIER_DISCOVERY_OR_EXECUTION"
    if "APT_INSTALL_FAILED" in s or "PROBE_FAILED" in s:
        return "SUPPLIER_PROBE_OR_ACQUISITION_FAILURE"
    if "NO_CANDIDATE" in s or "DISCOVERY" in s and "FAILED" in s:
        return "CAPABILITY_DISCOVERY_FAILURE"
    return "UNCLASSIFIED_FIRST_BLOCKER"

def acceptance(mission):
    acc=mission["acceptance"]
    path=ROOT/acc["output_path"]
    if not path.is_file():
        return False,"OUTPUT_MISSING"
    mid=mission["mission_id"]
    try:
        if mid=="ORTHO-GZIP-001":
            raw=gzip.open(path,"rb").read()
            want=acc["decompressed_utf8_exact"].encode()
            return raw==want,("GZIP_EXACT_PASS" if raw==want else "GZIP_CONTENT_MISMATCH")
        if mid=="ORTHO-SQLITE-001":
            con=sqlite3.connect(path)
            try:
                cols=[r[1:3] for r in con.execute("pragma table_info(probe)").fetchall()]
                rows=con.execute("select k,v from probe order by k").fetchall()
            finally:
                con.close()
            ok=(cols==[("k","TEXT"),("v","INTEGER")] and rows==[("alpha",7),("beta",11)])
            return ok,("SQLITE_SCHEMA_ROWS_PASS" if ok else f"SQLITE_MISMATCH:{cols}:{rows}")
        if mid=="ORTHO-XML-001":
            root=ET.parse(path).getroot()
            values={c.tag:(c.text or "") for c in list(root)}
            ok=(root.tag=="record" and values=={"name":"brain","value":"23"})
            return ok,("XML_SEMANTIC_PASS" if ok else f"XML_MISMATCH:{root.tag}:{values}")
    except Exception as exc:
        return False,type(exc).__name__+":"+str(exc)
    return False,"UNKNOWN_ACCEPTANCE"

def main():
    if len(sys.argv)!=2 or sys.argv[1] not in PROBES:
        raise SystemExit("usage: run_orthogonal_tool_learning_probe.py "+ "|".join(PROBES))
    probe_id=sys.argv[1]
    mission_rel=PROBES[probe_id]
    mission=json.loads((ROOT/mission_rel).read_text())
    goal=mission["goal"]
    evid=ROOT/"canonical"/"astra_runtime"/"evidence"
    evid.mkdir(parents=True,exist_ok=True)
    result_path=evid/f"{probe_id}__ORTHOGONAL_RESULT.json"
    discovery_path=evid/f"{probe_id}__DISCOVERY.json"

    result={
      "schema":"PROJECT_BRAIN_ORTHOGONAL_TOOL_LEARNING_RESULT_V1",
      "portfolio_id":"ORTHO-TOOL-LEARNING-PORTFOLIO-001",
      "probe_id":probe_id,
      "mission_path":mission_rel,
      "goal":goal,
      "runtime_changed_before_first_execution":False,
      "status":"RUNNING",
      "first_blocker_class":None,
      "first_blocker_detail":None,
      "stages":[],
    }
    t0=time.monotonic()

    try:
        t=time.monotonic()
        discovery=capability_discovery.search_all(goal,limit_per_source=20)
        discovery_path.write_text(json.dumps(discovery,indent=2,sort_keys=True)+"\n")
        result["stages"].append({
          "stage":"DISCOVERY",
          "status":"PASS",
          "wall_s":round(time.monotonic()-t,6),
          "candidate_count":len(discovery.get("candidates",[]) or []),
          "top_candidates":[
            {
              "name":x.get("name"),
              "source":x.get("discovery_source"),
              "score":x.get("score"),
              "binding_kind":x.get("binding_kind"),
            }
            for x in (discovery.get("candidates",[]) or [])[:12]
          ]
        })
    except Exception as exc:
        result["status"]="TERMINAL_FAIL"
        result["first_blocker_detail"]=type(exc).__name__+":"+str(exc)
        result["first_blocker_class"]=blocker_class(result["first_blocker_detail"])
        result["stages"].append({"stage":"DISCOVERY","status":"FAIL","error":result["first_blocker_detail"]})
        result["wall_s"]=round(time.monotonic()-t0,6)
        result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        print(json.dumps(result,sort_keys=True))
        return 0

    try:
        t=time.monotonic()
        dispatch=auto_capability_acquisition.dispatch(
          goal,probe_id,mission_rel,ROOT,discovery=discovery
        )
        result["dispatch"]=dispatch
        result["stages"].append({
          "stage":"DISCOVERY_SELECTION_CONTRACT_LEARNING",
          "status":"PASS",
          "wall_s":round(time.monotonic()-t,6),
          "supplier":dispatch.get("supplier"),
          "capability_id":dispatch.get("capability_id"),
        })
    except Exception as exc:
        detail=type(exc).__name__+":"+str(exc)
        result["status"]="TERMINAL_FAIL"
        result["first_blocker_detail"]=detail
        result["first_blocker_class"]=blocker_class(detail)
        result["stages"].append({
          "stage":"DISCOVERY_SELECTION_CONTRACT_LEARNING",
          "status":"FAIL",
          "error":detail,
          "traceback_tail":traceback.format_exc()[-6000:],
        })
        result["wall_s"]=round(time.monotonic()-t0,6)
        result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        print(json.dumps(result,sort_keys=True))
        return 0

    pending_rel=dispatch.get("pending_binding_path")
    if not pending_rel or not (ROOT/pending_rel).is_file():
        result["status"]="TERMINAL_FAIL"
        result["first_blocker_class"]="PENDING_VERIFICATION_ROUTE_MISSING"
        result["first_blocker_detail"]="dispatch returned no readable pending binding"
        result["stages"].append({"stage":"VERIFICATION_ROUTE","status":"FAIL","error":result["first_blocker_detail"]})
        result["wall_s"]=round(time.monotonic()-t0,6)
        result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        print(json.dumps(result,sort_keys=True))
        return 0

    pending=json.loads((ROOT/pending_rel).read_text())
    verify_rel=pending.get("verification_result_path") or f"canonical/astra_runtime/evidence/{probe_id}__PORTFOLIO_VERIFY.json"
    t=time.monotonic()
    proc=subprocess.run(
      [sys.executable,str(RUNTIME/"verify_pending_cli_binding.py"),pending_rel,verify_rel],
      cwd=ROOT,text=True,capture_output=True,timeout=180
    )
    result["stages"].append({
      "stage":"RUNTIME_INDEPENDENT_VERIFICATION",
      "status":"PASS" if proc.returncode==0 else "FAIL",
      "returncode":proc.returncode,
      "wall_s":round(time.monotonic()-t,6),
      "stdout_tail":proc.stdout[-5000:],
      "stderr_tail":proc.stderr[-5000:],
    })

    ok,detail=acceptance(mission)
    result["independent_portfolio_acceptance"]={"pass":ok,"detail":detail}
    if proc.returncode!=0:
        blob=(proc.stderr+"\n"+proc.stdout)
        result["status"]="TERMINAL_FAIL"
        result["first_blocker_class"]=blocker_class(blob)
        result["first_blocker_detail"]=blob[-7000:]
    elif not ok:
        result["status"]="TERMINAL_FAIL"
        result["first_blocker_class"]="REAL_EFFECT_MISMATCH_AFTER_RUNTIME_VERIFICATION"
        result["first_blocker_detail"]=detail
    else:
        result["status"]="PASS_FULL_LOOP_CANDIDATE"
        result["first_blocker_class"]=None
        result["first_blocker_detail"]=None

    result["wall_s"]=round(time.monotonic()-t0,6)
    result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
