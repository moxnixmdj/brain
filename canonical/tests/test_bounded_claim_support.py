import unittest

from canonical.runtime.bounded_claim_support import (
    build_support_graph,
    classify_support,
    parse_fact,
)


class BoundedClaimSupportTests(unittest.TestCase):
    def test_plain_fact(self):
        out=parse_fact("Atlas cost is 12.")
        self.assertEqual(out["status"],"RESOLVED")
        self.assertEqual(out["fact"]["entity"],"atlas")
        self.assertEqual(out["fact"]["field"],"cost")
        self.assertEqual(out["fact"]["value"],"12")

    def test_provenance_prefixes(self):
        out=parse_fact("Audited ledger reports that Atlas cost is 12.")
        self.assertEqual(out["status"],"RESOLVED")
        self.assertEqual(out["fact"]["source"],"Audited ledger")

    def test_support(self):
        out=classify_support(
            "Atlas cost is 12.",
            "Audited ledger reports that Atlas cost is 12.",
            evidence_id="E1",
        )
        self.assertEqual(out["relation"],"SUPPORTS")

    def test_conflict(self):
        out=classify_support(
            "Atlas cost is 12.",
            "Forecast states Atlas cost is 15.",
            evidence_id="E2",
        )
        self.assertEqual(out["relation"],"CONFLICTS")

    def test_unrelated_same_value_is_not_support(self):
        out=classify_support(
            "Atlas cost is 12.",
            "Forecast states Atlas schedule is 12.",
        )
        self.assertEqual(out["relation"],"UNRELATED")

    def test_outside_grammar_fails_closed(self):
        out=parse_fact("Atlas probably costs roughly twelve.")
        self.assertEqual(out["status"],"UNRESOLVED")

    def test_graph_keeps_support_and_conflict(self):
        out=build_support_graph(
            [{"claim_id":"C1","text":"Atlas cost is 12."}],
            [
                {"evidence_id":"E1","text":"Ledger reports that Atlas cost is 12."},
                {"evidence_id":"E2","text":"Forecast states Atlas cost is 15."},
                {"evidence_id":"E3","text":"Memo states Atlas schedule is 12."},
            ],
        )
        self.assertEqual(out["status"],"COMPILED")
        self.assertEqual(
            out["edges"],
            [
                {"claim_id":"C1","evidence_id":"E1","relation":"SUPPORTS"},
                {"claim_id":"C1","evidence_id":"E2","relation":"CONFLICTS"},
            ],
        )


if __name__=="__main__":
    unittest.main()
