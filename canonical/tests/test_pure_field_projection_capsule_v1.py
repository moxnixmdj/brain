from __future__ import annotations

import copy
import unittest

from canonical.runtime.pure_field_projection_capsule_v1 import (
    compile_capsule,
    semantic_equivalent,
)


CONSUMER = """
def evaluate(projection):
    authority = projection["sources"][0]["projection"]
    return {
        "closed": authority["/terminal/closed"],
        "open_count": authority["/terminal/open_count"],
    }
"""


class PureFieldProjectionCapsuleTests(unittest.TestCase):
    def documents(self):
        return {
            "canonical/governance/CURRENT.json": {
                "terminal": {
                    "closed": False,
                    "open_count": 12,
                },
                "scheduler": {
                    "generation": 44,
                    "worker": "alpha",
                },
                "telemetry": {
                    "last_refresh": "old",
                },
            }
        }

    def dependencies(self):
        return {
            "canonical/governance/CURRENT.json": [
                "/terminal/closed",
                "/terminal/open_count",
            ]
        }

    def compile(self, docs=None, source=CONSUMER):
        return compile_capsule(
            source_documents=docs or self.documents(),
            field_dependencies=self.dependencies(),
            consumer_source=source,
        )

    def test_unrelated_same_file_churn_preserves_semantic_identity(self):
        a=self.compile()
        docs=self.documents()
        docs["canonical/governance/CURRENT.json"]["scheduler"]["generation"]=999
        docs["canonical/governance/CURRENT.json"]["telemetry"]["last_refresh"]="new"
        b=self.compile(docs)
        self.assertEqual(a["semantic_identity_sha256"],b["semantic_identity_sha256"])
        self.assertTrue(semantic_equivalent(a,b))

    def test_declared_field_change_changes_semantic_identity(self):
        a=self.compile()
        docs=self.documents()
        docs["canonical/governance/CURRENT.json"]["terminal"]["open_count"]=11
        b=self.compile(docs)
        self.assertNotEqual(a["semantic_identity_sha256"],b["semantic_identity_sha256"])
        self.assertFalse(semantic_equivalent(a,b))

    def test_consumer_source_change_changes_identity_even_same_result(self):
        a=self.compile()
        source=(
            "def evaluate(projection):\n"
            "    authority = projection['sources'][0]['projection']\n"
            "    closed = authority['/terminal/closed']\n"
            "    open_count = authority['/terminal/open_count']\n"
            "    return {'closed': closed, 'open_count': open_count}\n"
        )
        b=self.compile(source=source)
        self.assertEqual(a["consumer_result"],b["consumer_result"])
        self.assertNotEqual(a["semantic_identity_sha256"],b["semantic_identity_sha256"])

    def test_selected_source_metadata_contains_only_pointer_hashes_not_full_doc(self):
        out=self.compile()
        self.assertNotIn("scheduler",str(out["selected_sources"]))
        self.assertNotIn("telemetry",str(out["selected_sources"]))
        self.assertEqual(out["selected_field_count"],2)
        self.assertFalse(out["undeclared_source_fields_material_to_identity"])

    def test_invalid_consumer_fails_closed(self):
        out=self.compile(source="import os\ndef evaluate(projection):\n    return {}\n")
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertFalse(out["execution_authority"])

    def test_missing_declared_field_fails_closed(self):
        docs=self.documents()
        del docs["canonical/governance/CURRENT.json"]["terminal"]["open_count"]
        out=self.compile(docs)
        self.assertFalse(out["pass"])
        self.assertIn("GateError",out["error"])

    def test_source_dependency_path_mismatch_fails_closed(self):
        out=compile_capsule(
            source_documents=self.documents(),
            field_dependencies={"other.json":["/x"]},
            consumer_source=CONSUMER,
        )
        self.assertFalse(out["pass"])
        self.assertIn("SOURCE_DEPENDENCY_PATH_SET_MISMATCH",out["error"])

    def test_output_is_deterministic(self):
        a=self.compile()
        b=self.compile(copy.deepcopy(self.documents()))
        self.assertEqual(a["semantic_identity_sha256"],b["semantic_identity_sha256"])
        self.assertEqual(a["projection_bundle_sha256"],b["projection_bundle_sha256"])
        self.assertEqual(a["consumer_result_sha256"],b["consumer_result_sha256"])

    def test_all_authority_remains_false(self):
        out=self.compile()
        self.assertNotIn("pass",out)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["fresh_reality_authority"])
        self.assertEqual(out["acceptance_credit_delta"],0)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["ownership_credit_delta"],0)
        self.assertEqual(out["terminal_credit_delta"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
