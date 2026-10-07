from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

import canonical.runtime.capability_composition_capsule_integration_audit_v1 as audit


def bound_texts():
    texts, errors = audit._load_bound_sources(audit.ROOT)
    if errors:
        raise AssertionError(errors)
    return texts


class CapabilityCompositionCapsuleIntegrationAuditTests(unittest.TestCase):
    def test_exact_bound_sources_pass(self):
        out = audit.evaluate()
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__CAPABILITY_PLANNED_CROSS_CAPABILITY_STATE_IS_CAPSULE_MEDIATED",
        )
        self.assertIn("SEMANTIC_DECLARATION_COMPLETENESS", out["remaining"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_missing_planner_capsule_activation_fails(self):
        texts = bound_texts()
        astra = texts["astra_runtime"].replace(
            'derived["_composition_capsule_enforced"]=True',
            'derived["_composition_capsule_enforced"]=False',
            1,
        )
        out = audit.evaluate_texts(astra, texts["guard_v2"], texts["capsule_v2"])
        self.assertFalse(out["pass"])
        self.assertIn("planner_forces_capsule_enforcement", out["errors"])

    def test_missing_result_commit_fails(self):
        texts = bound_texts()
        astra = texts["astra_runtime"].replace(
            "composition_guard.append_action_result(",
            "composition_guard.DO_NOT_COMMIT(",
            1,
        )
        out = audit.evaluate_texts(astra, texts["guard_v2"], texts["capsule_v2"])
        self.assertFalse(out["pass"])
        self.assertIn("result_committed_to_capsule", out["errors"])

    def test_missing_provider_identity_guard_fails(self):
        texts = bound_texts()
        guard = texts["guard_v2"].replace(
            '"CAPSULE_PROVIDER_IDENTITY_MISMATCH:"',
            '"PROVIDER_IDENTITY_NOT_CHECKED:"',
            1,
        )
        out = audit.evaluate_texts(texts["astra_runtime"], guard, texts["capsule_v2"])
        self.assertFalse(out["pass"])
        self.assertIn("guard_rejects_provider_identity_drift", out["errors"])

    def test_non_append_only_capsule_fails(self):
        texts = bound_texts()
        capsule = texts["capsule_v2"].replace(
            'out["records"] = list(out["records"]) + [record]',
            'out["records"] = [record]',
            1,
        )
        out = audit.evaluate_texts(texts["astra_runtime"], texts["guard_v2"], capsule)
        self.assertFalse(out["pass"])
        self.assertIn("capsule_is_append_only", out["errors"])

    def test_bound_source_sha_drift_fails_closed(self):
        bad = copy.deepcopy(audit.SOURCES)
        rel, _sha = bad["astra_runtime"]
        bad["astra_runtime"] = (rel, "0" * 40)
        with patch.object(audit, "SOURCES", bad):
            out = audit.evaluate()
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED__SOURCE_BINDING_FAILED")
        self.assertTrue(
            any(x.startswith("SOURCE_BLOB_DRIFT:astra_runtime") for x in out["errors"]),
            out,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
