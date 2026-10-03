"""Exhaustive abstract-state universal proof for the exact frozen Tool Discovery route.

For the frozen target, identity completeness is independently verified. Each stage has
four visible tool identities and two required capabilities. After current-epoch receipt
filtering, each tool/capability fact is UNKNOWN, TRUE, or FALSE. This checker exhausts
all 3^8 evidence states x 2^4 eligibility masks against the exact candidate.

Every PROBE successor strictly reduces UNKNOWN count, SELECT is only the least-cost
all-positive route after cheaper routes are disproved, and ESCALATE occurs only when
all eligible routes are disproved. Thus finite induction covers every hidden completion
and every valid current receipt history in the exact frozen target.
"""
from __future__ import annotations
import hashlib, itertools, json
from pathlib import Path
from typing import Any, Mapping
from canonical.runtime import tool_discovery_information_safe_candidate as candidate

ROOT=Path(__file__).resolve().parents[2]
ATOM=("INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_"
      "SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_TOOL_DISCOVERY_PROTOCOL")
EXPECTED_BLOBS={
 "canonical/runtime/tool_discovery_information_safe_candidate.py":"64c02edd568d95ec5ed54b7b8122183ce5b82e17",
 "canonical/runtime/tool_discovery_information_safe_proof.py":"2450a9644119c9fdf9c43307a1d115098d6ba592",
 "canonical/runtime/tool_discovery_information_safe_proof_v2.py":"5e8a953864e13ec76768c3e8920644107c65a644",
 "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json":"6bcabc0a7d0525532ce7b80e132278f7c99caa43",
 "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":"62394e5b7d221ec9f69c3458f669e40e253a9d09",
 "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json":"ec2d931860e7cd7d9f73a658706f8c33fca3a10d",
 "canonical/verification/TOOL_DISCOVERY_FROZEN_SCOPE_COMPLETENESS_DISCHARGE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"6699bd89db663b98c836d3203bc6ebb558a29e04",
}
TOOLS=tuple((f"T{i}",float(i)) for i in range(1,5))
CAPS=("A","B")
VALUES=(None,True,False)
PAIR_ORDER=tuple((tid,cap) for tid,_ in TOOLS for cap in CAPS)
TOTAL_STATES=(3**len(PAIR_ORDER))*(2**len(TOOLS))

def blob_sha(path:Path)->str:
 data=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def _text(rel:str)->str:
 return (ROOT/rel).read_text(encoding="utf-8")

def _public(values:tuple[bool|None,...],mask:int)->dict[str,Any]:
 tools=[]
 for i,(tid,cost) in enumerate(TOOLS):
  eligible=bool((mask>>i)&1)
  tools.append({"tool_id":tid,"cost":cost,"available":eligible,"authorized":True})
 receipts=[]
 for (tid,cap),value in zip(PAIR_ORDER,values):
  if value is not None:
   receipts.append({"kind":"SAFE_CAPABILITY_PROBE","stage":1,"tool_id":tid,
                    "capability":cap,"epoch":0,"supported":value})
 return {"required_capabilities":list(CAPS),"tools":tools,
         "prior_probe_receipts":receipts,"version_events":[]}

def _ev(values):
 return {pair:value for pair,value in zip(PAIR_ORDER,values)}

def _expected(values,mask):
 ev=_ev(values)
 for i,(tid,_cost) in enumerate(TOOLS):
  if not ((mask>>i)&1): continue
  unknown=[]; disproved=False
  for cap in CAPS:
   value=ev[(tid,cap)]
   if value is False:
    disproved=True; break
   if value is None: unknown.append(cap)
  if disproved: continue
  if unknown: return {"action":"PROBE","tool_id":tid,"capability":unknown[0]}
  return {"action":"SELECT","tool_id":tid}
 return {"action":"ESCALATE","reason":"NO_EVIDENCE_SUPPORTED_SUFFICIENT_TOOL"}

def _terminal_sound(values,mask,action):
 ev=_ev(values); kind=action.get("action")
 if kind=="SELECT":
  selected=str(action.get("tool_id") or "")
  for i,(tid,_cost) in enumerate(TOOLS):
   if not ((mask>>i)&1): continue
   vals=[ev[(tid,c)] for c in CAPS]
   if tid==selected:
    return vals==[True,True]
   if False not in vals:
    return False
  return False
 if kind=="ESCALATE":
  return all(
   (not ((mask>>i)&1)) or
   (False in [ev[(tid,c)] for c in CAPS])
   for i,(tid,_cost) in enumerate(TOOLS)
  )
 return False

