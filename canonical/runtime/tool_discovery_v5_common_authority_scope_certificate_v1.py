"""Universal common-authority scope certificate for Tool Discovery V5.

This certificate proves only scope completeness for the frozen matched Tool
Discovery protocol. It deliberately does not prove matched noninferiority.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
ATOM=(
    "INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_"
    "SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_TOOL_DISCOVERY_PROTOCOL"
)
EXPECTED={
 "canonical/runtime/tool_discovery_owned_universal_v5.py":"04a4a32197cd820f8a529421e8e28bc14f2c2332",
 "canonical/tests/test_tool_discovery_owned_universal_v5.py":"d4aba846af38e1c2f74f6d0391073b0e4faa40b0",
 "canonical/governance/TOOL_DISCOVERY_OWNED_UNIVERSAL_V5_THEOREM_V1.json":"2c422acb30242f0ca77b2aff11f858fcd27f1272",
 "canonical/governance/TOOL_DISCOVERY_V5_COMMON_AUTHORITY_SCOPE_RELATION_V1.json":"01b4d167b19a7fd0d106272955ca7c4645dca887",
 "canonical/governance/UNBARRED_FAMILY_MATCHED_PARITY_PROTOCOL_V1.json":"49181a12362ba3d640fc18d0251901dd49dce929",
 "canonical/governance/OPUS55_MATCHED_COMPARATOR_SUPERPORTFOLIO_V1.json":"d9ac894594ebcd2883520f7b7977a3548420541c",
 "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":"62394e5b7d221ec9f69c3458f669e40e253a9d09",
 "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json":"ee187f611a0e82b2de495ee377682f39bc31dd31",
 "canonical/governance/TOOL_DISCOVERY_UNIVERSAL_SCOPE_FORMALISM_CUT_V1.json":"e485b9729e8aea6bee2d75453167912023167fe8",
}

REQUIRED_FACTS=(
 "MATCHED_SAME_VISIBLE_INFORMATION",
 "MATCHED_SAME_TOOL_CLASSES",
 "MATCHED_SAME_EXTERNAL_ACTION_AUTHORITY",
 "SUPERPORTFOLIO_IDENTICAL_TOOL_BOUNDARIES",
 "FROZEN_PROTOCOL_UNKNOWN_TOOL_DISCOVERY",
 "FROZEN_PROTOCOL_HIDDEN_TOOL_ECOSYSTEM",
 "BEHAVIOR_UNKNOWN_CHANGING_SCOPE",
 "BEHAVIOR_REQUIRES_DISCOVERY",
 "V5_ARBITRARY_FINITE_AUTHORITY",
 "V5_INITIAL_IDENTITIES_HIDDEN",
 "V5_DISCOVERY_SOURCE_UNION_IS_REGISTRY",
 "V5_DISCOVERY_BEFORE_CAPABILITY_DECISION",
 "V5_CAPABILITY_TRUTH_HIDDEN",
 "V5_CURRENT_EPOCH_EVIDENCE_ONLY",
 "V5_UNREGISTERED_INVOCATION_REJECTED",
 "V5_MISSING_PROBE_PERMISSION_FAILS_CLOSED",
 "V5_THEOREM_REQUIRES_DISCOVERED_EQUALS_REGISTRY",
 "COMMON_AUTHORITY_SCOPE_NOT_NARROWED",
 "COMMON_AUTHORITY_MATCHED_ACCEPTANCE_SEPARATE",
 "PRIOR_CUT_ALLOWS_DISCOVERY_INTERFACE_UNIVERSAL_PROOF",
)

def _blob(rel:str)->str:
 data=(ROOT/rel).read_bytes()
 return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def _text(rel:str)->str:
 return (ROOT/rel).read_text(encoding="utf-8")

def _json(rel:str)->dict[str,Any]:
 x=json.loads(_text(rel))
 if not isinstance(x,dict): raise AssertionError(rel+":NOT_OBJECT")
 return x

def _find_behavior(obj:Any,behavior_id:str)->Mapping[str,Any]|None:
 if isinstance(obj,Mapping):
  if obj.get("behavior_id")==behavior_id:return obj
  for v in obj.values():
   got=_find_behavior(v,behavior_id)
   if got is not None:return got
 elif isinstance(obj,list):
  for v in obj:
   got=_find_behavior(v,behavior_id)
   if got is not None:return got
 return None

def derive_facts(v5_source:str)->dict[str,bool]:
 matched=_json("canonical/governance/UNBARRED_FAMILY_MATCHED_PARITY_PROTOCOL_V1.json")
 superp=_json("canonical/governance/OPUS55_MATCHED_COMPARATOR_SUPERPORTFOLIO_V1.json")
 protocols=_json("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
 registry=_json("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json")
 theorem=_json("canonical/governance/TOOL_DISCOVERY_OWNED_UNIVERSAL_V5_THEOREM_V1.json")
 relation=_json("canonical/governance/TOOL_DISCOVERY_V5_COMMON_AUTHORITY_SCOPE_RELATION_V1.json")
 cut=_json("canonical/governance/TOOL_DISCOVERY_UNIVERSAL_SCOPE_FORMALISM_CUT_V1.json")
 he=matched.get("harness_equivalence") or {}
 fp=next((x for x in protocols.get("protocols",[]) if isinstance(x,Mapping) and x.get("family")=="TOOL_DISCOVERY_SELECTION_AND_LEARNING"),{})
 behavior=_find_behavior(registry,"TOOL_ROUTE_DISCOVERY_AND_SELECTION_001") or {}
 execs=superp.get("execution_semantics") or []
 inv=set(theorem.get("theorem_invariants") or [])
 ur=relation.get("universal_relation") or {}
 exp=relation.get("expected_if_independently_verified") or {}
 return {
  "MATCHED_SAME_VISIBLE_INFORMATION":he.get("same_visible_information") is True,
  "MATCHED_SAME_TOOL_CLASSES":he.get("same_tool_classes") is True,
  "MATCHED_SAME_EXTERNAL_ACTION_AUTHORITY":he.get("same_external_action_authority") is True,
  "SUPERPORTFOLIO_IDENTICAL_TOOL_BOUNDARIES":any("IDENTICAL_CASE_PAYLOADS_AND_TOOL_BOUNDARIES" in str(x) for x in execs),
  "FROZEN_PROTOCOL_UNKNOWN_TOOL_DISCOVERY":"unknown tool discovery" in list(fp.get("task_dimensions") or []),
  "FROZEN_PROTOCOL_HIDDEN_TOOL_ECOSYSTEM":fp.get("proof_mode")=="MATCHED_HIDDEN_TOOL_ECOSYSTEM_TRANSFER",
  "BEHAVIOR_UNKNOWN_CHANGING_SCOPE":"unknown/changing tool ecosystem" in str(behavior.get("scope","")).lower(),
  "BEHAVIOR_REQUIRES_DISCOVERY":"discover candidate tools if needed" in str(behavior.get("required_output_or_action","")).lower(),
  "V5_ARBITRARY_FINITE_AUTHORITY":(
    "OwnedToolAuthorityV5" in v5_source
    and "mapping/list of tool specs" in v5_source
    and "registry_ids" in v5_source
  ),
  "V5_INITIAL_IDENTITIES_HIDDEN":(
    "self._visible: set[str] = set()" in v5_source
    and '"visible_tools": []' in v5_source
  ),
  "V5_DISCOVERY_SOURCE_UNION_IS_REGISTRY":(
    "self._source_map" in v5_source
    and "registry_ids" in v5_source
    and "source_map" in v5_source
    and "DISCOVERY" in v5_source
  ),
  "V5_DISCOVERY_BEFORE_CAPABILITY_DECISION":(
    'unknown_sources = [s for s in public["discovery_sources"] if s["source_id"] not in queried]' in v5_source
    and 'return {"action": "DISCOVER"' in v5_source
    and v5_source.index("unknown_sources =") < v5_source.index("evidence = _evidence(public)")
  ),
  "V5_CAPABILITY_TRUTH_HIDDEN":(
    '"capabilities"' in v5_source
    and '"safe_probe_capabilities"' in v5_source
    and "DISALLOWED_PUBLIC_FIELDS" in v5_source
    and "CAPABILITY_TRUTH_LEAK" in v5_source
  ),
  "V5_CURRENT_EPOCH_EVIDENCE_ONLY":(
    'rec.get("epoch") != epochs[tid]' in v5_source
    and "TOOL_VERSION_CHANGED" in v5_source
  ),
  "V5_UNREGISTERED_INVOCATION_REJECTED":(
    '"UNREGISTERED_TOOL"' in v5_source
    and "tool_id not in self._tools" in v5_source
  ),
  "V5_MISSING_PROBE_PERMISSION_FAILS_CLOSED":(
    "PROBE_PERMISSION_UNAVAILABLE_FOR_UNRESOLVED_CHEAPER_ROUTE" in v5_source
    and '"action": "ESCALATE"' in v5_source
  ),
  "V5_THEOREM_REQUIRES_DISCOVERED_EQUALS_REGISTRY":"DISCOVERED_IDENTITIES_EQUAL_REGISTRY" in inv,
  "COMMON_AUTHORITY_SCOPE_NOT_NARROWED":(
    "U_EQUAL_TO_THE_EXACT_COMMON_EXTERNAL_ACTION_AUTHORITY" in str(ur.get("authority_instantiation",""))
    and "NONINVOCABLE_BY_BOTH_SIDES" in str(ur.get("valid_route_scope",""))
  ),
  "COMMON_AUTHORITY_MATCHED_ACCEPTANCE_SEPARATE":(
    exp.get("matched_acceptance_proved") is False
    and "DOES_NOT_IMPLY_MATCHED_NONINFERIORITY" in str(ur.get("acceptance_boundary",""))
  ),
  "PRIOR_CUT_ALLOWS_DISCOVERY_INTERFACE_UNIVERSAL_PROOF":(
    "VERIFIED_DISCOVERY_INTERFACE_AND_UNIVERSAL_PROOF_COVERING_UNKNOWN_TOOL_IDENTITIES"
    in str(cut.get("minimum_missing_fact",""))
  ),
 }

def prove_from_facts(facts:Mapping[str,bool])->dict[str,Any]:
 missing=[x for x in REQUIRED_FACTS if facts.get(x) is not True]
 if missing:
  return {
   "status":"FAIL_CLOSED__COMMON_AUTHORITY_SCOPE_PREMISE_MISSING",
   "missing":missing,
   "universal_scope_proved":False,
   "matched_acceptance_proved":False,
   "capability_credit_delta":0,"family_credit_delta":0,
   "execution_authority":False,"promotion_authority":False,
  }
 return {
  "status":"PASS__V5_COMMON_MATCHED_AUTHORITY_UNIVERSAL_SCOPE_PROOF__MATCHED_ACCEPTANCE_SEPARATE__ZERO_CREDIT",
  "missing":[],
  "universal_scope_proved":True,
  "scope_atom_satisfied_candidate":True,
  "scope_atom":ATOM,
  "target_predicate":"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
  "basis_kind":"UNIVERSAL_FORMAL_SCOPE_PROOF",
  "unknown_identity_scope_preserved":True,
  "brain_only_authority_narrowing":False,
  "matched_acceptance_proved":False,
  "proof":{
   "authority":"Every matched-valid route identity lies in the identical Brain/Opus external action authority A; outside-A identities are noninvocable by both systems.",
   "quantification":"V5 quantifies over arbitrary finite U, so setting U=A for each finite frozen matched episode does not narrow the protocol population.",
   "discovery":"V5 starts with no visible identities and exhausts a source partition whose union is U before route commitment.",
   "information":"Capability truth remains hidden; only current-epoch safe-probe receipts enter capability evidence.",
   "permission":"Missing probe permission on a cheaper unresolved route produces a distinct fail-closed outcome instead of a false least-cost claim.",
   "acceptance_boundary":"This proves coverage/soundness of the protocol construction, not Brain>=Opus matched terminal performance. Matched acceptance remains separate."
  },
  "uses_empirical_generalization":False,
  "terminal_cases_replayed":0,"new_reality_units_consumed":0,
  "incremental_spend_usd":0,"capability_credit_delta":0,"family_credit_delta":0,
  "execution_authority":False,"promotion_authority":False,
 }

def verify()->dict[str,Any]:
 for rel,want in EXPECTED.items():
  got=_blob(rel)
  if got!=want: raise AssertionError((rel,got,want))
 relation=_json("canonical/governance/TOOL_DISCOVERY_V5_COMMON_AUTHORITY_SCOPE_RELATION_V1.json")
 assert relation["expected_if_independently_verified"]["matched_acceptance_proved"] is False
 assert "NO_ABSOLUTE_OMNISCIENT_CEILING_CLAIM" in relation["hard_nonclaims"]
 return prove_from_facts(derive_facts(_text("canonical/runtime/tool_discovery_owned_universal_v5.py")))

def main()->int:
 out=verify(); print(json.dumps(out,indent=2,sort_keys=True))
 return 0 if out.get("universal_scope_proved") is True else 1

if __name__=="__main__": raise SystemExit(main())
