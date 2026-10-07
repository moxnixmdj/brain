from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
M=ROOT/"canonical/governance/V9_SELECTED_CELL_MANIFEST_20261007_V2.json"
T=ROOT/"canonical/governance/V9_ROUTE_BUNDLE_TRIAGE_20261007_V1.json"
def sha(p):
 b=p.read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def verify():
 e=[]
 if sha(M)!="275a5d0813b4e4acbbe6015b5b92a9f2a959f126":e.append("MANIFEST_DRIFT")
 m=json.loads(M.read_text());t=json.loads(T.read_text())
 mb=set(m["route_bundles"]); tb=set(t["bundles"])
 if mb!=tb:e.append("BUNDLE_SET_MISMATCH")
 ps=[int(x["priority"]) for x in t["bundles"].values()]
 if sorted(ps)!=list(range(1,14)):e.append("PRIORITY_NOT_1_TO_13")
 if any(x.get("fresh_target_info_default") is True for x in t["bundles"].values()):e.append("FRESH_TARGET_INFO_DEFAULT_TRUE")
 return {"pass":not e,"errors":e,"bundle_count":13 if not e else None,"fresh_target_query_authorized":False,"terminal_credit_delta":0}
if __name__=="__main__":print(json.dumps(verify(),sort_keys=True))
