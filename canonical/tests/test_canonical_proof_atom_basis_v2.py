from __future__ import annotations
import json
from pathlib import Path

from canonical.runtime.canonical_proof_atom_basis_v2 import compile_basis

ROOT=Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

# Synthetic exact partition.
frontier={
    "unresolved_predicates":["A","B","C"],
    "certificates":[
        {"id":"P","target_predicates":["A","B"],"requires":["RA","RB"]},
        {"id":"Q","target_predicates":["C"],"requires":["SHARED"]},
    ],
}
overlay={
    "refinements":[
        {
            "parent_certificate_id":"P",
            "mode":"EXACT_REQUIREMENT_PARTITION",
            "independent_verified":True,
            "verification_receipt":"r://p",
            "children":[
                {"id":"PA","target_predicates":["A"],"requires":["RA"]},
                {"id":"PB","target_predicates":["B"],"requires":["RB"]},
            ],
        }
    ]
}
out=compile_basis(frontier,overlay)
assert out["status"].startswith("PASS"), out
assert out["leaf_atom_count"]==3, out
by_prop={x["proposition"]:x for x in out["atoms"]}
assert by_prop["RA"]["associated_target_predicates"]==["A"]
assert by_prop["RB"]["associated_target_predicates"]==["B"]

# Semantic replacement may change requirement literals but only with an independent receipt.
sem={
    "refinements":[
        {
            "parent_certificate_id":"P",
            "mode":"INDEPENDENTLY_VERIFIED_SEMANTIC_REPLACEMENT",
            "independent_verified":True,
            "verification_receipt":"r://semantic",
            "source_blob_sha":"0"*40,
            "children":[
                {"id":"PA","target_predicates":["A"],"requires":["XA","YA"]},
                {"id":"PB","target_predicates":["B"],"requires":["XB","YB"]},
            ],
        }
    ]
}
s=compile_basis(frontier,sem)
assert s["status"].startswith("PASS"), s
assert s["leaf_atom_count"]==5, s
assert all(x["atom_id"].startswith("PA1:") for x in s["atoms"]), s

bad_sem=json.loads(json.dumps(sem))
bad_sem["refinements"][0].pop("source_blob_sha")
assert compile_basis(frontier,bad_sem)["status"]=="FAIL_CLOSED"

bad=json.loads(json.dumps(overlay))
bad["refinements"][0]["independent_verified"]=False
assert compile_basis(frontier,bad)["status"]=="FAIL_CLOSED"

bad=json.loads(json.dumps(overlay))
bad["refinements"][0]["children"][1]["target_predicates"]=["A"]
assert compile_basis(frontier,bad)["status"]=="FAIL_CLOSED"

bad=json.loads(json.dumps(overlay))
bad["refinements"][0]["children"][1]["requires"]=["NOT_RB"]
assert compile_basis(frontier,bad)["status"]=="FAIL_CLOSED"

# Live projection.
live=compile_basis(
    load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
    load("canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json"),
)
assert live["status"].startswith("PASS"), live
assert live["global_unresolved_predicate_count"]==31, live
assert live["global_certificate_count"]==17, live
assert live["refined_parent_count"]==3, live
assert live["leaf_requirement_occurrence_count"]==40, live
assert live["leaf_atom_count"]==40, live
assert live["exact_duplicate_savings"]==0, live
assert live["max_structural_target_fanout"]==3, live
by_prop={x["proposition"]:x for x in live["atoms"]}
assert by_prop["FRONTIERCODE_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS"]["associated_target_predicates"]==["CODING_FRONTIERCODE_GE_54_4"]
assert by_prop["CURSORBENCH_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS"]["associated_target_predicates"]==["CODING_CURSORBENCH_GE_57_8"]
assert by_prop["PROWORK_AA_BRIEFCASE_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS"]["associated_target_predicates"]==["PROWORK_AA_BRIEFCASE_GE_1822"]
assert by_prop["ARTIFACT_AA_BRIEFCASE_FROZEN_BAR_SCOPE_COMPLETE_STRONGER_PROOF_INDEPENDENT_PASS"]["associated_target_predicates"]==["ARTIFACT_AA_BRIEFCASE_GE_1822"]
assert live["capability_credit_delta"]==0
assert live["family_credit_delta"]==0
assert live["execution_authority"] is False
assert live["promotion_authority"] is False

print("test_canonical_proof_atom_basis_v2: PASS")
