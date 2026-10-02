from __future__ import annotations

import copy
import unittest

from canonical.runtime import synthesis_required_coverage_universal_verifier_v1 as v


class SynthesisRequiredCoverageUniversalTests(unittest.TestCase):
    def docs(self):
        return (
            v._load(v.CANDIDATE),
            v._load(v.REGISTRY),
            v._load(v.TARGETS),
            v._load(v.BINDING_RECEIPT),
        )

    def shas(self):
        return {
            "runtime": v._blob(v.RUNTIME),
            "registry": v._blob(v.REGISTRY),
            "targets": v._blob(v.TARGETS),
            "binding_receipt": v._blob(v.BINDING_RECEIPT),
        }

    def test_live_exact_runtime_proves_universal_coverage_but_not_target_transport(self):
        out = v.evaluate(
            *self.docs(),
            source_shas=self.shas(),
            runtime_source=v.RUNTIME.read_text(encoding="utf-8"),
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["universal_required_coverage_proved"])
        self.assertEqual(out["brain_required_claim_coverage_lower_bound"], 1.0)
        self.assertEqual(out["theoretical_upper_bound"], 1.0)
        self.assertFalse(out["target_scope_transport_authorized"])
        self.assertIn(
            "INDEPENDENT_EXACT_OR_SUPERSET_SYNTHESIS_TARGET_SCOPE_RELATION",
            out["remaining_acceptance_blockers"],
        )
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)

    def test_required_claim_deletion_path_fails_closed(self):
        source = v.RUNTIME.read_text(encoding="utf-8")
        source = source.replace(
            "selected=required+optional",
            "selected=optional",
            1,
        )
        out = v.evaluate(
            *self.docs(),
            source_shas=self.shas(),
            runtime_source=source,
        )
        self.assertFalse(out["pass"])
        self.assertIn("SELECTED_NOT_ALWAYS_REQUIRED_PLUS_OPTIONAL", out["errors"])

    def test_candidate_cannot_self_authorize_cross_scope_transport(self):
        candidate, registry, targets, receipt = self.docs()
        candidate = copy.deepcopy(candidate)
        candidate["target_transport"]["acceptance_metric_bound_authorized"] = True
        out = v.evaluate(
            candidate,
            registry,
            targets,
            receipt,
            source_shas=self.shas(),
            runtime_source=v.RUNTIME.read_text(encoding="utf-8"),
        )
        self.assertFalse(out["pass"])
        self.assertIn("TARGET_SCOPE_TRANSPORT_MUST_REMAIN_UNAUTHORIZED", out["errors"])

    def test_existing_atom_receipt_must_not_claim_numeric_bound(self):
        candidate, registry, targets, receipt = self.docs()
        receipt = copy.deepcopy(receipt)
        receipt["numeric_metric_bounds_verified"] = True
        out = v.evaluate(
            candidate,
            registry,
            targets,
            receipt,
            source_shas=self.shas(),
            runtime_source=v.RUNTIME.read_text(encoding="utf-8"),
        )
        self.assertFalse(out["pass"])
        self.assertIn("BASELINE_BINDING_MUST_NOT_ALREADY_CLAIM_NUMERIC_BOUND", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
