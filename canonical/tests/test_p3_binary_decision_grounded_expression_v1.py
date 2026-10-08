import unittest
from canonical.runtime.p3_binary_decision_grounded_expression_v1 import evaluate
from canonical.runtime.synthesis_certified_visible_support_policy_v2 import INPUT_SCHEMA


def base(fmt="BULLETS"):
    return {
      "objective":"Determine whether thermal conductivity of AISI type 304 stainless steel is higher than thermal conductivity of 6061 aluminum.",
      "v2_input":{
        "schema":INPUT_SCHEMA,
        "task":{
          "claims":[
            {"claim_id":"left","text":"Thermal conductivity of AISI type 304 stainless steel is 16 W/mK.","required":False},
            {"claim_id":"right","text":"Thermal conductivity of 6061 aluminum is 167 W/mK.","required":False},
          ],
          "evidence":[
            {"evidence_id":"E1","text":"Thermal conductivity of AISI type 304 stainless steel is 16 W/mK.","verified":True,"provenance":[{"source_id":"S1","locator":"p1"}]},
            {"evidence_id":"E2","text":"Thermal conductivity of 6061 aluminum is 167 W/mK.","verified":True,"provenance":[{"source_id":"S2","locator":"p2"}]},
          ],
          "audience_profile":{
            "profile_id":"EXPLICIT",
            "constraints":{
              "output_format":fmt,"citation_mode":"INLINE_SOURCE_IDS","style":"VERBATIM_GROUNDED",
              "required_sections":[],"allowed_sections":None,"max_items":3,"max_chars":3000,
              "heading_level":2,"require_title":False,
            },
          },
        },
      },
    }


class Tests(unittest.TestCase):
    def test_false_decision_is_first_and_provenance_bound(self):
        out=evaluate(base())
        self.assertTrue(out["pass"],out)
        lines=out["rendered_text"].splitlines()
        self.assertTrue(lines[0].startswith('- Decision: "Determine whether'))
        self.assertIn("=> FALSE.",lines[0])
        self.assertIn("[src:S1@p1;S2@p2]",lines[0])
        self.assertTrue(out["decision_expression_covered"])
        self.assertTrue(out["bound_cell_required_decision_coverage_complete"])
        self.assertEqual(out["audit"]["unsupported_material_claim_count"],0)

    def test_reversing_objective_roles_reverses_truth_and_fact_order(self):
        p=base()
        p["objective"]="Determine whether thermal conductivity of 6061 aluminum is higher than thermal conductivity of AISI type 304 stainless steel."
        out=evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertIs(out["decision_truth"],True)
        self.assertEqual(out["objective_role_order"],["right","left"])
        lines=out["rendered_text"].splitlines()
        self.assertIn("=> TRUE.",lines[0])
        self.assertIn("6061 aluminum",lines[1])
        self.assertIn("AISI type 304",lines[2])

    def test_claim_input_order_cannot_change_objective_order(self):
        p=base();p["v2_input"]["task"]["claims"].reverse()
        out=evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["objective_role_order"],["left","right"])
        lines=out["rendered_text"].splitlines()
        self.assertIn("AISI type 304",lines[1])
        self.assertIn("6061 aluminum",lines[2])

    def test_paragraph_format_supported_without_content_change(self):
        out=evaluate(base("PARAGRAPHS"))
        self.assertTrue(out["pass"],out)
        parts=out["rendered_text"].split("\n\n")
        self.assertEqual(len(parts),3)
        self.assertTrue(parts[0].startswith("Decision:"))

    def test_insufficient_item_budget_fails_closed(self):
        p=base();p["v2_input"]["task"]["audience_profile"]["constraints"]["max_items"]=2
        out=evaluate(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"OUTPUT_BUDGET_INFEASIBLE")

    def test_char_budget_never_truncates(self):
        p=base();p["v2_input"]["task"]["audience_profile"]["constraints"]["max_chars"]=30
        out=evaluate(p)
        self.assertFalse(out["pass"])
        self.assertIn(out["reason"],{"OPERAND_PRESENTATION_UNRESOLVED","MAX_CHARS_INFEASIBLE__NO_TRUNCATION"})
        self.assertFalse(out["pass"])

    def test_sections_and_title_fail_closed(self):
        p=base();p["v2_input"]["task"]["audience_profile"]["constraints"]["require_title"]=True
        out=evaluate(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"TITLE_OUTSIDE_CELL")

    def test_unsupported_format_fails_closed(self):
        p=base("SECTIONED_MARKDOWN")
        out=evaluate(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"OUTPUT_FORMAT_OUTSIDE_CELL")

    def test_caller_selection_and_order_still_forbidden(self):
        p=base();p["v2_input"]["task"]["claims"][0]["include"]=True
        self.assertFalse(evaluate(p)["pass"])
        p=base();p["v2_input"]["task"]["claim_order"]=["right","left"]
        self.assertFalse(evaluate(p)["pass"])

    def test_unverified_evidence_fails_closed(self):
        p=base();p["v2_input"]["task"]["evidence"][0]["verified"]=False
        self.assertFalse(evaluate(p)["pass"])

    def test_no_authority_escalation(self):
        out=evaluate(base())
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["real_context_semantic_scope_complete"])
        for k in ("policy_adequacy_authority","db_admission_authority","u_subtraction_authority","terminal_authority"):
            self.assertFalse(out[k])
        self.assertEqual(out["terminal_credit_delta"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
