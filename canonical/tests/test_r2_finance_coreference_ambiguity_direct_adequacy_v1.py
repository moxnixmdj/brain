from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import finance_coreference_ambiguity_control_v1 as producer
from canonical.runtime import finance_coreference_ambiguity_control_verify_v1 as verifier
from canonical.runtime import r2_finance_coreference_ambiguity_direct_adequacy_v1 as route
from canonical.runtime import r2_direct_end_to_end_adequacy_v15 as router


def _mention(mid, text, start, end, sent, *, entity="UNKNOWN", number="UNKNOWN", ref=False):
    return {
        "mention_id": mid,
        "text": text,
        "start": start,
        "end": end,
        "sentence_index": sent,
        "entity_class": entity,
        "number": number,
        "is_reference": ref,
    }


class BoundedCoreferenceAmbiguityV1Tests(unittest.TestCase):
    def _case(self, same_terminal=True, with_observation=False):
        source = "The bank rejected the waiver. The request challenged it."
        bank_start = source.index("bank")
        waiver_start = source.index("waiver")
        it_start = source.rindex("it")
        case = {
            "schema": producer.INPUT_SCHEMA,
            "domain": "FINANCE",
            "source_id": "finance:test",
            "source_text": source,
            "mention_universe_complete": True,
            "mentions": [
                _mention("bank", "bank", bank_start, bank_start + 4, 0, entity="NONPERSON", number="SINGULAR"),
                _mention("waiver", "waiver", waiver_start, waiver_start + 6, 0, entity="NONPERSON", number="SINGULAR"),
                _mention("it", "it", it_start, it_start + 2, 1, entity="NONPERSON", number="SINGULAR", ref=True),
            ],
            "reference_id": "it",
            "ambiguity_owner": "USER_INTENT",
            "antecedent_terminal_signatures": {
                "bank": {
                    "terminal_signature_complete": True,
                    "terminal_signature": {"action": "PRESERVE_UNCERTAINTY" if same_terminal else "ACTION_BANK"},
                },
                "waiver": {
                    "terminal_signature_complete": True,
                    "terminal_signature": {"action": "PRESERVE_UNCERTAINTY" if same_terminal else "ACTION_WAIVER"},
                },
            },
            "observations": [],
        }
        if with_observation:
            case["observations"] = [{
                "observation_id": "explicit_reference_binding",
                "cost_units": 1,
                "outcome_map_complete": True,
                "outcomes": {
                    "bank": "SOURCE_EXPLICIT_BANK",
                    "waiver": "SOURCE_EXPLICIT_WAIVER",
                },
            }]
        return case

    def test_terminally_equivalent_candidates_need_no_resolution(self):
        out = producer.compute(self._case(same_terminal=True))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["candidate_antecedent_ids"], ["bank", "waiver"])
        self.assertEqual(out["decision"]["action"], "CONTINUE_WITHOUT_DISAMBIGUATION")
        self.assertFalse(out["antecedent_identity_asserted"])
        self.assertFalse(out["semantic_truth_authority"])

    def test_terminally_distinct_user_ambiguity_asks_when_no_separator_exists(self):
        out = producer.compute(self._case(same_terminal=False))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["decision"]["action"], "ASK_USER_MINIMUM_CLARIFICATION")
        self.assertTrue(out["ambiguity_preserved"])

    def test_minimum_declared_discriminator_is_selected(self):
        out = producer.compute(self._case(same_terminal=False, with_observation=True))
        self.assertEqual(
            out["decision"]["action"],
            "ACQUIRE_MINIMUM_TERMINALLY_RELEVANT_DISCRIMINATOR",
        )
        self.assertEqual(out["decision"]["next_observation_id"], "explicit_reference_binding")

    def test_incomplete_mention_universe_fails_closed(self):
        case = self._case()
        case["mention_universe_complete"] = False
        with self.assertRaisesRegex(ValueError, "MENTION_UNIVERSE_COMPLETENESS_REQUIRED"):
            producer.compute(case)

    def test_incomplete_terminal_cover_fails_closed(self):
        case = self._case()
        case["antecedent_terminal_signatures"].pop("bank")
        with self.assertRaisesRegex(ValueError, "TERMINAL_SIGNATURE_CANDIDATE_COVERAGE_INCOMPLETE"):
            producer.compute(case)

    def test_independent_verifier_rejects_tamper(self):
        case = self._case()
        out = producer.compute(case)
        out["candidate_count"] = 99
        checked = verifier.verify(case, out)
        self.assertFalse(checked["verified"], checked)

    def test_direct_route_transaction_succeeds_and_verifies(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "canonical" / "cases" / "case.json"
            outp = root / "canonical" / "out" / "result.json"
            inp.parent.mkdir(parents=True)
            inp.write_text(json.dumps(self._case(), sort_keys=True), encoding="utf-8")
            goal = (
                "Using the bounded finance coreference ambiguity case at canonical/cases/case.json, "
                "compute and independently verify the decision-relevant ambiguity control and save it to "
                "canonical/out/result.json."
            )
            request = {"task_id": "coref-direct", "goal": goal}
            result = route.run(request, repo_root=root)
            self.assertTrue(result["pass"], result)
            self.assertTrue(outp.is_file())
            stored = json.loads(outp.read_text(encoding="utf-8"))
            self.assertEqual(stored["decision"]["action"], "CONTINUE_WITHOUT_DISAMBIGUATION")
            self.assertEqual(result["route_id"], route.ROUTE_ID)

    def test_direct_route_rolls_back_on_verifier_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "canonical" / "cases" / "case.json"
            outp = root / "canonical" / "out" / "result.json"
            inp.parent.mkdir(parents=True)
            outp.parent.mkdir(parents=True)
            inp.write_text(json.dumps(self._case(), sort_keys=True), encoding="utf-8")
            outp.write_text('{"old":true}\n', encoding="utf-8")
            before = outp.read_bytes()
            goal = (
                "Using the bounded finance coreference ambiguity case at canonical/cases/case.json, "
                "compute and independently verify the decision-relevant ambiguity control and save it to "
                "canonical/out/result.json."
            )
            request = {"task_id": "coref-rollback", "goal": goal}
            good = route.preflight(request, repo_root=root)
            self.assertTrue(good["matched"], good)
            first = route.verifier.verify(self._case(), route.producer.compute(self._case()))
            with patch.object(route.verifier, "verify", side_effect=[
                first,
                {
                    "verified": False,
                    "producer_independent": True,
                    "reason": "forced",
                },
            ]):
                result = route.run(request, repo_root=root)
            self.assertFalse(result["pass"], result)
            self.assertTrue(result["rollback_complete"], result)
            self.assertEqual(outp.read_bytes(), before)

    def test_v15_delegates_unmatched_requests_to_v14(self):
        sentinel = {"matched": False, "status": "DELEGATED"}
        with patch.object(router.v14, "preflight", return_value=sentinel) as delegated:
            out = router.preflight({"task_id": "x", "goal": "not this grammar"})
        self.assertEqual(out, sentinel)
        delegated.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
