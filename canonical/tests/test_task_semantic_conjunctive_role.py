#!/usr/bin/env python3
import importlib.util
import pathlib
import sys
import unittest

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
PATH=CANONICAL_ROOT/"runtime"/"capability_discovery.py"
spec=importlib.util.spec_from_file_location("task_semantic_discovery_target",PATH)
d=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=d
spec.loader.exec_module(d)

class TaskSemanticConjunctiveRoleTests(unittest.TestCase):
    def test_json_payload_words_do_not_become_domain(self):
        goal='Transform the JSON text {"project":"brain","alpha":7} into an XML document at canonical/astra_runtime/tmp/X.xml.'
        roles=d.effect_semantic_roles(goal)
        domain=set(roles["domain"])
        self.assertNotIn("project",domain)
        self.assertNotIn("brain",domain)
        self.assertNotIn("alpha",domain)
        self.assertIn("structured",domain)
        self.assertIn("xml",roles["format"])

    def test_quoted_payload_words_do_not_enter_queries(self):
        goal='Compress the text "project brain arbitrary payload" into a gzip archive at canonical/astra_runtime/tmp/X.gz.'
        q=d.effect_queries(goal)
        for token in ("project","brain","arbitrary","payload"):
            self.assertNotIn(token,q)
        self.assertTrue(any(x in q for x in ("compress","gzip","compression","archive")))

    def test_audio_transcode_requires_operation_and_domain(self):
        roles=d.effect_semantic_roles(
            "Transcode a WAV audio recording into a FLAC audio file at canonical/astra_runtime/tmp/X.flac."
        )
        good=d._candidate_role_alignment(
            "media-cli","tools for transcoding multimedia and audio files",roles
        )
        bad=d._candidate_role_alignment(
            "audio-icons","audio file icons and metadata assets",roles
        )
        self.assertTrue(d._essential_role_compatibility(good,roles)["compatible"])
        self.assertFalse(d._essential_role_compatibility(bad,roles)["compatible"])

    def test_markup_converter_family_matches_converter_morphology(self):
        roles=d.effect_semantic_roles(
            "Convert a Markdown document into an HTML document at canonical/astra_runtime/tmp/X.html."
        )
        alignment=d._candidate_role_alignment(
            "universal-markup","general markup converter for document formats",roles
        )
        self.assertTrue(d._essential_role_compatibility(alignment,roles)["compatible"])

    def test_png_optimizer_requires_optimize_not_topic_only(self):
        roles=d.effect_semantic_roles(
            "Optimize a PNG image losslessly at canonical/astra_runtime/tmp/X.png."
        )
        good=d._candidate_role_alignment(
            "png-optimizer","advanced PNG image optimizer",roles
        )
        bad=d._candidate_role_alignment(
            "png-viewer","PNG image viewer and graphics utility",roles
        )
        self.assertTrue(d._essential_role_compatibility(good,roles)["compatible"])
        self.assertFalse(d._essential_role_compatibility(bad,roles)["compatible"])

if __name__=="__main__":
    unittest.main(verbosity=2)
