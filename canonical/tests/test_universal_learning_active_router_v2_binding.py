from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / "canonical/governance/UNIVERSAL_LEARNING_ACTIVE_ROUTER_V2.json"


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class UniversalLearningActiveRouterV2BindingTests(unittest.TestCase):
    def test_every_bound_component_matches_exact_blob(self):
        gov = json.loads(GOV.read_text(encoding="utf-8"))
        for rel, expected in gov["exact_bound_components"].items():
            with self.subTest(path=rel):
                self.assertEqual(blob_sha(ROOT / rel), expected)

    def test_trusted_execution_requires_v1_and_zero_novelty_delta(self):
        gov = json.loads(GOV.read_text(encoding="utf-8"))
        self.assertEqual(
            gov["trusted_route_rule"],
            "V1_USE_VERIFIED_CAPABILITY_AND_NOVELTY_DELTA_EMPTY",
        )

    def test_unknown_domain_bridge_is_explicitly_partial(self):
        gov = json.loads(GOV.read_text(encoding="utf-8"))
        bridge = gov["unknown_domain_bridge"]
        self.assertEqual(bridge["status"], "STRUCTURAL_PARTIAL_ONLY")
        self.assertFalse(bridge["unknown_domain_acceptance_proved"])
        self.assertEqual(gov["acceptance_credit_delta"], 0)
        self.assertEqual(gov["ownership_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
