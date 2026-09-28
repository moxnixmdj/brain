#!/usr/bin/env python3
import json, pathlib, sys, traceback

ROOT=pathlib.Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"canonical"/"runtime"
sys.path.insert(0,str(RUNTIME))
import capability_discovery
import auto_capability_acquisition
import verify_pending_cli_binding

_test_contract={
  "executable":"/usr/bin/generic-reader",
  "argv":["/usr/bin/generic-reader","__OUTPUT_PATH__"],
  "inference_basis":"POSITIONAL_FILE_TO_STDOUT",
  "help_excerpt":"  -e, --minimum-edge=N        smallest expected edge\n",
}
_test_variants=verify_pending_cli_binding._semantic_execution_variants(
    _test_contract,"canonical/astra_runtime/tmp/example.png"
)
assert _test_variants[0]["basis"]=="PRIMARY_CONTRACT"
assert _test_variants[1]["basis"]=="HELP_DECLARED_MINIMUM_NUMERIC_RELAXATION"
assert _test_variants[1]["argv"]==[
    "/usr/bin/generic-reader","-e","1","canonical/astra_runtime/tmp/example.png"
]

MISSION_REL="canonical/astra_runtime/missions/OBSOLESCENCE_TOOL_LEARNING_DATAMATRIX_001.json"
MISSION_ID="OBSOLESCENCE-TOOL-LEARNING-DATAMATRIX-001"
GOAL="Generate a Data Matrix barcode image for the text PROJECT BRAIN V4 and save it as canonical/astra_runtime/tmp/PROJECT_BRAIN_DATAMATRIX.png."
EVID=ROOT/"canonical"/"astra_runtime"/"evidence"
EVID.mkdir(parents=True,exist_ok=True)

SOURCE_MISSION=ROOT/"canonical"/"experiments"/"OBSOLESCENCE_TOOL_LEARNING_DATAMATRIX_001.json"
RUNTIME_MISSION=ROOT/MISSION_REL
if SOURCE_MISSION.read_bytes()!=RUNTIME_MISSION.read_bytes():
    raise SystemExit("FROZEN_MISSION_BYTES_DIVERGED")

registry=json.loads((RUNTIME/"BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
caps=registry.get("capabilities") or {}
inherited=caps.get("auto.apt.iec16022")
if inherited is not None:
    source=(inherited.get("source") or {})
    packages=source.get("packages") or []
    exact_inheritance=(
        inherited.get("status")=="VERIFIED_BOUND_CAPABILITY"
        and source.get("type")=="apt"
        and any(
            p.get("name")=="iec16022" and p.get("version")=="0.2.7-1"
            for p in packages if isinstance(p,dict)
        )
        and (inherited.get("verification") or {}).get("independent_verified") is True
    )
    if not exact_inheritance:
        raise SystemExit("PREBOUND_DATAMATRIX_CAPABILITY_CONFLICT")
    print("VERIFIED_INHERITED_CAPABILITY_PRESENT auto.apt.iec16022")
other_caps={k:v for k,v in caps.items() if k!="auto.apt.iec16022"}
other_blob=json.dumps(other_caps).lower()
if "datamatrix" in other_blob or "data matrix" in other_blob:
    raise SystemExit("UNRELATED_PREBOUND_DATAMATRIX_CAPABILITY_PRESENT")

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
semantic=data.get("semantic_verification") or {}
semantic.pop("verifier_package_hints",None)
data["semantic_verification"]=semantic
pending.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
contract=data.get("contract") or {}
argv=[str(x) for x in (contract.get("argv_template") or [])]
joined=" ".join(argv).lower().replace("-","").replace("_","").replace(" ","")
selected_executable=str(contract.get("executable") or "")
selected_help=""
for exe in (data.get("probe") or {}).get("executables",[]) or []:
    if str(exe.get("executable") or "")!=selected_executable:
        continue
    selected_help="\n".join(str(att.get("text") or "") for att in (exe.get("help_attempts") or []))
explicit_selector=("datamatrix" in joined)
intrinsic_tool_semantics=("data matrix" in selected_help.lower() or "iso/iec 16022" in selected_help.lower())
supplier_description=str((data.get("selected_supplier") or {}).get("description") or "")
discovery_semantics=("data matrix" in supplier_description.lower() or "iso/iec 16022" in supplier_description.lower())
mode_bound=explicit_selector or intrinsic_tool_semantics or discovery_semantics
binding_basis=(
    "EXPLICIT_ARGV_SELECTOR" if explicit_selector
    else (
      "SELECTED_EXECUTABLE_HELP_DECLARATION" if intrinsic_tool_semantics
      else ("DISCOVERY_SUPPLIER_SEMANTIC_DECLARATION" if discovery_semantics else None)
    )
)
result={
  "status":"CONTRACT_INFERRED",
  "dispatch":out,
  "selected_supplier":data.get("selected_supplier"),
  "argv_template":argv,
  "requested_symbology":"Data Matrix",
  "requested_symbology_explicitly_bound":mode_bound,
  "semantic_binding_basis":binding_basis,
  "selected_executable":selected_executable,
  "selected_help_declares_data_matrix":intrinsic_tool_semantics,
  "supplier_description":supplier_description,
  "discovery_description_declares_data_matrix":discovery_semantics,
  "verification_mission_path":out["verification_mission_path"],
  "promotion_allowed":False
}
(EVID/(MISSION_ID+"__RESULT.json")).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
import subprocess

diag=[]
output_path=ROOT/"canonical"/"astra_runtime"/"tmp"/"PROJECT_BRAIN_DATAMATRIX.png"
for label,argv in [
    ("default",["dmtxread",str(output_path)]),
    ("edge1",["dmtxread","-e","1",str(output_path)]),
]:
    try:
        proc=subprocess.run(argv,text=True,capture_output=True,timeout=30,cwd=ROOT)
        diag.append({
          "label":label,
          "argv":argv,
          "returncode":proc.returncode,
          "stdout":proc.stdout,
          "stderr":proc.stderr,
        })
    except Exception as exc:
        diag.append({"label":label,"argv":argv,"error":type(exc).__name__+":"+str(exc)})
result["decoder_edge_diagnostic"]=diag
(EVID/(MISSION_ID+"__RESULT.json")).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print("CONTRACT_RESULT",json.dumps(result,sort_keys=True))
if not mode_bound:
    raise SystemExit("REQUESTED_SYMBOLOGY_NOT_BOUND_IN_LEARNED_CONTRACT")
print("DATAMATRIX_CONTRACT_MODE_BOUND")
