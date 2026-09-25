#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parents[2]
REG=ROOT/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

def main():
    if len(sys.argv)!=2:
        raise SystemExit("usage: promote_browser_capability.py <verification.json>")
    evidence_path=(ROOT/sys.argv[1]).resolve()
    if ROOT.resolve() not in evidence_path.parents:
        raise RuntimeError("EVIDENCE_OUTSIDE_REPOSITORY")
    evidence=json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence.get("schema")!="PROJECT_BRAIN_RENDERED_BROWSER_VERIFICATION_V1":
        raise RuntimeError("BROWSER_VERIFICATION_SCHEMA_INVALID")
    if evidence.get("verified") is not True or evidence.get("status")!="VERIFIED":
        raise RuntimeError("BROWSER_VERIFICATION_NOT_VERIFIED")
    if evidence.get("producer_independent_verifier")!="urllib_official_python_downloads_page":
        raise RuntimeError("BROWSER_VERIFIER_INDEPENDENCE_MISSING")
    data=json.loads(REG.read_text(encoding="utf-8"))
    caps=data["capabilities"]
    cid="web.browser.rendered.capture.chromedriver"
    caps[cid]={
      "provides":["web.browser.rendered.capture"],
      "requires":[],
      "keywords":["browser","web","rendered","navigate","open","page","screenshot","url","website"],
      "cost":2,
      "platforms":["linux"],
      "limitations":[
        "Requires a compatible local Chrome/Chromium binary and Chromedriver.",
        "Captures one rendered page, visible text, title, final URL, result JSON, and a bounded full-page screenshot."
      ],
      "adapter_module":"browser_chromedriver",
      "entrypoint":"run",
      "action_template":{
        "type":"invoke_capability",
        "args":{
          "capability_id":cid,
          "url":"${input.url}",
          "screenshot_path":"${input.screenshot_path}",
          "result_path":"${input.result_path}"
        },
        "expect":{"type":"field_equals","field":"output_verified","value":True}
      },
      "source":{"type":"system_tool","executable":"chromedriver"},
      "incremental_spend_usd":0,
      "status":"VERIFIED_BOUND_CAPABILITY",
      "verification":{
        "mission_id":"ASTRA-BROWSER-PYTHON-RELEASE-VERIFY-001",
        "verification_result_path":str(evidence_path.relative_to(ROOT)),
        "producer_independent_verifier":True,
        "observed_effect":{
          "rendered":evidence.get("rendered"),
          "latest_stable_python3":evidence.get("latest_stable_python3"),
          "screenshot_sha256":evidence.get("screenshot_sha256"),
          "screenshot_bytes":evidence.get("screenshot_bytes"),
          "page_title":evidence.get("page_title")
        }
      }
    }
    REG.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("RENDERED_BROWSER_CAPABILITY_PROMOTED")

if __name__=="__main__":
    main()
