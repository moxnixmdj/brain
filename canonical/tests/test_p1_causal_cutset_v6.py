from __future__ import annotations
import unittest
from canonical.runtime import p1_causal_cutset_v6 as candidate
from canonical.runtime import p1_causal_cutset_v6_proof as proof
from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as v5


class P1CausalCutsetV6Tests(unittest.TestCase):
    def test_reference_cross_product_and_false_earliest_counterexamples(self):
        result=proof.prove(candidate)
        self.assertTrue(result["pass"],result)
        self.assertEqual(result["cross_product_cases"],192)
        self.assertEqual(result["false_earliest_alternative_cases"],6)
        self.assertEqual(result["total_cases"],198)

    def test_scope_is_first_class_and_executable(self):
        for domain in proof.DOMAINS:
            c=proof.generate_case(domain,"SCOPE","DELAYED")
            out=candidate.solve(c)
            self.assertEqual(out["status"],"IDENTIFIED")
            self.assertEqual(out["mechanism_classes"],["SCOPE"])
            self.assertTrue(proof.score(c["task"],out)["pass"])

    def test_interaction_requires_both_repairs(self):
        c=proof.generate_case("TOOL_API","SCOPE","INTERACTION")
        out=candidate.solve(c)
        self.assertEqual(out["status"],"INTERACTION")
        s=set(out["minimal_repair_check_ids"])
        self.assertEqual(len(s),2)
        self.assertTrue(proof.reference_success(c["task"],s))
        for cid in s:
            self.assertFalse(proof.reference_success(c["task"],s-{cid}))

    def test_alternative_causes_preserve_ambiguity(self):
        c=proof.generate_case("BROWSER","SCOPE","AMBIGUOUS")
        out=candidate.solve(c)
        self.assertEqual(out["status"],"AMBIGUOUS")
        self.assertEqual(len(out["minimal_rescue_sets"]),2)
        self.assertTrue(proof.score(c["task"],out)["pass"])

    def test_false_earliest_scope_violation_is_not_causal(self):
        c=proof.false_earliest_alternative_case("CODE","SCOPE","STATE_TRANSITION")
        old=v5.solve(c)
        self.assertEqual(old["status"],"IDENTIFIED")
        self.assertEqual(old["cause_action_ids"],["A1"])
        self.assertEqual(old["mechanism_classes"],["SCOPE"])
        out=candidate.solve(c)
        self.assertEqual(out["status"],"IDENTIFIED")
        self.assertEqual(out["cause_action_ids"],["A4"])
        self.assertEqual(out["mechanism_classes"],["STATE_TRANSITION"])
        self.assertEqual(out["minimal_repair_check_ids"],["A4:STATE_TRANSITION"])
        self.assertTrue(proof.score(c["task"],out)["pass"])

    def test_empty_failed_evidence_fails_closed(self):
        c=proof.generate_case("RESEARCH","PROVENANCE","SINGLE")
        for r in c["task"]["trajectory"]:
            for chk in r["checks"]:
                if chk["pass"] is False:
                    chk["evidence"]=[]
        out=candidate.solve(c)
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_unsupported_large_repair_space_escalates(self):
        rows=[]
        for i in range(candidate.MAX_REPAIR_ATOMS+1):
            aid=f"A{i}"
            rows.append(proof.row(aid,writes=[f"r{i}"],failed_kind="INVARIANT"))
        c={"task":{"trajectory":rows,"terminal_failed_resources":[f"r{candidate.MAX_REPAIR_ATOMS}"]}}
        out=candidate.solve(c)
        self.assertEqual(out["status"],"ESCALATE")
        self.assertEqual(out["reason"],"REPAIR_SPACE_EXCEEDS_EXACT_BOUND")


if __name__=="__main__":
    unittest.main(verbosity=2)
