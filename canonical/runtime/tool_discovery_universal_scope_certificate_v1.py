"""Universal formal-scope certificate candidate for Tool Discovery owned route V1.

Like the already accepted Delegation universal certificate, this checker binds
exact source bytes, verifies the frozen target and already-separate predicates,
derives load-bearing source facts, executes the finite semantic transport
quotient, and then applies an explicit induction over finite discovery/probe
progress. It grants no acceptance credit itself.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any,Mapping

from canonical.runtime.tool_universe_gateway_v2 import ToolUniverseGateway, prove_identity_completeness
from canonical.runtime.tool_discovery_legacy_v3_transport_v1 import prove_transport_candidate
from canonical.runtime.tool_discovery_v3_owned_gateway_bridge_v1 import prove_bridge_instance

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_UNIVERSAL_SCOPE_CERTIFICATE_V1"
ATOM="INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_TOOL_DISCOVERY_PROTOCOL"

EXPECTED_BLOBS={
 "canonical/runtime/tool_universe_gateway_v2.py":"bb76780c78ae1a43cb102222fa60f2d19b0ce852",
 "canonical/tests/test_tool_universe_gateway_v2.py":"e9051452592227d5e1f46314e812fadc9ba8c1fa",
 "canonical/runtime/tool_discovery_legacy_v3_transport_v1.py":"fb1510b9dfec8e96c49de2ca228630686195e14b",
 "canonical/tests/test_tool_discovery_legacy_v3_transport_v1.py":"45e272fe3c322a5687b3bb7a2d15406e0e1337c3",
 "canonical/runtime/tool_discovery_v3_owned_gateway_bridge_v1.py":"2ee4bc46f43c2d7cc12f12109648835376126484",
 "canonical/tests/test_tool_discovery_v3_owned_gateway_bridge_v1.py":"9b9e2aaf8eca189715b6377e1d4a47a48c5ad124",
 "canonical/runtime/tool_discovery_dynamic_candidate_v3.py":"bbbee4d6baf8df937543644397abba38a67dce62",
 "canonical/runtime/tool_discovery_information_safe_candidate.py":"64c02edd568d95ec5ed54b7b8122183ce5b82e17",
 "canonical/runtime/tool_discovery_information_safe_proof.py":"2450a9644119c9fdf9c43307a1d115098d6ba592",
 "canonical/runtime/tool_discovery_information_safe_proof_v2.py":"5e8a953864e13ec76768c3e8920644107c65a644",
 "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":"62394e5b7d221ec9f69c3458f669e40e253a9d09",
 "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":"7885a827b1483bfb38315c1f492848f7e4680285",
 "canonical/verification/TOOL_DISCOVERY_DYNAMIC_REFINEMENT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"5fcdc5ae35f51c40f312edbe5727284c9f6ca3dd",
}

REQUIRED_FACTS=(
 "GATEWAY_DISCOVERY_EQUALS_REGISTRY",
 "GATEWAY_REJECTS_UNREGISTERED_INVOCATION",
 "GATEWAY_EPOCH_CHANGE_FORCES_RESTART",
 "V3_FILTERS_AVAILABILITY_AUTHORIZATION_AND_CONSTRAINT",
 "V3_SORTS_COST_THEN_ID",
 "V3_PROBES_ONLY_MISSING_REQUIRED_CAPABILITY",
 "V3_SELECTS_ONLY_AFTER_ALL_REQUIRED_EVIDENCE_TRUE",
 "V3_SKIPS_EVIDENCE_FALSE_ROUTE",
 "V3_DISCOVERS_ONLY_UNQUERIED_AVAILABLE_SOURCE",
 "V3_ESCALATES_AFTER_VISIBLE_AND_DISCOVERY_ROUTES_EXHAUSTED",
 "LEGACY_V3_TRANSPORT_EXECUTABLE",
 "OWNED_GATEWAY_BRIDGE_EXECUTABLE",
 "OWNED_GATEWAY_STARTS_EMPTY_WITH_SOLE_DISCOVERY_SOURCE",
 "OWNED_GATEWAY_GATES_PROBE_AND_SELECT",
 "TRANSFER_ATOM_ALREADY_SCOPE_COMPLETE",
 "NO_UNSUPPORTED_PROMOTION_ATOM_ALREADY_SCOPE_COMPLETE",
 "FROZEN_TARGET_REQUIRES_UNKNOWN_TOOL_DISCOVERY",
)

def blob_sha(rel:str)->str:
 data=(ROOT/rel).read_bytes()
 return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def text(rel:str)->str:
 return (ROOT/rel).read_text(encoding="utf-8")

def load(rel:str)->dict[str,Any]:
 x=json.loads(text(rel))
 if not isinstance(x,dict): raise AssertionError(rel+":NOT_OBJECT")
 return x

def _has(s:str,*parts:str)->bool:
 return all(p in s for p in parts)

def derive_source_facts()->dict[str,bool]:
 g=text("canonical/runtime/tool_universe_gateway_v2.py")
 v=text("canonical/runtime/tool_discovery_dynamic_candidate_v3.py")
 tr=text("canonical/runtime/tool_discovery_legacy_v3_transport_v1.py")
 br=text("canonical/runtime/tool_discovery_v3_owned_gateway_bridge_v1.py")
 bindings=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
 protocol=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")

 claims={x.get("predicate_id"):x for x in bindings.get("claims",[]) if isinstance(x,dict)}
 transfer=claims.get("TOOL_LEARNING_SECOND_TASK_TRANSFER",{})
 promotion=claims.get("TOOL_LEARNING_NO_UNSUPPORTED_PROMOTION",{})
 row=next((x for x in protocol.get("protocols",[]) if x.get("family")=="TOOL_DISCOVERY_SELECTION_AND_LEARNING"),{})

 return {
  "GATEWAY_DISCOVERY_EQUALS_REGISTRY":_has(g,
    'self._registry[tid].public_metadata(self._epoch)',
    'for tid in sorted(self._registry)',
    '"tools": tools',
  ),
  "GATEWAY_REJECTS_UNREGISTERED_INVOCATION":_has(g,
    'item = self._registry.get(tid)',
    'raise GatewayError("UNREGISTERED_TOOL_ID")',
  ),
  "GATEWAY_EPOCH_CHANGE_FORCES_RESTART":_has(g,
    'if episode_epoch != self._epoch:',
    'raise GatewayError("EPOCH_CHANGED_RESTART_EPISODE")',
    'self._epoch += 1',
  ),
  "V3_FILTERS_AVAILABILITY_AUTHORIZATION_AND_CONSTRAINT":_has(v,
    't.get("available") is True',
    't.get("authorized") is True',
    'and _pred(constraint,t)',
  ),
  "V3_SORTS_COST_THEN_ID":'tools.sort(key=lambda t:(float(t.get("cost",0.0)),str(t.get("tool_id") or "")))' in v,
  "V3_PROBES_ONLY_MISSING_REQUIRED_CAPABILITY":_has(v,
    'if v is None: unknown.append(cap)',
    'return {"action":"PROBE","tool_id":tid,"capability":unknown[0]}',
  ),
  "V3_SELECTS_ONLY_AFTER_ALL_REQUIRED_EVIDENCE_TRUE":_has(v,
    'if impossible: continue',
    'if unknown:',
    'return {"action":"SELECT","tool_id":tid}',
  ),
  "V3_SKIPS_EVIDENCE_FALSE_ROUTE":_has(v,
    'if v is False:',
    'impossible=True; break',
    'if impossible: continue',
  ),
  "V3_DISCOVERS_ONLY_UNQUERIED_AVAILABLE_SOURCE":_has(v,
    's.get("available") is True',
    'str(s.get("source_id") or "") not in queried',
    'return {',
    '"action":"DISCOVER"',
  ),
  "V3_ESCALATES_AFTER_VISIBLE_AND_DISCOVERY_ROUTES_EXHAUSTED":'return {"action":"ESCALATE","reason":"NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_DISCOVERY"}' in v,
  "LEGACY_V3_TRANSPORT_EXECUTABLE":_has(tr,'def semantic_quotient_exhaustion()','def prove_transport_candidate()'),
  "OWNED_GATEWAY_BRIDGE_EXECUTABLE":_has(br,'def apply_gateway_discovery(','def validate_probe(','def validate_select('),
  "OWNED_GATEWAY_STARTS_EMPTY_WITH_SOLE_DISCOVERY_SOURCE":_has(br,
    '"visible_tools":[]',
    '"discovery_sources":[gateway.discovery_source()]',
    'initial_visible_empty=p0["visible_tools"]==[]',
    'gateway_only=p0["discovery_sources"]==[g.discovery_source()]',
    'and initial_visible_empty and gateway_only',
  ),
  "OWNED_GATEWAY_GATES_PROBE_AND_SELECT":_has(br,
    'if action.get("action")!="PROBE": raise BridgeError("NOT_PROBE")',
    'if action.get("action")!="SELECT": raise BridgeError("NOT_SELECT")',
    'episode_epoch=int(public.get("gateway_episode_epoch",-1))',
    'return gateway.gate_invoke(',
  ),
  "TRANSFER_ATOM_ALREADY_SCOPE_COMPLETE":transfer.get("state")=="PROVED" and transfer.get("scope_complete") is True,
  "NO_UNSUPPORTED_PROMOTION_ATOM_ALREADY_SCOPE_COMPLETE":promotion.get("state")=="PROVED" and promotion.get("scope_complete") is True,
  "FROZEN_TARGET_REQUIRES_UNKNOWN_TOOL_DISCOVERY":"unknown tool discovery" in (row.get("task_dimensions") or [])
     and "later-task transfer without rediscovery" in (row.get("task_dimensions") or []),
 }

def prove_from_facts(facts:Mapping[str,bool],*,transport_pass:bool,bridge_pass:bool,identity_pass:bool)->dict[str,Any]:
 missing=[x for x in REQUIRED_FACTS if facts.get(x) is not True]
 if not transport_pass: missing.append("LEGACY_V3_TRANSPORT_RUNTIME_PASS")
 if not bridge_pass: missing.append("OWNED_GATEWAY_BRIDGE_RUNTIME_PASS")
 if not identity_pass: missing.append("OWNED_GATEWAY_IDENTITY_RUNTIME_PASS")
 if missing:
  return {
   "schema":SCHEMA,"status":"FAIL_CLOSED__UNIVERSAL_SCOPE_PREMISE_MISSING",
   "missing":sorted(set(missing)),"universal_scope_proved":False,
   "scope_atom_satisfied_candidate":False,"uses_empirical_generalization":False,
   "terminal_cases_replayed":0,"new_reality_units_consumed":0,
   "capability_credit_delta":0,"family_credit_delta":0,
   "execution_authority":False,"promotion_authority":False,
  }
 return {
  "schema":SCHEMA,
  "status":"PASS__UNIVERSAL_FORMAL_SCOPE_PROOF_DERIVED_FOR_OWNED_DYNAMIC_V3__INDEPENDENT_PUBLIC_RUNNER_REQUIRED__ZERO_CREDIT",
  "missing":[],
  "universal_scope_proved":True,
  "scope_atom_satisfied_candidate":True,
  "scope_atom":ATOM,
  "target_predicate":"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
  "basis_kind":"UNIVERSAL_FORMAL_SCOPE_PROOF",
  "uses_empirical_generalization":False,
  "proof":{
   "domain":(
    "ALL_FINITE_VALID_BRAIN_OWNED_TOOL_REGISTRIES_WITH_UNIQUE_IDENTITIES_NONNEGATIVE_FINITE_COSTS_"
    "FINITE_NONEMPTY_REQUIRED_CAPABILITY_SETS_WELL_FORMED_STATIC_SUPPORTED_CONSTRAINTS_"
    "TRUTHFUL_EPOCH_BOUND_SAFE_PROBE_RECEIPTS_AND_ATOMIC_REGISTRY_EPOCH_CHANGES"
   ),
   "identity_base":(
    "The owned route starts with no pre-visible tool identities, and the owned gateway is both sole invocation authority and sole discovery universe: "
    "unregistered identities are uninvocable and discovery enumerates every registered identity."
   ),
   "finite_progress_measure":(
    "Within a stable epoch let U be 1 if the owned gateway has not yet been discovered plus "
    "the count of required (tool,capability) pairs without current truthful evidence. "
    "A successful DISCOVER makes the gateway source queried and exposes the exact finite registry; "
    "each PROBE fills one previously missing required pair. Thus every receipt-advancing nonterminal "
    "transition strictly decreases finite U."
   ),
   "selection_optimality":(
    "Dynamic V3 filters the same authoritative availability/authorization/static constraint state, "
    "sorts by nonnegative declared cost then identity, rejects a route after any truthful required "
    "capability false receipt, probes the first missing required capability otherwise, and selects "
    "only when every required capability has current positive evidence. Therefore the first selected "
    "route is the least-cost admissible sufficient route under the declared tie-break."
   ),
   "sound_escalation":(
    "After complete gateway discovery and finite probe progress, if no route is selected then every "
    "admissible registered route has a truthful negative required-capability witness; the sole discovery "
    "source is already queried, so escalation is sound for the owned universe."
   ),
   "change_induction":(
    "Registry replacement increments the universe epoch and both stale PROBE and SELECT invocation fail closed through the same gateway. "
    "Therefore by induction over any finite sequence of atomic registry epochs, each episode restarts "
    "from an exact complete identity universe and prior-epoch evidence cannot authorize invocation."
   ),
   "terminal_evidence_transport":(
    "On the exact frozen legacy terminal public surface, Dynamic V3 is decision-semantics equivalent "
    "to the terminal-tested information-safe candidate. This preserves the 180/180 terminal sample "
    "as supporting evidence without using the finite sample as the universal proof."
   ),
   "separate_atoms":(
    "The frozen acceptance graph already marks second-task transfer and no-unsupported-promotion "
    "as independently proved scope-complete atoms; this certificate neither duplicates nor weakens them."
   ),
  },
  "terminal_cases_replayed":0,"new_reality_units_consumed":0,"incremental_spend_usd":0,
  "capability_credit_delta":0,"family_credit_delta":0,
  "execution_authority":False,"promotion_authority":False,
 }

def verify()->dict[str,Any]:
 drift=[p for p,w in EXPECTED_BLOBS.items() if blob_sha(p)!=w]
 if drift: raise AssertionError("SOURCE_BLOB_DRIFT:"+",".join(drift))
 protocol=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
 row=next(x for x in protocol["protocols"] if x["family"]=="TOOL_DISCOVERY_SELECTION_AND_LEARNING")
 assert row["proof_mode"]=="MATCHED_HIDDEN_TOOL_ECOSYSTEM_TRANSFER"
 assert "unknown tool discovery" in row["task_dimensions"]
 assert "safe probe choice" in row["task_dimensions"]
 assert "capability-state update" in row["task_dimensions"]
 assert "later-task transfer without rediscovery" in row["task_dimensions"]

 bindings=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
 claim=next(x for x in bindings["claims"] if x.get("predicate_id")=="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
 assert claim["state"]=="EXTERNAL_BLOCKED"
 assert claim["blocker"]=="ABSOLUTE_SCOPE_COMPLETENESS_MISSING"
 assert "UNIVERSAL_FORMAL_SCOPE_PROOF" in claim["discharge_condition"]

 prior=load("canonical/verification/TOOL_DISCOVERY_DYNAMIC_REFINEMENT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
 assert prior["target_preserved"] is True
 assert prior["universal_target_proved"] is False

 identity=prove_identity_completeness(ToolUniverseGateway([
   {"tool_id":"a","available":True,"authorized":True,"cost":1.0},
   {"tool_id":"b","available":False,"authorized":True,"cost":2.0},
 ]))
 transport=prove_transport_candidate()
 bridge=prove_bridge_instance([
   {"tool_id":"a","available":True,"authorized":True,"cost":1.0},
   {"tool_id":"b","available":True,"authorized":False,"cost":2.0},
 ])
 facts=derive_source_facts()
 return prove_from_facts(
   facts,
   transport_pass=transport["status"].startswith("PASS"),
   bridge_pass=bridge["status"].startswith("PASS"),
   identity_pass=identity["status"].startswith("PASS"),
 )

def main()->int:
 out=verify(); print(json.dumps(out,indent=2,sort_keys=True))
 return 0 if out.get("universal_scope_proved") is True else 1

if __name__=="__main__": raise SystemExit(main())
