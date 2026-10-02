from __future__ import annotations

import copy
import unittest

from canonical.runtime.opus55_composition_component_interface_manifest_v1 import (
    MANIFEST,
    _load,
    evaluate,
)


class CompositionComponentInterfaceManifestTests(unittest.TestCase):
    def fixtures(self):
        manifest = _load(MANIFEST)
        auth = manifest["authority"]
        protocols = _load(auth["protocols"]["path"])
        registry = _load(auth["predicate_registry"]["path"])
        decomposition = _load(auth["direct_scope_decomposition"]["path"])
        contracts = _load(auth["behavioral_contract_registry"]["path"])
        shas = {row["path"]: row["git_blob_sha"] for row in auth.values()}
        return manifest, protocols, registry, decomposition, contracts, shas

    def test_live_candidate_is_exact_representation_only(self):
        m, p, r, d, c, shas = self.fixtures()
        out = evaluate(m, p, r, d, c, actual_blob_shas=shas)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["interface_count"], 10)
        self.assertEqual(out["slicer_open_interface_count"], 10)
        self.assertTrue(out["representation_precondition_satisfied"])
        self.assertFalse(out["composition_component_predicate_closed"])
        self.assertFalse(out["promotion_authority"])

    def test_missing_dimension_interface_fails_closed(self):
        m, p, r, d, c, shas = self.fixtures()
        m = copy.deepcopy(m)
        m["dimension_to_interfaces"]["research+tool use+artifact creation"] = []
        out = evaluate(m, p, r, d, c, actual_blob_shas=shas)
        self.assertFalse(out["pass"])
        self.assertTrue(any("DIMENSION_HAS_NO_INTERFACES" in x for x in out["errors"]))

    def test_authority_hash_drift_fails_closed(self):
        m, p, r, d, c, shas = self.fixtures()
        shas = dict(shas)
        path = m["authority"]["protocols"]["path"]
        shas[path] = "0" * 40
        out = evaluate(m, p, r, d, c, actual_blob_shas=shas)
        self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_BLOB_MISMATCH:protocols", out["errors"])

    def test_embedded_unverified_receipt_fails_closed(self):
        m, p, r, d, c, shas = self.fixtures()
        m = copy.deepcopy(m)
        m["receipts"] = [{"receipt_id": "wishful-thinking"}]
        out = evaluate(m, p, r, d, c, actual_blob_shas=shas)
        self.assertFalse(out["pass"])
        self.assertIn("INITIAL_MANIFEST_MUST_NOT_EMBED_UNVERIFIED_RECEIPTS", out["errors"])

    def test_removed_component_role_fails_closed(self):
        m, p, r, d, c, shas = self.fixtures()
        m = copy.deepcopy(m)
        m["interfaces"] = [x for x in m["interfaces"] if x["component_role"] != "MEMORY"]
        out = evaluate(m, p, r, d, c, actual_blob_shas=shas)
        self.assertFalse(out["pass"])
        self.assertIn("INTERFACE_ROLE_SET_MISMATCH", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
