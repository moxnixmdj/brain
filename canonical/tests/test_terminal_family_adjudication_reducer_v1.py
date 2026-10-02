import unittest
from copy import deepcopy
from canonical.runtime.terminal_family_adjudication_reducer_v1 import evaluate_documents, reduce_family_verdicts, REGISTRY, BASIS, DOMINANCE

ACTIVE=[f"B{i}" for i in range(12)]
FAMILIES=[f"F{i}" for i in range(19)]
PREPASS={"F17","F18"}

def fixture():
    rows=[]
    for bid in ACTIVE:
        rows.append({
            "behavior_id":bid,"source":"s","inputs":"i","environment_state":"e",
            "allowed_information":"a","required_output_or_action":"o","success_condition":"s",
            "failure_condition":"f","terminal_consequence":"t","verification_route":"v",
            "dependency_boundary":"d","scope":"x"
        })
    fmap={}
    for i,f in enumerate(FAMILIES[:17]):
        fmap[f]=[ACTIVE[i%12]]
    # Make every active contract load-bearing.
    for i,bid in enumerate(ACTIVE):
        f=FAMILIES[i%17]
        if bid not in fmap[f]: fmap[f].append(bid)
    registry={"active_contracted_residuals":rows,"family_to_residual_contracts":fmap}
    basis={"contracts":[{"behavior_id":x,"proof_state":"TERMINAL_ROUTE_FROZEN_ADMISSIBLE","blockers":[]} for x in ACTIVE]}
    protocols={"protocols":[{"family":f,"status":"PASS" if f in PREPASS else "DEFINED_RESULT_OPEN","proof_mode":"X"} for f in FAMILIES]}
    closure={"families":[{"id":f,"closure_state":"PASS" if f in PREPASS else "OPEN"} for f in FAMILIES]}
    dominance={
        "schema":"PROJECT_BRAIN_GLOBAL_TERMINAL_SURFACE_DOMINANCE_INPUT_V6",
        "authority":{
            "behavioral_contract_registry":{"blob_sha":"reg"},
            "active_terminal_proof_basis":{"blob_sha":"basis"},
        },
        "obligations":[{"id":x,"min_oracle_strength":3} for x in ACTIVE],
        "surface_family_mapping":[
            {"surface":"S","represented_family":"F0","contracts":[fmap["F0"][0]]}
        ],
    }
    receipt={
        "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__EXACT_V6_COMPLETE",
        "exact_brain_blobs":{
            DOMINANCE:"dom",
            "canonical/runtime/proof_route_dominance.py":"compiler",
        },
        "verified":[
            "DOMINANCE_STATUS_COMPLETE",
            "GLOBAL_UNCOVERED_BEHAVIORAL_OBLIGATIONS_ZERO",
            "ALL_14_NAMED_SURFACES_REDUNDANT",
            "ZERO_TERMINAL_CASES_CONSUMED",
        ],
        "terminal_results_observed":0,
        "fresh_terminal_evidence_consumed":0,
    }
    blobs={REGISTRY:"reg",BASIS:"basis",DOMINANCE:"dom","canonical/runtime/proof_route_dominance.py":"compiler"}
    return registry,basis,protocols,closure,dominance,receipt,blobs

class FamilyAdjudicationTests(unittest.TestCase):
    def test_prewave_exact_mapping_passes(self):
        out=evaluate_documents(*fixture()[:-1],current_blobs=fixture()[-1])
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["active_contract_count"],12)
        self.assertEqual(out["mapped_open_family_count"],17)

    def test_orphan_contract_fails_closed(self):
        registry,basis,protocols,closure,dominance,receipt,blobs=fixture()
        for family in registry["family_to_residual_contracts"].values():
            if "B11" in family: family.remove("B11")
        out=evaluate_documents(registry,basis,protocols,closure,dominance,receipt,current_blobs=blobs)
        self.assertFalse(out["pass"])
        self.assertIn("ORPHAN_ACTIVE_CONTRACTS:B11",out["errors"])

    def test_stale_dominance_receipt_fails_closed(self):
        registry,basis,protocols,closure,dominance,receipt,blobs=fixture()
        receipt["exact_brain_blobs"][DOMINANCE]="old"
        out=evaluate_documents(registry,basis,protocols,closure,dominance,receipt,current_blobs=blobs)
        self.assertFalse(out["pass"])
        self.assertIn("DOMINANCE_RECEIPT_INPUT_BLOB_NOT_CURRENT",out["errors"])

    def test_all_contract_passes_yield_19_provisional_passes(self):
        registry,basis,protocols,closure,dominance,receipt,blobs=fixture()
        normalized={
            "valid":True,"terminal_result":True,"contract_count":12,
            "candidate_package_commitment":"c","post_freeze_beacon":"b",
            "contract_verdicts":{
                bid:{"behavior_id":bid,"pass":True,"terminal_result":True}
                for bid in ACTIVE
            },
        }
        out=reduce_family_verdicts(normalized,registry,protocols,closure)
        self.assertTrue(out["valid"],out)
        self.assertTrue(out["all_families_pass"])
        self.assertEqual(out["family_pass_count"],19)
        self.assertEqual(out["family_credit_delta"],0)

    def test_one_contract_failure_propagates_only_to_dependents(self):
        registry,basis,protocols,closure,dominance,receipt,blobs=fixture()
        normalized={
            "valid":True,"terminal_result":True,"contract_count":12,
            "candidate_package_commitment":"c","post_freeze_beacon":"b",
            "contract_verdicts":{
                bid:{"behavior_id":bid,"pass":bid!="B0","terminal_result":True}
                for bid in ACTIVE
            },
        }
        out=reduce_family_verdicts(normalized,registry,protocols,closure)
        self.assertTrue(out["valid"],out)
        self.assertFalse(out["all_families_pass"])
        affected=[f for f,r in out["family_verdicts"].items() if not r["pass"]]
        self.assertTrue(affected)
        self.assertTrue(all("B0" in registry["family_to_residual_contracts"][f] for f in affected))

if __name__=="__main__":
    unittest.main(verbosity=2)
