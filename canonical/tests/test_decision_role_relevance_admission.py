#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
BOUND=ROOT/"canonical/runtime/bound_capabilities"

def load(name):
    p=BOUND/(name+".py")
    spec=importlib.util.spec_from_file_location("decision_role_test_"+name,p)
    if spec is None or spec.loader is None:
        raise RuntimeError("LOAD_FAILED:"+name)
    m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m
    spec.loader.exec_module(m)
    return m

class DecisionRoleAdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roles=load("decision_role_relevance_admission")
        cls.rank=load("objective_relevance_bm25")

    def test_wrong_property_high_overlap_is_rejected(self):
        objective=(
            "Determine whether the room-temperature thermal diffusivity of annealed Alloy 7123 "
            "is greater than that of annealed Alloy 408 under comparable bulk-material conditions."
        )
        wrong=(
            "Ignition temperature of bulk annealed Alloy 7123 and Alloy 409 under comparable "
            "room-temperature conditions"
        )
        out=self.roles.evaluate(objective,wrong)
        self.assertTrue(out["applicable"],out)
        self.assertFalse(out["verified"],out)
        self.assertEqual(
            out["property_check"]["requested_property_tokens"],
            ["thermal","diffusivity"],
            out,
        )
        self.assertFalse(out["property_check"]["verified"],out)

    def test_wrong_operand_with_correct_property_is_rejected(self):
        objective=(
            "Determine whether the room-temperature thermal diffusivity of annealed Alloy 7123 "
            "is greater than that of annealed Alloy 408 under comparable bulk-material conditions."
        )
        wrong="Thermal diffusivity of annealed Alloy 409 at room temperature"
        out=self.roles.evaluate(objective,wrong)
        self.assertTrue(out["applicable"],out)
        self.assertTrue(out["property_check"]["verified"],out)
        self.assertFalse(out["operand_check"]["verified"],out)
        self.assertFalse(out["verified"],out)

    def test_single_operand_evidence_with_property_is_admitted(self):
        objective=(
            "Determine whether the room-temperature thermal diffusivity of annealed Alloy 7123 "
            "is greater than that of annealed Alloy 408 under comparable bulk-material conditions."
        )
        candidate="Thermal diffusivity measurements of annealed Alloy 408 near room temperature"
        out=self.roles.evaluate(objective,candidate)
        self.assertTrue(out["applicable"],out)
        self.assertTrue(out["property_check"]["verified"],out)
        self.assertTrue(out["operand_check"]["verified"],out)
        self.assertTrue(out["verified"],out)
        self.assertEqual(out["operand_check"]["matched_discriminators"],["408"],out)

    def test_protocol_versions_use_operand_discriminators(self):
        objective="Determine whether RFC 9110 is greater than RFC 7230."
        good=self.roles.evaluate(objective,"RFC 9110 HTTP Semantics")
        bad=self.roles.evaluate(objective,"RFC 7540 HTTP/2 overview")
        self.assertTrue(good["applicable"],good)
        self.assertTrue(good["verified"],good)
        self.assertTrue(bad["applicable"],bad)
        self.assertFalse(bad["verified"],bad)

    def test_unsupported_objective_preserves_incumbent_behavior(self):
        objective="Explain practical thermal management approaches for electronic enclosures."
        out=self.roles.evaluate(objective,"Thermal management approaches for electronic enclosures")
        self.assertFalse(out["applicable"],out)
        self.assertTrue(out["verified"],out)

    def test_ranker_skips_higher_scoring_wrong_role_candidate(self):
        objective=(
            "Determine whether the room-temperature thermal diffusivity of annealed Alloy 7123 "
            "is greater than that of annealed Alloy 408 under comparable bulk-material conditions."
        )
        candidates=[
            {
                "url":"https://wrong.example/high-overlap",
                "title":"Ignition temperature of bulk annealed Alloy 7123 and Alloy 409",
                "snippet":"room temperature comparable bulk material conditions annealed alloy",
            },
            {
                "url":"https://right.example/property",
                "title":"Thermal diffusivity of annealed Alloy 408",
                "snippet":"measured thermal diffusivity near room temperature",
            },
        ]
        out=self.rank.rank(objective,candidates)
        self.assertEqual(out["status"],"LEXICAL_RELEVANCE_RANKED",out)
        raw=out["raw_top_candidate_original_index"]
        selected=out["top_candidate_original_index"]
        self.assertEqual(raw,0,out)
        self.assertEqual(selected,1,out)
        self.assertFalse(
            out["ranked_candidates"][0]["candidate_admission"]["decision_role"]["verified"],
            out,
        )
        self.assertTrue(out["top_candidate_admission"]["verified"],out)
        self.assertGreaterEqual(out["role_admitted_positive_count"],1,out)

    def test_broad_objective_ranker_remains_legacy_compatible(self):
        objective="Find authoritative documentation about thermal management for electronic enclosures."
        candidates=[
            {
                "url":"https://example.org/relevant",
                "title":"Thermal management for electronic enclosures",
                "snippet":"authoritative technical documentation",
            },
            {
                "url":"https://example.org/noise",
                "title":"Unrelated gardening notes",
                "snippet":"soil and plants",
            },
        ]
        out=self.rank.rank(objective,candidates)
        self.assertEqual(out["status"],"LEXICAL_RELEVANCE_RANKED",out)
        self.assertEqual(out["top_candidate_original_index"],0,out)
        role=out["top_candidate_admission"]["decision_role"]
        self.assertFalse(role["applicable"],out)
        self.assertTrue(role["verified"],out)
        self.assertEqual(out["verification_method"],"DETERMINISTIC_BM25",out)

if __name__=="__main__":
    unittest.main(verbosity=2)