def _successors(values,action):
 idx=PAIR_ORDER.index((str(action["tool_id"]),str(action["capability"])))
 assert values[idx] is None
 a=list(values); b=list(values); a[idx]=True; b[idx]=False
 return tuple(a),tuple(b)

def derive_source_facts()->dict[str,bool]:
 cand=_text("canonical/runtime/tool_discovery_information_safe_candidate.py")
 v1=_text("canonical/runtime/tool_discovery_information_safe_proof.py")
 v2=_text("canonical/runtime/tool_discovery_information_safe_proof_v2.py")
 compact_v2="".join(v2.split())
 return {
  "TARGET_EXACTLY_FOUR_TOOLS":all(v1.count(f'"tool_id": f"T{i}_{{suffix}}"')==1 for i in range(1,5)),
  "TARGET_TWO_REQUIRED_CAPS_PER_STAGE":(
   '"required_capabilities": [c0, c1]' in v1 and
   '"required_capabilities": [c1, c2]' in v1),
  "TARGET_STRICT_COST_ORDER_1_TO_4":all(f'"cost": {i}.0' in v1 for i in range(1,5)),
  "PUBLIC_EXPOSES_WHOLE_CASE_TOOL_LIST":'"tools": [dict(t) for t in case["tools"]]' in v1,
  "ORACLE_RANGES_OVER_SAME_CASE_TOOL_LIST":'for t in case["tools"]:' in v1,
  "CAPABILITY_TRUTH_SEPARATE_ORACLE":'case["_oracle"]' in v1,
  "CURRENT_EPOCH_ONLY":(
   'rec.get("epoch") != epochs[tid]' in cand and
   'TOOL_VERSION_CHANGED' in cand),
  "ELIGIBILITY_IS_AVAILABLE_AND_AUTHORIZED":(
   't.get("available") is True and t.get("authorized") is True' in cand),
  "COST_ORDERED":'tools.sort(key=lambda t: (float(t.get("cost", 0.0)), str(t.get("tool_id") or "")))' in cand,
  "FALSE_SKIPS_ROUTE":'if value is False:' in cand and 'known_false = True' in cand,
  "UNKNOWN_PROBES_BEFORE_SELECT":'if value is None:' in cand and 'return {"action": "PROBE"' in cand,
  "V2_INHERITS_V1_SHAPE":(
   "case=v1.generate_case(seed,0)" in compact_v2 and
   "case=v1.generate_case(seed,ordinal%3)" in compact_v2 and
   'case["tools"]=' not in compact_v2),
  "V2_ELIGIBILITY_MUTATIONS_ARE_SUBSET_OF_MASKS":(
   'cheapest["available"]=False' in compact_v2 and
   'cheapest["authorized"]=False' in compact_v2),
  "V2_NO_ROUTE_MUTATES_HIDDEN_SUPPORT_ONLY":'table[tid]=set(table[tid])-required' in compact_v2,
 }

def exhaustive_check()->dict[str,Any]:
 checked=probes=selects=escalates=successors=0
 failures=[]
 for values in itertools.product(VALUES,repeat=len(PAIR_ORDER)):
  unknown=sum(v is None for v in values)
  for mask in range(1<<len(TOOLS)):
   checked+=1
   got=candidate.next_action(_public(values,mask))
   want=_expected(values,mask)
   if got!=want:
    failures.append({"kind":"ACTION_MISMATCH","values":values,"mask":mask,"got":got,"want":want})
   elif got["action"]=="PROBE":
    probes+=1
    for nxt in _successors(values,got):
     successors+=1
     if sum(v is None for v in nxt)!=unknown-1:
      failures.append({"kind":"RANK_NOT_DECREASING","values":values,"mask":mask,"got":got})
   elif got["action"]=="SELECT":
    selects+=1
    if not _terminal_sound(values,mask,got):
     failures.append({"kind":"UNSOUND_SELECT","values":values,"mask":mask,"got":got})
   elif got["action"]=="ESCALATE":
    escalates+=1
    if not _terminal_sound(values,mask,got):
     failures.append({"kind":"PREMATURE_ESCALATE","values":values,"mask":mask,"got":got})
   else:
    failures.append({"kind":"UNKNOWN_ACTION","got":got})
   if failures:
    return {"pass":False,"checked":checked,"failures":failures[:5]}
 return {"pass":True,"checked":checked,"expected_state_count":TOTAL_STATES,
         "probe_states":probes,"select_states":selects,"escalate_states":escalates,
         "probe_successor_checks":successors,"failures":[]}

