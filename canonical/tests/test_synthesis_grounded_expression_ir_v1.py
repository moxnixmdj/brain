import unittest

from canonical.runtime.synthesis_grounded_expression_ir_v1 import solve


def base_task(*, output_format="BULLETS"):
    return {
        "schema": "PROJECT_BRAIN_SYNTHESIS_C2_INPUT_V1",
        "task": {
            "title": "Decision brief",
            "items": [
                {
                    "id": "C1",
                    "kind": "CLAIM",
                    "text": "Revenue increased to 12 million.",
                    "provenance": [{"source_id": "LEDGER", "locator": "p4"}],
                    "section": "Findings",
                },
                {
                    "id": "U1",
                    "kind": "UNCERTAINTY",
                    "text": "The forecast range remains wide.",
                    "provenance": [{"source_id": "FORECAST", "locator": "table2"}],
                    "section": "Risks",
                },
                {
                    "id": "X1",
                    "kind": "CONFLICT",
                    "text": "Two sources disagree on unit cost.",
                    "provenance": [
                        {"source_id": "LEDGER", "locator": "p7"},
                        {"source_id": "FORECAST", "locator": "p2"},
                    ],
                    "section": "Risks",
                },
            ],
            "constraints": {
                "output_format": output_format,
                "citation_mode": "INLINE_SOURCE_IDS",
                "item_order": "INPUT",
                "required_sections": ["Findings", "Risks"] if output_format == "SECTIONED_MARKDOWN" else [],
                "allowed_sections": ["Findings", "Risks"],
                "max_items": 3,
                "max_chars": 5000,
                "heading_level": 2,
                "require_title": True,
                "style": "VERBATIM_GROUNDED",
            },
        },
    }


class GroundedExpressionIRTests(unittest.TestCase):
    def test_bullets_preserve_all_content_and_provenance(self):
        out = solve(base_task())
        self.assertEqual(out["status"], "PASS", out)
        self.assertEqual(out["audit"]["input_item_count"], 3)
        self.assertEqual(out["audit"]["rendered_item_count"], 3)
        self.assertEqual(out["audit"]["dropped_item_count"], 0)
        self.assertEqual(out["audit"]["new_material_claim_count"], 0)
        self.assertIn("Revenue increased to 12 million. [src:LEDGER@p4]", out["rendered_text"])
        self.assertIn("Uncertainty: The forecast range remains wide. [src:FORECAST@table2]", out["rendered_text"])
        self.assertIn("Conflict: Two sources disagree on unit cost. [src:LEDGER@p7;FORECAST@p2]", out["rendered_text"])

    def test_sectioned_markdown_realizes_required_structure(self):
        out = solve(base_task(output_format="SECTIONED_MARKDOWN"))
        self.assertEqual(out["status"], "PASS", out)
        self.assertIn("# Decision brief", out["rendered_text"])
        self.assertIn("## Findings", out["rendered_text"])
        self.assertIn("## Risks", out["rendered_text"])
        self.assertEqual([x["item_id"] for x in out["trace"]], ["C1", "U1", "X1"])

    def test_exact_explicit_order_is_honored(self):
        task = base_task()
        task["task"]["constraints"]["item_order"] = ["X1", "C1", "U1"]
        out = solve(task)
        self.assertEqual(out["status"], "PASS", out)
        self.assertEqual([x["item_id"] for x in out["trace"]], ["X1", "C1", "U1"])

    def test_infeasible_item_budget_fails_instead_of_dropping(self):
        task = base_task()
        task["task"]["constraints"]["max_items"] = 2
        out = solve(task)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "MAX_ITEMS_INFEASIBLE__NO_CONTENT_DROPPED")

    def test_infeasible_character_budget_fails_instead_of_truncating(self):
        task = base_task()
        task["task"]["constraints"]["max_chars"] = 20
        out = solve(task)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "MAX_CHARS_INFEASIBLE__NO_CONTENT_TRUNCATED")

    def test_missing_provenance_fails_closed(self):
        task = base_task()
        task["task"]["items"][0]["provenance"] = []
        out = solve(task)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "PROVENANCE_REQUIRED")

    def test_ambiguous_provenance_locator_delimiters_fail_closed(self):
        task = base_task()
        task["task"]["items"][0]["provenance"][0]["locator"] = "p4;FAKE@p9"
        out = solve(task)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "LOCATOR_UNSAFE")

    def test_sectioned_markdown_preserves_interleaved_exact_item_order(self):
        task = base_task(output_format="SECTIONED_MARKDOWN")
        task["task"]["items"][2]["section"] = "Findings"
        out = solve(task)
        self.assertEqual(out["status"], "PASS", out)
        self.assertEqual([x["item_id"] for x in out["trace"]], ["C1", "U1", "X1"])
        self.assertEqual(out["rendered_text"].count("## Findings"), 2)
        self.assertLess(out["rendered_text"].index("Revenue increased"), out["rendered_text"].index("The forecast range"))
        self.assertLess(out["rendered_text"].index("The forecast range"), out["rendered_text"].index("Two sources disagree"))

    def test_unknown_writing_constraint_is_not_silently_ignored(self):
        task = base_task()
        task["task"]["constraints"]["tone"] = "persuasive"
        out = solve(task)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(out["reason"].startswith("UNSUPPORTED_CONSTRAINT:"))

    def test_unsupported_semantic_kind_is_not_asserted(self):
        task = base_task()
        task["task"]["items"][0]["kind"] = "UNSUPPORTED_CLAIM"
        out = solve(task)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "KIND_UNSUPPORTED")

    def test_bad_order_cannot_drop_an_item(self):
        task = base_task()
        task["task"]["constraints"]["item_order"] = ["C1", "U1"]
        out = solve(task)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "ITEM_ORDER_MUST_BE_EXACT_PERMUTATION")

    def test_section_constraints_fail_closed(self):
        task = base_task(output_format="SECTIONED_MARKDOWN")
        task["task"]["constraints"]["required_sections"].append("Recommendations")
        out = solve(task)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "REQUIRED_SECTION_MISSING")

    def test_no_terminal_or_promotion_authority(self):
        out = solve(base_task())
        self.assertFalse(out["terminal_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main()
