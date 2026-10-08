import copy
import unittest

from canonical.runtime.p3_bounded_objective_role_presentation_compiler_v1 import evaluate
from canonical.runtime.synthesis_certified_visible_support_policy_v2 import INPUT_SCHEMA


def base():
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
            {"evidence_id":"E1","text":"Thermal conductivity of AISI type 304 stainless steel is 16 W/mK.","verified":True,
             "provenance":[{"source_id":"S1","locator":"p1"}]},
            {"evidence_id":"E2","text":"Thermal conductivity of 6061 aluminum is 167 W/mK.","verified":True,
             "provenance":[{"source_id":"S2","locator":"p2"}]},
          ],
          "audience_profile":{
            "profile_id":"EXPLICIT",
            "constraints":{
              "output_format":"BULLETS","citation_mode":"INLINE_SOURCE_IDS","style":"VERBATIM_GROUNDED",
              "required_sections":[],"allowed_sections":None,"max_items":2,"max_chars":2000,
              "heading_level":2,"require_title":False,
            },
          },
        },
      },
    }


class Tests(unittest.TestCase):
    def test_constructs_objective_role_preserving_top_law_policy(self):
        out=evaluate(base())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["objective_role_order"],["left","right"])
        self.assertTrue(out["presentation_policy_constructed"])
        self.assertTrue(out["declared_cell_top_law_conditions_mechanically_satisfied"])
        self.assertFalse(out["real_context_semantic_scope_complete"])
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertEqual(out["terminal_credit_delta"],0)
        trace=[r["item_id"] for r in out["render_trace"]]
        self.assertEqual(trace,["CLAIM_left","CLAIM_right"])

    def test_caller_cannot_choose_include(self):
        p=base();p["v2_input"]["task"]["claims"][0]["include"]=True
        out=evaluate(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"CALLER_INCLUDE_FORBIDDEN")

    def test_caller_cannot_choose_order(self):
        p=base();p["v2_input"]["task"]["claim_order"]=["right","left"]
        out=evaluate(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"CALLER_CLAIM_ORDER_FORBIDDEN")

    def test_input_claim_order_does_not_override_objective_role_order(self):
        p=base()
        p["v2_input"]["task"]["claims"].reverse()
        out=evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["objective_role_order"],["left","right"])
        trace=[r["item_id"] for r in out["render_trace"]]
        self.assertEqual(trace,["CLAIM_left","CLAIM_right"])

    def test_reversing_objective_roles_reverses_presentation_order(self):
        p=base()
        p["objective"]="Determine whether thermal conductivity of 6061 aluminum is higher than thermal conductivity of AISI type 304 stainless steel."
        out=evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["objective_role_order"],["right","left"])
        trace=[r["item_id"] for r in out["render_trace"]]
        self.assertEqual(trace,["CLAIM_right","CLAIM_left"])

    def test_extra_claim_fails_closed(self):
        p=base()
        p["v2_input"]["task"]["claims"].append({"claim_id":"x","text":"Density is 10.","required":False})
        out=evaluate(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"EXACTLY_TWO_CLAIMS_REQUIRED")

    def test_required_claim_fails_closed(self):
        p=base();p["v2_input"]["task"]["claims"][0]["required"]=True
        out=evaluate(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"EXACT_CELL_REQUIRES_TWO_OPTIONAL_CLAIMS")

    def test_ambiguous_role_evidence_fails_closed(self):
        p=base()
        p["v2_input"]["task"]["evidence"].append({
          "evidence_id":"E3","text":"AISI type 304 stainless steel has another conductivity observation.",
          "verified":True,"provenance":[{"source_id":"S3","locator":"p3"}]})
        out=evaluate(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"OBJECTIVE_ROLE_RELEVANCE_UNRESOLVED")

    def test_unverified_evidence_fails_closed(self):
        p=base();p["v2_input"]["task"]["evidence"][0]["verified"]=False
        out=evaluate(p)
        self.assertFalse(out["pass"])

    def test_no_authority_escalation(self):
        out=evaluate(base())
        self.assertTrue(out["pass"],out)
        for key in ("policy_adequacy_authority","db_admission_authority","u_subtraction_authority","terminal_authority"):
            self.assertFalse(out[key])
        self.assertEqual(out["terminal_credit_delta"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
