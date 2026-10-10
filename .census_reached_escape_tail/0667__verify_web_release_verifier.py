#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[2]
RESULT=ROOT/"canonical/astra_runtime/evidence/ASTRA-WEB-RELEASE-VERIFIER-VERIFY-001__RESULT.json"
BROWSER_EVIDENCE=ROOT/"canonical/astra_runtime/evidence/ASTRA-BROWSER-PYTHON-RELEASE-VERIFY-001__RESULT.json"


def load_adapter():
    p=ROOT/"canonical/runtime/bound_capabilities/web_release_verify.py"
    s=importlib.util.spec_from_file_location("web_release_verify_under_test",p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def main():
    observed=load_adapter().run({
      "result_path":"canonical/astra_runtime/tmp/PYTHON_DOWNLOADS_RESULT.json",
      "version_field":"latest_stable_python3",
      "product":"Python",
      "major":"3",
      "timeout_s":30,
      "max_bytes":3000000,
    },ROOT)
    if observed.get("verified") is not True:
        raise RuntimeError("WEB_RELEASE_VERIFIER_EFFECT_NOT_VERIFIED")
    reference=json.loads(BROWSER_EVIDENCE.read_text(encoding="utf-8"))
    reference_version=str(reference.get("independent_latest_stable_python3") or "")
    if reference.get("verified") is not True or not reference_version:
        raise RuntimeError("REFERENCE_BROWSER_VERIFICATION_INVALID")
    if observed.get("observed_version")!=reference_version:
        raise RuntimeError("INDEPENDENT_REFERENCE_MISMATCH")
    evidence={
      "schema":"PROJECT_BRAIN_WEB_RELEASE_VERIFIER_VERIFICATION_V1",
      "status":"VERIFIED",
      "verified":True,
      "verification_mission_id":"ASTRA-WEB-RELEASE-VERIFIER-VERIFY-001",
      "observed_effect":observed,
      "independent_reference_evidence":"canonical/astra_runtime/evidence/ASTRA-BROWSER-PYTHON-RELEASE-VERIFY-001__RESULT.json",
      "independent_reference_version":reference_version,
      "producer_independent_of_rendered_browser":True,
    }
    RESULT.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("WEB_RELEASE_VERIFIER_EFFECT_VERIFIED "+json.dumps(evidence,sort_keys=True))

if __name__=="__main__":
    main()
