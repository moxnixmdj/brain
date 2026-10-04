"""Cross-authority verifier for the verified synthesis Root3 scope reconciliation."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any,Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_ROOT3_SYNTHESIS_SCOPE_RECONCILIATION_VERIFIER_V1"
FILES={
"canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json":"c19135025f17cdb9acf65aaf7d17d660aae9189d",
"canonical/governance/ROOT3_RESIDUAL_COMPRESSION_V1.json":"bad32d1e90bf0e54bb1176b67ad677336f40d71d",
"canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V1.json":"6cfc9d1365e879637261e6c14d6cd09f21719d26",
"canonical/governance/ROOT3_UNIVERSAL_SCOPE_CLOSURE_ACTIVATION_V1.json":"28573015115365d76422bddf80520c7d313040df",
"canonical/governance/ROOT3_MATCHED_SUPERPORTFOLIO_MINIMUM_REALITY_BINDING_V1.json":"78615211c9cd40e79afc2c5e5624893b9a503ef7",
"canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json":"cc1981abb7e80b7d197105fdcb3955a5e54d4e44",
"canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json":"12e3ff86ad5f4436f1679ec5257d92f7c89f5c08",
"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json":"2c759919f8ff640453fccff645bfb4681957e20e",
"canonical/governance/SYNTHESIS_SCOPE_CERTIFICATE_V1.json":"dea9028f92f111ee3c8be71615fa4b02e8a8bfb6",
"canonical/verification/SYNTHESIS_SCOPE_CERTIFICATE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json":"1528485a15c98e89c9fb4dc50d691b6682e08542",
}
PID="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"

def blob(p:str)->str:
 b=(ROOT/p).read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(p:str)->dict[str,Any]:
 x=json.loads((ROOT/p).read_text(encoding="utf-8"))
 if not isinstance(x,dict): raise ValueError(p)
 return x

def evaluate()->dict[str,Any]:
 e=[]
 for p,h in FILES.items():
  if blob(p)!=h: e.append("BLOB_DRIFT:"+p)
 roots=load("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
 res=load("canonical/governance/ROOT3_RESIDUAL_COMPRESSION_V1.json")
 cut=load("canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V1.json")
 ua=load("canonical/governance/ROOT3_UNIVERSAL_SCOPE_CLOSURE_ACTIVATION_V1.json")
 sp=load("canonical/governance/ROOT3_MATCHED_SUPERPORTFOLIO_MINIMUM_REALITY_BINDING_V1.json")
 z=load("canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json")
 fr=load("canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json")
 ta=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")

 acc=roots.get("current_acceptance") or {}
 if (acc.get("accepted_families"),acc.get("open_families"),acc.get("proved_atomic"),acc.get("unresolved_atomic"),acc.get("terminal"))!=(5,14,12,26,False):
  e.append("ACCEPTANCE_TRUTH_DRIFT")
 part=roots.get("current_residual_root_partition") or {}
 r2=part.get("root2_only") or []; r3=part.get("root3_only") or []; mixed=part.get("root2_and_root3") or []
 if (part.get("root2_only_count"),part.get("root3_only_count"),part.get("root2_and_root3_count"),part.get("unresolved_total"))!=(16,7,3,26):
  e.append("ROOT_COUNTS")
 if PID not in r2 or PID in mixed or PID in r3: e.append("SYNTHESIS_CLASS")
 if len(set(r2)|set(r3)|set(mixed))!=26: e.append("PARTITION_SET_SIZE")
 if set(r2)&set(r3) or set(r2)&set(mixed) or set(r3)&set(mixed): e.append("PARTITION_OVERLAP")

 row=next((x for x in res.get("compressed_residuals",[]) if x.get("predicate_id")==PID),None)
 if not isinstance(row,Mapping): e.append("SYNTHESIS_RESIDUAL_ROW_MISSING")
 else:
  if row.get("root_class")!="ROOT2": e.append("RESIDUAL_ROOT_CLASS")
  if row.get("scope_relation_closed") is not True: e.append("RESIDUAL_SCOPE_NOT_CLOSED")

 if (cut.get("derivation") or {}).get("live_root3_predicates")!=10: e.append("MINCUT_ROOT3_COUNT")
 if "SYNTHESIS" not in str((cut.get("derivation") or {}).get("synthesis_root3_residual","")): e.append("MINCUT_SYNTHESIS_STATE")

 if (ua.get("current_truth") or {}).get("live_root3_predicates")!=10: e.append("UA_ROOT3_COUNT")
 live_ids={x.get("id") for x in ua.get("exact_work_classes",[]) if isinstance(x,Mapping)}
 if "ROOT3_SYNTHESIS_SCOPE_RELATION_V1" in live_ids: e.append("UA_SYNTHESIS_STILL_LIVE")
 closed_ids={x.get("id") for x in ua.get("closed_work_classes",[]) if isinstance(x,Mapping)}
 if "ROOT3_SYNTHESIS_SCOPE_RELATION_V1" not in closed_ids: e.append("UA_SYNTHESIS_NOT_CLOSED")

 spids={x.get("predicate_id") for x in sp.get("matched_scope_targets",[]) if isinstance(x,Mapping)}
 if PID in spids: e.append("ROOT3_SUPERPORTFOLIO_SYNTHESIS_STILL_BOUND")
 if (sp.get("execution_compression") or {}).get("matched_scope_target_count")!=7: e.append("ROOT3_SUPERPORTFOLIO_COUNT")

 ex=z.get("exact_state") or {}
 if (ex.get("root2_only_count"),ex.get("root3_only_count"),ex.get("root2_and_root3_count"))!=(16,7,3): e.append("ZERO_CUT_ROOT_COUNTS")

 fx=fr.get("exact_state") or {}
 if (fx.get("root2_only_count"),fx.get("root3_only_count"),fx.get("root2_and_root3_count"),fx.get("root2_involved_count"),fx.get("root3_involved_count"))!=(16,7,3,19,10):
  e.append("FRONTIER_ROOT_COUNTS")
 if (fr.get("authority") or {}).get("root_state",{}).get("git_blob_sha")!=FILES["canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"]:
  e.append("FRONTIER_ROOT_POINTER")
 if (fr.get("authority") or {}).get("root3_residual_compression",{}).get("git_blob_sha")!=FILES["canonical/governance/ROOT3_RESIDUAL_COMPRESSION_V1.json"]:
  e.append("FRONTIER_RESIDUAL_POINTER")
 if (fr.get("authority") or {}).get("root3_minimum_action_cut",{}).get("git_blob_sha")!=FILES["canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V1.json"]:
  e.append("FRONTIER_MINCUT_POINTER")

 truth=ta.get("truth") or {}
 if truth.get("opus55_acceptance")!="5/19_PASS__14/19_OPEN" or truth.get("achieved") is not False: e.append("TERMINAL_TRUTH_DRIFT")
 src=ta.get("sources") or {}
 if src.get("terminal_root_cause_state",{}).get("git_blob_sha")!=FILES["canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"]: e.append("TA_ROOT_POINTER")
 if src.get("root2_root3_minimum_execution_frontier_v1",{}).get("git_blob_sha")!=FILES["canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json"]: e.append("TA_FRONTIER_POINTER")
 if src.get("root3_residual_compression_v1",{}).get("git_blob_sha")!=FILES["canonical/governance/ROOT3_RESIDUAL_COMPRESSION_V1.json"]: e.append("TA_RESIDUAL_POINTER")
 if src.get("current_zero_reality_minimum_cut_v8",{}).get("git_blob_sha")!=FILES["canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V8.json"]: e.append("TA_ZEROCUT_POINTER")
 if src.get("root3_minimum_action_cut",{}).get("git_blob_sha")!=FILES["canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V1.json"]: e.append("TA_MINCUT_POINTER")
 ssrc=src.get("synthesis_lossless_scope_activation") or {}
 if ssrc.get("certificate_git_blob_sha")!=FILES["canonical/governance/SYNTHESIS_SCOPE_CERTIFICATE_V1.json"]: e.append("TA_SYNTH_CERT_POINTER")
 if ssrc.get("verification_git_blob_sha")!=FILES["canonical/verification/SYNTHESIS_SCOPE_CERTIFICATE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"]: e.append("TA_SYNTH_VERIFY_POINTER")

 ok=not e
 return {
  "schema":SCHEMA,
  "status":"PASS__SYNTHESIS_RECLASSIFIED_ROOT2_ONLY__ROOT3_11_TO_10__ROOT2_19_UNCHANGED__26_UNRESOLVED__ZERO_ACCEPTANCE_CREDIT" if ok else "FAIL_CLOSED",
  "pass":ok,"errors":sorted(set(e)),
  "accepted_families":5,"proved_atomic":12,"unresolved_atomic":26,
  "root2_only_count":16,"root3_only_count":7,"root2_and_root3_count":3,
  "root2_involved_count":19,"root3_involved_count":10,
  "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,
  "new_reality_units_consumed":0,"incremental_spend_usd":0,
  "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False,
 }
if __name__=="__main__":
 out=evaluate(); print(json.dumps(out,indent=2,sort_keys=True)); raise SystemExit(0 if out["pass"] else 1)
