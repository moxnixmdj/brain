from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.brain_witness_contamination_admissibility_v1 import (
    ARTIFACT_SCOPE,
    DELEGATION_CEILING,
    TERMINAL_V3,
    TOOL_CEILING,
    evaluate,
    git_blob_sha,
)

ROOT = Path(__file__).resolve().parents[2]
NORMALIZATION = ROOT / "canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json"
SOURCES = [TERMINAL_V3, ARTIFACT_SCOPE, TOOL_CEILING, DELEGATION_CEILING]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class BrainWitnessContaminationAdmissibilityTests(unittest.TestCase):
    def docs(self):
        normalization = json.loads(NORMALIZATION.read_text(encoding="utf-8"))
        docs = {p: load(p) for p in SOURCES}
        shas = {p: git_blob_sha(ROOT / p) for p in SOURCES}
        return normalization, docs, shas

    def test_live_catalog_is_contamination_admissible(self):
        normalization, docs, shas = self.docs()
        out = evaluate(normalization, docs, shas)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["witness_count"], 9)
        self.assertEqual(out["unique_source_count"], 4)
        self.assertEqual(out["contamination_admissible_witness_count"], 9)
        self.assertFalse(out["semantic_implication_verified"])
        self.assertFalse(out["target_atom_metric_bindings_verified"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_terminal_tuning_replay_guard_fails_closed(self):
        normalization, docs, shas = self.docs()
        docs = copy.deepcopy(docs)
        docs[TERMINAL_V3]["result_guards"]["no_tuning_replay"] = False
        out = evaluate(normalization, docs, shas)
        self.assertFalse(out["pass"])
        self.assertIn("NOT_ALL_WITNESSES_CONTAMINATION_ADMISSIBLE", out["errors"])
        self.assertTrue(any("TERMINAL_V3_GUARD_MISMATCH:no_tuning_replay" in e for e in out["errors"]))

    def test_declared_ceiling_contamination_flip_fails_closed(self):
        normalization, docs, shas = self.docs()
        docs = copy.deepcopy(docs)
        docs[TOOL_CEILING]["contamination_clean"] = False
        out = evaluate(normalization, docs, shas)
        self.assertFalse(out["pass"])
        self.assertTrue(any("CEILING_WITNESS_MISMATCH:TOOL_DISCOVERY_SELECTION_AND_LEARNING:contamination_clean" in e for e in out["errors"]))

    def test_stale_source_sha_fails_closed(self):
        normalization, docs, shas = self.docs()
        shas = dict(shas)
        shas[DELEGATION_CEILING] = "0" * 40
        out = evaluate(normalization, docs, shas)
        self.assertFalse(out["pass"])
        self.assertTrue(any("SOURCE_BLOB_SHA_MISMATCH" in e for e in out["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
