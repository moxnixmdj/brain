import unittest
from canonical.runtime.bounded_research_frontier import EvidenceGap,Source,compile_queries,source_frontier

class BoundedResearchFrontierTests(unittest.TestCase):
    def test_query_compile(self):
        o=compile_queries(EvidenceGap("g","SA-CCR","maturity factor",("credit derivatives",),("bis.org",)))
        self.assertEqual(o["status"],"COMPILED")
        self.assertIn('site:bis.org',o["queries"][1])
    def test_bad_domain_fails(self):
        self.assertEqual(compile_queries(EvidenceGap("g","x","y",preferred_domains=("bad domain",)))["status"],"FAIL_CLOSED")
    def test_unique_dominant_source(self):
        ss=[
          Source("weak",frozenset({"x"}),2,.7,10,2),
          Source("strong",frozenset({"x","y"}),1,.9,2,1),
        ]
        o=source_frontier({"x"},ss)
        self.assertEqual(o["status"],"SELECT"); self.assertEqual(o["selected_source_id"],"strong")
    def test_tradeoff_returns_frontier(self):
        ss=[
          Source("authority",frozenset({"x"}),0,.7,10,1),
          Source("fresh",frozenset({"x"}),1,.9,1,1),
        ]
        o=source_frontier({"x"},ss)
        self.assertEqual(o["status"],"FRONTIER"); self.assertEqual(set(o["frontier"]),{"authority","fresh"})
    def test_unknown_coverage_escalates(self):
        self.assertEqual(source_frontier({"x"},[Source("a",frozenset(),0,1,0,0)])["status"],"ESCALATE")
if __name__=="__main__": unittest.main()
