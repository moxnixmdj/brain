from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from canonical.runtime import contract_native_proof_suites as native
from canonical.runtime import trajectory_failure_typed_ir_candidate_v7 as v7
from canonical.runtime.p1_shared_failure_semantics_batch_v1 import (
    CONTRACT,SURFACES,DIFFICULTIES,derive_seed,normalize_native_case,
    score_typed_result,execute_batch
)
from canonical.runtime.p1_shared_failure_semantics_batch_freeze_verifier_v1 import evaluate

ROOT=Path(__file__).resolve().parents[2]
SPEC=json.loads((ROOT/"canonical/governance/P1_SHARED_FAILURE_SEMANTICS_BATCH_FREEZE_V1.json").read_text())

class P1SharedBatchTests(unittest.TestCase):
    def test_freeze_passes_and_consumes_zero_reality(self):
        out=evaluate(copy.deepcopy(SPEC))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["fresh_reality_units_consumed"],0)
        self.assertFalse(out["execution_authority"])

    def test_fixed_preexecution_self_test_covers_all_surfaces_and_difficulties(self):
        out=execute_batch("11"*32,1)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["case_count"],15)
        self.assertEqual(set(out["surfaces_covered"]),set(SURFACES))
        self.assertEqual(out["difficulty_schedule"],list(DIFFICULTIES))

    def test_seed_derivation_is_surface_and_difficulty_separated(self):
        vals={derive_seed("22"*32,s,d) for s in SURFACES for d in DIFFICULTIES}
        self.assertEqual(len(vals),15)

    def test_oracle_never_enters_v7_payload(self):
        source=native.generate_case(CONTRACT,12345,4)
        typed=normalize_native_case(source,SURFACES[0])
        self.assertNotIn("_oracle",typed)
        self.assertNotIn("repair_candidates",typed["task"])

    def test_direct_vs_derived_is_load_bearing(self):
        source=native.generate_case(CONTRACT,33333,3)
        typed=normalize_native_case(source,SURFACES[1])
        good=v7.solve(copy.deepcopy(typed))
        self.assertTrue(score_typed_result(source,typed,good)["pass"])

        mutated=copy.deepcopy(typed)
        for row in mutated["task"]["trajectory"]:
            for check in row["checks"]:
                if check["pass"] is False and check["failure_semantics"]=="DIRECT_CONTRACT":
                    check["failure_semantics"]="DERIVED_UPSTREAM"
        bad=v7.solve(copy.deepcopy(mutated))
        self.assertFalse(score_typed_result(source,mutated,bad)["pass"])
        self.assertEqual(bad.get("status"),"ESCALATE")

    def test_failed_evidence_is_mandatory(self):
        source=native.generate_case(CONTRACT,44444,2)
        typed=normalize_native_case(source,SURFACES[2])
        for row in typed["task"]["trajectory"]:
            for check in row["checks"]:
                if check["pass"] is False and check["failure_semantics"]=="DIRECT_CONTRACT":
                    check["evidence"]=[]
        out=v7.solve(copy.deepcopy(typed))
        self.assertEqual(out.get("status"),"FAIL_CLOSED")

    def test_prefreeze_spec_cannot_contain_beacon_result(self):
        d=copy.deepcopy(SPEC)
        d["post_freeze_beacon"]["randomness"]="00"*32
        out=evaluate(d)
        self.assertFalse(out["pass"])
        self.assertIn("PREFREEZE_BEACON_RESULT_PRESENT:randomness",out["errors"])

    def test_source_pin_mutation_fails(self):
        d=copy.deepcopy(SPEC)
        key=next(iter(d["exact_source_blobs"]))
        d["exact_source_blobs"][key]="0"*40
        out=evaluate(d)
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("PIN_DRIFT:") for x in out["errors"]))

if __name__=="__main__":
    unittest.main(verbosity=2)
