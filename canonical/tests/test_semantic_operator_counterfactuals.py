import random
import unittest

from canonical.runtime.semantic_operator_counterfactuals import (
    compile_explicit_operator_contract,
    extract_semantic_operators,
    generate_counterfactual_obligations,
    expected_disposition_for_counterfactual_kind,
    validate_counterfactual_coverage,
    validate_operator_bindings,
)


def correct_bindings(text, source="case"):
    out = []
    for op in extract_semantic_operators(text, source=source):
        row = {
            "operator_id": op.operator_id,
            "semantic_class": op.semantic_class,
        }
        if op.bound_value is not None:
            row["bound_value"] = op.bound_value
        if op.semantic_class == "AMBIGUOUS_ANY":
            row["interpretations"] = ["existential_or_free_choice", "universal_in_negative_context"]
        out.append(row)
    return out


def complete_scenarios(text, source="case"):
    rows = []
    for ob in generate_counterfactual_obligations(text, source=source):
        kind = ob.counterfactual_kind
        disposition = expected_disposition_for_counterfactual_kind(kind)
        if disposition is None:
            raise AssertionError("unbound counterfactual disposition: " + kind)
        rows.append({
            "operator_id": ob.operator_id,
            "counterfactual_kind": kind,
            "expected_disposition": disposition,
        })
    return rows


