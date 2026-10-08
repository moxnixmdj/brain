import copy,json,unittest

from canonical.runtime.p3_binary_explicit_source_membership_v1 import (
    CONTRACT, compile_membership,
)
from canonical.tests.test_p3_binary_decision_grounded_expression_v1 import base


def doc():
    p=base()
    return {"contract":CONTRACT,"objective":p["objective"],"v2_input":p["v2_input"]}


def raw(value):
    return json.dumps(value,separators=(",",":"),ensure_ascii=False)


class Tests(unittest.TestCase):
    def test_exact_explicit_source_membership_passes(self):
        out=compile_membership(raw(doc()),source_id="TASK")
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["scope_membership_proved"])
        self.assertTrue(out["real_context_semantic_scope_complete"])
        self.assertTrue(out["expression_receipt"]["decision_expression_covered"])
        self.assertFalse(out["source_authorization_verified"])
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertEqual(out["terminal_credit_delta"],0)

    def test_reversed_exact_objective_still_passes(self):
        p=doc()
        p["objective"]="Determine whether thermal conductivity of 6061 aluminum is higher than thermal conductivity of AISI type 304 stainless steel."
        out=compile_membership(raw(p),source_id="TASK")
        self.assertTrue(out["pass"],out)
        self.assertIs(out["expression_receipt"]["decision_truth"],True)

    def test_trailing_sentence_requirement_is_not_silently_projected(self):
        p=doc()
        p["objective"]=p["objective"]+" Also explain the implications."
        out=compile_membership(raw(p),source_id="TASK")
        self.assertFalse(out["pass"],out)
        self.assertIn("OBJECTIVE_",out["errors"][0])

    def test_same_sentence_extra_requirement_is_not_silently_projected(self):
        p=doc()
        p["objective"]=p["objective"].rstrip(".")+" and explain why."
        out=compile_membership(raw(p),source_id="TASK")
        self.assertFalse(out["pass"],out)

    def test_duplicate_json_key_fails_closed(self):
        good=raw(doc())
        attacked=good[:-1]+',"objective":"forged"}'
        out=compile_membership(attacked,source_id="TASK")
        self.assertFalse(out["pass"],out)
        self.assertTrue(any(x.startswith("DUPLICATE_JSON_KEY:objective") for x in out["errors"]))

    def test_unknown_top_level_semantics_fail(self):
        p=doc();p["also"]="Translate to German"
        out=compile_membership(raw(p),source_id="TASK")
        self.assertFalse(out["pass"])
        self.assertIn("TOP_LEVEL_KEYS_NOT_EXACT_BOUND_CELL",out["errors"])

    def test_unknown_task_semantics_fail(self):
        p=doc();p["v2_input"]["task"]["hidden_requirement"]="explain implications"
        out=compile_membership(raw(p),source_id="TASK")
        self.assertFalse(out["pass"])
        self.assertIn("TASK_KEYS_NOT_EXACT_BOUND_CELL",out["errors"])

    def test_unknown_claim_semantics_fail(self):
        p=doc();p["v2_input"]["task"]["claims"][0]["must_explain"]=True
        out=compile_membership(raw(p),source_id="TASK")
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("CLAIM_KEYS_NOT_EXACT") for x in out["errors"]))

    def test_unknown_evidence_semantics_fail(self):
        p=doc();p["v2_input"]["task"]["evidence"][0]["authority_rank"]=1
        out=compile_membership(raw(p),source_id="TASK")
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("EVIDENCE_KEYS_NOT_EXACT") for x in out["errors"]))

    def test_unknown_provenance_semantics_fail(self):
        p=doc();p["v2_input"]["task"]["evidence"][0]["provenance"][0]["authority"]="primary"
        out=compile_membership(raw(p),source_id="TASK")
        self.assertFalse(out["pass"])
        self.assertTrue(any("PROVENANCE:E1_ROW_FIELDS_INVALID" in x for x in out["errors"]))

    def test_named_audience_profile_fails(self):
        p=doc();p["v2_input"]["task"]["audience_profile"]["profile_id"]="EXECUTIVE"
        out=compile_membership(raw(p),source_id="TASK")
        self.assertFalse(out["pass"])
        self.assertIn("EXPLICIT_AUDIENCE_PROFILE_REQUIRED",out["errors"])

    def test_unknown_audience_profile_field_fails(self):
        p=doc();p["v2_input"]["task"]["audience_profile"]["language"]="German"
        out=compile_membership(raw(p),source_id="TASK")
        self.assertFalse(out["pass"])
        self.assertIn("AUDIENCE_PROFILE_KEYS_NOT_EXACT",out["errors"])

    def test_unknown_constraint_fails(self):
        p=doc();p["v2_input"]["task"]["audience_profile"]["constraints"]["tone"]="brief"
        out=compile_membership(raw(p),source_id="TASK")
        self.assertFalse(out["pass"])
        self.assertIn("AUDIENCE_CONSTRAINT_KEYS_NOT_EXACT",out["errors"])

    def test_extra_claim_fails(self):
        p=doc();p["v2_input"]["task"]["claims"].append({"claim_id":"x","text":"Density is 10.","required":False})
        out=compile_membership(raw(p),source_id="TASK")
        self.assertFalse(out["pass"])
        self.assertIn("EXACTLY_TWO_CLAIMS_REQUIRED",out["errors"])

    def test_extra_evidence_fails_even_if_decoy(self):
        p=doc();p["v2_input"]["task"]["evidence"].append({
          "evidence_id":"D","text":"Office count is 999 W/mK.","verified":True,
          "provenance":[{"source_id":"D"}]})
        out=compile_membership(raw(p),source_id="TASK")
        self.assertFalse(out["pass"])
        self.assertIn("EXACTLY_TWO_EVIDENCE_UNITS_REQUIRED",out["errors"])

    def test_required_claim_fails(self):
        p=doc();p["v2_input"]["task"]["claims"][0]["required"]=True
        out=compile_membership(raw(p),source_id="TASK")
        self.assertFalse(out["pass"])
        self.assertIn("EXACT_CELL_REQUIRES_TWO_OPTIONAL_CLAIMS",out["errors"])

    def test_unsupported_format_fails_via_verified_expression(self):
        p=doc();p["v2_input"]["task"]["audience_profile"]["constraints"]["output_format"]="SECTIONED_MARKDOWN"
        out=compile_membership(raw(p),source_id="TASK")
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("VERIFIED_BOUND_CELL_EXPRESSION_DID_NOT_PASS:") for x in out["errors"]))

    def test_budget_infeasible_fails_via_verified_expression(self):
        p=doc();p["v2_input"]["task"]["audience_profile"]["constraints"]["max_items"]=2
        out=compile_membership(raw(p),source_id="TASK")
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("VERIFIED_BOUND_CELL_EXPRESSION_DID_NOT_PASS:") for x in out["errors"]))

    def test_membership_receipt_is_deterministic_and_source_bound(self):
        s=raw(doc())
        a=compile_membership(s,source_id="TASK")
        b=compile_membership(s,source_id="TASK")
        c=compile_membership(s,source_id="OTHER")
        self.assertEqual(a["membership_receipt"],b["membership_receipt"])
        self.assertNotEqual(a["membership_receipt"],c["membership_receipt"])
        self.assertEqual(a["raw_source_sha256"],b["raw_source_sha256"])

    def test_no_authority_escalation(self):
        out=compile_membership(raw(doc()),source_id="TASK")
        self.assertTrue(out["pass"],out)
        for k in ("source_authorization_verified","policy_adequacy_authority","db_admission_authority","u_subtraction_authority","terminal_authority"):
            self.assertFalse(out[k])
        self.assertEqual(out["terminal_credit_delta"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
