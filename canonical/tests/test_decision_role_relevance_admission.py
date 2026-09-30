#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/objective_relevance_bm25.py"

def load():
    spec=importlib.util.spec_from_file_location("decision_role_relevance_under_test",P)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED")
    m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m
    spec.loader.exec_module(m)
    return m

class DecisionRoleRelevanceAdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=load()

    def test_anaphoric_property_comparison_rejects_off_property_high_overlap(self):
        objective=(
            "Determine whether the boiling point of compound X7 is greater than "
            "that of compound Z9."
        )
        candidates=[
            {
                "title":"Ignition temperature of compound X7 and compound Z8 under laboratory conditions",
                "snippet":"compound thermal comparison temperature study",
            },
            {
                "title":"Boiling point measurements of compound Z9",
                "snippet":"reference boiling point data for compound Z9",
            },
            {
                "title":"Boiling point measurements of compound X7",
                "snippet":"reference boiling point data for compound X7",
            },
        ]
        out=self.m.rank(objective,candidates)
        self.assertEqual(out["status"],"LEXICAL_RELEVANCE_RANKED",out)
        self.assertIn(out["top_candidate_original_index"],{1,2},out)
        self.assertEqual(out["decision_role_signature"]["property_head"],"point",out)
        decoy=next(
            x for x in out["ranked_candidates"]
            if x["original_index"]==0
        )
        self.assertFalse(decoy["decision_role_coverage"]["verified"],decoy)
        self.assertFalse(decoy["decision_role_coverage"]["property"]["verified"],decoy)
        self.assertTrue(out["top_candidate_admission"]["verified"],out)
        self.assertTrue(
            out["top_candidate_admission"]["decision_role_coverage"]["verified"],out
        )

    def test_exact_alphanumeric_operand_discriminator_cannot_be_substituted(self):
        objective=(
            "Determine whether the yield strength of alloy A12 is greater than "
            "that of alloy B34."
        )
        candidates=[
            {
                "title":"Yield strength comparison of alloy A11 and alloy B35",
                "snippet":"yield strength alloy laboratory results",
            },
            {
                "title":"Yield strength of alloy B34",
                "snippet":"reference yield strength measurement for B34 alloy",
            },
        ]
        out=self.m.rank(objective,candidates)
        self.assertEqual(out["status"],"LEXICAL_RELEVANCE_RANKED",out)
        self.assertEqual(out["top_candidate_original_index"],1,out)
        decoy=next(x for x in out["ranked_candidates"] if x["original_index"]==0)
        self.assertFalse(decoy["decision_role_coverage"]["verified"],decoy)
        self.assertEqual(
            decoy["decision_role_coverage"]["left_operand"]["discriminator_tokens"],
            ["a12"],
            decoy,
        )
        self.assertEqual(
            decoy["decision_role_coverage"]["right_operand"]["discriminator_tokens"],
            ["b34"],
            decoy,
        )

    def test_shared_property_direct_comparison_uses_operand_roles(self):
        objective=(
            "Assess whether reference genome sequence length of isolate A12 is greater "
            "than mitochondrial reference genome sequence length of species B34."
        )
        candidates=[
            {
                "title":"Growth rate and colony morphology of isolate A12",
                "snippet":"reference laboratory isolate study",
            },
            {
                "title":"Mitochondrial reference genome sequence length of species B34",
                "snippet":"complete genome sequence length record B34",
            },
        ]
        out=self.m.rank(objective,candidates)
        self.assertEqual(out["status"],"LEXICAL_RELEVANCE_RANKED",out)
        self.assertEqual(out["top_candidate_original_index"],1,out)
        sig=out["decision_role_signature"]
        self.assertEqual(sig["property_head"],"length",sig)
        self.assertIn("sequence",sig["property_tokens"],sig)
        self.assertIn("genome",sig["property_tokens"],sig)

    def test_no_candidate_with_property_and_operand_role_fails_closed(self):
        objective=(
            "Determine whether the boiling point of compound X7 is greater than "
            "that of compound Z9."
        )
        candidates=[
            {"title":"Ignition temperature of compound X7","snippet":"thermal test"},
            {"title":"Boiling point of compound Q2","snippet":"reference boiling point"},
        ]
        out=self.m.rank(objective,candidates)
        self.assertEqual(out["status"],"RELEVANCE_UNRESOLVED",out)
        self.assertEqual(out["reason"],"NO_DECISION_ROLE_COVERAGE_CANDIDATE",out)
        self.assertFalse(out.get("output_verified",False),out)

    def test_numeric_threshold_comparison_keeps_existing_relevance_path(self):
        objective="Determine whether observed wave amplitude exceeds 1 meter."
        candidates=[
            {
                "title":"Observed wave amplitude measurements",
                "snippet":"maximum wave amplitude monitoring record",
            },
            {
                "title":"Unrelated weather bulletin",
                "snippet":"temperature and wind",
            },
        ]
        out=self.m.rank(objective,candidates)
        self.assertEqual(out["status"],"LEXICAL_RELEVANCE_RANKED",out)
        self.assertEqual(out["top_candidate_original_index"],0,out)
        self.assertIsNone(out["decision_role_signature"],out)
        self.assertEqual(
            out["top_candidate_admission"]["method"],
            "FOCUSED_QUERY_TOKEN_COVERAGE_V1",
            out,
        )

if __name__=="__main__":
    unittest.main(verbosity=2)