class SemanticOperatorCounterfactualTests(unittest.TestCase):
    def test_extracts_high_confidence_operators(self):
        text = (
            "Every worker must not write before approval. "
            "Use at least 3 sources and at most 5 tools. "
            "Return exactly 2 files only after validation."
        )
        classes = [x.semantic_class for x in extract_semantic_operators(text, source="x")]
        self.assertEqual(
            classes,
            [
                "UNIVERSAL_QUANTIFIER",
                "PROHIBITION",
                "TEMPORAL_BEFORE",
                "MIN_INCLUSIVE",
                "MAX_INCLUSIVE",
                "EXACT_VALUE",
                "EXCLUSIVITY",
                "TEMPORAL_AFTER",
            ],
        )

    def test_shared_wrong_conceptual_error_is_rejected(self):
        text = "Use at least 3 independent sources."
        op = extract_semantic_operators(text, source="shared")[0]
        # Imagine both semantic extractors agreed on this same wrong mapping.
        wrong_consensus = [{
            "operator_id": op.operator_id,
            "semantic_class": "MAX_INCLUSIVE",
            "bound_value": 3,
        }]
        verdict = validate_operator_bindings(text, wrong_consensus, source="shared")
        self.assertFalse(verdict["pass"])
        self.assertTrue(any("SEMANTIC_OPERATOR_MISMATCH" in x for x in verdict["errors"]))

    def test_wrong_bound_is_rejected_even_if_semantic_class_matches(self):
        text = "Use no more than 7 retries."
        op = extract_semantic_operators(text, source="bound")[0]
        verdict = validate_operator_bindings(
            text,
            [{
                "operator_id": op.operator_id,
                "semantic_class": "MAX_INCLUSIVE",
                "bound_value": 8,
            }],
            source="bound",
        )
        self.assertFalse(verdict["pass"])
        self.assertTrue(any("BOUND_VALUE_MISMATCH" in x for x in verdict["errors"]))

    def test_missing_explicit_operator_fails_closed(self):
        text = "Every result must not be published before review."
        bindings = correct_bindings(text, source="missing")
        bindings.pop()
        verdict = validate_operator_bindings(text, bindings, source="missing")
        self.assertFalse(verdict["pass"])
        self.assertTrue(any("UNBOUND_EXPLICIT_SEMANTIC_OPERATOR" in x for x in verdict["errors"]))

    def test_any_requires_alternative_interpretations(self):
        text = "Do not accept any unsigned artifact."
        bindings = correct_bindings(text, source="any")
        any_row = next(x for x in bindings if x["semantic_class"] == "AMBIGUOUS_ANY")
        any_row.pop("interpretations")
        verdict = validate_operator_bindings(text, bindings, source="any")
        self.assertFalse(verdict["pass"])
        self.assertTrue(any("AMBIGUOUS_ANY_WITHOUT_ALTERNATIVES" in x for x in verdict["errors"]))

    def test_threshold_counterfactuals_cover_boundary_direction(self):
        text = "Keep at least 3 copies and at most 8 snapshots and exactly 2 receipts."
        obs = generate_counterfactual_obligations(text, source="threshold")
        kinds = {o.counterfactual_kind for o in obs}
        self.assertIn("BELOW_BOUND_MUST_BE_REJECTED", kinds)
        self.assertIn("ABOVE_BOUND_MUST_BE_REJECTED", kinds)
        self.assertIn("BELOW_EXACT_MUST_BE_REJECTED", kinds)
        self.assertIn("ABOVE_EXACT_MUST_BE_REJECTED", kinds)
        self.assertIn("EXACT_VALUE_MUST_BE_ACCEPTED", kinds)

    def test_acceptance_plan_missing_one_counterfactual_fails(self):
        text = "Every artifact must not be emitted before approval."
        scenarios = complete_scenarios(text, source="coverage")
        scenarios.pop()
        verdict = validate_counterfactual_coverage(text, scenarios, source="coverage")
        self.assertFalse(verdict["pass"])
        self.assertTrue(any("MISSING_SEMANTIC_COUNTERFACTUAL" in x for x in verdict["errors"]))

    def test_wrong_counterfactual_disposition_is_rejected(self):
        text = "The transfer must not execute before approval."
        scenarios = complete_scenarios(text, source="wrong-disposition")
        self.assertTrue(scenarios)
        scenarios[0]["expected_disposition"] = "ACCEPT"
        verdict = validate_counterfactual_coverage(
            text, scenarios, source="wrong-disposition"
        )
        self.assertFalse(verdict["pass"])
        self.assertTrue(
            any("COUNTERFACTUAL_DISPOSITION_MISMATCH" in x for x in verdict["errors"])
        )

    def test_complete_explicit_operator_contract_passes(self):
        text = (
            "Every record must not be emitted before approval. "
            "Use at least 2 sources, at most 4 retries, and exactly 1 final artifact only after validation."
        )
        result = compile_explicit_operator_contract(
            text,
            bindings=correct_bindings(text, source="full"),
            scenarios=complete_scenarios(text, source="full"),
            source="full",
        )
        self.assertTrue(result["pass"], result)

    def test_conditionals_generate_distinguishing_obligations(self):
        text = "If validation fails, retry when safe unless authority was revoked."
        kinds = {o.counterfactual_kind for o in generate_counterfactual_obligations(text, source="cond")}
        self.assertIn("ANTECEDENT_TRUE_CONSEQUENT_FALSE_MUST_FAIL", kinds)
        self.assertIn("UNLESS_EXCEPTION_BRANCH_MUST_BE_DISTINGUISHED", kinds)

    def test_operator_ids_are_source_and_position_bound(self):
        text = "Use at least 3 sources."
        a = extract_semantic_operators(text, source="A")[0]
        b = extract_semantic_operators(text, source="B")[0]
        self.assertNotEqual(a.operator_id, b.operator_id)
        self.assertEqual(a.semantic_class, b.semantic_class)

    def test_randomized_threshold_direction_2000(self):
        rng = random.Random(20261002)
        templates = [
            ("at least", "MIN_INCLUSIVE"),
            ("no less than", "MIN_INCLUSIVE"),
            ("at most", "MAX_INCLUSIVE"),
            ("no more than", "MAX_INCLUSIVE"),
            ("exactly", "EXACT_VALUE"),
        ]
        for i in range(2000):
            token, cls = rng.choice(templates)
            value = rng.randint(-1000, 1000)
            text = f"Case {i}: retain {token} {value} independently verified items."
            ops = extract_semantic_operators(text, source=f"r{i}")
            self.assertEqual(len(ops), 1)
            self.assertEqual(ops[0].semantic_class, cls)
            self.assertEqual(ops[0].bound_value, float(value))
            result = compile_explicit_operator_contract(
                text,
                bindings=correct_bindings(text, source=f"r{i}"),
                scenarios=complete_scenarios(text, source=f"r{i}"),
                source=f"r{i}",
            )
            self.assertTrue(result["pass"], result)

    def test_randomized_opposite_semantics_rejected_1000(self):
        rng = random.Random(919191)
        for i in range(1000):
            lower = bool(rng.getrandbits(1))
            token = "at least" if lower else "at most"
            expected = "MIN_INCLUSIVE" if lower else "MAX_INCLUSIVE"
            wrong = "MAX_INCLUSIVE" if lower else "MIN_INCLUSIVE"
            value = rng.randint(0, 500)
            text = f"Require {token} {value} samples."
            op = extract_semantic_operators(text, source=f"w{i}")[0]
            self.assertEqual(op.semantic_class, expected)
            verdict = validate_operator_bindings(
                text,
                [{
                    "operator_id": op.operator_id,
                    "semantic_class": wrong,
                    "bound_value": value,
                }],
                source=f"w{i}",
            )
            self.assertFalse(verdict["pass"])


if __name__ == "__main__":
    unittest.main()
