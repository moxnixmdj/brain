from copy import deepcopy
import json
import unittest

from canonical.runtime import fibo_prod_tbox_scope_manifest_v1 as scope


class FiboProdTBoxScopeManifestV1Tests(unittest.TestCase):
    @staticmethod
    def manifest():
        return json.loads(scope.MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_current_manifest_passes(self):
        out = scope.evaluate()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["ontology_file_count"], 106)
        self.assertEqual(out["total_source_bytes"], 3452615)
        self.assertFalse(out["task_mapping_authority"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["open_world_ontology_completeness"])
        self.assertFalse(out["terminal_authority"])

    def test_examples_metadata_and_load_files_are_absent(self):
        manifest = self.manifest()
        for row in manifest["ontology_files"]:
            path = row["path"]
            name = path.rsplit("/", 1)[-1]
            self.assertFalse(path.startswith("EXMP/"), path)
            self.assertFalse(name.startswith("Metadata"), path)
            self.assertFalse(name.startswith("All"), path)

    def test_duplicate_import_fails_closed(self):
        manifest = self.manifest()
        manifest["ontology_files"].append(deepcopy(manifest["ontology_files"][0]))
        manifest["scope"]["loader_import_count"] += 1
        manifest["scope"]["unique_loader_import_count"] += 1
        manifest["scope"]["resolved_blob_count"] += 1
        out = scope.evaluate(manifest)
        self.assertFalse(out["pass"])

    def test_source_identity_tamper_fails_closed(self):
        manifest = self.manifest()
        manifest["source"]["commit_sha"] = "0" * 40
        out = scope.evaluate(manifest)
        self.assertFalse(out["pass"])
        self.assertIn("SOURCE_IDENTITY_DRIFT", out["reason"])

    def test_scope_cannot_self_promote_mapping_or_truth_authority(self):
        for field in (
            "task_context_to_fibo_concept_mapping_authority",
            "factual_world_truth_authority",
            "semantic_relation_inference_authority",
            "policy_adequacy_authority",
        ):
            with self.subTest(field=field):
                manifest = self.manifest()
                manifest["authority_boundary"][field] = True
                out = scope.evaluate(manifest)
                self.assertFalse(out["pass"])
                self.assertEqual(out["reason"], "AUTHORITY_ESCALATION:" + field)

    def test_external_dependency_closure_is_not_claimed(self):
        manifest = self.manifest()
        self.assertFalse(manifest["scope"]["external_dependency_closure_in_scope"])
        manifest["scope"]["external_dependency_closure_in_scope"] = True
        out = scope.evaluate(manifest)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "SCOPE_BOUNDARY_ESCALATION:external_dependency_closure_in_scope",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
