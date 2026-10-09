from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import finance_marked_mention_universe_v1 as compiler
from canonical.runtime import finance_marked_mention_universe_verify_v1 as verifier
from canonical.runtime import finance_coreference_ambiguity_control_v1 as ambiguity
from canonical.runtime import r2_finance_marked_mention_universe_direct_adequacy_v1 as route


class MarkedMentionUniverseV1Tests(unittest.TestCase):
    def _source(self, *, same_terminal=True, with_observation=False):
        source = {
            "schema": compiler.INPUT_SCHEMA,
            "domain": "FINANCE",
            "source_id": "finance:marked:test",
            "marked_mention_universe_complete": True,
            "segments": [
                {"kind": "TEXT", "text": "The "},
                {
                    "kind": "MENTION",
                    "mention_id": "bank",
                    "text": "bank",
                    "entity_class": "NONPERSON",
                    "number": "SINGULAR",
                },
                {"kind": "TEXT", "text": " rejected the "},
                {
                    "kind": "MENTION",
                    "mention_id": "waiver",
                    "text": "waiver",
                    "entity_class": "NONPERSON",
                    "number": "SINGULAR",
                },
                {"kind": "TEXT", "text": ". The request challenged "},
                {"kind": "REFERENCE", "mention_id": "it", "text": "it"},
                {"kind": "TEXT", "text": "."},
            ],
            "reference_id": "it",
            "ambiguity_owner": "USER_INTENT",
            "antecedent_terminal_signatures": {
                "bank": {
                    "terminal_signature_complete": True,
                    "terminal_signature": {
                        "action": "PRESERVE_UNCERTAINTY" if same_terminal else "ACTION_BANK"
                    },
                },
                "waiver": {
                    "terminal_signature_complete": True,
                    "terminal_signature": {
                        "action": "PRESERVE_UNCERTAINTY" if same_terminal else "ACTION_WAIVER"
                    },
                },
            },
            "observations": [],
        }
        if with_observation:
            source["observations"] = [{
                "observation_id": "explicit_reference_binding",
                "cost_units": 1,
                "outcome_map_complete": True,
                "outcomes": {
                    "bank": "SOURCE_EXPLICIT_BANK",
                    "waiver": "SOURCE_EXPLICIT_WAIVER",
                },
            }]
        return source

    def test_compiler_proves_structural_completeness_relative_to_marked_contract(self):
        out = compiler.compile_case(self._source())
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["case"]["source_text"],
            "The bank rejected the waiver. The request challenged it.",
        )
        self.assertEqual(out["candidate_antecedent_ids"], ["bank", "waiver"])
        self.assertEqual(out["mention_count"], 3)
        self.assertTrue(out["mention_universe_complete_relative_to_marked_segment_contract"])
        self.assertFalse(out["open_world_plain_text_mention_completeness_claimed"])

    def test_terminally_equivalent_marked_candidates_need_no_disambiguation(self):
        compiled = compiler.compile_case(self._source(same_terminal=True))
        result = ambiguity.compute(compiled["case"])
        self.assertEqual(result["decision"]["action"], "CONTINUE_WITHOUT_DISAMBIGUATION")
        checked = verifier.verify(self._source(same_terminal=True), result)
        self.assertTrue(checked["verified"], checked)

    def test_marked_case_selects_minimum_declared_discriminator(self):
        source = self._source(same_terminal=False, with_observation=True)
        compiled = compiler.compile_case(source)
        result = ambiguity.compute(compiled["case"])
        self.assertEqual(
            result["decision"]["action"],
            "ACQUIRE_MINIMUM_TERMINALLY_RELEVANT_DISCRIMINATOR",
        )
        self.assertEqual(result["decision"]["next_observation_id"], "explicit_reference_binding")
        self.assertTrue(verifier.verify(source, result)["verified"])

    def test_supported_reference_hidden_in_text_fails_closed(self):
        source = self._source()
        source["segments"][4]["text"] = ". It was challenged "
        with self.assertRaisesRegex(
            compiler.MarkedMentionUniverseError,
            "SUPPORTED_REFERENCE_FORM_MUST_BE_MARKED",
        ):
            compiler.compile_case(source)
        checked = verifier.verify(source, {})
        self.assertFalse(checked["verified"], checked)
        self.assertIn("SUPPORTED_REFERENCE_FORM_MUST_BE_MARKED", checked["reason"])

    def test_reference_form_mismarked_as_mention_fails_closed(self):
        source = self._source()
        source["segments"][5] = {
            "kind": "MENTION",
            "mention_id": "it",
            "text": "it",
            "entity_class": "NONPERSON",
            "number": "SINGULAR",
        }
        with self.assertRaisesRegex(
            compiler.MarkedMentionUniverseError,
            "REFERENCE_FORM_MISMARKED_AS_MENTION",
        ):
            compiler.compile_case(source)

    def test_incomplete_terminal_signature_cover_fails_closed(self):
        source = self._source()
        source["antecedent_terminal_signatures"].pop("bank")
        with self.assertRaisesRegex(
            compiler.MarkedMentionUniverseError,
            "TERMINAL_SIGNATURE_CANDIDATE_COVERAGE_INCOMPLETE",
        ):
            compiler.compile_case(source)

    def test_independent_verifier_rejects_result_tamper(self):
        source = self._source()
        compiled = compiler.compile_case(source)
        result = ambiguity.compute(compiled["case"])
        result["candidate_count"] = 99
        checked = verifier.verify(source, result)
        self.assertFalse(checked["verified"], checked)

    def test_preflight_is_pure_and_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "canonical" / "cases" / "marked.json"
            outp = root / "canonical" / "out" / "decision.json"
            inp.parent.mkdir(parents=True)
            inp.write_text(json.dumps(self._source(), sort_keys=True), encoding="utf-8")
            goal = (
                "Using the structurally complete marked finance coreference source at "
                "canonical/cases/marked.json, compute and independently verify the "
                "decision-relevant ambiguity control and save it to "
                "canonical/out/decision.json."
            )
            before = inp.read_bytes()
            result = route.preflight({"task_id": "marked-coref-preflight", "goal": goal}, repo_root=root)
            self.assertTrue(result["matched"], result)
            self.assertEqual(result["status"], "DIRECT_ADEQUACY_ROUTE_MATCHED")
            self.assertEqual(inp.read_bytes(), before)
            self.assertFalse(outp.exists())

    def test_direct_route_transaction_succeeds(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "canonical" / "cases" / "marked.json"
            outp = root / "canonical" / "out" / "decision.json"
            inp.parent.mkdir(parents=True)
            inp.write_text(json.dumps(self._source(), sort_keys=True), encoding="utf-8")
            goal = (
                "Using the structurally complete marked finance coreference source at "
                "canonical/cases/marked.json, compute and independently verify the "
                "decision-relevant ambiguity control and save it to "
                "canonical/out/decision.json."
            )
            request = {"task_id": "marked-coref-direct", "goal": goal}
            out = route.run(request, repo_root=root)
            self.assertTrue(out["pass"], out)
            self.assertTrue(out["direct_adequacy_authority"])
            self.assertTrue(out["mention_universe_complete_relative_to_marked_segment_contract"])
            self.assertFalse(out["open_world_plain_text_mention_completeness_claimed"])
            stored = json.loads(outp.read_text(encoding="utf-8"))
            self.assertEqual(stored["decision"]["action"], "CONTINUE_WITHOUT_DISAMBIGUATION")

    def test_direct_route_rolls_back_on_independent_verifier_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "canonical" / "cases" / "marked.json"
            outp = root / "canonical" / "out" / "decision.json"
            inp.parent.mkdir(parents=True)
            outp.parent.mkdir(parents=True)
            source = self._source()
            inp.write_text(json.dumps(source, sort_keys=True), encoding="utf-8")
            outp.write_text('{"old":true}\n', encoding="utf-8")
            before = outp.read_bytes()
            goal = (
                "Using the structurally complete marked finance coreference source at "
                "canonical/cases/marked.json, compute and independently verify the "
                "decision-relevant ambiguity control and save it to "
                "canonical/out/decision.json."
            )
            request = {"task_id": "marked-coref-rollback", "goal": goal}
            first = route.preflight(request, repo_root=root)
            self.assertTrue(first["matched"], first)
            good_result = ambiguity.compute(compiler.compile_case(source)["case"])
            good_verify = verifier.verify(source, good_result)
            with patch.object(route.verifier, "verify", side_effect=[
                good_verify,
                {"verified": False, "producer_independent": True, "reason": "forced"},
            ]):
                out = route.run(request, repo_root=root)
            self.assertFalse(out["pass"], out)
            self.assertTrue(out["rollback_complete"], out)
            self.assertEqual(outp.read_bytes(), before)

    def test_output_never_mints_general_semantic_or_terminal_authority(self):
        source = self._source()
        compiled = compiler.compile_case(source)
        checked = verifier.verify(source, ambiguity.compute(compiled["case"]))
        self.assertTrue(checked["verified"])
        self.assertFalse(checked["open_world_plain_text_mention_completeness_claimed"])
        self.assertFalse(checked["semantic_authority"])
        self.assertFalse(checked["policy_adequacy_authority"])
        self.assertFalse(checked["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
