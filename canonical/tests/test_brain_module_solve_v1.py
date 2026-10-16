"""brain.module.function.solve: describe the task, give the payload; Brain picks the function."""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as adm  # noqa: E402
from canonical.runtime import module_invocation_evidence_v1 as evidence  # noqa: E402
from canonical.runtime.bound_capabilities import brain_module_invoke_v1 as invoker  # noqa: E402
from canonical.runtime.bound_capabilities import brain_module_solve_v1 as solver  # noqa: E402

DEONTIC = "canonical/runtime/certified_deontic_rule_fragment_v1.py"
SCRATCH = ROOT / "tmp" / "test_brain_module_solve"


class SelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ev = invoker.load_evidence(ROOT)

    def test_task_and_payload_find_the_function_without_naming_it(self):
        top, _ = solver.select("parse the deontic rule", {"text": "The tenant must pay rent monthly."}, self.ev)
        self.assertEqual((top["source_path"], top["function"]), (DEONTIC, "parse_deontic_rule"))
        self.assertEqual(top["compatibility"], "EXACT_KWARGS")

    def test_cross_family_tie_fails_closed_and_lists_the_candidates(self):
        payload = {"claim_text": "Orion budget is 40.", "evidence_text": "Ledger: Orion budget is 40."}
        with self.assertRaises(invoker.ModuleInvokeRefused) as ctx:
            solver.select("classify whether the claim is supported by the evidence", payload, self.ev)
        message = str(ctx.exception)
        self.assertTrue(message.startswith("AMBIGUOUS_TASK"), message)
        self.assertIn("bounded_claim_support.py:classify_support", message)
        self.assertGreaterEqual(message.count("classify_support"), 2)

    def test_unrelated_task_or_empty_task_fails_closed(self):
        with self.assertRaises(invoker.ModuleInvokeRefused) as ctx:
            solver.select("xylophone quasar", {"text": "x"}, self.ev)
        self.assertIn("NO_FUNCTION_MATCHES_THE_TASK", str(ctx.exception))
        with self.assertRaises(invoker.ModuleInvokeRefused) as ctx:
            solver.select("the a of", {"text": "x"}, self.ev)
        self.assertIn("TASK_DESCRIPTION_REQUIRED", str(ctx.exception))

    def test_only_signature_compatible_functions_are_candidates(self):
        payload = {"claim_text": "a", "evidence_text": "b"}
        for cand in solver.rank("claim support", payload, self.ev)[:50]:
            fn = self.ev["modules"][cand["source_path"]]["functions"][cand["function"]]
            self.assertIsNotNone(solver.compatibility(fn["signature"], payload), cand)


class LiveSentenceTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(SCRATCH, ignore_errors=True)
        SCRATCH.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(SCRATCH, ignore_errors=True)

    def _solve(self, task: str, payload, name: str) -> tuple[dict, dict | None]:
        rel = SCRATCH.relative_to(ROOT).as_posix()
        (SCRATCH / (name + ".json")).write_text(json.dumps(payload), encoding="utf-8")
        goal = ('Use a Brain function for the task "%s" on the payload %s/%s.json and save the result to %s/%s_out.json.'
                % (task, rel, name, rel, name))
        result = adm.solve({"task_id": "test-solve-" + name, "goal": goal})
        out = SCRATCH / (name + "_out.json")
        return result, (json.loads(out.read_text(encoding="utf-8")) if out.exists() else None)

    def test_sentence_finds_runs_and_matches_the_guarded_direct_call(self):
        payload = {"text": "The tenant must pay rent monthly."}
        result, record = self._solve("parse the deontic rule", payload, "rule")
        self.assertTrue(result["status"].startswith("PASS"), result["status"])
        self.assertEqual(record["capability_id"], solver.CAPABILITY_ID)
        self.assertEqual((record["source_path"], record["function"]), (DEONTIC, "parse_deontic_rule"))
        self.assertEqual(record["tier"], invoker.TIER_TESTED)
        self.assertEqual(record["result"], invoker.invoke(ROOT, DEONTIC, "parse_deontic_rule", payload))
        self.assertIn("next_candidates", record["selected_by"])

    def test_ambiguous_sentence_writes_nothing(self):
        payload = {"claim_text": "Orion budget is 40.", "evidence_text": "Ledger: Orion budget is 40."}
        result, record = self._solve("classify whether the claim is supported by the evidence", payload, "amb")
        self.assertFalse(result["status"].startswith("PASS"), result["status"])
        self.assertIsNone(record)


class RegistryEntryTests(unittest.TestCase):
    def test_entry_is_verified_with_zero_wrong_self_retrievals_and_pins_files(self):
        entry = json.loads((ROOT / evidence.INVENTORY_REL).read_text(encoding="utf-8"))["capabilities"][solver.CAPABILITY_ID]
        self.assertEqual(entry["status"], "VERIFIED_BOUND_CAPABILITY")
        v = entry["verification"]
        self.assertEqual(v["adapter_sha256"], evidence._sha(ROOT / entry["source"]["adapter_path"]))
        self.assertEqual(v["evidence_sha256"], evidence._sha(ROOT / invoker.EVIDENCE_REL))
        counts = v["report"]["selection_self_retrieval"]["counts"]
        self.assertEqual(counts.get("WRONG", 0), 0)
        self.assertGreater(counts["EXACT"], 0)


if __name__ == "__main__":
    unittest.main()