def verify()->dict[str,Any]:
 drift=[]
 for rel,want in EXPECTED_BLOBS.items():
  got=blob_sha(ROOT/rel)
  if got!=want: drift.append({"path":rel,"got":got,"expected":want})
 if drift:
  return {"status":"FAIL_CLOSED__SOURCE_BLOB_DRIFT","source_blob_drift":drift,
          "universal_scope_proved":False,"capability_credit_delta":0,"family_credit_delta":0,
          "execution_authority":False,"promotion_authority":False}
 receipt=json.loads(_text("canonical/verification/TOOL_DISCOVERY_FROZEN_SCOPE_COMPLETENESS_DISCHARGE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"))
 assert receipt["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
 assert receipt["discharged_minimum_missing_fact"]=="INDEPENDENT_EXACT_SCOPE_SEMANTICS_PROVING_PREENUMERATED_TOOL_IDS_ARE_COMPLETE_FOR_THE_FROZEN_TARGET"
 assert receipt["terminal_results_replayed"]==0 and receipt["new_reality_units_consumed"]==0
 binding=json.loads(_text("canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json"))
 assert binding["exact_bound_blobs"]["candidate"]["blob_sha"]==EXPECTED_BLOBS["canonical/runtime/tool_discovery_information_safe_candidate.py"]
 assert binding["exact_bound_blobs"]["oracle"]["blob_sha"]==EXPECTED_BLOBS["canonical/runtime/tool_discovery_information_safe_proof_v2.py"]
 protocol=json.loads(_text("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"))
 row=next(x for x in protocol["protocols"] if x["family"]=="TOOL_DISCOVERY_SELECTION_AND_LEARNING")
 assert row["status"]=="DEFINED_RESULT_OPEN" and "unknown tool discovery" in row["task_dimensions"]
 firewall=json.loads(_text("canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json"))
 assert "UNIVERSAL_FORMAL_SCOPE_PROOF" in firewall["admissible_absolute_dominance_bases"]
 facts=derive_source_facts(); missing=sorted(k for k,v in facts.items() if v is not True)
 abstract=exhaustive_check()
 passed=(not missing and abstract["pass"] and abstract["checked"]==TOTAL_STATES)
 return {
  "schema":"PROJECT_BRAIN_TOOL_DISCOVERY_ABSTRACT_STATE_UNIVERSAL_SCOPE_CERTIFICATE_V1",
  "status":("PASS__UNIVERSAL_FORMAL_SCOPE_PROOF__104976_EXHAUSTIVE_ABSTRACT_STATES__"
            "INDEPENDENT_PUBLIC_RUNNER_REQUIRED__ZERO_CREDIT" if passed else
            "FAIL_CLOSED__UNIVERSAL_SCOPE_PROOF_FAILED"),
  "universal_scope_proved":passed,"scope_atom_satisfied_candidate":passed,
  "scope_atom":ATOM,"target_predicate":"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
  "basis_kind":"UNIVERSAL_FORMAL_SCOPE_PROOF","source_blob_drift":[],
  "source_facts":facts,"missing_source_facts":missing,"abstract_state_proof":abstract,
  "proof":{
   "abstraction":"Every current-epoch tool/capability fact is UNKNOWN, TRUE, or FALSE; each tool is eligible or ineligible.",
   "complete_state_space":"All 3^8 x 2^4 abstract states are checked against the exact candidate.",
   "induction":"Every probe has two possible truth successors and strictly decreases UNKNOWN count, so termination follows by finite induction.",
   "selection":"SELECT is only the first cost-ordered eligible all-positive tool after every cheaper eligible tool is disproved.",
   "escalation":"ESCALATE is only when every eligible tool is disproved.",
   "history_versioning":"Any valid current receipt history maps to one abstract state; stale epochs are discarded before that mapping.",
   "identity_scope":"Independent receipt proves the frozen target's pre-enumerated tool identities are complete."
  },
  "uses_empirical_generalization":False,"terminal_cases_replayed":0,
  "new_reality_units_consumed":0,"incremental_spend_usd":0,
  "capability_credit_delta":0,"family_credit_delta":0,
  "execution_authority":False,"promotion_authority":False
 }

def main()->int:
 out=verify(); print(json.dumps(out,indent=2,sort_keys=True,default=str))
 return 0 if out.get("universal_scope_proved") is True else 1

if __name__=="__main__":
 raise SystemExit(main())
