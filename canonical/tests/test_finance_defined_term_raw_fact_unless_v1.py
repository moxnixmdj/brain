from __future__ import annotations

import copy
import hashlib
import json
import unittest

from canonical.runtime.source_contract_compiler import (
    atomize_source,
    semantic_unit_id,
    obligation_lower_bound,
)
from canonical.runtime import finance_defined_term_raw_fact_unless_branch_v1 as producer
from canonical.runtime import finance_defined_term_raw_fact_unless_verify_v1 as verifier


POLICY = (
    "Total exposure means exposure_amount.\n"
    "Apply Rule A unless Total exposure is at least 125.50.\n"
)
SOURCE = "finance-policy"


def facts(value="130.00"):
    return json.dumps({
        "schema_id": "FINANCE_TYPED_CONTEXT_V1",
        "fields": {
            "exposure_amount": {"type": "DECIMAL_STRING", "value": value},
        },
    }, separators=(",", ":"))


def coverage(text=POLICY, source=SOURCE):
    atoms = atomize_source(text, source)
    units = []
    dispositions = []
    requirements = []
    manifest_rows = []
    req_counter = 0

    for atom in atoms:
        lower = obligation_lower_bound(atom.text)
        if not (atom.normative or atom.high_risk):
            dispositions.append({
                "atom_id": atom.atom_id,
                "kind": "INFORMATIVE",
                "rationale": (
                    "definition semantics are certified separately by the "
                    "defined-term semantic proof"
                ),
                "requirement_ids": [],
            })
            continue

        if lower <= 1:
            spans = [(0, len(atom.text))]
        else:
            marker = atom.text.lower().find("unless")
            if marker <= 0 or lower != 2:
                raise AssertionError("unexpected risky-source fixture shape")
            spans = [(0, marker), (marker, len(atom.text))]

        req_ids = []
        for start_i, end_i in spans:
            req_counter += 1
            rid = f"R{req_counter}"
            eid = f"E{req_counter}"
            sid = semantic_unit_id(atom.atom_id, start_i, end_i)
            span_text = atom.text[start_i:end_i]
            units.append({
                "atom_id": atom.atom_id,
                "start": start_i,
                "end": end_i,
                "text_sha256": hashlib.sha256(span_text.encode()).hexdigest(),
                "kind": "BEHAVIOR",
                "semantic_fingerprint": f"finance-defined-term-{req_counter}",
                "rationale": "operative finance source semantics",
            })
            requirements.append({
                "id": rid,
                "source_atom_ids": [atom.atom_id],
                "source_semantic_unit_ids": [sid],
                "evidence_ids": [eid],
            })
            manifest_rows.append({
                "id": f"u{req_counter:04d}",
                "start": atom.start + start_i,
                "end": atom.start + end_i,
                "evidence_ids": [eid],
            })
            req_ids.append(rid)

        dispositions.append({
            "atom_id": atom.atom_id,
            "kind": "BEHAVIOR",
            "rationale": "operative finance source",
            "requirement_ids": req_ids,
        })

    return {
        "source_coverage_manifest": {"units": manifest_rows},
        "source_semantic_coverage": {
            "dispositions": dispositions,
            "requirements": requirements,
            "extractor_units": {
                "extractor-a": copy.deepcopy(units),
                "extractor-b": copy.deepcopy(units),
            },
        },
    }


def case(value="130.00"):
    c = {
        "schema": producer.INPUT_SCHEMA,
        "policy_source_id": SOURCE,
        "policy_source_text": POLICY,
        "fact_source_id": "finance-facts",
        "fact_source": facts(value),
    }
    c.update(coverage())
    return c


