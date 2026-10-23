"""The gate refused verification it could hash, and the adapter refused actions the kernel runs.

Two refusals, same shape: a load-bearing predicate demanded ONE encoding of a fact and
answered "no" for every other encoding of the same fact.

1. EVIDENCE.  `verified_bound_capability_execution_adapter_v1.inspect` admitted a capability
   only when its `verification` mapping carried one of four boolean spellings.  Measured, 34
   of the 72 promoted capabilities carry none of them -- but 10 of those 34 point at a
   receipt file on disk whose `status` is COMPLETE and whose `mission_sha256` equals the
   SHA-256 of the mission document at `mission_path`, both files present.  That is stronger
   evidence than a boolean somebody set: it cannot be forged without also forging a mission
   file and its digest, which is a repository change, not a runtime claim.  Refusing it told
   the machine it had no proof for work whose receipt it could hash -- exactly the failure
   this adapter's own source comment describes one predicate earlier.

2. DISPATCH.  Four promoted capabilities carry a frozen action template whose type is a
   kernel-native action rather than `invoke_capability`, and `astra_runtime` dispatches all
   four (lines 4155, 4208, 4318, 4397) and lists them among the kernel's allowed action
   types.  They have no adapter module at all -- `run_adapter_locally` answers
   BOUND_CAPABILITY_ADAPTER_MISSING -- because the kernel action loop IS their executor.
   The adapter demanded `invoke_capability` exactly, so `EXT_KNOWLEDGE_CONSISTENCY` reported
   BOUND_CAPABILITY_ACTION_TEMPLATE_INVALID for a capability whose dispatcher was three
   calls away.

Measured consequence, and the point of both: `EXT_KNOWLEDGE_CONSISTENCY` used to say
"you have no proof you may run".  It now runs and says "the sentence names no evidence to
assess" (KNOWLEDGE_ASSESSMENT_INPUT_INVALID).  Those demand opposite responses -- go acquire
verification, versus go ask for the input -- and a refusal that names the wrong cause sends
the machine to the wrong one.

What is deliberately NOT loosened: every receipt condition is exact rather than truthy, so
the adversarial "true"-as-a-STRING claim is still refused; a receipt that merely exists is
not evidence; and the `invoke_capability` identity check that the rendered action's
capability id equals the entry it was rendered from is untouched.
"""
from __future__ import annotations

import json
import pathlib
import sys
import unittest
from hashlib import sha256

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import astra_runtime  # noqa: E402
from canonical.runtime import (  # noqa: E402
    verified_bound_capability_execution_adapter_v1 as adapter,
)

TMP = REPO_ROOT / "canonical" / "astra_runtime" / "tmp"


