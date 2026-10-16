"""brain.module.function.invoke: test-evidenced repository modules callable read-only from a sentence."""
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

CLAIM_MODULE = "canonical/runtime/bounded_claim_support.py"
SCRATCH = ROOT / "tmp" / "test_brain_module_invoke"


def _registry() -> dict:
    return json.loads((ROOT / evidence.INVENTORY_REL).read_text(encoding="utf-8"))["capabilities"]


class EvidenceTests(unittest.TestCase):
    def test_check_mode_finds_no_drift(self):
        self.assertEqual(evidence.check(), [])

    def test_every_admitted_module_came_from_the_unverified_inventory(self):
        data = invoker.load_evidence(ROOT)
        inventory = set(evidence.inventory_paths())
        self.assertGreater(len(data["modules"]), 0)
        self.assertEqual(set(data["modules"]) - inventory, set())
        for rel, row in data["modules"].items():
            self.assertGreater(row["test_cases_passed"], 0, rel)
            self.assertTrue(row["tests"], rel)
            self.assertTrue(row["functions"], rel)

    def test_inventory_rows_themselves_stay_unexecutable(self):
        caps = _registry()
        flipped = [k for k, v in caps.items()
                   if (v.get("source") or {}).get("type") == "repository_python_source" and v.get("status") == "VERIFIED_BOUND_CAPABILITY"]
        self.assertEqual(flipped, [])


class InvokerSafetyTests(unittest.TestCase):
    def test_read_only_guard_refuses_every_effect_probe(self):
        report = evidence._probe_guard(ROOT)
        self.assertEqual(report["escaped"], [])
        self.assertEqual(sorted(report["refused"]), sorted(list(evidence._PROBES) + ["import_effects"]))
        failed = [name for name, ok in report["binding"].items() if not ok]
        self.assertEqual(failed, [])

    def test_admission_refuses_unlisted_and_drifted_calls(self):
        failed = [name for name, ok in evidence._probe_admission(ROOT, invoker.load_evidence(ROOT)).items() if not ok]
        self.assertEqual(failed, [])


class LiveRouteTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(SCRATCH, ignore_errors=True)
        SCRATCH.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(SCRATCH, ignore_errors=True)

    def _solve(self, function: str, payload, name: str) -> tuple[dict, dict | None]:
        rel = SCRATCH.relative_to(ROOT).as_posix()
        (SCRATCH / (name + ".json")).write_text(json.dumps(payload), encoding="utf-8")
        goal = ("Invoke function %s of module %s with the payload %s/%s.json and save the result to %s/%s_out.json."
                % (function, CLAIM_MODULE, rel, name, rel, name))
        result = adm.solve({"task_id": "test-invoke-" + name, "goal": goal})
        out = SCRATCH / (name + "_out.json")
        return result, (json.loads(out.read_text(encoding="utf-8")) if out.exists() else None)

    def test_plain_sentence_invokes_the_module_and_matches_a_direct_call(self):
        from canonical.runtime.bounded_claim_support import classify_support
        cases = {
            "support": ("Orion budget is 40.", "Audited ledger reports that Orion budget is 40.", "SUPPORTS"),
            "conflict": ("Orion budget is 40.", "A draft memo states Orion budget is 45.", "CONFLICTS"),
        }
        for name, (claim, ev, relation) in cases.items():
            with self.subTest(name):
                result, record = self._solve("classify_support", {"claim_text": claim, "evidence_text": ev}, name)
                self.assertTrue(result["status"].startswith("PASS"), result["status"])
                self.assertEqual(record["result"], classify_support(claim, ev))
                self.assertEqual(record["result"]["relation"], relation)
                self.assertEqual(record["result_correctness"], "NOT_INDEPENDENTLY_VERIFIED__MODULE_TESTS_PASSED_AT_THIS_SHA")

    def test_sentence_naming_an_unadmitted_function_fails_closed(self):
        result, record = self._solve("compile_goal_not_here", {"x": 1}, "neg")
        self.assertFalse(result["status"].startswith("PASS"), result["status"])
        self.assertIsNone(record)


class RegistryEntryTests(unittest.TestCase):
    def test_entry_is_verified_and_pins_the_current_files(self):
        entry = _registry()[invoker.CAPABILITY_ID]
        self.assertEqual(entry["status"], "VERIFIED_BOUND_CAPABILITY")
        v = entry["verification"]
        self.assertEqual(v["adapter_sha256"], evidence._sha(ROOT / entry["source"]["adapter_path"]))
        self.assertEqual(v["runner_sha256"], evidence._sha(ROOT / invoker.RUNNER_REL))
        self.assertEqual(v["evidence_sha256"], evidence._sha(ROOT / invoker.EVIDENCE_REL))
        report = v["report"]
        self.assertEqual(report["differential_agreed"], report["differential_compared"])
        self.assertGreater(report["differential_compared"], 0)
        self.assertEqual(report["guard"]["escaped"], [])


if __name__ == "__main__":
    unittest.main()