class FinanceDefinedTermRawFactUnlessTests(unittest.TestCase):
    def test_true_numeric_condition_selects_exception_and_verifies(self):
        c = case("130.00")
        out = producer.compute(c)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["condition_holds"])
        self.assertEqual(out["defined_term"], "Total exposure")
        self.assertEqual(out["field_name"], "exposure_amount")
        self.assertEqual(out["selected_branch"], "EXCEPTION_BRANCH")
        checked = verifier.verify(c, out)
        self.assertTrue(checked["verified"], checked)
        self.assertTrue(checked["producer_independent"])

    def test_false_numeric_condition_selects_ordinary_and_verifies(self):
        c = case("100.00")
        out = producer.compute(c)
        self.assertFalse(out["condition_holds"])
        self.assertEqual(out["selected_branch"], "ORDINARY_BRANCH")
        checked = verifier.verify(c, out)
        self.assertTrue(checked["verified"], checked)

    def test_boolean_defined_term(self):
        policy = (
            "Material exception means exception_holds.\n"
            "Apply Rule A unless Material exception is true.\n"
        )
        raw = json.dumps({
            "schema_id": "FINANCE_TYPED_CONTEXT_V1",
            "fields": {"exception_holds": {"type": "BOOL", "value": True}},
        }, separators=(",", ":"))
        c = {
            "schema": producer.INPUT_SCHEMA,
            "policy_source_id": SOURCE,
            "policy_source_text": policy,
            "fact_source_id": "finance-facts",
            "fact_source": raw,
        }
        c.update(coverage(policy, SOURCE))
        out = producer.compute(c)
        self.assertTrue(out["condition_holds"])
        self.assertEqual(out["selected_branch"], "EXCEPTION_BRANCH")
        self.assertTrue(verifier.verify(c, out)["verified"])

    def test_duplicate_fact_key_fails_closed(self):
        c = case()
        c["fact_source"] = (
            '{"schema_id":"X","fields":{'
            '"exposure_amount":{"type":"DECIMAL_STRING","value":"130"},'
            '"exposure_amount":{"type":"DECIMAL_STRING","value":"0"}}}'
        )
        with self.assertRaisesRegex(ValueError, "CONDITION_NOT_PROVED"):
            producer.compute(c)

    def test_missing_explicit_definition_fails_closed(self):
        policy = "Apply Rule A unless Total exposure is at least 125.50.\n"
        c = {
            "schema": producer.INPUT_SCHEMA,
            "policy_source_id": SOURCE,
            "policy_source_text": policy,
            "fact_source_id": "finance-facts",
            "fact_source": facts(),
        }
        c.update(coverage(policy, SOURCE))
        with self.assertRaisesRegex(ValueError, "CONDITION_NOT_PROVED"):
            producer.compute(c)

    def test_paraphrase_not_licensed(self):
        policy = (
            "Total exposure means exposure_amount.\n"
            "Apply Rule A unless Aggregate exposure is at least 125.50.\n"
        )
        c = {
            "schema": producer.INPUT_SCHEMA,
            "policy_source_id": SOURCE,
            "policy_source_text": policy,
            "fact_source_id": "finance-facts",
            "fact_source": facts(),
        }
        c.update(coverage(policy, SOURCE))
        with self.assertRaisesRegex(ValueError, "CONDITION_NOT_PROVED"):
            producer.compute(c)

    def test_conflicting_definition_fails_closed(self):
        policy = (
            "Total exposure means exposure_amount.\n"
            "Total exposure means other_amount.\n"
            "Apply Rule A unless Total exposure is at least 125.50.\n"
        )
        raw = json.dumps({
            "schema_id": "FINANCE_TYPED_CONTEXT_V1",
            "fields": {
                "exposure_amount": {"type": "DECIMAL_STRING", "value": "130.00"},
                "other_amount": {"type": "DECIMAL_STRING", "value": "0.00"},
            },
        }, separators=(",", ":"))
        c = {
            "schema": producer.INPUT_SCHEMA,
            "policy_source_id": SOURCE,
            "policy_source_text": policy,
            "fact_source_id": "finance-facts",
            "fact_source": raw,
        }
        c.update(coverage(policy, SOURCE))
        with self.assertRaisesRegex(ValueError, "CONDITION_NOT_PROVED"):
            producer.compute(c)

    def test_structural_source_coverage_failure_blocks(self):
        c = case()
        c["source_semantic_coverage"]["extractor_units"]["extractor-b"].pop()
        with self.assertRaisesRegex(
            ValueError,
            "SOURCE_SEMANTIC_COVERAGE_NOT_PROVED",
        ):
            producer.compute(c)

    def test_tampered_result_rejected_by_independent_verifier(self):
        c = case()
        out = producer.compute(c)
        out["condition_holds"] = False
        checked = verifier.verify(c, out)
        self.assertFalse(checked["verified"])
        self.assertIn("MISMATCH:condition_holds", checked["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
