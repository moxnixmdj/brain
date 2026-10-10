"""Verify the exact synthesis proof-obligation residual under the hardened delta compiler."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping
from canonical.runtime.proof_obligation_delta_compiler_v1 import compile_delta

ROOT=Path(__file__).resolve().parents[2]
INPUT=ROOT/"canonical/governance/OPUS55_SYNTHESIS_PROOF_OBLIGATION_DELTA_INPUT_V1.json"

def load()->Mapping[str,Any]:
    return json.loads(INPUT.read_text(encoding="utf-8"))

def evaluate(doc:Mapping[str,Any])->dict[str,Any]:
    raw=compile_delta(doc)
    expected=doc.get("expected_residual")
    errors=[]
    if raw.get("status")!="RESIDUAL_DELTA_OPEN": errors.append("COMPILER_STATUS_NOT_RESIDUAL_OPEN")
    if raw.get("scope_relation") is not None: errors.append("UNPROVED_SCOPE_RELATION_INFERRED")
    if not isinstance(expected,Mapping) or raw.get("residual")!=expected: errors.append("EXACT_RESIDUAL_MISMATCH")
    if raw.get("covered",{}).get("atoms")!=sorted([
        "dimension:audience_adaptation",
        "dimension:claim_to_source_fidelity",
        "dimension:compression_without_decision_relevant_loss",
        "dimension:format_and_style_constraints",
        "dimension:required_evidence_coverage",
        "dimension:uncertainty_and_disagreement_preservation",
        "metric:required_claim_coverage",
    ]): errors.append("COVERED_ATOM_SET_MISMATCH")
    receipts=raw.get("binding_receipts_used",[])
    if receipts!=["canonical/verification/OPUS55_SYNTHESIS_WITNESS_TARGET_BINDING_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json@64ad40c1c10bd01e4c0f4418fac29efafea838fc"]:
        errors.append("CONTENT_ADDRESSED_RECEIPT_SET_MISMATCH")
    if errors:
        return {"schema":"PROJECT_BRAIN_SYNTHESIS_PROOF_OBLIGATION_DELTA_APPLICATION_VERDICT_V1","status":"FAIL_CLOSED","pass":False,"errors":sorted(set(errors)),"raw_compiler_result":raw,"capability_credit_delta":0,"family_credit_delta":0,"new_reality_units_consumed":0}
    return {
      "schema":"PROJECT_BRAIN_SYNTHESIS_PROOF_OBLIGATION_DELTA_APPLICATION_VERDICT_V1",
      "status":"PASS__EXACT_HARDENED_SYNTHESIS_RESIDUAL_NORMAL_FORM__ZERO_CREDIT",
      "pass":True,
      "errors":[],
      "target_predicate_id":"SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",
      "covered_atom_count":7,
      "scope_relation":None,
      "residual":raw["residual"],
      "binding_receipts_used":raw["binding_receipts_used"],
      "execution_authority":False,
      "promotion_authority":False,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "new_reality_units_consumed":0
    }

def main()->int:
    out=evaluate(load())
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())
