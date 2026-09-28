#!/usr/bin/env python3
import json, pathlib, sys, traceback

ROOT=pathlib.Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"canonical"/"runtime"
sys.path.insert(0,str(RUNTIME))
import capability_discovery
import auto_capability_acquisition

MISSION_REL="canonical/experiments/OBSOLESCENCE_TOOL_LEARNING_DATAMATRIX_001.json"
MISSION_ID="OBSOLESCENCE-TOOL-LEARNING-DATAMATRIX-001"
GOAL="Generate a Data Matrix barcode image for the text PROJECT BRAIN V4 and save it as canonical/astra_runtime/tmp/PROJECT_BRAIN_DATAMATRIX.png."
EVID=ROOT/"canonical"/"astra_runtime"/"evidence"
EVID.mkdir(parents=True,exist_ok=True)

registry=json.loads((RUNTIME/"BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
blob=json.dumps(registry).lower()
if "datamatrix" in blob or "data matrix" in blob:
    raise SystemExit("PREBOUND_DATAMATRIX_CAPABILITY_PRESENT")

discovery=capability_discovery.search_all(GOAL,limit_per_source=24)
(EVID/(MISSION_ID+"__DISCOVERY.json")).write_text(json.dumps(discovery,indent=2,sort_keys=True)+"\n")
print("DISCOVERY_CANDIDATES",[(x.get("discovery_source"),x.get("name"),x.get("score")) for x in discovery.get("candidates",[])[:12]])

try:
    out=auto_capability_acquisition.dispatch(GOAL,MISSION_ID,MISSION_REL,ROOT,discovery=discovery)
except Exception as exc:
    failure={
      "status":"DISPATCH_FAILED",
      "error":type(exc).__name__+":"+str(exc),
      "traceback":traceback.format_exc()
    }
    (EVID/(MISSION_ID+"__RESULT.json")).write_text(json.dumps(failure,indent=2,sort_keys=True)+"\n")
    print("OBSERVED_BLOCKER",failure["error"])
    raise

pending=ROOT/out["pending_binding_path"]
data=json.loads(pending.read_text())
argv=[str(x) for x in ((data.get("contract") or {}).get("argv_template") or [])]
joined=" ".join(argv).lower().replace("-","").replace("_","").replace(" ","")
mode_bound=("datamatrix" in joined)
result={
  "status":"CONTRACT_INFERRED",
  "dispatch":out,
  "selected_supplier":data.get("selected_supplier"),
  "argv_template":argv,
  "requested_symbology":"Data Matrix",
  "requested_symbology_explicitly_bound":mode_bound,
  "promotion_allowed":False
}
(EVID/(MISSION_ID+"__RESULT.json")).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print("CONTRACT_RESULT",json.dumps(result,sort_keys=True))
if not mode_bound:
    raise SystemExit("REQUESTED_SYMBOLOGY_NOT_BOUND_IN_LEARNED_CONTRACT")
print("DATAMATRIX_CONTRACT_MODE_BOUND")
