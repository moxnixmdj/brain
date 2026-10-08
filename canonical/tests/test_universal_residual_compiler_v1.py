import json
import pathlib
import tempfile
import unittest

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.universal_residual_compiler_v1 import compile_residual

SCOPE = "scope://unit/universal-residual-v1"


def spec():
    return {
        "schema": "PROJECT_BRAIN_UNIVERSAL_RESIDUAL_SPEC_V1",
        "scope_id": SCOPE,
        "variables": ["x", "y"],
        "overapprox_cnf": [],
        "routes": [
            {"route_id": "x_true", "admission_cnf": [["x"]]},
            {"route_id": "x_false", "admission_cnf": [["!x"]]},
        ],
    }


def run(value, expected_scope_id=SCOPE, mutate_digest=False):
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        path = root / "residual.json"
        content = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        path.write_bytes(content)
        digest = git_blob_id(content, object_format="sha1")
        if mutate_digest:
            digest = "0" * 40
        return compile_residual(
            {"path": "residual.json", "git_blob_sha": digest},
            repo_root=root,
            expected_scope_id=expected_scope_id,
        )


class ResidualCompilerTests(unittest.TestCase):
    def test_total_cover_compiles_to_unsat_residual(self):
        out = run(spec())
        self.assertTrue(out["pass"])
        self.assertEqual(out["status"], "PASS__RESIDUAL_COMPILED")
        self.assertEqual(out["semantic_status"], "UNSAT_ON_DECLARED_BOUNDED_MODEL")
        self.assertEqual(out["residual_model"], None)
        self.assertFalse(out["u_empty_authorized"])
        self.assertIn("p cnf", out["dimacs"])

    def test_missing_route_returns_constructive_sat_witness(self):
        p = spec()
        p["routes"].pop()
        out = run(p)
        self.assertTrue(out["pass"])
        self.assertEqual(out["semantic_status"], "SAT_ON_DECLARED_BOUNDED_MODEL")
        self.assertEqual(out["residual_model"]["x"], False)
        self.assertFalse(out["u_empty_authorized"])

    def test_scope_swap_fails_closed(self):
        out = run(spec(), expected_scope_id="scope://other")
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SPEC_SCOPE_MISMATCH")

    def test_forged_blob_fails_closed(self):
        out = run(spec(), mutate_digest=True)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SPEC_BINDING_OR_REPLAY_INVALID")

    def test_unknown_top_level_field_fails_closed(self):
        p = spec()
        p["u_empty_authorized"] = True
        out = run(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SPEC_FIELDS_INVALID")

    def test_duplicate_route_id_fails_closed(self):
        p = spec()
        p["routes"][1]["route_id"] = "x_true"
        out = run(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "ROUTE_ID_INVALID")

    def test_empty_declared_scope_not_creditable(self):
        p = spec()
        p["overapprox_cnf"] = [[]]
        out = run(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "EMPTY_DECLARED_SCOPE_NOT_CREDITABLE")

    def test_dimacs_is_deterministic(self):
        a = run(spec())
        b = run(spec())
        self.assertEqual(a["dimacs"], b["dimacs"])
        self.assertEqual(a["residual_sha256"], b["residual_sha256"])


if __name__ == "__main__":
    unittest.main()
