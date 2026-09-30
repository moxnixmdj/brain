#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/source_candidate_provenance_verify.py"
def load():
    s=importlib.util.spec_from_file_location("pv",P); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
class ProvenanceVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.m=load()
    def test_doi_extraction(self):
        self.assertEqual(self.m._doi({"url":"https://doi.org/10.17487/RFC9110"}),"10.17487/RFC9110")
    def test_unsafe_url_rejected(self):
        self.assertEqual(self.m.verify({"url":"http://localhost/x"})["status"],"UNVERIFIED")
    def test_live_crossref_doi_identity(self):
        x=self.m.verify({"url":"https://doi.org/10.17487/RFC9110","doi":"10.17487/RFC9110"},timeout=20)
        self.assertEqual(x["status"],"BIBLIOGRAPHIC_PROVENANCE_VERIFIED",x)
        self.assertEqual(x["doi"].lower(),"10.17487/rfc9110")
        self.assertEqual(x["model_dependency_count"],0)
        self.assertIn("UNVERIFIED",x["authority_status"])
        self.assertEqual(x["primary_source_status"],"UNVERIFIED")
    def test_live_web_retrieval_identity(self):
        x=self.m.verify({"url":"https://docs.python.org/3/library/urllib.request.html"},timeout=20)
        self.assertEqual(x["status"],"RETRIEVAL_PROVENANCE_VERIFIED",x)
        self.assertEqual(x["final_host"],"docs.python.org")
        self.assertEqual(x["model_dependency_count"],0)
        self.assertIn("UNVERIFIED",x["authority_status"])
    def test_bad_doi_fails_closed(self):
        x=self.m.verify({"url":"https://doi.org/10.0000/definitely-not-a-real-doi","doi":"10.0000/definitely-not-a-real-doi"},timeout=15)
        self.assertEqual(x["status"],"UNVERIFIED",x)
if __name__=="__main__": unittest.main(verbosity=2)
