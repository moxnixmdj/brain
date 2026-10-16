"""brain.module.function.invoke: the repository's module surface, callable read-only, honestly tiered.

The surface is one capability, not 2,020 registrations: `bound_capabilities/brain_module_invoke_v1.py`
invokes a NAMED admitted function of a NAMED admitted module in a child process whose audit hook
refuses writes, deletes, subprocesses and sockets, after re-checking the module's and its tests'
content hashes against `MODULE_INVOCATION_EVIDENCE_V1.json` (rebuilt on this tree from a real
11,199-case test run, not copied from another branch's snapshot).

Admission of this capability itself is by independently reproduced evidence:
`live_integrated_brain_v1._receipt_admits` needs a producer receipt for this module at this content
hash AND a verification record minted by a different identity whose run reference carries a
platform-attested `github_run_id`.  The `status` field in the registry entry is decoration and the
test below asserts exactly that, because admitting on a self-written string is the failure mode
this repository already paid for once.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_receipt_lane_v1 as lane  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as adm  # noqa: E402
from canonical.runtime import unified_cognitive_fabric_v1 as fabric  # noqa: E402
from canonical.runtime import live_integrated_brain_v1 as lib  # noqa: E402
from canonical.runtime import module_invocation_evidence_v1 as evidence  # noqa: E402
from canonical.runtime.bound_capabilities import brain_module_invoke_v1 as invoker  # noqa: E402

CID = invoker.CAPABILITY_ID
ADAPTER_REL = invoker.__file__.replace(str(ROOT) + "/", "")
EXTENDED_REL = "canonical/runtime/AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json"
CLAIM_MODULE = "canonical/runtime/bounded_claim_support.py"
SCRATCH = ROOT / "canonical/astra_runtime/tmp/test_brain_module_invoke"


def _extended() -> dict:
    return json.loads((ROOT / EXTENDED_REL).read_text(encoding="utf-8"))["capabilities"]


def _projection() -> dict:
    return json.loads((ROOT / "canonical/runtime/CAPABILITY_RECEIPT_PROJECTION_V1.json").read_text(encoding="utf-8"))


class EvidenceTests(unittest.TestCase):
    def test_check_mode_finds_no_drift(self):
        self.assertEqual(evidence.check(), [])

    def test_every_admitted_function_came_from_the_inventory_with_an_honest_tier(self):
        data = invoker.load_evidence(ROOT)
        inventory = set(evidence.inventory_paths())
        self.assertGreater(len(data["modules"]), 2000)
        self.assertEqual(set(data["modules"]) - inventory, set())
        for rel, row in data["modules"].items():
            self.assertTrue(row["functions"], rel)
            for fname, fn in row["functions"].items():
                self.assertIn(fn["tier"], invoker.CORRECTNESS, (rel, fname))
                self.assertFalse(fname.startswith("_"), (rel, fname))
                if fn["tier"] == invoker.TIER_TESTED:
                    self.assertGreater(fn["passing_cases"], 0, (rel, fname))
                    self.assertTrue(row["tests"], rel)
                else:
                    self.assertEqual(fn.get("passing_cases", 0), 0, (rel, fname))

    def test_functions_named_by_a_failing_test_case_are_never_admitted(self):
        data = invoker.load_evidence(ROOT)
        self.assertTrue(data["refused"])
        for rel, fns in data["refused"].items():
            admitted = set((data["modules"].get(rel) or {}).get("functions") or {})
            self.assertEqual(admitted & set(fns), set(), rel)

    def test_inventory_rows_themselves_stay_unexecutable(self):
        flipped = [k for k, v in _extended().items()
                   if (v.get("source") or {}).get("type") == "repository_python_source"
                   and v.get("status") == "VERIFIED_BOUND_CAPABILITY"]
        self.assertEqual(flipped, [])


class AdmissionTests(unittest.TestCase):
    def test_exactly_one_registration_declares_this_surface(self):
        """One declaration, and the executable entry the lane DERIVED from the receipt.

        The 294 receipt-backed capabilities live in exactly these two places (measured), so the
        module surface is registered the same way rather than by a new mechanism."""
        declared = [cid for cid, v in _extended().items()
                    if (v.get("source") or {}).get("adapter_path") == ADAPTER_REL]
        self.assertEqual(declared, [CID])
        self.assertIn(CID, _projection()["entries"])

    def test_admission_is_decided_by_the_independent_verification_record_not_the_status(self):
        """The whole admission rule in one line: declaration present, receipt present, and
        admission still false until a DIFFERENT identity's verification record exists.

        Measured locally (no runner): receipt issued, verification absent,
        `CID in load_verified_registry()` is False and the registry stays at 361.  On the pull
        request the CI runner re-executes this same receipt, stamps the verification record with
        a platform-attested `github_run_id`, and the same expression becomes True."""
        entry = _projection()["entries"][CID]
        receipt = ROOT / entry["verification"]["receipt_path"]
        verification = ROOT / lane.verification_path_for(entry["verification"]["receipt_path"])
        self.assertTrue(receipt.is_file(), "the producer receipt must exist for a runner to verify")
        self.assertEqual(json.loads(receipt.read_text(encoding="utf-8"))["capability_id"], CID)
        self.assertEqual(entry["verification"]["module_sha256"], evidence._sha(ROOT / ADAPTER_REL))
        self.assertEqual(CID in lib.load_verified_registry(), verification.is_file())

    def test_the_declaration_trusts_the_adapter_status_and_never_the_self_reported_output_verified(self):
        expect = _extended()[CID]["action_template"]["expect"]
        self.assertEqual((expect["type"], expect["field"], expect["value"]),
                         ("field_equals", "status", "MODULE_FUNCTION_INVOKED"))
        self.assertNotIn("output_verified", json.dumps(_extended()[CID]["action_template"]))

    def test_no_door_executes_this_capability_before_the_receipt_is_independently_verified(self):
        """The invariant every door must keep, asserted as one equality so it stays true after
        the CI record lands: executed through the public door IFF admitted by the loader."""
        admitted = CID in lib.load_verified_registry()
        response = fabric.run({"payload": {"capability_id": CID, "inputs": {}}})
        executed = "MODULE_FUNCTION_INVOKED" in json.dumps(response)
        self.assertEqual(executed, admitted, json.dumps(response)[:400])

    @unittest.skipUnless(CID in lib.load_verified_registry(),
                         "activates when the CI runner has independently reproduced the receipt")
    def test_the_public_door_dispatches_the_family_by_id_once_verified(self):
        rel = SCRATCH.relative_to(ROOT).as_posix()
        SCRATCH.mkdir(parents=True, exist_ok=True)
        (SCRATCH / "live.json").write_text(json.dumps({"claim_text": "Orion budget is 40.",
                                                       "evidence_text": "Audited ledger reports that Orion budget is 40."}),
                                           encoding="utf-8")
        response = fabric.run({"payload": {"capability_id": CID, "inputs": {
            "source_path": CLAIM_MODULE, "function": "classify_support",
            "json_path": rel + "/live.json", "output_path": rel + "/live_out.json"}}})
        self.assertIn("PASS__RECEIPT_BACKED_BOUND_CAPABILITY_EXECUTED", json.dumps(response))
        record = json.loads((SCRATCH / "live_out.json").read_text(encoding="utf-8"))
        from canonical.runtime.bounded_claim_support import classify_support
        self.assertEqual(record["result"],
                         classify_support("Orion budget is 40.", "Audited ledger reports that Orion budget is 40."))
        self.assertEqual(record["tier"], invoker.TIER_TESTED)
        shutil.rmtree(SCRATCH, ignore_errors=True)


class SelfTestTests(unittest.TestCase):
    def test_the_zero_input_form_is_a_real_differential_check(self):
        verdict = invoker.run({}, ROOT)
        self.assertEqual(verdict["status"], "MODULE_FUNCTION_INVOKED", verdict)
        self.assertTrue(verdict["pass"])
        self.assertEqual(verdict["tier"], invoker.TIER_TESTED)
        self.assertEqual(verdict["differential"]["agreed"], verdict["differential"]["compared"])
        self.assertGreaterEqual(verdict["differential"]["compared"], 1)
        self.assertTrue(verdict["attempts"], "the walk must record every candidate it tried")
        self.assertEqual(verdict["model_dependency_count"], 0)

    def test_the_self_test_never_claims_per_call_correctness(self):
        verdict = invoker.run({}, ROOT)
        self.assertEqual(verdict["result_correctness"],
                         "ZERO_ARGUMENT_SELF_TEST__DIFFERENTIAL_AGREEMENT__NOT_PER_CALL_CORRECTNESS")
        self.assertEqual(verdict["guard"], "child process, audit hook: no writes, deletes, subprocesses or sockets")

    def test_the_lane_can_execute_the_adapter_as_a_contract_capability(self):
        self.assertEqual(lane.contract_shape(ADAPTER_REL), ("run", "root"))
        receipt = lane.execute_and_receipt(CID, ADAPTER_REL, "run", str(ROOT), ran_by="unittest", kind="contract")
        self.assertIsNotNone(receipt, "the receipt lane must be able to run this capability")
        self.assertEqual(receipt["observed"]["status"], "MODULE_FUNCTION_INVOKED")
        self.assertEqual(receipt["model_dependency_count"], 0)
        self.assertNotIn("output_verified", receipt["observed"])


class InvokerSafetyTests(unittest.TestCase):
    def test_read_only_guard_refuses_every_effect_probe(self):
        report = evidence._probe_guard(ROOT)
        self.assertEqual(report["escaped"], [])
        self.assertEqual(sorted(report["refused"]), sorted(list(evidence._PROBES) + ["import_effects"]))
        self.assertEqual([name for name, ok in report["binding"].items() if not ok], [])

    def test_admission_refuses_unlisted_and_drifted_calls(self):
        failed = [name for name, ok in evidence._probe_admission(ROOT, invoker.load_evidence(ROOT)).items() if not ok]
        self.assertEqual(failed, [])


class GoalDrivenInvocationTests(unittest.TestCase):
    """The executor path a door uses once admission holds: explicit inputs -> a real module call.

    Sentence-form selection of this capability is deliberately NOT claimed here: the front
    compiler's scoring matches curated capabilities by content, so a sentence that names a
    module and a function today selects a content-matching curated capability instead.  Making
    the module surface selectable from a sentence is the tool-search step, not this one; what
    this class proves is that once a door has the id, the execution is real.
    """

    def setUp(self):
        shutil.rmtree(SCRATCH, ignore_errors=True)
        SCRATCH.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(SCRATCH, ignore_errors=True)

    def _execute(self, function: str, payload, name: str, module: str = CLAIM_MODULE) -> tuple[dict, dict]:
        rel = SCRATCH.relative_to(ROOT).as_posix()
        (SCRATCH / (name + ".json")).write_text(json.dumps(payload), encoding="utf-8")
        declaration = _extended()[CID]
        entry = {**declaration, "capability_id": CID}
        action = {"type": "invoke_capability",
                  "args": {"source_path": module, "function": function,
                           "json_path": rel + "/" + name + ".json", "output_path": rel + "/" + name + "_out.json"},
                  "expect": declaration["action_template"]["expect"]}
        tool = adm.run_adapter_locally(entry, action)
        return tool, json.loads((SCRATCH / (name + "_out.json")).read_text(encoding="utf-8"))

    def test_explicit_inputs_run_a_named_module_function_and_match_a_direct_call(self):
        from canonical.runtime.bounded_claim_support import classify_support
        cases = {
            "support": ("Orion budget is 40.", "Audited ledger reports that Orion budget is 40.", "SUPPORTS"),
            "conflict": ("Orion budget is 40.", "A draft memo states Orion budget is 45.", "CONFLICTS"),
        }
        for name, (claim, ev, relation) in cases.items():
            with self.subTest(name):
                tool, record = self._execute("classify_support", {"claim_text": claim, "evidence_text": ev}, name)
                self.assertEqual(tool["status"], "MODULE_FUNCTION_INVOKED", tool)
                self.assertEqual(record["result"], classify_support(claim, ev))
                self.assertEqual(record["result"]["relation"], relation)
                self.assertEqual(record["tier"], invoker.TIER_TESTED)
                self.assertEqual(record["result_correctness"], invoker.CORRECTNESS[invoker.TIER_TESTED])
                self.assertGreater(record["evidence"]["passing_test_cases"], 0)

    def test_an_untested_function_runs_and_says_it_has_no_test_evidence(self):
        from canonical.runtime.goal_front_compiler_v1 import sentence_clauses
        text = "Hash the file. Then write the report; finally stop."
        tool, record = self._execute("sentence_clauses", {"text": text}, "untested",
                                     module="canonical/runtime/goal_front_compiler_v1.py")
        self.assertEqual(tool["status"], "MODULE_FUNCTION_INVOKED", tool)
        self.assertEqual(record["tier"], invoker.TIER_UNTESTED)
        self.assertEqual(record["result_correctness"], invoker.CORRECTNESS[invoker.TIER_UNTESTED])
        self.assertEqual(record["result"], json.loads(json.dumps(sentence_clauses(text))))

    def test_a_function_that_is_not_admitted_fails_closed_and_writes_nothing(self):
        declaration = _extended()[CID]
        (SCRATCH / "neg.json").write_text(json.dumps({"x": 1}), encoding="utf-8")
        rel = SCRATCH.relative_to(ROOT).as_posix()
        action = {"type": "invoke_capability",
                  "args": {"source_path": CLAIM_MODULE, "function": "compile_goal_not_here",
                           "json_path": rel + "/neg.json", "output_path": rel + "/neg_out.json"},
                  "expect": declaration["action_template"]["expect"]}
        try:
            adm.run_adapter_locally({**declaration, "capability_id": CID}, action)
        except Exception as exc:  # the executor loads the adapter as its own module instance
            self.assertIn("FUNCTION_NOT_ADMITTED", str(exc))
        else:
            self.fail("an unadmitted function must be refused, and nothing may be written")
        self.assertFalse((SCRATCH / "neg_out.json").exists())

    def test_the_declaration_names_the_four_inputs_a_caller_must_state(self):
        args = _extended()[CID]["action_template"]["args"]
        for key in ("source_path", "function", "json_path", "output_path"):
            self.assertEqual(args[key], "${input.%s}" % key)


if __name__ == "__main__":
    unittest.main()
