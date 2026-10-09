from __future__ import annotations
import unittest

from canonical.runtime import oewn_decision_manifest_lattice_v1 as l
from canonical.runtime import oewn_decision_manifest_lattice_verify_v1 as lv
from canonical.runtime.oewn_release_sense_universe_v1 import (
    SCHEMA as OEWN_SCHEMA, RELEASE_ID, RELEASE_SHA256,
)


def universe():
    return {
        "schema":OEWN_SCHEMA,
        "status":"PASS__OEWN_2025_RELEASE_RELATIVE_SENSE_UNIVERSE_ENUMERATED",
        "pass":True,
        "release_id":RELEASE_ID,
        "archive_sha256":RELEASE_SHA256,
        "candidate_set_complete_relative_to_release":True,
        "open_world_english_sense_completeness_claimed":False,
        "lemma":"margin",
        "requested_part_of_speech":"n",
        "senses":[
            {"sense_id":"margin-1","synset_id":"ewn-margin-1-n","part_of_speech":"n"},
            {"sense_id":"margin-2","synset_id":"ewn-margin-2-n","part_of_speech":"n"},
        ],
    }


def problem(text):
    return {
        "schema":l.SCHEMA,
        "scope_id":"finance-margin",
        "sense_universe":universe(),
        "source_id":"doc",
        "source_text":text,
    }


def terminal(sid,policy):
    return f'Sense terminal {sid}: {{"policy":"{policy}"}}'


def obs(oid,cost,sid,value):
    return f'Sense observation {oid} cost {cost} for {sid}: "{value}"'


def observed(oid,value):
    return f'Sense observed {oid}: "{value}"'


class OewnDecisionManifestLatticeV1Tests(unittest.TestCase):
    def test_missing_terminal_signature_remains_top(self):
        p=problem(terminal("margin-1","A"))
        out=l.evaluate(p)
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["status"],"OPEN__SENSE_TERMINAL_SIGNATURE_TOP_REMAINS")
        self.assertEqual(out["open_lattice_atoms"][0]["sense_id"],"margin-2")
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_terminally_equivalent_senses_close_without_identifying_sense(self):
        p=problem("\n".join([
            terminal("margin-1","A"),
            terminal("margin-2","A"),
        ]))
        out=l.evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["intended_sense_identified"])
        self.assertEqual(set(out["surviving_sense_ids"]),{"margin-1","margin-2"})
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_distinct_senses_return_minimum_complete_discriminator(self):
        p=problem("\n".join([
            terminal("margin-1","A"),
            terminal("margin-2","B"),
            obs("context-domain",1,"margin-1","profit"),
            obs("context-domain",1,"margin-2","collateral"),
        ]))
        out=l.evaluate(p)
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["status"],"OPEN__MINIMUM_TERMINAL_DISCRIMINATOR_REQUIRED")
        self.assertEqual(out["next_observation_id"],"context-domain")
        self.assertEqual(out["minimum_worst_case_cost_units"],1.0)
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_partial_observation_map_with_observed_value_stays_open(self):
        p=problem("\n".join([
            terminal("margin-1","A"),
            terminal("margin-2","B"),
            obs("context-domain",1,"margin-1","profit"),
            observed("context-domain","profit"),
        ]))
        out=l.evaluate(p)
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["status"],"OPEN__OBSERVED_OUTCOME_MAP_TOP_REMAINS")
        self.assertEqual(out["blocking_observation_ids"],["context-domain"])
        self.assertEqual(
            out["next_proof_obligations"][0]["missing_sense_ids"],["margin-2"]
        )
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_observed_complete_outcome_identifies_one_sense(self):
        p=problem("\n".join([
            terminal("margin-1","A"),
            terminal("margin-2","B"),
            obs("context-domain",1,"margin-1","profit"),
            obs("context-domain",1,"margin-2","collateral"),
            observed("context-domain","collateral"),
        ]))
        out=l.evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["intended_sense_identified"])
        self.assertEqual(out["identified_sense_id"],"margin-2")
        self.assertEqual(out["terminal_signature"],{"policy":"B"})
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_observed_outcome_excluding_every_sense_falsifies_model(self):
        p=problem("\n".join([
            terminal("margin-1","A"),
            terminal("margin-2","B"),
            obs("context-domain",1,"margin-1","profit"),
            obs("context-domain",1,"margin-2","collateral"),
            observed("context-domain","neither"),
        ]))
        out=l.evaluate(p)
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["status"],
            "MODEL_FALSIFIED__OBSERVED_OUTCOMES_EXCLUDE_ALL_RELEASE_SENSES",
        )
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_inconsistent_observation_cost_fails_closed(self):
        p=problem("\n".join([
            terminal("margin-1","A"),
            terminal("margin-2","B"),
            obs("context-domain",1,"margin-1","profit"),
            obs("context-domain",2,"margin-2","collateral"),
        ]))
        out=l.evaluate(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("OBSERVATION_COST_INCONSISTENT",out["reason"])

    def test_unknown_sense_clause_fails_closed(self):
        p=problem("\n".join([
            terminal("margin-1","A"),
            terminal("margin-2","B"),
            terminal("margin-3","C"),
        ]))
        out=l.evaluate(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("TERMINAL_SENSE_NOT_IN_RELEASE_UNIVERSE",out["reason"])

    def test_distinct_senses_without_separating_observation_stay_open(self):
        p=problem("\n".join([
            terminal("margin-1","A"),
            terminal("margin-2","B"),
        ]))
        out=l.evaluate(p)
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["status"],"OPEN__SEPARATING_OBSERVATION_REQUIRED")
        self.assertEqual(
            out["next_proof_obligations"][0]["kind"],
            "DISCOVER_OR_PROVE_SEPARATING_OBSERVATION",
        )
        self.assertTrue(lv.verify(p,out)["verified"])


if __name__=="__main__":
    unittest.main()
