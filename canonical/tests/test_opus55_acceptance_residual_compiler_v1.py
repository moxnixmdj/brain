from __future__ import annotations
import unittest

from canonical.runtime.opus55_acceptance_residual_compiler_v1 import evaluate


class AcceptanceResidualCompilerTests(unittest.TestCase):
    def fixture(self):
        families=[f"F{i}" for i in range(17)]
        registry={
            "residual_families":families,
            "predicates":[
                {"id":f"P{i}","family":family,"kind":"PUBLIC_FIXED_BAR","acceptance":"x"}
                for i,family in enumerate(families)
            ],
        }
        evidence={"claims":[]}
        comparator={"exact_opus55_zero_incremental_route":False}
        return registry,evidence,comparator

    def test_open_public_predicates_are_authorized_and_fail_closed(self):
        out=evaluate(*self.fixture())
        self.assertFalse(out["pass"])
        self.assertEqual(out["open_predicate_count"],17)
        self.assertEqual(len(out["authorized_actions"]),17)
        self.assertFalse(out["terminal_promotion_allowed"])

    def test_matched_predicate_without_zero_cost_comparator_is_blocked(self):
        registry,evidence,comparator=self.fixture()
        registry["predicates"][0]["kind"]="MATCHED_NONINFERIORITY"
        out=evaluate(registry,evidence,comparator)
        self.assertFalse(out["pass"])
        self.assertEqual(out["blocked_predicate_count"],1)
        self.assertEqual(out["blocker_certificates"][0]["predicate_id"],"P0")
        self.assertNotIn("P0",{a["predicate_id"] for a in out["authorized_actions"]})

    def test_bound_dominance_can_close_matched_predicate_without_comparator(self):
        registry,evidence,comparator=self.fixture()
        registry["predicates"][0]["kind"]="MATCHED_NONINFERIORITY"
        evidence["claims"].append({
            "predicate_id":"P0",
            "state":"PROVED",
            "proof_kind":"BOUND_DOMINANCE",
            "source_path":"canonical/verification/p0.json",
            "source_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "independent_or_objective":True,
            "scope_complete":True,
            "brain_lower_bound":1.0,
            "opus_upper_bound":1.0,
        })
        out=evaluate(registry,evidence,comparator)
        p0=next(x for x in out["predicates"] if x["predicate_id"]=="P0")
        self.assertEqual(p0["state"],"PROVED")
        self.assertEqual(out["blocked_predicate_count"],0)

    def test_invalid_bound_dominance_fails_closed(self):
        registry,evidence,comparator=self.fixture()
        evidence["claims"].append({
            "predicate_id":"P0",
            "state":"PROVED",
            "proof_kind":"BOUND_DOMINANCE",
            "source_path":"canonical/verification/p0.json",
            "source_sha":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "independent_or_objective":True,
            "scope_complete":True,
            "brain_lower_bound":0.8,
            "opus_upper_bound":0.9,
        })
        out=evaluate(registry,evidence,comparator)
        self.assertIn("BOUND_DOMINANCE_NOT_PROVED:P0",out["errors"])
        p0=next(x for x in out["predicates"] if x["predicate_id"]=="P0")
        self.assertEqual(p0["state"],"OPEN")

    def test_all_predicates_proved_is_only_promotion_path(self):
        registry,evidence,comparator=self.fixture()
        for i in range(17):
            evidence["claims"].append({
                "predicate_id":f"P{i}",
                "state":"PROVED",
                "proof_kind":"PUBLIC_BAR_RESULT",
                "source_path":f"canonical/verification/p{i}.json",
                "source_sha":f"{i:040x}"[-40:],
                "independent_or_objective":True,
                "scope_complete":True,
                "measured_value":1.0,
                "threshold":1.0,
            })
        out=evaluate(registry,evidence,comparator)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["terminal_promotion_allowed"])
        self.assertEqual(out["proved_predicate_count"],17)
        self.assertEqual(out["authorized_actions"],[])

    def test_unbound_proof_claim_is_rejected(self):
        registry,evidence,comparator=self.fixture()
        evidence["claims"].append({
            "predicate_id":"P0",
            "state":"PROVED",
            "proof_kind":"RECEIPT",
            "independent_or_objective":True,
            "scope_complete":True,
        })
        out=evaluate(registry,evidence,comparator)
        self.assertIn("UNBOUND_EVIDENCE:P0",out["errors"])
        p0=next(x for x in out["predicates"] if x["predicate_id"]=="P0")
        self.assertEqual(p0["state"],"OPEN")


if __name__=="__main__":
    unittest.main(verbosity=2)
