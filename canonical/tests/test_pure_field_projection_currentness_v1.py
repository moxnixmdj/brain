from __future__ import annotations

import copy
import unittest

from canonical.runtime.pure_field_projection_capsule_v1 import compile_capsule
from canonical.runtime.pure_field_projection_currentness_v1 import verify_currentness


CONSUMER = """
def evaluate(projection):
    authority = projection["sources"][0]["projection"]
    return {
        "closed": authority["/terminal/closed"],
        "open_count": authority["/terminal/open_count"],
    }
"""


class PureFieldProjectionCurrentnessTests(unittest.TestCase):
    def documents(self):
        return {
            "canonical/governance/CURRENT.json": {
                "terminal": {"closed": False, "open_count": 12},
                "scheduler": {"generation": 44, "worker": "alpha"},
                "telemetry": {"refresh": "old"},
            }
        }

    def dependencies(self):
        return {
            "canonical/governance/CURRENT.json": [
                "/terminal/closed",
                "/terminal/open_count",
            ]
        }

    def frozen(self):
        return compile_capsule(
            source_documents=self.documents(),
            field_dependencies=self.dependencies(),
            consumer_source=CONSUMER,
        )

    def verify(self, docs=None, deps=None, source=CONSUMER, frozen=None):
        return verify_currentness(
            frozen_capsule=frozen or self.frozen(),
            current_source_documents=docs or self.documents(),
            field_dependencies=deps or self.dependencies(),
            consumer_source=source,
        )

    def test_unrelated_same_file_churn_is_current(self):
        docs=self.documents()
        docs["canonical/governance/CURRENT.json"]["scheduler"]["generation"]=999
        docs["canonical/governance/CURRENT.json"]["telemetry"]["refresh"]="new"
        out=self.verify(docs=docs)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["semantic_identity_current"])
        self.assertEqual(
            out["status"],
            "PASS__PURE_FIELD_PROJECTION_SEMANTIC_IDENTITY_CURRENT",
        )

    def test_declared_field_change_is_semantic_drift(self):
        docs=self.documents()
        docs["canonical/governance/CURRENT.json"]["terminal"]["open_count"]=11
        out=self.verify(docs=docs)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__PURE_FIELD_PROJECTION_SEMANTIC_DRIFT",
        )

    def test_consumer_source_change_fails_closed_even_if_result_same(self):
        source=(
            "def evaluate(projection):\n"
            "    authority = projection['sources'][0]['projection']\n"
            "    closed = authority['/terminal/closed']\n"
            "    open_count = authority['/terminal/open_count']\n"
            "    return {'closed': closed, 'open_count': open_count}\n"
        )
        out=self.verify(source=source)
        self.assertFalse(out["pass"])
        self.assertIn("PURE_CONSUMER_SOURCE_CHANGED",out["error"])

    def test_pointer_scope_change_fails_closed(self):
        deps={
            "canonical/governance/CURRENT.json":[
                "/terminal/closed",
            ]
        }
        out=self.verify(deps=deps)
        self.assertFalse(out["pass"])
        self.assertIn("FIELD_DEPENDENCY_SCOPE_CHANGED",out["error"])

    def test_tampered_frozen_result_fails_closed(self):
        frozen=copy.deepcopy(self.frozen())
        frozen["consumer_result"]["open_count"]=999
        out=self.verify(frozen=frozen)
        self.assertFalse(out["pass"])
        self.assertIn("FROZEN_CONSUMER_RESULT_SHA256_MISMATCH",out["error"])

    def test_tampered_frozen_identity_fails_closed(self):
        frozen=copy.deepcopy(self.frozen())
        frozen["semantic_identity_sha256"]="0"*64
        out=self.verify(frozen=frozen)
        self.assertFalse(out["pass"])
        self.assertIn("FROZEN_SEMANTIC_IDENTITY_INVALID",out["error"])

    def test_missing_current_declared_field_fails_closed(self):
        docs=self.documents()
        del docs["canonical/governance/CURRENT.json"]["terminal"]["open_count"]
        out=self.verify(docs=docs)
        self.assertFalse(out["pass"])
        self.assertIn("CURRENT_CAPSULE_RECOMPUTE_FAILED",out["error"])

    def test_currentness_does_not_grant_reuse_or_consequential_authority(self):
        out=self.verify()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["prior_independent_verification_binding_required"])
        self.assertFalse(out["verification_reuse_authority_granted_by_this_module"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["fresh_reality_authority"])
        self.assertEqual(out["terminal_credit_delta"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
