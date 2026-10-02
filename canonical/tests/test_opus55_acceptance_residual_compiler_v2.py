from __future__ import annotations
import unittest

from canonical.runtime.opus55_acceptance_residual_compiler_v2 import evaluate


class AcceptanceResidualCompilerV2Tests(unittest.TestCase):
    def fixture(self):
        families=[f"F{i}" for i in range(17)]
        registry={
            "residual_families":families,
            "predicates":[
                {"id":f"P{i}","family":family,"kind":"PUBLIC_FIXED_BAR","surface":f"S{i}","acceptance":"x"}
                for i,family in enumerate(families)
            ],
        }
        evidence={"claims":[],"saturation":{"status":"REQUIRED"}}
        comparator={"exact_opus55_zero_incremental_route":False}
        readiness={"rows":[{"surface":f"S{i}","score_producing_route_ready":True} for i in range(17)]}
        return registry,evidence,comparator,readiness

    def test_saturation_is_only_authorized_action_before_new_reality(self):
        out=evaluate(*self.fixture())
        self.assertFalse(out["receipt_saturation_complete"])
        self.assertEqual([a["action_id"] for a in out["authorized_actions"]],["ACTION::SATURATE_EXISTING_RECEIPTS"])
        self.assertEqual(out["open_predicate_count"],17)

    def test_public_bar_blocked_when_route_not_ready_after_saturation(self):
        registry,evidence,comparator,readiness=self.fixture()
        evidence["saturation"]={"status":"COMPLETE","source_snapshot_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}
        readiness["rows"][0]["score_producing_route_ready"]=False
        out=evaluate(registry,evidence,comparator,readiness)
        p0=next(x for x in out["predicates"] if x["predicate_id"]=="P0")
        self.assertEqual(p0["state"],"EXTERNAL_BLOCKED")
        self.assertTrue(any(b["predicate_id"]=="P0" for b in out["blocker_certificates"]))

    def test_ready_public_bar_is_authorized_after_saturation(self):
        registry,evidence,comparator,readiness=self.fixture()
        evidence["saturation"]={"status":"COMPLETE","source_snapshot_sha":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}
        out=evaluate(registry,evidence,comparator,readiness)
        self.assertIn("P0",{a.get("predicate_id") for a in out["authorized_actions"]})

    def test_matched_predicate_blocked_without_comparator(self):
        registry,evidence,comparator,readiness=self.fixture()
        registry["predicates"][0].pop("surface")
        registry["predicates"][0]["kind"]="MATCHED_NONINFERIORITY"
        evidence["saturation"]={"status":"COMPLETE","source_snapshot_sha":"cccccccccccccccccccccccccccccccccccccccc"}
        out=evaluate(registry,evidence,comparator,readiness)
        p0=next(x for x in out["predicates"] if x["predicate_id"]=="P0")
        self.assertEqual(p0["state"],"EXTERNAL_BLOCKED")

    def test_bound_dominance_closes_matched_without_comparator(self):
        registry,evidence,comparator,readiness=self.fixture()
        registry["predicates"][0].pop("surface")
        registry["predicates"][0]["kind"]="MATCHED_NONINFERIORITY"
        evidence["saturation"]={"status":"COMPLETE","source_snapshot_sha":"dddddddddddddddddddddddddddddddddddddddd"}
        evidence["claims"].append({
            "predicate_id":"P0",
            "state":"PROVED",
            "proof_kind":"BOUND_DOMINANCE",
            "source_path":"canonical/verification/p0.json",
            "source_sha":"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
            "independent_or_objective":True,
            "scope_complete":True,
            "brain_lower_bound":1.0,
            "opus_upper_bound":1.0,
        })
        out=evaluate(registry,evidence,comparator,readiness)
        p0=next(x for x in out["predicates"] if x["predicate_id"]=="P0")
        self.assertEqual(p0["state"],"PROVED")

    def test_invalid_bound_dominance_is_rejected(self):
        registry,evidence,comparator,readiness=self.fixture()
        evidence["saturation"]={"status":"COMPLETE","source_snapshot_sha":"ffffffffffffffffffffffffffffffffffffffff"}
        evidence["claims"].append({
            "predicate_id":"P0",
            "state":"PROVED",
            "proof_kind":"BOUND_DOMINANCE",
            "source_path":"canonical/verification/p0.json",
            "source_sha":"1111111111111111111111111111111111111111",
            "independent_or_objective":True,
            "scope_complete":True,
            "brain_lower_bound":0.8,
            "opus_upper_bound":0.9,
        })
        out=evaluate(registry,evidence,comparator,readiness)
        self.assertIn("BOUND_DOMINANCE_NOT_PROVED:P0",out["errors"])
        p0=next(x for x in out["predicates"] if x["predicate_id"]=="P0")
        self.assertEqual(p0["state"],"OPEN")

    def test_all_proved_is_only_terminal_promotion_path(self):
        registry,evidence,comparator,readiness=self.fixture()
        evidence["saturation"]={"status":"COMPLETE","source_snapshot_sha":"2222222222222222222222222222222222222222"}
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
        out=evaluate(registry,evidence,comparator,readiness)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["terminal_promotion_allowed"])
        self.assertEqual(out["authorized_actions"],[])


if __name__=="__main__":
    unittest.main(verbosity=2)
