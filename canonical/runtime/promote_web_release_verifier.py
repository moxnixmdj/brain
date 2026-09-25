#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parents[2]
REG=ROOT/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

def main():
    if len(sys.argv)!=2:
        raise SystemExit("usage: promote_web_release_verifier.py <verification.json>")
    ep=(ROOT/sys.argv[1]).resolve()
    if ROOT.resolve() not in ep.parents:
        raise RuntimeError("EVIDENCE_OUTSIDE_REPOSITORY")
    ev=json.loads(ep.read_text(encoding="utf-8"))
    if ev.get("schema")!="PROJECT_BRAIN_WEB_RELEASE_VERIFIER_VERIFICATION_V1":
        raise RuntimeError("WEB_RELEASE_VERIFIER_SCHEMA_INVALID")
    if ev.get("verified") is not True or ev.get("status")!="VERIFIED":
        raise RuntimeError("WEB_RELEASE_VERIFIER_NOT_VERIFIED")
    if ev.get("producer_independent_of_rendered_browser") is not True:
        raise RuntimeError("WEB_RELEASE_VERIFIER_INDEPENDENCE_MISSING")
    data=json.loads(REG.read_text(encoding="utf-8"))
    cid="web.release.verify.independent_http"
    data["capabilities"][cid]={
      "provides":["web.release.verify.current"],
      "requires":["structured.release_claim.available"],
      "keywords":["web","release","version","latest","stable","verify","independent","official","http"],
      "cost":1,
      "platforms":["linux","windows","darwin"],
      "limitations":[
        "Verifies semantic versions exposed in an official HTTPS page's visible text.",
        "Current verified contract targets major.minor.patch release strings and compares against a claimed field in repository-local JSON."
      ],
      "adapter_module":"web_release_verify",
      "entrypoint":"run",
      "action_template":{
        "type":"invoke_capability",
        "args":{
          "capability_id":cid,
          "result_path":"${input.result_path}",
          "version_field":"${input.version_field}",
          "product":"${input.product}",
          "major":"${input.major}",
          "timeout_s":30,
          "max_bytes":3000000
        },
        "expect":{"type":"field_equals","field":"verified","value":True}
      },
      "source":{"type":"python_stdlib","modules":["urllib.request","html.parser","gzip"]},
      "incremental_spend_usd":0,
      "status":"VERIFIED_BOUND_CAPABILITY",
      "verification":{
        "mission_id":"ASTRA-WEB-RELEASE-VERIFIER-VERIFY-001",
        "verification_result_path":str(ep.relative_to(ROOT)),
        "independent_reference_evidence":ev.get("independent_reference_evidence"),
        "observed_effect":ev.get("observed_effect")
      }
    }
    REG.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("WEB_RELEASE_VERIFIER_CAPABILITY_PROMOTED")

if __name__=="__main__":
    main()
