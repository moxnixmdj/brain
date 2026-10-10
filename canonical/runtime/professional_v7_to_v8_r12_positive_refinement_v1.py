"""V7 -> V8 R12 positive-route refinement verifier V1.

Proves a narrow structural fact only:
  every V8 positive final route retains the V7 authenticated-step preconditions
  and adds stricter final totality + exact R12 semantic binding.

This is NOT cross-subject property authority. It authorizes reuse-oriented
reverification of preserved V7 clauses while explicitly excluding existential
nonvacuity C8 and any property/quality/terminal credit.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any

from canonical.runtime import professional_quality_p1_router_v7 as v7
from canonical.runtime import professional_quality_p1_router_v8 as v8
from canonical.runtime import professional_step_binding_authority_v1 as a1
from canonical.runtime import professional_step_binding_authority_v2 as a2

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_V7_TO_V8_R12_POSITIVE_REFINEMENT_V1"
V7_PATH="canonical/runtime/professional_quality_p1_router_v7.py"
V7_BLOB="765b5994c2fcb5eb669b5fd0d989cc79c1609908"
V8_PATH="canonical/runtime/professional_quality_p1_router_v8.py"
V8_BLOB="48c6839071b8de1309f87b0df1803a9eb29f0e13"
A1_PATH="canonical/runtime/professional_step_binding_authority_v1.py"
A1_BLOB="27f3c137dae7f00925083a0824d008c2b4d10f0a"
A2_PATH="canonical/runtime/professional_step_binding_authority_v2.py"
A2_BLOB="a3df22c695f8b204ab7802cc4c8e21efbed49af2"
R12_RECON_PATH="canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_TRUTH_RECONCILIATION_20261010_V3.json"
R12_RECON_BLOB="56a5f85e6133661dd7afbc8fc5041ad799f0736f"
PRESERVED_CLAUSES=(
 "R12C1_ASSUMPTION_GUARANTEE_COMPOSITION",
 "R12C2_SAME_SUBJECT_ROOT_CONJUNCTION",
 "R12C3_ABSTRACTION_SOUNDNESS",
 "R12C4_INDEPENDENT_DEFEATER_SEARCH",
 "R12C5_COVERAGE_ACCOUNTING",
 "R12C6_PROOF_SEARCH_HONESTY",
 "R12C7_META_CONTROLLER_FALSIFICATION",
)
NONTRANSPORTED_CLAUSE="R12C8_NONVACUITY"

def _blob(p:Path)->str:
    d=p.read_bytes()
    return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _base(passed:bool,status:str,**extra:Any)->dict[str,Any]:
    return {
      "schema":SCHEMA,"pass":passed,"status":status,
      "positive_route_refinement_proved":False,
      "preserved_clause_reverification_admissible":False,
      "c8_nonvacuity_transport_proved":False,
      "cross_subject_property_authority_transport":False,
      "semantic_property_truth_authority":False,
      "quality_authority":False,"acceptance_authority":False,
      "promotion_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
    }

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return _base(False,"FAIL_CLOSED",reason=reason,**extra)

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    pins={V7_PATH:V7_BLOB,V8_PATH:V8_BLOB,A1_PATH:A1_BLOB,A2_PATH:A2_BLOB,R12_RECON_PATH:R12_RECON_BLOB}
    for rel,expected in pins.items():
        p=root/rel
        if not p.is_file() or p.is_symlink(): return _fail("PIN_MISSING",path=rel)
        got=_blob(p)
        if got!=expected: return _fail("PIN_BLOB_DRIFT",path=rel,observed_blob=got)

    if tuple(v7.AUTHENTICATED_STEPS)!=tuple(v8.AUTHENTICATED_STEPS):
        return _fail("AUTHENTICATED_STEP_SET_DRIFT")
    if v7.BEHAVIOR_ID!=v8.BEHAVIOR_ID:
        return _fail("BEHAVIOR_ID_DRIFT")
    if v8.FINAL_STEP!=a2.FINAL_STEP or v8.FINAL_STEP!=v7.AUTHENTICATED_STEPS[-1]:
        return _fail("FINAL_STEP_ID_DRIFT")
    if a2.base is not a1:
        return _fail("V2_DOES_NOT_WRAP_V1_MODULE")

    v2_text=(root/A2_PATH).read_text(encoding="utf-8")
    required_v2=(
      "prior=base.authenticate_step_binding(",
      "if prior.get(\"pass\") is not True:",
      "if step_id!=FINAL_STEP:",
      "\"v1_authenticated\":True",
      "if outcome==\"ABSTAIN\":",
      "\"positive_certification_authorized\":True",
      "\"material_totality_proved\":True",
    )
    for anchor in required_v2:
        if anchor not in v2_text:return _fail("V2_REFINEMENT_ANCHOR_MISSING:"+anchor)

    v8_text=(root/V8_PATH).read_text(encoding="utf-8")
    required_v8=(
      'if outcome=="ABSTAIN":',
      'if outcome!="POSITIVE_CERTIFICATE":',
      'if result.get("positive_certification_authorized") is not True:',
      'if result.get("material_totality_proved") is not True:',
      '_authenticate_r12_totality_semantics(bindings.get(step),root=root)',
      '"semantic_property_claim_id":R12_PROPERTY_CLAIM_ID',
      '"semantic_scope_claim_id":R12_SCOPE_CLAIM_ID',
      '"semantic_obligation":R12_MATERIAL_OBLIGATION',
    )
    for anchor in required_v8:
        if anchor not in v8_text:return _fail("V8_STRICTER_POSITIVE_ANCHOR_MISSING:"+anchor)

    recon=json.loads((root/R12_RECON_PATH).read_text(encoding="utf-8"))
    states={row.get("id"):row.get("state") for row in recon.get("clause_state",[]) if isinstance(row,dict)}
    if any(states.get(cid)!="VERIFIED_CURRENT" for cid in PRESERVED_CLAUSES):
        return _fail("V7_PRESERVED_CLAUSE_PREMISE_NOT_CURRENT",clause_states=states)
    if states.get(NONTRANSPORTED_CLAUSE)!="VERIFIED_CURRENT":
        return _fail("V7_C8_PREMISE_NOT_CURRENT")

    return _base(
      True,
      "PASS__V8_POSITIVE_ROUTES_STRICTLY_REFINE_V7_AUTHENTICATED_ROUTE_PRECONDITIONS__C8_EXCLUDED",
      positive_route_refinement_proved=True,
      v1_authentication_preserved_for_all_steps=True,
      v2_nonfinal_semantics_preserve_v1=True,
      v8_final_positive_adds_material_totality=True,
      v8_final_positive_adds_exact_r12_semantic_binding=True,
      authenticated_step_count=len(v8.AUTHENTICATED_STEPS),
      v7_current_preserved_clause_count=len(PRESERVED_CLAUSES),
      preserved_clause_ids=list(PRESERVED_CLAUSES),
      preserved_clause_reverification_admissible=True,
      c8_nonvacuity_transport_proved=False,
      c8_reason="EXISTENTIAL_POSITIVE_ROUTE_MAY_BE_REMOVED_BY_STRICTER_V8_FINAL_TOTALITY_GATE",
      cross_subject_property_authority_transport=False,
      semantic_property_truth_authority=False,
      exact_next="REVERIFY_PRESERVED_C1_TO_C7_ON_V8_SUBJECT__PRODUCE_ONE_REAL_V8_POSITIVE_TOTALITY_WITNESS_FOR_C8__THEN_R4",
    )
