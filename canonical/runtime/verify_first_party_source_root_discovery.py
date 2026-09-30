#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[2]
ADAPTER=ROOT/"canonical/runtime/bound_capabilities/authoritative_root_discovery_wikidata.py"
API="https://www.wikidata.org/w/api.php"
UA="ProjectBrain-FirstPartySourceDiscovery-IndependentVerifier/1.0"

CASES=[
    {"query":"Python (programming language)","expected_host_suffix":"python.org"},
    {"query":"World Health Organization","expected_host_suffix":"who.int"},
    {"query":"European Space Agency","expected_host_suffix":"esa.int"},
]


def get_json(params):
    url=API+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=25) as resp:
        raw=resp.read(3_000_001)
        if len(raw)>3_000_000:
            raise RuntimeError("ORACLE_RESPONSE_TOO_LARGE")
        if getattr(resp,"status",200)!=200:
            raise RuntimeError("ORACLE_HTTP_STATUS_"+str(resp.status))
    return url,json.loads(raw.decode("utf-8"))


def independent_search_ids(query, limit=8):
    _,payload=get_json({
        "action":"wbsearchentities","search":query,"language":"en","uselang":"en",
        "format":"json","limit":limit,"type":"item",
    })
    return [
        str(x.get("id") or "")
        for x in (payload.get("search") or [])
        if isinstance(x,dict)
    ]


def independent_p856(qid):
    _,payload=get_json({
        "action":"wbgetentities","ids":qid,"props":"claims","format":"json",
    })
    entity=(payload.get("entities") or {}).get(qid) or {}
    out=[]
    for row in ((entity.get("claims") or {}).get("P856") or []):
        try:
            value=row["mainsnak"]["datavalue"]["value"]
        except Exception:
            continue
        if isinstance(value,str):
            out.append(value.strip())
    return list(dict.fromkeys(out))


def producer(query, output_path):
    code=r"""
import importlib.util,json,pathlib,sys
adapter=pathlib.Path(sys.argv[1])
root=pathlib.Path(sys.argv[2])
query=sys.argv[3]
out=sys.argv[4]
spec=importlib.util.spec_from_file_location("candidate_source_discovery",adapter)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
result=m.run({"query":query,"output_path":out,"language":"en","max_results":8,"timeout_s":25},root)
print(json.dumps(result,sort_keys=True))
"""
    p=subprocess.run(
        [sys.executable,"-c",code,str(ADAPTER),str(ROOT),query,str(output_path)],
        cwd=ROOT,text=True,capture_output=True,timeout=60,
    )
    if p.returncode!=0:
        raise RuntimeError("PRODUCER_FAILED:"+p.stderr[-2000:])
    return json.loads(pathlib.Path(output_path).read_text(encoding="utf-8"))


def producer_should_fail(query):
    code=r"""
import importlib.util,pathlib,sys
adapter=pathlib.Path(sys.argv[1])
spec=importlib.util.spec_from_file_location("candidate_source_discovery_negative",adapter)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
try:
    m.discover(sys.argv[2])
except Exception as exc:
    print(type(exc).__name__+":"+str(exc))
    raise SystemExit(0)
raise SystemExit(2)
"""
    p=subprocess.run(
        [sys.executable,"-c",code,str(ADAPTER),query],
        cwd=ROOT,text=True,capture_output=True,timeout=20,
    )
    return p.returncode==0


def main():
    results=[]
    with tempfile.TemporaryDirectory(prefix="brain-first-party-source-") as td:
        td=pathlib.Path(td)
        for index,case in enumerate(CASES,1):
            rel=f"canonical/astra_runtime/tmp/FIRST_PARTY_SOURCE_ROOT_QUAL_{index}.json"
            out=producer(case["query"],rel)
            search_ids=independent_search_ids(case["query"],8)
            failures=[]
            if out.get("model_dependency_count")!=0:
                failures.append("MODEL_DEPENDENCY_NOT_ZERO")
            if out.get("incremental_spend_usd")!=0:
                failures.append("NONZERO_SPEND")
            if not isinstance(out.get("candidates"),list) or not out["candidates"]:
                failures.append("NO_CANDIDATES")
            matched_expected=False
            checked=[]
            for cand in out.get("candidates") or []:
                qid=str(cand.get("entity_id") or "")
                urls=list(cand.get("official_urls") or [])
                if qid not in search_ids:
                    failures.append("ENTITY_NOT_IN_INDEPENDENT_SEARCH:"+qid)
                    continue
                oracle_urls=independent_p856(qid)
                if not urls:
                    failures.append("EMPTY_URLS:"+qid)
                for url in urls:
                    if url not in oracle_urls:
                        failures.append("URL_NOT_IN_P856:"+qid+":"+url)
                    host=(urllib.parse.urlsplit(url).hostname or "").lower()
                    if host==case["expected_host_suffix"] or host.endswith("."+case["expected_host_suffix"]):
                        matched_expected=True
                checked.append({"entity_id":qid,"producer_urls":urls,"oracle_urls":oracle_urls})
            if not matched_expected:
                failures.append("EXPECTED_FIRST_PARTY_HOST_NOT_FOUND:"+case["expected_host_suffix"])
            results.append({
                "query":case["query"],
                "expected_host_suffix":case["expected_host_suffix"],
                "pass":not failures,
                "failures":failures,
                "checked":checked,
            })

    negatives={
        "empty_query_rejected":producer_should_fail(""),
        "control_character_rejected":producer_should_fail("NASA\x01"),
        "overlong_query_rejected":producer_should_fail("x"*513),
    }
    all_pass=all(x["pass"] for x in results) and all(negatives.values())
    report={
        "schema":"PROJECT_BRAIN_FIRST_PARTY_SOURCE_ROOT_DISCOVERY_QUALIFICATION_V1",
        "capability_id":"MODEL_INDEPENDENT_FIRST_PARTY_SOURCE_ROOT_DISCOVERY_V1",
        "producer":"canonical/runtime/bound_capabilities/authoritative_root_discovery_wikidata.py",
        "independent_oracle":"fresh direct Wikidata wbsearchentities + wbgetentities P856 queries without producer import",
        "cases":results,
        "negative_cases":negatives,
        "all_pass":all_pass,
        "model_dependency_count":0,
        "incremental_spend_usd":0,
        "parent_task_replay":False,
        "sqlite_task_used":False,
        "mauna_task_used":False,
    }
    path=ROOT/"canonical/astra_runtime/evidence/MODEL_INDEPENDENT_FIRST_PARTY_SOURCE_ROOT_DISCOVERY_V1__QUALIFICATION.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))
    if not all_pass:
        raise SystemExit(1)
    print("FIRST_PARTY_SOURCE_ROOT_DISCOVERY_QUALIFIED")


if __name__=="__main__":
    main()
