import unittest

from canonical.runtime import finance_margin_context_proof_v1 as p
from canonical.runtime.finance_margin_context_truth_certificate_v1 import evaluate


class ProofTests(unittest.TestCase):
    def test_interest_rate_add_on(self):
        text="The margin is added to the specified index rate."
        out=p.verify_context(text,source_id="doc:rate")
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["proved_atom_ids"],[p.ATOM_RATE])
        self.assertEqual(out["authority_binding"]["source_git_blob_sha"],p.FIBO_SOURCE_GIT_BLOB_SHA)
        self.assertFalse(out["semantic_identity_authority"])

    def test_index_rate_plus_margin(self):
        text="The benchmark rate plus the margin determines the fully indexed rate."
        out=p.verify_context(text,source_id="doc:rate")
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["proved_atom_ids"],[p.ATOM_RATE])

    def test_collateral_broker_deposit(self):
        text=(
            "The margin is the amount of collateral a customer deposits with a "
            "broker when borrowing from the broker to buy securities."
        )
        out=p.verify_context(text,source_id="doc:broker")
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["proved_atom_ids"],[p.ATOM_COLLATERAL])
        self.assertEqual(out["authority_binding"]["release_sha256"],p.OEWN_RELEASE_SHA256)

    def test_gross_profit_formula(self):
        text="The margin is the net sales minus the cost of goods and services sold."
        out=p.verify_context(text,source_id="doc:profit")
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["proved_atom_ids"],[p.ATOM_GROSS_PROFIT])

    def test_bare_margin_increased_stays_open(self):
        out=p.verify_context("Margin increased.",source_id="doc:bare")
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"OPEN__NO_BOUND_FINANCE_MARGIN_CONTEXT_FACT")
        self.assertEqual(out["proved_atom_ids"],[])

    def test_negated_rate_statement_does_not_match(self):
        out=p.verify_context(
            "The margin is not added to the specified index rate.",
            source_id="doc:negated",
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["proved_atom_ids"],[])

    def test_multiple_signatures_fail_closed(self):
        text=(
            "The margin is added to the specified index rate. "
            "The margin is the net sales minus the cost of goods sold."
        )
        out=p.verify_context(text,source_id="doc:ambiguous")
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(
            set(out["matched_atom_ids"]),
            {p.ATOM_RATE,p.ATOM_GROSS_PROFIT},
        )


class TruthTests(unittest.TestCase):
    def payload(self,text,target):
        return {
            "truth_kind":"FINANCE_MARGIN_CONTEXT_ATOM",
            "predicate_id":"caller-label",
            "source_text":text,
            "source_id":"doc:A",
            "start":0,
            "end":len(text),
            "target_atom_id":target,
        }

    def test_positive_target_true(self):
        text="The margin is added to the specified index rate."
        out=evaluate(self.payload(text,p.ATOM_RATE))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["predicate_truth"],"TRUE")
        self.assertTrue(out["semantic_truth_authority"])
        self.assertFalse(out["semantic_identity_authority"])
        self.assertFalse(out["policy_adequacy_authority"])

    def test_wrong_target_unknown_not_false(self):
        text="The margin is added to the specified index rate."
        out=evaluate(self.payload(text,p.ATOM_GROSS_PROFIT))
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"],"UNKNOWN")

    def test_bare_margin_unknown(self):
        text="Margin increased."
        out=evaluate(self.payload(text,p.ATOM_RATE))
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"],"UNKNOWN")

    def test_unsupported_atom_fails_closed(self):
        text="The margin is added to the specified index rate."
        out=evaluate(self.payload(text,"MARGIN::MAGIC"))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")


if __name__=="__main__":
    unittest.main(verbosity=2)
