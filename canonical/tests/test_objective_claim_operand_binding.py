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

    def test_gt_binds_and_invokes_verified_evaluator(self):
        out=self.m.bind(
          "Determine whether France population growth is higher than Germany population growth.",
          fixture()
        )
        self.assertEqual(out["status"],"CLAIM_SPEC_AND_OPERANDS_BOUND",out)
        self.assertEqual(out["relation_spec"]["operator"],"GT",out)
        self.assertTrue(out["relation_result"]["predicate"],out)
        self.assertEqual(out["relation_result"]["status"],"NUMERIC_RELATION_VERIFIED",out)
        self.assertEqual(out["factual_correctness_status"],"UNVERIFIED",out)

    def test_lt_preserves_role_direction(self):
        out=self.m.bind(
          "Determine whether Germany population growth is lower than France population growth.",
          fixture()
        )
        self.assertEqual(out["relation_spec"]["operator"],"LT",out)
        self.assertTrue(out["relation_result"]["predicate"],out)
        self.assertIn("Germany",out["left_binding"]["text"])
        self.assertIn("France",out["right_binding"]["text"])

    def test_exceeds_grammar(self):
        out=self.m.bind(
          "France population growth exceeds Germany population growth.",
          fixture()
        )
        self.assertEqual(out["relation_spec"]["operator"],"GT",out)
        self.assertTrue(out["relation_result"]["predicate"],out)

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

    def test_full_coverage_extra_words_still_fail_closed_as_ambiguous(self):
        data=fixture()
        extra=dict(data["evidence_units"][0])
        extra["text"]="River Alpha annual discharge at second gauge was 1240 percent."
        extra["text_sha256"]=sha(extra["text"])
        extra["visible_text_start"]=100
        extra["visible_text_end"]=100+len(extra["text"])
        extra["evidence_unit_id"]=sha(
          f'{data["page_raw_sha256"]}:{extra["visible_text_start"]}:{extra["visible_text_end"]}:{extra["text_sha256"]}'
        )
        data["evidence_units"]=[
          {
            **data["evidence_units"][0],
            "text":"River Alpha annual discharge was 0.35 percent.",
            "text_sha256":sha("River Alpha annual discharge was 0.35 percent."),
          },
          extra,
          data["evidence_units"][1],
        ]
        # Rebuild the first unit ID after changing its text.
        first=data["evidence_units"][0]
        first["visible_text_end"]=first["visible_text_start"]+len(first["text"])
        first["evidence_unit_id"]=sha(
          f'{data["page_raw_sha256"]}:{first["visible_text_start"]}:{first["visible_text_end"]}:{first["text_sha256"]}'
        )
        out=self.m.bind(
          "Determine whether River Alpha annual discharge is higher than Germany population growth.",
          data,evaluate_relation=False
        )
        self.assertEqual(out["reason"],"LEFT_AMBIGUOUS_EVIDENCE_UNIT_FOR_ENTITY",out)

    def test_uppercase_single_letter_entity_labels_are_distinct(self):
        data=fixture(
          left_text="Database A checkpoint latency was 42 ms.",
          right_text="Database B checkpoint latency was 35 ms."
        )
        out=self.m.bind(
          "Does Database A checkpoint latency exceed Database B checkpoint latency?",
          data
        )
        self.assertEqual(out["status"],"CLAIM_SPEC_AND_OPERANDS_BOUND",out)
        self.assertEqual(out["relation_spec"]["operator"],"GT",out)
        self.assertTrue(out["relation_result"]["predicate"],out)
        self.assertIn("a",out["parsed_objective"]["left_tokens"])
        self.assertIn("b",out["parsed_objective"]["right_tokens"])

    def test_multiple_compatible_numbers_fail_closed(self):
        data=fixture("France population growth was 0.35 percent and revised to 0.40 percent.")
        out=self.m.bind(
          "Determine whether France population growth is higher than Germany population growth.",
          data,evaluate_relation=False
        )
        self.assertEqual(out["reason"],"AMBIGUOUS_COMPATIBLE_OPERAND_PAIR",out)

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
