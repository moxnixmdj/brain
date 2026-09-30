#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, pathlib, unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/"canonical/runtime/bound_capabilities/objective_claim_operand_binding.py"

def load():
    s=importlib.util.spec_from_file_location("objective_claim_operand_binding_test",P)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def sha(x):
    if isinstance(x,str): x=x.encode()
    return hashlib.sha256(x).hexdigest()

def fixture(left_text="France population growth was 0.35 percent.",
            right_text="Germany population growth was -0.10 percent."):
    page=sha(b"page")
    texts=[left_text,right_text]
    visible=sha("\n".join(texts))
    rows=[]; offset=0
    for text in texts:
        tsha=sha(text); start=offset; end=start+len(text)
        uid=sha(f"{page}:{start}:{end}:{tsha}")
        rows.append({
          "evidence_unit_id":uid,"source_url":"https://example.org/data",
          "page_raw_sha256":page,"visible_text_sha256":visible,
          "text":text,"text_sha256":tsha,
          "visible_text_start":start,"visible_text_end":end,
        })
        offset=end+1
    return {
      "schema":"PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2",
      "status":"OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
      "output_verified":True,
      "source_url":"https://example.org/data",
      "page_raw_sha256":page,"visible_text_sha256":visible,
      "evidence_units":rows,
    }

class BinderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.m=load()

    def relation(self,objective,data=None):
        return self.m.bind(objective,data or fixture())

    def test_gt_binds_and_invokes_verified_evaluator(self):
        out=self.relation("Determine whether France population growth is higher than Germany population growth.")
        self.assertEqual(out["status"],"CLAIM_SPEC_AND_OPERANDS_BOUND",out)
        self.assertEqual(out["relation_spec"]["operator"],"GT",out)
        self.assertTrue(out["relation_result"]["predicate"],out)
        self.assertEqual(out["relation_result"]["status"],"NUMERIC_RELATION_VERIFIED",out)
        self.assertEqual(out["factual_correctness_status"],"UNVERIFIED",out)

    def test_lt_preserves_role_direction(self):
        out=self.relation("Determine whether Germany population growth is lower than France population growth.")
        self.assertEqual(out["relation_spec"]["operator"],"LT",out)
        self.assertTrue(out["relation_result"]["predicate"],out)
        self.assertIn("Germany",out["left_binding"]["text"])
        self.assertIn("France",out["right_binding"]["text"])

    def test_single_letter_entity_discriminators_are_preserved(self):
        data=fixture(
          left_text="Planet Kepler A orbital period was 120 days.",
          right_text="Planet Kepler B orbital period was 180 days."
        )
        out=self.relation(
          "Planet Kepler A orbital period exceeds Planet Kepler B orbital period.",
          data
        )
        self.assertEqual(out["status"],"CLAIM_SPEC_AND_OPERANDS_BOUND",out)
        self.assertEqual(out["relation_spec"]["operator"],"GT",out)
        self.assertFalse(out["relation_result"]["predicate"],out)
        self.assertIn("Kepler A",out["left_binding"]["text"])
        self.assertIn("Kepler B",out["right_binding"]["text"])

    def test_gte_and_lte(self):
        a=self.relation("Determine whether France population growth is at least Germany population growth.")
        b=self.relation("Determine whether Germany population growth is at most France population growth.")
        self.assertEqual(a["relation_spec"]["operator"],"GTE",a)
        self.assertEqual(b["relation_spec"]["operator"],"LTE",b)
        self.assertTrue(a["relation_result"]["predicate"],a)
        self.assertTrue(b["relation_result"]["predicate"],b)

    def test_eq_and_ne(self):
        equal=fixture(right_text="Germany population growth was 0.35 percent.")
        eq=self.relation("Determine whether France population growth is equal to Germany population growth.",equal)
        ne=self.relation("Determine whether France population growth is different from Germany population growth.")
        self.assertEqual(eq["relation_spec"]["operator"],"EQ",eq)
        self.assertEqual(ne["relation_spec"]["operator"],"NE",ne)
        self.assertTrue(eq["relation_result"]["predicate"],eq)
        self.assertTrue(ne["relation_result"]["predicate"],ne)

    def test_exceeds_grammar(self):
        out=self.relation("France population growth exceeds Germany population growth.")
        self.assertEqual(out["relation_spec"]["operator"],"GT",out)
        self.assertTrue(out["relation_result"]["predicate"],out)

    def test_abs_diff_lte_literal_threshold(self):
        out=self.relation(
          "Determine whether France population growth and Germany population growth differ by at most 0.5 percent."
        )
        self.assertEqual(out["relation_spec"]["operator"],"ABS_DIFF_LTE",out)
        self.assertEqual(out["relation_spec"]["threshold"],"0.5 percent",out)
        self.assertTrue(out["relation_result"]["predicate"],out)

    def test_abs_diff_threshold_unit_mismatch_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"THRESHOLD_UNIT_MISMATCH"):
            self.relation(
              "Determine whether France population growth and Germany population growth differ by at most 0.5 points."
            )

    def test_exact_quoted_claim_binds_one_unit(self):
        out=self.relation(
          'Verify whether the evidence states "France population growth was 0.35 percent."'
        )
        self.assertEqual(out["status"],"CLAIM_SPEC_BOUND",out)
        self.assertEqual(out["relation_spec"]["mode"],"VERBATIM_SUPPORT",out)
        self.assertEqual(out["relation_result"]["status"],"EXACT_TEXT_SUPPORT_VERIFIED",out)
        self.assertEqual(len(out["relation_result"]["matches"]),1,out)

    def test_unsupported_compare_without_relation_fails_closed(self):
        out=self.m.bind("Compare France and Germany population growth.",fixture())
        self.assertEqual(out["status"],"UNBOUND",out)
        self.assertEqual(out["reason"],"OBJECTIVE_RELATION_AMBIGUOUS_OR_UNSUPPORTED",out)

    def test_ambiguous_left_evidence_fails_closed(self):
        data=fixture()
        row=dict(data["evidence_units"][0])
        row["visible_text_start"]=100
        row["visible_text_end"]=100+len(row["text"])
        row["evidence_unit_id"]=sha(f'{data["page_raw_sha256"]}:{row["visible_text_start"]}:{row["visible_text_end"]}:{row["text_sha256"]}')
        data["evidence_units"].append(row)
        out=self.m.bind(
          "Determine whether France population growth is higher than Germany population growth.",
          data,evaluate_relation=False
        )
        self.assertEqual(out["reason"],"LEFT_AMBIGUOUS_EVIDENCE_UNIT_FOR_ENTITY",out)

    def test_multiple_compatible_numbers_fail_closed(self):
        data=fixture("France population growth was 0.35 percent and revised to 0.40 percent.")
        out=self.m.bind(
          "Determine whether France population growth is higher than Germany population growth.",
          data,evaluate_relation=False
        )
        self.assertEqual(out["reason"],"AMBIGUOUS_COMPATIBLE_OPERAND_PAIR",out)

    def test_unitless_year_decoys_are_bypassed_by_explicit_shared_unit(self):
        data=fixture(
          "France population growth in 2025 was 0.35 percent.",
          "Germany population growth in 2024 was -0.10 percent."
        )
        out=self.m.bind(
          "Determine whether France population growth is higher than Germany population growth.",
          data
        )
        self.assertEqual(out["operand_pair"]["left_surface"],"0.35 percent",out)
        self.assertEqual(out["operand_pair"]["right_surface"],"-0.10 percent",out)

    def test_unit_mismatch_fails_closed(self):
        data=fixture(right_text="Germany population growth was -0.10 points.")
        out=self.m.bind(
          "Determine whether France population growth is higher than Germany population growth.",
          data,evaluate_relation=False
        )
        self.assertEqual(out["reason"],"NO_EXACT_UNIT_COMPATIBLE_OPERAND_PAIR",out)

    def test_role_collision_fails_closed(self):
        data=fixture(
          left_text="France population growth 0.35 percent and Germany population growth -0.10 percent.",
          right_text="Administrative reference text 1 percent."
        )
        out=self.m.bind(
          "Determine whether France population growth is higher than Germany population growth.",
          data,evaluate_relation=False
        )
        self.assertEqual(out["reason"],"LEFT_RIGHT_ROLE_COLLISION",out)

    def test_duplicate_exact_claim_is_ambiguous(self):
        data=fixture(
          "The protocol says retry after 5 seconds.",
          "The protocol says retry after 5 seconds."
        )
        out=self.m.bind(
          'Verify the exact claim "retry after 5 seconds."',
          data,evaluate_relation=False
        )
        self.assertEqual(out["reason"],"EXACT_QUOTED_CLAIM_EVIDENCE_AMBIGUOUS",out)

    def test_tampered_v2_unit_is_rejected_by_verified_evaluator(self):
        data=fixture()
        data["evidence_units"][0]["text"]+=" altered"
        with self.assertRaisesRegex(ValueError,"TEXT_HASH_MISMATCH|OFFSET_INVALID"):
            self.m.bind(
              "Determine whether France population growth is higher than Germany population growth.",
              data,evaluate_relation=True
            )

if __name__=="__main__":
    unittest.main(verbosity=2)
