from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256
from canonical.runtime import r2_finance_oewn_synonym_unless_direct_adequacy_v1 as direct
from canonical.runtime import finance_oewn_synonym_unless_branch_v1 as producer
from canonical.runtime import finance_oewn_synonym_unless_verify_v1 as verifier

ROOT = Path(__file__).resolve().parents[1]
PINNED = ROOT / "governance" / "H100_OEWN_REAL_LEXICAL_KNOWLEDGE_V1.json"


def _ctx(field: str, value):
    typ = "BOOL" if isinstance(value, bool) else "DECIMAL_STRING"
    c = {
        "schema_id": "FINANCE_TYPED_CONTEXT_V1",
        "fields": {field: {"type": typ, "value": value}},
    }
    return c, typed_context_sha256(c)


def _case(
    *,
    cue="upshot",
    field="result",
    context="The policy concerns a consequence effect outcome from a previous event.",
    value=True,
    literal="true",
):
    c, h = _ctx(field, value)
    return {
        "schema": "PROJECT_BRAIN_FINANCE_OEWN_SYNONYM_UNLESS_CASE_V1",
        "source_id": "oewn-finance-case",
        "source_text": f"{context} Apply Rule A unless {cue} is {literal}.",
        "target_field": field,
        "typed_context": c,
        "typed_context_sha256": h,
        "knowledge_path": "canonical/governance/H100_OEWN_REAL_LEXICAL_KNOWLEDGE_V1.json",
    }


def _goal():
    return (
        "Using the OEWN-bound typed finance UNLESS case at "
        "canonical/tmp/oewn_case.json, select and independently verify the "
        "applicable branch and save it to canonical/tmp/oewn_out.json."
    )


class R2FinanceOEWNSynonymUnlessTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def _write(self, case):
        p = self.root / "canonical/tmp/oewn_case.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(case), encoding="utf-8")
        kp = self.root / "canonical/governance/H100_OEWN_REAL_LEXICAL_KNOWLEDGE_V1.json"
        kp.parent.mkdir(parents=True, exist_ok=True)
        kp.write_bytes(PINNED.read_bytes())
        return p

    def test_inferred_synonym_consensus_upshot_to_result_passes(self):
        self._write(_case())
        out = direct.run({"task_id": "o1", "goal": _goal()}, repo_root=self.root)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["lexical_binding_mode"], "SENSE_CONSENSUS_SYNONYM")
        self.assertEqual(out["target_field"], "result")
        self.assertEqual(out["selected_branch"], "EXCEPTION_BRANCH")
        self.assertTrue(out["acceptance_receipt"]["producer_independent"])

    def test_context_word_sense_comment_to_input_passes(self):
        case = _case(
            cue="comment",
            field="input",
            context="A personal opinion belief that adds information from users is relevant.",
        )
        self._write(case)
        out = direct.run({"task_id": "o2", "goal": _goal()}, repo_root=self.root)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["lexical_binding_mode"], "CONTEXT_UNIQUE_TOP_SENSE_SYNONYM")
        self.assertEqual(out["selected_synsets"], ["06777755-n"])

    def test_context_selecting_non_target_sense_fails_closed(self):
        case = _case(
            cue="comment",
            field="input",
            context="A written explanation criticism illustration added to a book is relevant.",
        )
        self._write(case)
        out = direct.preflight({"task_id": "o3", "goal": _goal()}, repo_root=self.root)
        self.assertTrue(out["matched"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("SELECTED_SENSE_NOT_TARGET_FIELD_SYNONYM", out["reason"])

    def test_ambiguous_polysemy_without_context_fails_closed(self):
        self._write(_case(cue="comment", field="input", context="Context unavailable."))
        out = direct.preflight({"task_id": "o4", "goal": _goal()}, repo_root=self.root)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("LEXICAL_SENSE_AMBIGUOUS", out["reason"])

    def test_target_field_must_be_member_of_selected_synset(self):
        case = _case(field="not_a_member")
        case["typed_context"], case["typed_context_sha256"] = _ctx("not_a_member", True)
        self._write(case)
        out = direct.preflight({"task_id": "o5", "goal": _goal()}, repo_root=self.root)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("TARGET_FIELD_NOT_SYNONYM", out["reason"])

    def test_incomplete_query_tamper_fails_blob_binding(self):
        case = _case()
        self._write(case)
        kp = self.root / case["knowledge_path"]
        knowledge = json.loads(kp.read_text(encoding="utf-8"))
        knowledge["queries"]["upshot"]["noun_query_complete"] = False
        kp.write_text(json.dumps(knowledge), encoding="utf-8")
        out = direct.preflight({"task_id": "o6", "goal": _goal()}, repo_root=self.root)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("KNOWLEDGE_BLOB_MISMATCH", out["reason"])

    def test_query_completeness_tamper_fails_blob_binding(self):
        case = _case()
        self._write(case)
        kp = self.root / case["knowledge_path"]
        knowledge = json.loads(kp.read_text(encoding="utf-8"))
        knowledge["queries"]["upshot"]["records"][0]["members"] = ["not-upshot", "result"]
        kp.write_text(json.dumps(knowledge), encoding="utf-8")
        out = direct.preflight({"task_id": "o7", "goal": _goal()}, repo_root=self.root)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("KNOWLEDGE_BLOB_MISMATCH", out["reason"])

    def test_preflight_is_side_effect_free(self):
        self._write(_case())
        out = direct.preflight({"task_id": "o8", "goal": _goal()}, repo_root=self.root)
        self.assertEqual(out["status"], "DIRECT_ADEQUACY_ROUTE_MATCHED", out)
        self.assertFalse((self.root / "canonical/tmp/oewn_out.json").exists())

    def test_verifier_rejects_tampered_selected_branch(self):
        case = _case()
        self._write(case)
        res = producer.compute(case, repo_root=self.root)
        res["selected_branch"] = "ORDINARY_BRANCH"
        checked = verifier.verify(case, res, repo_root=self.root)
        self.assertFalse(checked["verified"])
        self.assertIn("MISMATCH:selected_branch", checked["errors"])

    def test_decimal_condition_and_ordinary_branch(self):
        case = _case(
            cue="upshot",
            field="result",
            context="The policy concerns a consequence effect outcome from a previous event.",
            value="9",
            literal="at least 10",
        )
        self._write(case)
        out = direct.run({"task_id": "o-dec", "goal": _goal()}, repo_root=self.root)
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["condition_holds"])
        self.assertEqual(out["selected_branch"], "ORDINARY_BRANCH")

    def test_verifier_rejects_tampered_proof_atom(self):
        case = _case()
        self._write(case)
        res = producer.compute(case, repo_root=self.root)
        res["condition_atom_id"] = "CERTIFIED_CONDITION::" + "0" * 64
        checked = verifier.verify(case, res, repo_root=self.root)
        self.assertFalse(checked["verified"])
        self.assertIn("MISMATCH:condition_atom_id", checked["errors"])

    def test_run_rolls_back_existing_output_on_postwrite_verifier_failure(self):
        from unittest.mock import patch

        case = _case()
        self._write(case)
        op = self.root / "canonical/tmp/oewn_out.json"
        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text('{"old":true}\n', encoding="utf-8")
        old = op.read_bytes()
        original = direct.verifier.verify
        calls = {"n": 0}

        def injected(c, result, repo_root=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return original(c, result, repo_root=repo_root)
            return {
                "verified": False,
                "producer_independent": True,
                "errors": ["forced-postwrite-failure"],
            }

        with patch.object(direct.verifier, "verify", side_effect=injected):
            out = direct.run(
                {"task_id": "o-rollback", "goal": _goal()},
                repo_root=self.root,
            )
        self.assertFalse(out["pass"], out)
        self.assertTrue(out["rollback_complete"], out)
        self.assertEqual(op.read_bytes(), old)

    def test_nonmatching_goal_claims_no_scope(self):
        out = direct.preflight(
            {"task_id": "o10", "goal": "Analyze this finance policy."},
            repo_root=self.root,
        )
        self.assertFalse(out["matched"])
        self.assertFalse(out["pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
