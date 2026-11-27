from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_ROOT3_NONREPO_EFFECT_CARRIER_CENSUS_C1_CANDIDATE_V1"
OUTPUT_SCHEMA="PROJECT_BRAIN_ROOT3_NONREPO_EFFECT_CARRIER_CENSUS_C1_OUTPUT_V1"
NONREPO={"apt","npm","pypi","system_tool"}


class CarrierCensusError(ValueError):
    pass


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def _verify_signature(carrier: str, text: str, adapter: str) -> None:
    if carrier=="IN_PROCESS_THIRD_PARTY_PYTHON":
        if "subprocess" in text:
            raise CarrierCensusError("IN_PROCESS_ADAPTER_HAS_SUBPROCESS:"+adapter)
        return
    if carrier=="CHILD_PROCESS_TOOL":
        if "subprocess.run" not in text and "subprocess.Popen" not in text:
            raise CarrierCensusError("CHILD_PROCESS_SIGNATURE_MISSING:"+adapter)
        return
    if carrier=="EXTERNAL_BROWSER_BRIDGE":
        required=("subprocess.Popen","127.0.0.1","urllib.request")
        if not all(x in text for x in required):
            raise CarrierCensusError("BROWSER_BRIDGE_SIGNATURE_MISSING:"+adapter)
        return
    raise CarrierCensusError("UNKNOWN_CARRIER_CLASS:"+carrier)


def compile_census(repo_root: str | Path, manifest_path: str | Path) -> dict[str,Any]:
    root=Path(repo_root).resolve()
    mp=(root/manifest_path).resolve()
    m=json.loads(mp.read_text(encoding="utf-8"))
    if m.get("schema")!=SCHEMA:
        raise CarrierCensusError("MANIFEST_SCHEMA_INVALID")

    reg_rel=m["subject"]["registry_path"]
    reg=(root/reg_rel).resolve()
    raw=reg.read_bytes()
    reg_sha=git_blob_sha(raw)
    if reg_sha!=m["subject"]["registry_git_blob_sha"]:
        raise CarrierCensusError("REGISTRY_BLOB_DRIFT")
    data=json.loads(raw)
    caps=data.get("capabilities")
    if not isinstance(caps,dict):
        raise CarrierCensusError("REGISTRY_CAPABILITIES_INVALID")

    rows=[]
    source_types=set()
    adapters=set()
    carrier_counts=Counter()
    adapter_counts=Counter()
    amap=m["adapter_carrier_map"]
    expected_blobs=m["adapter_blobs"]

    for cid,entry in sorted(caps.items()):
        if not isinstance(entry,dict):
            raise CarrierCensusError("CAPABILITY_ENTRY_INVALID:"+str(cid))
        source=entry.get("source") or {}
        st=str(source.get("type") or "")
        if st not in NONREPO:
            continue
        source_types.add(st)
        adapter=str(entry.get("adapter_module") or "")
        if adapter not in amap:
            raise CarrierCensusError("NONREPO_ADAPTER_UNCLASSIFIED:"+cid+":"+adapter)
        carrier=amap[adapter]
        adapters.add(adapter)
        carrier_counts[carrier]+=1
        adapter_counts[adapter]+=1
        rows.append({
            "capability_id":cid,
            "source_type":st,
            "adapter_module":adapter,
            "effect_carrier":carrier,
        })

    ids=[x["capability_id"] for x in rows]
    if ids!=sorted(m["expected_nonrepo_capability_ids"]):
        raise CarrierCensusError("NONREPO_CAPABILITY_SET_DRIFT")
    if sorted(source_types)!=sorted(m["expected_nonrepo_source_types"]):
        raise CarrierCensusError("NONREPO_SOURCE_TYPE_SET_DRIFT")
    if set(adapters)!=set(amap):
        raise CarrierCensusError("ADAPTER_SET_DRIFT")

    adapter_rows=[]
    for adapter in sorted(adapters):
        p=root/"canonical/runtime/bound_capabilities"/(adapter+".py")
        if not p.is_file():
            raise CarrierCensusError("ADAPTER_FILE_MISSING:"+adapter)
        b=p.read_bytes()
        sha=git_blob_sha(b)
        if sha!=expected_blobs.get(adapter):
            raise CarrierCensusError("ADAPTER_BLOB_DRIFT:"+adapter)
        text=b.decode("utf-8")
        carrier=amap[adapter]
        _verify_signature(carrier,text,adapter)
        adapter_rows.append({
            "adapter_module":adapter,
            "git_blob_sha":sha,
            "effect_carrier":carrier,
            "capability_reference_count":adapter_counts[adapter],
        })

    expected=m["expected_counts"]
    if len(rows)!=expected["nonrepo_capabilities"]:
        raise CarrierCensusError("NONREPO_CAPABILITY_COUNT_DRIFT")
    if len(adapters)!=expected["unique_nonrepo_adapters"]:
        raise CarrierCensusError("NONREPO_ADAPTER_COUNT_DRIFT")
    for carrier in ("IN_PROCESS_THIRD_PARTY_PYTHON","CHILD_PROCESS_TOOL","EXTERNAL_BROWSER_BRIDGE"):
        if carrier_counts[carrier]!=expected[carrier]:
            raise CarrierCensusError("CARRIER_COUNT_DRIFT:"+carrier)

    return {
        "schema":OUTPUT_SCHEMA,
        "status":"PASS__NONREPO_20_CAPABILITIES_COLLAPSED_TO_3_EXACT_BYTE_BOUND_EFFECT_CARRIERS__C1_STILL_OPEN",
        "registry_git_blob_sha":reg_sha,
        "nonrepo_capability_count":len(rows),
        "unique_nonrepo_adapter_count":len(adapters),
        "nonrepo_source_types":sorted(source_types),
        "effect_carrier_counts":dict(sorted(carrier_counts.items())),
        "capabilities":rows,
        "adapters":adapter_rows,
        "remaining_c1_residuals":[
            "IN_PROCESS_THIRD_PARTY_INTERNAL_EFFECT_TOTALITY_AND_NATIVE_EXTENSION_SPLIT",
            "CHILD_PROCESS_EFFECT_BOUNDARY_MEDIATION",
            "EXTERNAL_BROWSER_BRIDGE_EFFECT_MEDIATION",
        ],
        "c1_scope_complete":False,
        "acceptance_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }


if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=".")
    ap.add_argument("--manifest",default="canonical/governance/ROOT3_NONREPO_EFFECT_CARRIER_CENSUS_C1_CANDIDATE_V1.json")
    ns=ap.parse_args()
    print(json.dumps(compile_census(ns.repo_root,ns.manifest),indent=2,sort_keys=True))
