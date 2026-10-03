from __future__ import annotations

import copy
import unittest

from canonical.runtime.terminal_projection_consistency_v3 import (
    PATHS,
    _git_blob_sha,
    _load,
    evaluate_documents,
)


class TerminalProjectionConsistencyV3Tests(unittest.TestCase):
    def live(self):
        docs = {key: _load(rel) for key, rel in PATHS.items()}
        shas = {rel: _git_blob_sha(rel) for rel in PATHS.values()}
        return docs, shas

    def evaluate(self, docs, shas):
        return evaluate_documents(
            docs["authority"],
            docs["baseline_scope"],
            docs["atomic_bindings"],
            docs["delegation_scope"],
            docs["delegation_reduction"],
            docs["p1_propagation"],
            shas,
        )

    def test_live_post_delegation_projection_passes(self):
        docs, shas = self.live()
        out = self.evaluate(docs, shas)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["acceptance_closed_families"], 3)
        self.assertEqual(out["acceptance_open_families"], 16)
        self.assertEqual(out["atomic_predicates_proved"], 8)
        self.assertEqual(out["atomic_predicates_unresolved"], 30)

    def test_stale_pre_delegation_authority_fails_closed(self):
        docs, shas = self.live()
        docs = copy.deepcopy(docs)
        docs["authority"]["truth"]["opus55_acceptance"] = "2/19_PASS__17/19_OPEN"
        out = self.evaluate(docs, shas)
        self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_ACCEPTANCE_MISMATCH", out["errors"])

    def test_unverified_delegation_scope_cannot_create_family_credit(self):
        docs, shas = self.live()
        docs = copy.deepcopy(docs)
        docs["delegation_scope"]["status"] = "CANDIDATE"
        out = self.evaluate(docs, shas)
        self.assertFalse(out["pass"])
        self.assertIn("DELEGATION_SCOPE_NOT_INDEPENDENT_PASS", out["errors"])

    def test_reduction_cannot_close_extra_family(self):
        docs, shas = self.live()
        docs = copy.deepcopy(docs)
        docs["delegation_reduction"]["verified_result"]["newly_closed_families"].append(
            "TOOL_DISCOVERY_SELECTION_AND_LEARNING"
        )
        out = self.evaluate(docs, shas)
        self.assertFalse(out["pass"])
        self.assertIn("DELEGATION_REDUCTION_DELTA_SET_MISMATCH", out["errors"])

    def test_atomic_ledger_must_include_delegation_delta(self):
        docs, shas = self.live()
        docs = copy.deepcopy(docs)
        docs["atomic_bindings"]["saturation"]["proved_predicate_count"] = 7
        docs["atomic_bindings"]["saturation"]["unresolved_predicate_count"] = 31
        out = self.evaluate(docs, shas)
        self.assertFalse(out["pass"])
        self.assertIn("ATOMIC_PROVED_COUNT_NOT_8", out["errors"])
        self.assertIn("ATOMIC_UNRESOLVED_COUNT_NOT_30", out["errors"])

    def test_stale_atomic_pointer_fails_closed(self):
        docs, shas = self.live()
        docs = copy.deepcopy(docs)
        docs["authority"]["sources"]["acceptance_predicate_evidence_bindings_reconciled"][
            "git_blob_sha"
        ] = "0" * 40
        out = self.evaluate(docs, shas)
        self.assertFalse(out["pass"])
        self.assertIn(
            "AUTHORITY_SOURCE_BLOB_MISMATCH:acceptance_predicate_evidence_bindings_reconciled",
            out["errors"],
        )

    def test_delegation_receipt_hash_binding_is_mandatory(self):
        docs, shas = self.live()
        docs = copy.deepcopy(docs)
        docs["delegation_reduction"]["exact_brain_inputs"][PATHS["delegation_scope"]] = "0" * 40
        out = self.evaluate(docs, shas)
        self.assertFalse(out["pass"])
        self.assertIn("DELEGATION_REDUCTION_SCOPE_BLOB_BINDING_MISMATCH", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
