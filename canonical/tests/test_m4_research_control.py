import unittest
from canonical.runtime.m4_research_control import control

REQS=[
    {"id":"R1","text":"Compare sodium battery energy density with lithium battery energy density.","material":True},
    {"id":"R2","text":"Determine cycle life under the declared operating conditions.","material":True},
]

class Tests(unittest.TestCase):
    def test_selects_verified_action_and_focuses_unresolved_requirement(self):
        out=control(
            objective="Assess battery tradeoffs",
            material_requirements=REQS,
            resolved_requirement_ids=[],
            candidate_actions=[
                {"id":"cheap","covers":["R1"],"cost":0.5,"reliability":1.0,"verified":True},
                {"id":"broad","covers":["R1","R2"],"cost":2.0,"reliability":1.0,"verified":True},
            ],
        )
        self.assertEqual(out["status"],"ACT",out)
        self.assertEqual(out["selected_action_id"],"cheap")
        self.assertEqual(out["target_requirement_id"],"R1")
        self.assertTrue(out["query"])
        self.assertFalse(out["terminal_authority"])
        self.assertFalse(out["semantic_authority"])

    def test_exact_stop_only_when_all_material_requirements_resolved(self):
        out=control(
            objective="Assess battery tradeoffs",
            material_requirements=REQS,
            resolved_requirement_ids=["R1","R2"],
            candidate_actions=[],
        )
        self.assertEqual(out["status"],"STOP",out)
        self.assertEqual(out["unresolved_requirement_ids"],[])

    def test_unverified_action_cannot_drive_research(self):
        out=control(
            objective="Assess battery tradeoffs",
            material_requirements=REQS,
            resolved_requirement_ids=[],
            candidate_actions=[
                {"id":"opaque","covers":["R1","R2"],"cost":0.0,"reliability":1.0,"verified":False},
            ],
        )
        self.assertEqual(out["status"],"ESCALATE",out)

    def test_missing_requirement_graph_fails_closed(self):
        out=control(
            objective="Assess battery tradeoffs",
            material_requirements=[],
            resolved_requirement_ids=[],
            candidate_actions=[],
        )
        self.assertEqual(out["status"],"FAIL_CLOSED",out)
        self.assertIn("MATERIAL_REQUIREMENT_GRAPH_MISSING",out["errors"])

    def test_nonmaterial_requirement_cannot_sneak_into_graph(self):
        out=control(
            objective="x",
            material_requirements=[{"id":"R","text":"Find x","material":False}],
            resolved_requirement_ids=[],
            candidate_actions=[],
        )
        self.assertEqual(out["status"],"FAIL_CLOSED",out)
        self.assertIn("REQUIREMENT_MATERIALITY_NOT_EXPLICIT:R",out["errors"])

    def test_unknown_resolved_id_fails_closed(self):
        out=control(
            objective="x",
            material_requirements=[{"id":"R","text":"Find x","material":True}],
            resolved_requirement_ids=["OTHER"],
            candidate_actions=[],
        )
        self.assertEqual(out["status"],"FAIL_CLOSED",out)
        self.assertTrue(any(x.startswith("RESOLVED_UNKNOWN_REQUIREMENTS:") for x in out["errors"]))

    def test_action_cannot_claim_unknown_requirement_coverage(self):
        out=control(
            objective="x",
            material_requirements=[{"id":"R","text":"Find x","material":True}],
            resolved_requirement_ids=[],
            candidate_actions=[
                {"id":"bad","covers":["OTHER"],"cost":0,"reliability":1,"verified":True}
            ],
        )
        self.assertEqual(out["status"],"FAIL_CLOSED",out)
        self.assertIn("ACTION_COVERS_UNKNOWN_REQUIREMENT:bad",out["errors"])

    def test_duplicate_action_id_fails_closed(self):
        out=control(
            objective="x",
            material_requirements=[{"id":"R","text":"Find x","material":True}],
            resolved_requirement_ids=[],
            candidate_actions=[
                {"id":"dup","covers":["R"],"cost":1,"reliability":1,"verified":True},
                {"id":"dup","covers":["R"],"cost":0,"reliability":1,"verified":True},
            ],
        )
        self.assertEqual(out["status"],"FAIL_CLOSED",out)
        self.assertIn("ACTION_ID_DUPLICATE:dup",out["errors"])

    def test_focused_requirement_not_whole_orchestration_objective(self):
        req=[{"id":"R","text":"Determine whether France population growth is higher than Germany population growth.","material":True}]
        out=control(
            objective="Use every available tool and produce a polished report about population growth.",
            material_requirements=req,
            resolved_requirement_ids=[],
            candidate_actions=[{"id":"a","covers":["R"],"cost":1,"reliability":1,"verified":True}],
        )
        self.assertEqual(out["status"],"ACT",out)
        self.assertIn("france",out["query"])
        self.assertNotIn("polished",out["query"])
        self.assertNotIn("available",out["query"])

if __name__=="__main__":
    unittest.main(verbosity=2)
