#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
PATH=ROOT/"canonical"/"runtime"/"bound_capabilities"/"plain_goal_bound_grounding.py"
spec=importlib.util.spec_from_file_location("project_brain_grounding_constraint_test",PATH)
grounding=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=grounding
spec.loader.exec_module(grounding)


class GroundingConstraintTest(unittest.TestCase):
    def test_independent_verification_constraint_rejects_non_verifier(self):
        registry={
            "decision.synthesis.typed.stdlib":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "provides":["decision.synthesis.typed"],
                "requires":["structured.decision_evidence.available"],
                "keywords":["decision","evidence","synthesis"],
            },
            "decision.synthesis.verify.stdlib":{
                "status":"VERIFIED_BOUND_CAPABILITY",
                "incremental_spend_usd":0,
                "provides":["decision.synthesis.verified"],
                "requires":["decision.synthesis.typed"],
                "keywords":["decision","verify","independent","audit"],
            },
        }
        result=grounding.ground(
            "Independently verify the decision result.",
            registry,
            enforce_bindability=False,
        )
        self.assertEqual(len(result["clauses"]),1)
        clause=result["clauses"][0]
        self.assertIn("INDEPENDENT_VERIFICATION",clause["constraints"])
        self.assertEqual(
            [x["capability_id"] for x in clause["candidates"]],
            ["decision.synthesis.verify.stdlib"],
        )
        rejected={
            x["capability_id"]:x["reason"]
            for x in clause["rejected_constraint_candidates"]
        }
        self.assertEqual(
            rejected.get("decision.synthesis.typed.stdlib"),
            "INDEPENDENT_VERIFICATION_ROLE_REQUIRED",
        )
        self.assertEqual(clause["status"],"GROUNDED")


if __name__=="__main__":
    unittest.main()
