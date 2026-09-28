#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
PATH=CANONICAL_ROOT/"runtime"/"capability_discovery.py"
spec=importlib.util.spec_from_file_location("semantic_role_discovery_target",PATH)
discovery=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=discovery
spec.loader.exec_module(discovery)

class SemanticRoleDiscoveryTests(unittest.TestCase):
    def test_image_domain_survives_flat_query_loss(self):
        goal=(
            "Resize a PNG image to exactly 64 by 64 pixels and save the result "
            "at canonical/astra_runtime/tmp/ROLE_TEST.png."
        )
        roles=discovery.effect_semantic_roles(goal)
        self.assertIn("resize",roles["operation"])
        self.assertIn("png",roles["format"])
        self.assertIn("image",roles["domain"])
        queries=discovery.effect_queries(goal)
        self.assertIn("resize",queries)
        self.assertIn("image",queries)
        self.assertIn("png",queries)
        self.assertNotIn("at",queries)
        self.assertNotIn("exactly",queries)
        self.assertNotIn("result",queries)

    def test_format_can_supply_generic_domain_semantics(self):
        goal=(
            "Create a gzip-compressed file at canonical/astra_runtime/tmp/X.gz "
            "whose decompressed UTF-8 content is exactly hello."
        )
        roles=discovery.effect_semantic_roles(goal)
        self.assertTrue({"gzip","gz"} & set(roles["format"]))
        self.assertIn("compression",roles["domain"])
        self.assertIn("archive",roles["domain"])
        queries=discovery.effect_queries(goal)
        self.assertNotIn("at",queries)
        self.assertNotIn("whose",queries)

    def test_candidate_supplier_role_separates_auxiliary_from_direct(self):
        direct=discovery._apt_supplier_role(
            "vector-renderer",
            "command-line utility for rendering vector graphics",
        )
        editor=discovery._apt_supplier_role(
            "elpa-vector-render-mode",
            "editor mode for vector rendering",
        )
        binding=discovery._apt_supplier_role(
            "python3-vector",
            "Python bindings for vector graphics library",
        )
        backend=discovery._apt_supplier_role(
            "server-vector-modules",
            "vector graphics backend module for server integration",
        )
        self.assertEqual(direct["role"],"DIRECT_EXECUTABLE_CANDIDATE")
        for item in (editor,binding,backend):
            self.assertEqual(item["role"],"AUXILIARY_OR_NON_DIRECT")

    def test_direct_supplier_outranks_auxiliary_with_same_topic(self):
        roles={
          "operation":["render"],
          "domain":["vector","graphics"],
          "format":["png"],
          "constraints":[],
        }
        direct=discovery._score_apt_candidate(
            "vector-renderer",
            "command-line utility to render vector graphics to PNG",
            {"render","vector","graphics","png"},
            roles,
        )
        aux=discovery._score_apt_candidate(
            "elpa-vector-render-mode",
            "editor mode for vector graphics rendering and PNG previews",
            {"render","vector","graphics","png"},
            roles,
        )
        self.assertGreater(direct[0],aux[0])
        self.assertEqual(direct[2]["role"],"DIRECT_EXECUTABLE_CANDIDATE")
        self.assertEqual(aux[2]["role"],"AUXILIARY_OR_NON_DIRECT")

if __name__=="__main__":
    unittest.main(verbosity=2)
