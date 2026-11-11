"""Information-theoretic observability lower bound for Tool Discovery.

If two or more hidden worlds are identical under the exact allowed observation
but require mutually incompatible least-cost valid terminal actions, no
deterministic policy that sees only that observation can be universally correct.
This establishes only the lower bound / routing fact. It grants no acceptance.
"""
from __future__ import annotations
import hashlib,json
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_OBSERVABILITY_LOWER_BOUND_V1"

def _canon(v:Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def _sha(v:Any)->str:
    return "sha256:"+hashlib.sha256(_canon(v)).hexdigest()

def _fail(reason:str)->dict[str,Any]:
    return {
      "schema":SCHEMA,"status":"FAIL_CLOSED","reason":reason,
      "universal_deterministic_valid_and_least_cost_proof_impossible":False,
      "matched_or_additional_information_required":True,
      "capability_credit_delta":0,"family_credit_delta":0,
      "execution_authority":False,"promotion_authority":False,
    }

def prove(equivalence_class:Mapping[str,Any])->dict[str,Any]:
    obs=equivalence_class.get("public_observation")
    if not isinstance(obs,Mapping):
        return _fail("PUBLIC_OBSERVATION_NOT_OBJECT")
    allowed=equivalence_class.get("allowed_information_fields")
    if not isinstance(allowed,list) or not allowed:
        return _fail("ALLOWED_INFORMATION_FIELDS_NOT_LIST")
    allowed_names=[str(x) for x in allowed if isinstance(x,str) and x]
    if len(allowed_names)!=len(allowed) or len(set(allowed_names))!=len(allowed_names):
        return _fail("ALLOWED_INFORMATION_FIELDS_INVALID_OR_DUPLICATE")
    if set(allowed_names)!=set(obs):
        return _fail("PUBLIC_OBSERVATION_FIELDS_DO_NOT_MATCH_ALLOWED_INFORMATION")
    worlds=equivalence_class.get("hidden_worlds")
    if not isinstance(worlds,list) or len(worlds)<2:
        return _fail("AT_LEAST_TWO_HIDDEN_WORLDS_REQUIRED")

    observation_digest=_sha(obs)
    least_sets=[]
    valid_sets=[]
    hidden_digests=set()
    for i,w in enumerate(worlds):
        if not isinstance(w,Mapping):
            return _fail("HIDDEN_WORLD_NOT_OBJECT:"+str(i))
        if str(w.get("public_observation_sha256") or "")!=observation_digest:
            return _fail("WORLD_PUBLIC_OBSERVATION_MISMATCH:"+str(i))
        hidden=w.get("hidden_state")
        if not isinstance(hidden,Mapping):
            return _fail("HIDDEN_STATE_NOT_OBJECT:"+str(i))
        hd=_sha(hidden)
        if hd in hidden_digests:
            return _fail("DUPLICATE_HIDDEN_WORLD:"+str(i))
        hidden_digests.add(hd)
        valid=w.get("valid_terminal_actions")
        least=w.get("least_cost_valid_terminal_actions")
        if not isinstance(valid,list) or not valid:
            return _fail("VALID_TERMINAL_ACTIONS_EMPTY:"+str(i))
        if not isinstance(least,list) or not least:
            return _fail("LEAST_COST_VALID_ACTIONS_EMPTY:"+str(i))
        vs={str(x) for x in valid if str(x)}
        ls={str(x) for x in least if str(x)}
        if not ls or not ls<=vs:
            return _fail("LEAST_COST_ACTION_NOT_VALID_SUBSET:"+str(i))
        valid_sets.append(vs); least_sets.append(ls)

    common_valid=set.intersection(*valid_sets)
    common_least=set.intersection(*least_sets)
    valid_impossible=not common_valid
    least_cost_impossible=not common_least
    if not (valid_impossible or least_cost_impossible):
        return {
          "schema":SCHEMA,
          "status":"NO_LOWER_BOUND__COMMON_TERMINAL_ACTION_EXISTS",
          "public_observation_sha256":observation_digest,
          "common_valid_terminal_actions":sorted(common_valid),
          "common_least_cost_terminal_actions":sorted(common_least),
          "universal_deterministic_valid_and_least_cost_proof_impossible":False,
          "matched_or_additional_information_required":False,
          "capability_credit_delta":0,"family_credit_delta":0,
          "execution_authority":False,"promotion_authority":False,
        }

    return {
      "schema":SCHEMA,
      "status":"PASS__OBSERVATIONAL_INDISINGUISHABILITY_LOWER_BOUND",
      "public_observation_sha256":observation_digest,
      "hidden_world_count":len(worlds),
      "common_valid_terminal_actions":sorted(common_valid),
      "common_least_cost_terminal_actions":sorted(common_least),
      "universal_valid_route_impossible":valid_impossible,
      "universal_global_least_cost_impossible":least_cost_impossible,
      "universal_deterministic_valid_and_least_cost_proof_impossible":True,
      "matched_or_additional_information_required":True,
      "proof":(
        "A deterministic policy restricted to the declared public observation "
        "must emit the same terminal action in every hidden world in this "
        "equivalence class. Because no single terminal action is least-cost-valid "
        "in every world, universal valid-plus-global-least-cost correctness is "
        "impossible without additional information."
      ),
      "terminal_results_replayed":0,"new_reality_units_consumed":0,
      "incremental_spend_usd":0,"capability_credit_delta":0,
      "family_credit_delta":0,"execution_authority":False,
      "promotion_authority":False,
    }
