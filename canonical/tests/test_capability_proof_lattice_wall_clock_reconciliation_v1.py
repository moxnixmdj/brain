import importlib.util, json, pathlib, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

P=ROOT/"canonical/runtime/capability_proof_compression_optimizer_v1.py"
S=importlib.util.spec_from_file_location("wallopt",P)
wallopt=importlib.util.module_from_spec(S); S.loader.exec_module(wallopt)

class CapabilityProofLatticeWallClockReconciliationV1Tests(unittest.TestCase):
    def test_current_frontier_binds_v2_then_wall_clock_optimizer(self):
        f=load("canonical/governance/CURRENT_BENCHMARK_CAPABILITY_DOMINANCE_FRONTIER.json")
        self.assertIn("PROOF_LATTICE_V2",f["status"])
        p=f["post_lattice_optimization"]
        self.assertIn("ALREADY_ADMISSIBLE",p["role"])
        self.assertFalse(p["proof_credit_authority"])
        self.assertEqual(p["runtime"],"canonical/runtime/capability_proof_compression_optimizer_v1.py")

    def test_two_ledgers_are_materialized_and_disjoint_in_meaning(self):
        c=load("canonical/governance/CURRENT_CAPABILITY_COMPARISON_LEDGER.json")
        b=load("canonical/governance/CURRENT_BRANDED_BENCHMARK_RECEIPT_LEDGER.json")
        self.assertEqual(c["authority_law"],"canonical/laws/BENCHMARK_MEASUREMENT_VS_CAPABILITY_PROOF_LAW_V2.md")
        self.assertEqual(b["authority_law"],c["authority_law"])
        self.assertEqual({r["benchmark_id"] for r in c["rows"]},{r["benchmark_id"] for r in b["rows"]})
        self.assertTrue(all(r["capability_credit"]==0 for r in c["rows"]))
        self.assertTrue(all(r["benchmark_score_credit"]==0 for r in b["rows"]))

    def test_heuristic_projection_closes_neither_ledger(self):
        c=load("canonical/governance/CURRENT_CAPABILITY_COMPARISON_LEDGER.json")
        b=load("canonical/governance/CURRENT_BRANDED_BENCHMARK_RECEIPT_LEDGER.json")
        self.assertEqual(c["closed_comparison_count"],0)
        self.assertEqual(b["closed_receipt_count"],0)
        self.assertTrue(all(r["state"]=="OPEN_UNBOUND_RELATION" for r in c["rows"]))

    def test_shared_fast_certificate_beats_separate_routes(self):
        req=[{"id":"C1"},{"id":"C2"},{"id":"C3"}]
        opts=[
            {"id":"one","covers":["C1"],"wall_clock_cost":4},
            {"id":"two","covers":["C2"],"wall_clock_cost":4},
            {"id":"three","covers":["C3"],"wall_clock_cost":4},
            {"id":"shared","covers":["C1","C2","C3"],"wall_clock_cost":6,"reusable_coverage_bonus":5},
        ]
        out=wallopt.optimize(req,opts)
        self.assertTrue(out["complete_cover"])
        self.assertEqual(out["selected_evidence_ids"],["shared"])
        self.assertFalse(out["credit_authority"])

    def test_external_wait_is_not_runnable_proof_cover(self):
        out=wallopt.optimize(
            [{"id":"C"}],
            [{"id":"wait","covers":["C"],"wall_clock_cost":0,"waits_for_external_event":True}],
        )
        self.assertFalse(out["complete_cover"])
        self.assertEqual(out["uncovered_required_propositions"],["C"])
        self.assertEqual(out["rejected"][0]["reason"],"EXTERNAL_WAIT_NOT_EXECUTABLE_NOW")

    def test_active_v2_law_keeps_wall_clock_primary_and_scores_separate(self):
        law=(ROOT/"canonical/laws/BENCHMARK_MEASUREMENT_VS_CAPABILITY_PROOF_LAW_V2.md").read_text(encoding="utf-8")
        self.assertIn("minimum wall-clock time to the required proposition set",law)
        self.assertIn("B, C, and O are independent",law)
        self.assertIn("A benchmark-native run receives no scheduling privilege",law)

if __name__=="__main__":
    unittest.main(verbosity=2)
