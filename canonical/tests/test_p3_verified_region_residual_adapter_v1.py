import json
import pathlib
import shutil
import tempfile
import unittest

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.p3_verified_region_residual_adapter_v1 import build_bound_residual_spec
from canonical.runtime.universal_residual_compiler_v1 import compile_residual

ROOT = pathlib.Path("/home/sprite")
SCOPE = "scope://project-brain/universal-escape-v1"


class P3VerifiedRegionResidualAdapterTests(unittest.TestCase):
    def test_exact_canonical_region_builds_one_real_bound_atom(self):
        out = build_bound_residual_spec(repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["atom_id"], "P3_STRICT_TOPLAW_REGION")
        self.assertEqual(out["region_id"], "P3_BOUND_BINARY_REAL_CONTEXT_GROUNDED_DECISION_TOP_LAW_V1")
        self.assertFalse(out["u_empty_authorized"])
        spec = out["spec"]
        self.assertEqual(spec["scope_id"], SCOPE)
        self.assertEqual(spec["variables"], ["P3_STRICT_TOPLAW_REGION"])
        self.assertEqual(spec["overapprox_cnf"], [])
        self.assertEqual(
            spec["routes"],
            [{
                "route_id": "P3_BOUND_BINARY_REAL_CONTEXT_GROUNDED_DECISION_TOP_LAW_V1",
                "admission_cnf": [["P3_STRICT_TOPLAW_REGION"]],
            }],
        )

    def test_generated_real_bound_seed_has_exact_complement_witness(self):
        out = build_bound_residual_spec(repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            spec_path = root / "seed.json"
            data = json.dumps(out["spec"], sort_keys=True, separators=(",", ":")).encode()
            spec_path.write_bytes(data)
            result = compile_residual(
                {"path": "seed.json", "git_blob_sha": git_blob_id(data, object_format="sha1")},
                repo_root=root,
                expected_scope_id=SCOPE,
            )
        self.assertTrue(result["pass"], result)
        self.assertEqual(result["semantic_status"], "SAT_ON_DECLARED_BOUNDED_MODEL")
        self.assertEqual(
            result["residual_model"],
            {"P3_STRICT_TOPLAW_REGION": False},
        )
        self.assertFalse(result["u_empty_authorized"])

    def test_region_byte_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            shutil.copytree(ROOT / "canonical", root / "canonical")
            p = root / "canonical/governance/P3_BOUND_BINARY_REAL_CONTEXT_TOP_LAW_REGION_20261008_V1.json"
            doc = json.loads(p.read_text())
            doc["resource_and_ownership"]["brain_owned"] = False
            p.write_text(json.dumps(doc))
            out = build_bound_residual_spec(repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "PINNED_REGION_OR_VERIFICATION_BYTES_INVALID")

    def test_verification_byte_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            shutil.copytree(ROOT / "canonical", root / "canonical")
            p = root / "canonical/verification/P3_BINARY_EXPLICIT_TOP_LAW_REGION_TWO_SPRITE_VERIFICATION_20261008_V1.json"
            doc = json.loads(p.read_text())
            doc["verified"]["parameterized_D_B_region_candidate"] = False
            p.write_text(json.dumps(doc))
            out = build_bound_residual_spec(repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "PINNED_REGION_OR_VERIFICATION_BYTES_INVALID")

    def test_adapter_never_promotes_global_authority(self):
        out = build_bound_residual_spec(repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["global_scope_complete"])
        self.assertFalse(out["u_empty_authorized"])
        self.assertFalse(out["abc_closed_authorized"])
        self.assertFalse(out["terminal_authority"])


if __name__ == "__main__":
    unittest.main()
