#!/usr/bin/env python3
import json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"canonical"/"runtime"
sys.path.insert(0,str(RUNTIME))
import verify_pending_cli_binding as verifier

artifact=pathlib.Path(sys.argv[1]).resolve()
if not artifact.is_file():
    raise SystemExit("PRIOR_VERIFIED_ARTIFACT_MISSING")

pending={
  "selected_supplier":{"name":"iec16022"},
  "goal":"Generate a Data Matrix barcode image for the text PROJECT BRAIN V4.",
  "semantic_verification":{
    "required":True,
    "expected_text":"PROJECT BRAIN V4",
    "goal":"Generate a Data Matrix barcode image for the text PROJECT BRAIN V4.",
    "status":"PENDING_VERIFIER_ACQUISITION"
  }
}
if "verifier_package_hints" in pending["semantic_verification"]:
    raise SystemExit("VERIFIER_HINT_PRESENT")

evidence=verifier._acquire_and_run_semantic_verifier(pending,artifact)
if evidence.get("verified") is not True:
    raise SystemExit("AUTONOMOUS_VERIFIER_DISCOVERY_NOT_VERIFIED")
if evidence.get("producer_independent") is not True:
    raise SystemExit("VERIFIER_NOT_PRODUCER_INDEPENDENT")
if evidence.get("observed_text")!="PROJECT BRAIN V4":
    raise SystemExit("SEMANTIC_PAYLOAD_MISMATCH")
queries=evidence.get("autonomous_discovery_queries") or []
if not queries:
    raise SystemExit("AUTONOMOUS_DISCOVERY_QUERY_EVIDENCE_MISSING")
out={
  "schema":"PROJECT_BRAIN_AUTONOMOUS_VERIFIER_DISCOVERY_ADJUDICATION_V1",
  "capability":"AUTONOMOUS_INDEPENDENT_VERIFIER_DISCOVERY",
  "verified":True,
  "external_verifier_name_hint_used":False,
  "producer":"iec16022",
  "verifier_package":evidence.get("verifier_package"),
  "verifier_version":evidence.get("verifier_version"),
  "verifier_archive_sha256":evidence.get("verifier_archive_sha256"),
  "verifier_executable":evidence.get("verifier_executable"),
  "observed_text":evidence.get("observed_text"),
  "expected_text":evidence.get("expected_text"),
  "autonomous_discovery_queries":queries,
  "attempt_count":evidence.get("attempt_count"),
  "producer_independent":evidence.get("producer_independent"),
  "incremental_spend_usd":0
}
dst=ROOT/"canonical"/"astra_runtime"/"evidence"/"OBSOLESCENCE-TOOL-LEARNING-DATAMATRIX-001__AUTONOMOUS_VERIFIER_DISCOVERY.json"
dst.parent.mkdir(parents=True,exist_ok=True)
dst.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print("AUTONOMOUS_VERIFIER_DISCOVERY_VERIFIED",json.dumps(out,sort_keys=True))
