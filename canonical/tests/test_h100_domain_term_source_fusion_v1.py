from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.h100_domain_term_source_fusion_v1 import (
    resolve_lexical_role_with_fallback,
)

ROOT = Path(__file__).resolve().parents[1]
OEWN = ROOT / "governance" / "H100_OEWN_REAL_LEXICAL_KNOWLEDGE_V1.json"
FALLBACK = ROOT / "governance" / "H100_DOMAIN_TERM_SOURCE_FALLBACK_KNOWLEDGE_V1.json"
PRE = ROOT / "governance" / "H100_DOMAIN_TERM_SOURCE_FALLBACK_PREEXPOSURE_V1.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class H100DomainTermSourceFusionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oewn = load(OEWN)
        cls.fallback = load(FALLBACK)
        cls.pre = load(PRE)

    def test_all_preexposed_tasks_exact(self):
        for task in self.pre["tasks"]:
            out = resolve_lexical_role_with_fallback(
                task["cue"], task.get("context", ""), self.oewn, self.fallback
            )
            self.assertEqual(out["status"], task["expected_status"], (task, out))
            self.assertEqual(out["role"], task["expected_role"], (task, out))
            self.assertEqual(out["persistent_learned_bytes"], 0)
            self.assertEqual(out["external_frontier_model_calls"], 0)
            self.assertEqual(out["external_learned_capability_calls"], 0)

    def test_real_missing_terms_use_fallback(self):
        for cue in ("covariate", "regressor"):
            out = resolve_lexical_role_with_fallback(cue, "regression predictor", self.oewn, self.fallback)
            self.assertEqual(out["status"], "ROLE_IDENTIFIED")
            self.assertEqual(out["role"], "INPUT")
            self.assertEqual(out["fusion_source"], "DOMAIN_SOURCE_FALLBACK")
            self.assertGreaterEqual(out["source_count"], 2)

    def test_oewn_direct_resolution_has_precedence(self):
        out = resolve_lexical_role_with_fallback(
            "input", "a component goes into production", self.oewn, self.fallback
        )
        self.assertEqual(out["status"], "ROLE_IDENTIFIED")
        self.assertEqual(out["role"], "INPUT")
        self.assertEqual(out["fusion_source"], "OEWN_PRIMARY")
        self.assertFalse(out["fallback_attempted"])

    def test_oewn_ambiguity_may_not_be_overridden(self):
        mutated = copy.deepcopy(self.fallback)
        mutated["terms"]["comment"] = {
            "evidence": [
                {"source": "MGH_FREESURFER_GLM", "normalized_role": "INPUT"},
                {"source": "UCD_BIVARIATE_REGRESSION", "normalized_role": "INPUT"},
            ]
        }
        out = resolve_lexical_role_with_fallback("comment", "", self.oewn, mutated)
        self.assertEqual(out["status"], "ABSTAIN_LEXICAL_SENSE_AMBIGUOUS")
        self.assertEqual(out["fusion_source"], "OEWN_PRIMARY")
        self.assertFalse(out["fallback_attempted"])

    def test_conflicting_sources_force_abstention(self):
        mutated = copy.deepcopy(self.fallback)
        mutated["terms"]["covariate"]["evidence"][1]["normalized_role"] = "TARGET"
        out = resolve_lexical_role_with_fallback("covariate", "", self.oewn, mutated)
        self.assertEqual(out["status"], "ABSTAIN_SOURCE_CONFLICT")
        self.assertIsNone(out["role"])

    def test_single_source_is_insufficient(self):
        mutated = copy.deepcopy(self.fallback)
        mutated["terms"]["regressor"]["evidence"] = mutated["terms"]["regressor"]["evidence"][:1]
        out = resolve_lexical_role_with_fallback("regressor", "", self.oewn, mutated)
        self.assertEqual(out["status"], "ABSTAIN_SOURCE_SUPPORT_INSUFFICIENT")
        self.assertIsNone(out["role"])

    def test_unpinned_term_stays_unknown(self):
        out = resolve_lexical_role_with_fallback("latent-factor-zeta", "", self.oewn, self.fallback)
        self.assertEqual(out["status"], "ABSTAIN_SOURCE_TERM_UNPINNED")
        self.assertIsNone(out["role"])

    def test_order_of_source_evidence_does_not_change_result(self):
        reversed_pack = copy.deepcopy(self.fallback)
        reversed_pack["terms"]["regressor"]["evidence"].reverse()
        a = resolve_lexical_role_with_fallback("regressor", "", self.oewn, self.fallback)
        b = resolve_lexical_role_with_fallback("regressor", "", self.oewn, reversed_pack)
        self.assertEqual((a["status"], a["role"]), (b["status"], b["role"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
