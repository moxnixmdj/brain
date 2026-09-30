#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
BC=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BC/(name+".py")
    s=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

class OpenResearchSourceFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.front=load("open_research_source_frontend")
        cls.decomp=load("broad_objective_decompose")

    def _run(self,goal):
        d=self.decomp.decompose(goal)
        self.assertEqual(d["status"],"DECOMPOSED",d)
        return self.front.run(goal,d,limit=8,timeout=20)

    def test_standard_objective_reaches_provenance_frontier(self):
        x=self._run("Determine whether RFC 9110 defines HTTP semantics and identify provenance-bearing source evidence")
        self.assertEqual(x["status"],"SOURCE_FRONTEND_READY",x)
        self.assertGreaterEqual(x["provenance_verified_candidate_count"],1,x)
        self.assertEqual(x["authority_verified_candidate_count"],0)
        self.assertFalse(x["authority_claims_made"])
        self.assertEqual(x["model_dependency_count"],0)

    def test_scientific_objective_reaches_provenance_frontier(self):
        x=self._run("Assess whether lithium ion battery calendar aging is influenced by temperature using published experimental evidence")
        self.assertEqual(x["status"],"SOURCE_FRONTEND_READY",x)
        self.assertGreaterEqual(x["provenance_verified_candidate_count"],1,x)
        self.assertEqual(
            x["next_required_capability"],
            "MODEL_INDEPENDENT_SOURCE_AUTHORITY_PRIMARY_EVIDENCE_AND_RELEVANCE_VERIFICATION",
        )

    def test_mismatch_fails_closed(self):
        d=self.decomp.decompose("Assess whether A is greater than B")
        with self.assertRaises(ValueError):
            self.front.run("Assess whether C is greater than D",d)

if __name__=="__main__":
    unittest.main(verbosity=2)
