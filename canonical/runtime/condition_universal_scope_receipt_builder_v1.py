"""Build condition-restriction receipts only from universal all-input family proofs."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any
from canonical.runtime.terminal_condition_restriction_cell_compiler_v2 import (
    ConditionRestrictionError, verify_repo_blob,
)

def build_universal_receipts(matrix: dict[str, Any], ledger: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    rows = matrix.get("shared_condition_matrix")
    claims = ledger.get("claims")
    if not isinstance(rows, list):
        raise ConditionRestrictionError("MISSING_SHARED_CONDITION_MATRIX")
    if not isinstance(claims, list):
        raise ConditionRestrictionError("MISSING_ACCEPTANCE_CLAIMS")
    eligible=[]
    rejected=[]
    for c in claims:
        if not isinstance(c, dict):
            continue
        sc=c.get("scope_completeness")
        ok=(
            c.get("state")=="PROVED"
            and c.get("scope_complete") is True
            and c.get("independent_or_objective") is True
            and isinstance(c.get("family"), str) and bool(c.get("family"))
            and isinstance(sc, dict)
            and sc.get("all_admissible_target_inputs_proved") is True
            and sc.get("formal_completeness") is True
            and isinstance(c.get("source_path"), str)
            and isinstance(c.get("source_sha"), str)
            and verify_repo_blob(repo_root, c["source_path"], c["source_sha"])
        )
        if ok:
            eligible.append(c)
        elif c.get("state")=="PROVED" and c.get("family"):
            rejected.append({"predicate_id":c.get("predicate_id"),"family":c.get("family"),"reason":"NOT_UNIVERSAL_ALL_ADMISSIBLE_INPUTS_OR_SOURCE_BLOB_INVALID"})
    proofs=[]
    for c in eligible:
        covered=[]
        for row in rows:
            condition=row.get("condition")
            families=row.get("mapped_family_union")
            if isinstance(condition,str) and isinstance(families,list) and c["family"] in families:
                covered.append(condition)
        if not covered:
            continue
        proofs.append({
            "proof_id":"UNIVERSAL_RESTRICTION::"+str(c.get("predicate_id")),
            "family":c["family"],
            "proof_class":"OBJECTIVE_CEILING",
            "covered_conditions":covered,
            "independent_or_objective":True,
            "scope_complete":True,
            "source_path":c["source_path"],
            "source_sha":c["source_sha"],
            "derivation":"ALL_ADMISSIBLE_TARGET_INPUTS_PROVED__CONDITION_CELL_IS_A_RESTRICTION_OF_THE_FAMILY_INPUT_DOMAIN",
        })
    return {
        "schema":"PROJECT_BRAIN_UNIVERSAL_CONDITION_SCOPE_RECEIPTS_V1",
        "status":"PASS__UNIVERSAL_ALL_INPUT_SCOPE_RESTRICTION_ONLY",
        "eligible_universal_claim_count":len(eligible),
        "emitted_receipt_count":len(proofs),
        "covered_cell_count":sum(len(p["covered_conditions"]) for p in proofs),
        "proofs":proofs,
        "rejected_family_claims":rejected,
        "rules":[
            "NO_RECEIPT_WITHOUT_INDEPENDENT_OR_OBJECTIVE_PROVED_SCOPE_COMPLETE_SOURCE",
            "NO_RECEIPT_WITHOUT_FORMAL_ALL_ADMISSIBLE_TARGET_INPUTS_PROOF",
            "NO_RECEIPT_WITHOUT_EXACT_SOURCE_GIT_BLOB_IDENTITY",
            "CONDITION_COVERAGE_IS_ONLY_MATRIX_RESTRICTION_OF_THE_EXACT_PROVED_FAMILY",
            "NO_NEW_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=".")
    ap.add_argument("--matrix",required=True); ap.add_argument("--matrix-sha",required=True)
    ap.add_argument("--ledger",required=True); ap.add_argument("--ledger-sha",required=True)
    ap.add_argument("--output")
    ns=ap.parse_args()
    root=Path(ns.repo_root).resolve()
    try:
        if not verify_repo_blob(root,ns.matrix,ns.matrix_sha):
            raise ConditionRestrictionError("MATRIX_BLOB_IDENTITY_MISMATCH")
        if not verify_repo_blob(root,ns.ledger,ns.ledger_sha):
            raise ConditionRestrictionError("LEDGER_BLOB_IDENTITY_MISMATCH")
        matrix=json.loads((root/ns.matrix).read_text())
        ledger=json.loads((root/ns.ledger).read_text())
        out=build_universal_receipts(matrix,ledger,root)
        out["matrix_sha"]=ns.matrix_sha; out["ledger_sha"]=ns.ledger_sha
        rendered=json.dumps(out,indent=2,sort_keys=True)+"\n"
        if ns.output: Path(ns.output).write_text(rendered)
        else: print(rendered,end="")
        return 0
    except (OSError,json.JSONDecodeError,ConditionRestrictionError) as exc:
        print(json.dumps({"schema":"PROJECT_BRAIN_UNIVERSAL_CONDITION_SCOPE_RECEIPTS_V1","status":"FAIL_CLOSED","error":str(exc)},indent=2,sort_keys=True))
        return 43

if __name__=="__main__":
    raise SystemExit(main())