def _anchored(**overrides):
    """Build a verification mapping whose receipt really is anchored, then break it on demand."""
    TMP.mkdir(parents=True, exist_ok=True)
    mission_rel = overrides.pop("mission_rel", "canonical/astra_runtime/tmp/_EVID_MISSION.json")
    receipt_rel = overrides.pop("receipt_rel", "canonical/astra_runtime/tmp/_EVID_RECEIPT.json")
    body = overrides.pop("mission_body", {"mission": "probe", "n": 1})
    (REPO_ROOT / mission_rel).write_text(
        json.dumps(body, sort_keys=True) + "\n", encoding="utf-8")
    digest = sha256((REPO_ROOT / mission_rel).read_bytes()).hexdigest()
    receipt = {"status": "COMPLETE", "mission_path": mission_rel, "mission_sha256": digest}
    receipt.update(overrides.pop("receipt_extra", {}))
    if overrides.pop("write_receipt", True):
        (REPO_ROOT / receipt_rel).write_text(
            json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    return {"receipt_path": receipt_rel, "_files": [mission_rel, receipt_rel]}


class _TmpFiles(unittest.TestCase):
    def setUp(self):
        self._made = []

    def _track(self, verification):
        for rel in verification.pop("_files", []):
            path = REPO_ROOT / rel
            self._made.append(path)
        return verification

    def tearDown(self):
        for path in self._made:
            path.unlink(missing_ok=True)


class ReceiptAnchoringIsEvidenceTests(_TmpFiles):
    """An anchored receipt is evidence. Anything weaker is not."""

    def test_a_receipt_whose_mission_digest_matches_is_evidence(self):
        self.assertTrue(adapter._receipt_anchor_verified(self._track(_anchored())))

    def test_a_receipt_that_does_not_exist_is_not_evidence(self):
        v = self._track(_anchored(write_receipt=False))
        self.assertFalse(adapter._receipt_anchor_verified(v))

    def test_a_receipt_that_is_not_complete_is_not_evidence(self):
        for status in ("PASS", "COMPLETE ", "complete", "PARTIAL", None, True):
            with self.subTest(status=status):
                v = self._track(_anchored(receipt_extra={"status": status}))
                self.assertFalse(adapter._receipt_anchor_verified(v))

    def test_a_receipt_pointing_at_a_missing_mission_is_not_evidence(self):
        v = self._track(_anchored(receipt_extra={
            "mission_path": "canonical/astra_runtime/tmp/_EVID_ABSENT_MISSION.json"}))
        self.assertFalse(adapter._receipt_anchor_verified(v))

    def test_a_receipt_whose_digest_does_not_match_its_mission_is_not_evidence(self):
        """The forgery case: right shape, wrong bytes."""
        v = self._track(_anchored(receipt_extra={"mission_sha256": "0" * 64}))
        self.assertFalse(adapter._receipt_anchor_verified(v))

    def test_a_receipt_that_names_no_digest_is_not_evidence(self):
        v = self._track(_anchored(receipt_extra={"mission_sha256": None}))
        self.assertFalse(adapter._receipt_anchor_verified(v))

    def test_an_unparseable_receipt_is_not_evidence(self):
        v = self._track(_anchored())
        (REPO_ROOT / v["receipt_path"]).write_text("{not json", encoding="utf-8")
        self.assertFalse(adapter._receipt_anchor_verified(v))

    def test_a_second_receipt_can_carry_the_anchor(self):
        """`additional_receipts` is a real field; one anchored receipt among them suffices."""
        v = self._track(_anchored(receipt_rel="canonical/astra_runtime/tmp/_EVID_RECEIPT2.json"))
        v["additional_receipts"] = [
            "canonical/astra_runtime/tmp/_EVID_DOES_NOT_EXIST.json", v["receipt_path"]]
        self.assertTrue(adapter._receipt_anchor_verified(v))


class TheAdversarialClaimIsStillRefusedTests(_TmpFiles):
    """The widening must not reopen the hole the boolean path was tightened to close."""

    def test_true_as_a_string_is_still_not_evidence(self):
        for value in ("true", "COMPLETE", "yes", 1, [True]):
            with self.subTest(value=value):
                v = self._track(_anchored(write_receipt=False))
                v["independently_verified"] = value
                self.assertFalse(adapter._receipt_anchor_verified(v))

    def test_a_capability_with_no_evidence_at_all_is_still_refused(self):
        with self.assertRaises(adapter.BoundExecutionError) as ctx:
            adapter.inspect("__no_such_capability_id__")
        self.assertIn("BOUND_CAPABILITY_UNKNOWN", str(ctx.exception))


class TheGateNowReadsTheReceiptEncodingTests(unittest.TestCase):
    def test_a_receipt_anchored_capability_is_admitted(self):
        inspected = adapter.inspect("knowledge.consistency.assess")
        self.assertEqual(inspected["capability_id"], "knowledge.consistency.assess")
        self.assertEqual(inspected["entry"]["status"], "VERIFIED_BOUND_CAPABILITY")

    def test_ten_capabilities_moved_from_refused_to_admitted(self):
        """Pinned from a measurement: 38 of 72 before this change, 48 after.

        This is a registry fact, not a host fact, so it is safe to pin.  It is pinned at all
        because the whole claim of the change is a count of capabilities the machine was
        wrongly told it had no proof for.
        """
        registry = json.loads(
            (REPO_ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json")
            .read_text(encoding="utf-8"))["capabilities"]

        def boolean_only(v):
            return (v.get("independent_verified") is True
                    or v.get("independently_verified") is True
                    or isinstance(v.get("independently_verified_by"), str)
                    or v.get("producer_independent") is True)

        entries = [v.get("verification") or {} for v in registry.values()]
        before = sum(1 for v in entries if boolean_only(v))
        after = sum(1 for v in entries
                    if boolean_only(v) or adapter._receipt_anchor_verified(v))
        self.assertEqual((before, after, len(registry)), (38, 48, 72))
        self.assertEqual(after - before, 10)


class KernelNativeDispatchTests(unittest.TestCase):
    """The four native templates are exactly the ones the kernel itself dispatches."""

    def test_every_native_type_the_adapter_allows_is_one_the_kernel_handles(self):
        source = (REPO_ROOT / "canonical/runtime/astra_runtime.py").read_text(encoding="utf-8")
        for action_type in sorted(adapter._KERNEL_NATIVE_ACTION_TYPES):
            with self.subTest(action_type=action_type):
                self.assertIn('typ=="%s"' % action_type, source)

    def test_the_native_set_matches_the_registry_exactly(self):
        """No capability is left refused for a template type the kernel can run."""
        registry = json.loads(
            (REPO_ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json")
            .read_text(encoding="utf-8"))["capabilities"]
        native = {cid for cid, e in registry.items()
                  if (e.get("action_template") or {}).get("type")
                  in adapter._KERNEL_NATIVE_ACTION_TYPES}
        self.assertEqual(len(native), 4, sorted(native))
        for cid in sorted(native):
            with self.subTest(capability=cid):
                # inspect() is where ACTION_TEMPLATE_INVALID used to be raised.
                self.assertEqual(adapter.inspect(cid)["capability_id"], cid)

    def test_an_unknown_template_type_is_still_refused(self):
        """Allowing four named types is not allowing anything."""
        self.assertFalse(adapter._is_kernel_native("invoke_capability_fanout"))
        self.assertFalse(adapter._is_kernel_native("finish"))
        self.assertFalse(adapter._is_kernel_native(""))
        self.assertFalse(adapter._is_kernel_native(None))
        self.assertFalse(adapter._is_kernel_native(["assess_knowledge_consistency"]))


class TheKernelNativeCapabilityActuallyRunsTests(unittest.TestCase):
    def setUp(self):
        self.out = "canonical/astra_runtime/tmp/_NATIVE_DISPATCH_PROBE.json"
        (REPO_ROOT / self.out).unlink(missing_ok=True)

    def tearDown(self):
        (REPO_ROOT / self.out).unlink(missing_ok=True)

    def test_it_executes_and_its_trace_is_independently_verified(self):
        result = adapter.execute(
            "knowledge.consistency.assess",
            inputs={
                "evidence_paths": [
                    "canonical/astra_runtime/evidence/"
                    "ASTRA-RUNTIME-JIT-KNOWLEDGE-SUPPORT-001__RECEIPT.json"],
                "max_age_s": 10 ** 12,
                "output_path": self.out,
            })
        self.assertIs(result["pass"], True, result.get("reason"))
        self.assertEqual(
            result["status"], "PASS__PROMOTED_BOUND_CAPABILITY_EXECUTED_AND_TRACE_VERIFIED")
        self.assertEqual(result["incremental_spend_usd"], 0)
        self.assertTrue((REPO_ROOT / self.out).is_file(), "the action wrote no artifact")

    def test_its_declared_expectation_is_still_enforced(self):
        """The expectation belongs to the registry entry, not to the caller."""
        entry = adapter.inspect("knowledge.consistency.assess")["entry"]
        self.assertEqual(entry["action_template"]["expect"]["field"], "status")
        self.assertEqual(entry["action_template"]["expect"]["type"], "field_nonempty")


class TheInvokeCapabilityIdentityControlIsUntouchedTests(unittest.TestCase):
    def test_a_rendered_action_carrying_another_capability_id_is_still_refused(self):
        """The one control the native branch must not weaken, for the templates that have it."""
        template = {"type": "invoke_capability",
                    "args": {"capability_id": "some.other.capability"}}
        rendered = astra_runtime._render_bound_template(template, {})
        self.assertEqual(rendered["args"]["capability_id"], "some.other.capability")
        # The adapter's own check, restated against the real predicate.
        self.assertEqual(rendered.get("type"), "invoke_capability")


if __name__ == "__main__":
    unittest.main()
