#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/source_primary_relevance_pubmed.py"

def load():
    s=importlib.util.spec_from_file_location("pubmed_primary",P)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

class PubMedPrimaryRelevanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.m=load()

    def _run(self,publication_types,objective="intensive blood pressure cardiovascular control"):
        old_search=self.m._search_pmids
        old_fetch=self.m._fetch_record
        try:
            self.m._search_pmids=lambda doi,timeout: (["123"],"https://eutils.ncbi.nlm.nih.gov/esearch",200)
            self.m._fetch_record=lambda pmid,timeout: ({
                "pmid":"123","doi":"10.1234/example",
                "title":"Randomized intensive blood pressure control and cardiovascular outcomes",
                "abstract":"A controlled study of cardiovascular outcomes after intensive blood pressure treatment.",
                "publication_types":publication_types,
                "mesh_terms":["Blood Pressure","Cardiovascular Diseases"],
                "keywords":["intensive treatment"],
            },"https://eutils.ncbi.nlm.nih.gov/efetch",200)
            return self.m.verify(
                objective,
                {"doi":"10.1234/example"},
                {"status":"BIBLIOGRAPHIC_PROVENANCE_VERIFIED","doi":"10.1234/example"},
                timeout=5,
            )
        finally:
            self.m._search_pmids=old_search
            self.m._fetch_record=old_fetch

    def test_empirical_type_plus_topic_coverage_verifies_narrow_pair(self):
        x=self._run(["Journal Article","Randomized Controlled Trial"])
        self.assertEqual(x["status"],"PRIMARY_SOURCE_AND_OBJECTIVE_TOPIC_RELEVANCE_VERIFIED",x)
        self.assertEqual(x["primary_source_status"],"DIRECT_EMPIRICAL_STUDY_PUBLICATION_TYPE_VERIFIED")
        self.assertEqual(x["relevance_status"],"OBJECTIVE_TOPIC_ANCHOR_COVERAGE_VERIFIED")
        self.assertEqual(x["claim_relation_status"],"UNVERIFIED")
        self.assertEqual(x["evidence_sufficiency_status"],"UNVERIFIED")
        self.assertTrue(x["output_verified"])

    def test_review_fails_primary_even_when_topically_relevant(self):
        x=self._run(["Journal Article","Systematic Review","Meta-Analysis"])
        self.assertEqual(x["status"],"OBJECTIVE_TOPIC_RELEVANCE_VERIFIED__PRIMARY_SOURCE_UNVERIFIED",x)
        self.assertEqual(x["primary_source_status"],"UNVERIFIED")
        self.assertFalse(x["output_verified"])

    def test_empirical_unrelated_objective_fails_relevance(self):
        x=self._run(["Observational Study"],objective="genome sequencing rare variant inheritance")
        self.assertEqual(x["status"],"PRIMARY_SOURCE_VERIFIED__OBJECTIVE_TOPIC_RELEVANCE_UNVERIFIED",x)
        self.assertEqual(x["relevance_status"],"UNVERIFIED")
        self.assertFalse(x["output_verified"])

    def test_provenance_is_mandatory(self):
        x=self.m.verify("blood pressure trial",{"doi":"10.1234/example"},{"status":"UNVERIFIED"})
        self.assertEqual(x["status"],"UNVERIFIED")
        self.assertEqual(x["reason"],"BIBLIOGRAPHIC_PROVENANCE_REQUIRED")

if __name__=="__main__": unittest.main(verbosity=2)
