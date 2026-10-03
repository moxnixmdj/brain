from __future__ import annotations

import copy
import itertools
import unittest

from canonical.runtime import tool_discovery_complete_authority_manifest_v1 as manifest
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4


def tool(tid, cost, *, available=True, authorized=True, epoch=0):
    return {
        "tool_id": tid,
        "cost": float(cost),
        "available": available,
        "authorized": authorized,
        "epoch": epoch,
        "meta": {"region": "X", "risk": 0},
    }


class CompleteAuthorityManifestTests(unittest.TestCase):
    def _instance(self):
        return manifest.build_instance(
            epoch_id="E0",
            authority_tools=[
                tool("T0", 5),
                tool("T1", 3),
                tool("T2", 1),
                tool("T3", 2),
            ],
            initial_visible_tool_ids=["T0"],
            discovery_sources=[
                {"source_id": "S0", "cost": 0.1, "available": True, "tool_ids": ["T1", "T3"]},
                {"source_id": "S1", "cost": 0.2, "available": True, "tool_ids": ["T2"]},
            ],
        )

    def test_exact_partition_validates_and_is_content_addressed(self):
        instance = self._instance()
        out = manifest.validate_instance(instance)
        self.assertTrue(out["complete_exact_partition"])
        self.assertEqual(out["authority_tool_count"], 4)
        self.assertEqual(out["discovery_source_count"], 2)
        self.assertEqual(len(out["authority_sha256"]), 64)
        self.assertEqual(len(out["partition_sha256"]), 64)

    def test_missing_authority_member_fails_closed(self):
        instance = self._instance()
        instance["discovery_sources"][1]["tool_ids"] = []
        with self.assertRaises(manifest.ManifestError):
            manifest.validate_instance(instance)

    def test_partition_overlap_fails_closed(self):
        instance = self._instance()
        instance["discovery_sources"][0]["tool_ids"].append("T2")
        with self.assertRaises(manifest.ManifestError):
            manifest.validate_instance(instance)

    def test_authority_hash_tamper_fails_closed(self):
        instance = self._instance()
        instance["authority_tools"][0]["cost"] = 999.0
        with self.assertRaisesRegex(manifest.ManifestError, "AUTHORITY_HASH_MISMATCH"):
            manifest.validate_instance(instance)

    def test_partition_hash_tamper_fails_closed(self):
        instance = self._instance()
        instance["partition_sha256"] = "0" * 64
        with self.assertRaisesRegex(manifest.ManifestError, "PARTITION_HASH_MISMATCH"):
            manifest.validate_instance(instance)

    def test_hidden_capability_matrix_cannot_enter_public_manifest(self):
        raw = tool("T0", 1)
        raw["capabilities"] = ["CAP_A"]
        with self.assertRaisesRegex(manifest.ManifestError, "TOOL_NONPUBLIC_FIELDS"):
            manifest.build_instance(
                epoch_id="E0",
                authority_tools=[raw],
                initial_visible_tool_ids=["T0"],
                discovery_sources=[],
            )

    def test_initial_public_does_not_reveal_private_partition_membership(self):
        instance = self._instance()
        public = manifest.initial_public(instance, required_capabilities=["CAP_A"])
        self.assertEqual([x["tool_id"] for x in public["visible_tools"]], ["T0"])
        self.assertNotIn("authority_tools", public)
        self.assertTrue(all("tool_ids" not in x for x in public["discovery_sources"]))

    def test_discovery_receipt_is_bound_to_epoch_authority_partition_and_source(self):
        instance = self._instance()
        public = manifest.initial_public(instance, required_capabilities=["CAP_A"])
        receipt = manifest.discover(instance, "S0")
        self.assertEqual(receipt["source_id"], "S0")
        self.assertEqual({x["tool_id"] for x in receipt["tools"]}, {"T1", "T3"})
        public = manifest.apply_discovery(public, receipt)
        self.assertEqual({x["tool_id"] for x in public["visible_tools"]}, {"T0", "T1", "T3"})
        bad = copy.deepcopy(receipt)
        bad["authority_sha256"] = "0" * 64
        with self.assertRaisesRegex(manifest.ManifestError, "RECEIPT_AUTHORITY_MISMATCH"):
            manifest.apply_discovery(public, bad)

    def _run(self, instance, support):
        public = manifest.initial_public(instance, required_capabilities=["CAP_A"])
        authority = {x["tool_id"]: x for x in manifest.authority_rows(instance)}
        for _ in range(100):
            action = v4.next_action(public)
            kind = action["action"]
            if kind == "DISCOVER":
                public = manifest.apply_discovery(
                    public,
                    manifest.discover(instance, action["source_id"]),
                )
                continue
            if kind == "PROBE":
                tid = action["tool_id"]
                public["prior_probe_receipts"].append(
                    {
                        "kind": "SAFE_CAPABILITY_PROBE",
                        "tool_id": tid,
                        "capability": action["capability"],
                        "epoch": authority[tid]["epoch"],
                        "supported": bool(support[tid]),
                    }
                )
                continue
            if kind == "SELECT":
                return action["tool_id"], public
            if kind == "ESCALATE":
                return None, public
            self.fail(action)
        self.fail("action budget exceeded")

    def test_end_to_end_v4_reaches_complete_authority_before_probe_or_select(self):
        instance = self._instance()
        selected, public = self._run(
            instance,
            {"T0": True, "T1": True, "T2": True, "T3": True},
        )
        self.assertEqual(selected, "T2")
        self.assertEqual(
            {x["source_id"] for x in public["discovery_receipts"]},
            {"S0", "S1"},
        )
        self.assertEqual(
            {x["tool_id"] for x in public["visible_tools"]},
            {"T0", "T1", "T2", "T3"},
        )

    def test_exhaustive_support_assignments_choose_global_least_cost(self):
        instance = self._instance()
        rows = manifest.authority_rows(instance)
        ids = [x["tool_id"] for x in rows]
        by_id = {x["tool_id"]: x for x in rows}
        for bits in itertools.product((False, True), repeat=len(ids)):
            support = dict(zip(ids, bits))
            selected, _ = self._run(instance, support)
            sufficient = [
                by_id[tid] for tid in ids
                if support[tid] and by_id[tid]["available"] and by_id[tid]["authorized"]
            ]
            expected = (
                min(sufficient, key=lambda x: (x["cost"], x["tool_id"]))["tool_id"]
                if sufficient else None
            )
            self.assertEqual(selected, expected, support)


if __name__ == "__main__":
    unittest.main(verbosity=2)
