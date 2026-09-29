#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

grounding=load(
    "project_brain_plain_goal_grounding_test_target",
    ROOT/"runtime"/"bound_capabilities"/"plain_goal_bound_grounding.py",
)
verifier=load(
    "project_brain_plain_goal_grounding_verifier_test_target",
    ROOT/"runtime"/"bound_capabilities"/"plain_goal_bound_grounding_verify.py",
)


class PlainGoalBoundGroundingTests(unittest.TestCase):
    def registry(self):
        return {
            "codec.cbor.encode":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "provides":["binary.serialization.cbor"],
                "requires":["json.file.available"],
                "keywords":["cbor","binary","serialize","encode","records"],
            },
            "codec.msgpack.encode":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "provides":["binary.serialization.msgpack"],
                "requires":["json.file.available"],
                "keywords":["messagepack","msgpack","binary","serialize","encode","records"],
            },
            "decision.synthesis.typed.stdlib":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "provides":["decision.synthesis.typed"],
                "requires":["decision.problem.typed"],
                "keywords":["decision","synthesis","alternatives","evidence","constraints","choose"],
            },
            "decision.synthesis.verify.stdlib":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "provides":["decision.synthesis.verify"],
                "requires":["decision.problem.typed","decision.result.typed"],
                "keywords":["decision","verify","independent","evidence","constraints"],
            },
            "leela-zero":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "provides":["game.go.engine"],
                "requires":[],
                "keywords":["go","game","engine","zero"],
            },
            "paid.magic":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":1,
                "provides":["decision.magic"],
                "requires":[],
                "keywords":["decision","magic","choose"],
            },
        }

    def test_constraint_words_cannot_create_irrelevant_zero_match(self):
        result=grounding.ground(
            "Choose the best already verified zero cost binary serialization route.",
            self.registry(),
        )
        ids=set(result["candidate_capability_ids"])
        self.assertNotIn("leela-zero",ids)
        self.assertIn("codec.cbor.encode",ids)
        self.assertIn("codec.msgpack.encode",ids)

    def test_multiple_plausible_bound_routes_preserve_ambiguity(self):
        result=grounding.ground(
            "Choose a binary serialization route for these records.",
            self.registry(),
        )
        clause=result["clauses"][0]
        self.assertEqual(clause["status"],"AMBIGUOUS_BOUNDED")
        self.assertGreaterEqual(len(clause["candidates"]),2)
        self.assertTrue(result["whole_goal_external_discovery_forbidden_if_any_bound_grounding"])

    def test_unmatched_clause_stays_unresolved(self):
        result=grounding.ground(
            "Calibrate the neutrino interferometer phase drift.",
            self.registry(),
        )
        self.assertEqual(result["clauses"][0]["status"],"UNRESOLVED")
        self.assertEqual(result["candidate_capability_ids"],[])
        self.assertFalse(result["whole_goal_external_discovery_forbidden_if_any_bound_grounding"])
        self.assertTrue(result["external_discovery_allowed_for_unresolved_only"])

    def test_paid_candidate_is_never_grounded(self):
        result=grounding.ground(
            "Choose the decision magic route.",
            self.registry(),
        )
        self.assertNotIn("paid.magic",result["candidate_capability_ids"])

    def test_decision_and_verification_clauses_ground_separately(self):
        result=grounding.ground(
            "Choose the decision route using the available evidence and constraints, and independently verify the decision.",
            self.registry(),
        )
        self.assertGreaterEqual(len(result["clauses"]),2)
        first={x["capability_id"] for x in result["clauses"][0]["candidates"]}
        second={x["capability_id"] for x in result["clauses"][1]["candidates"]}
        self.assertIn("decision.synthesis.typed.stdlib",first)
        self.assertIn("decision.synthesis.verify.stdlib",second)

    def test_independent_verifier_accepts_valid_and_rejects_tamper(self):
        registry=self.registry()
        goal="Choose a binary serialization route for these records."
        result=grounding.ground(goal,registry)
        ok,reason=verifier.verify(goal,result,registry)
        self.assertTrue(ok,reason)

        tampered=__import__("copy").deepcopy(result)
        tampered["clauses"][0]["candidates"][0]["capability_id"]="missing.capability"
        ok,reason=verifier.verify(goal,tampered,registry)
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("CANDIDATE_NOT_VERIFIED:"),reason)

    def test_grounding_is_deterministic(self):
        goal="Choose a binary serialization route and independently verify the decision."
        a=grounding.ground(goal,self.registry())
        b=grounding.ground(goal,self.registry())
        self.assertEqual(a,b)


if __name__=="__main__":
    unittest.main(verbosity=2)
