from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest import mock

from canonical.runtime import goal_compiler
from canonical.runtime import r2_markdown_pdf_direct_adequacy_v1 as adequacy


class R2MarkdownPdfDirectAdequacyV1Tests(unittest.TestCase):
    def material(self):
        td=tempfile.TemporaryDirectory()
        root=Path(td.name)
        (root/"canonical").mkdir()
        src=root/"canonical/source.md"
        src.write_text(
            "# PROJECT BRAIN PDF\n\nAlpha verify 7319.\nBeta complete.\n",
            encoding="ascii",
        )
        goal="Convert canonical/source.md to canonical/output.pdf."
        req={"task_id":"mdpdf-test","goal":goal}
        return td,root,src,root/"canonical/output.pdf",req

    def test_exact_goal_compiler_escapes_pdf_extractor_ambiguity(self):
        td,root,src,dst,req=self.material()
        self.addCleanup(td.cleanup)
        registry=adequacy.live_bound.load_verified_registry()
        admissible=goal_compiler._platform_admissible_registry(dict(registry))
        out=goal_compiler.compile_goal(req["goal"],admissible,root)
        self.assertEqual(
            out["selected_capability"],
            "document.convert.markdown_pdf.pandoc_weasyprint",
        )
        self.assertEqual(
            out["compiler_mode"],
            "DETERMINISTIC_EXACT_MARKDOWN_PDF_CONVERSION",
        )
        self.assertEqual(out["inputs"]["markdown_path"],"canonical/source.md")
        self.assertEqual(out["inputs"]["output_path"],"canonical/output.pdf")

    def test_preflight_binds_exact_verified_producer_and_verifier(self):
        td,root,src,dst,req=self.material()
        self.addCleanup(td.cleanup)
        out=adequacy.preflight(req,repo_root=root)
        self.assertTrue(out["matched"],out)
        self.assertNotEqual(out["status"],"FAIL_CLOSED",out)
        self.assertEqual(out["capability_id"],adequacy.PRODUCER)
        self.assertEqual(out["verifier_capability_id"],adequacy.VERIFIER)
        self.assertEqual(out["visible_text"],"PROJECT BRAIN PDF Alpha verify 7319. Beta complete.")
        self.assertFalse(out["preflight_execution_authority"])

    def test_inline_or_rich_markdown_is_outside_exact_family(self):
        td,root,src,dst,req=self.material()
        self.addCleanup(td.cleanup)
        src.write_text("# TITLE\n\nUse **bold** text.\n",encoding="ascii")
        out=adequacy.preflight(req,repo_root=root)
        self.assertTrue(out["matched"],out)
        self.assertEqual(out["status"],"FAIL_CLOSED",out)
        self.assertIn("MARKDOWN_LINE_OUTSIDE_PLAIN_SEMANTIC_SUBSET",out["reason"])

    def test_success_commits_only_after_independent_acceptance(self):
        td,root,src,dst,req=self.material()
        self.addCleanup(td.cleanup)

        def execute(request):
            dst.write_bytes(b"%PDF-FAKE\n")
            return {
                "pass":True,
                "compiled_capability_id":adequacy.PRODUCER,
                "raw_goal_sha256":adequacy.sha256(req["goal"].encode()).hexdigest(),
                "raw_source_coverage_complete":True,
            }

        verifier=mock.Mock(return_value={
            "verified":True,
            "producer_independent_verifier":True,
            "verifier_capability_id":adequacy.VERIFIER,
        })
        with mock.patch.object(adequacy.live_bound,"run_raw_goal",side_effect=execute):
            out=adequacy.run(req,repo_root=root,verifier_provider=verifier)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["transaction_committed"])
        self.assertTrue(out["semantic_acceptance_complete"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertTrue(out["policy_adequacy_authority"])
        verifier.assert_called_once()
        self.assertTrue(dst.exists())

    def test_failed_independent_acceptance_restores_preexisting_output(self):
        td,root,src,dst,req=self.material()
        self.addCleanup(td.cleanup)
        dst.write_bytes(b"OLD")

        def execute(request):
            dst.write_bytes(b"%PDF-NEW\n")
            return {
                "pass":True,
                "compiled_capability_id":adequacy.PRODUCER,
                "raw_goal_sha256":adequacy.sha256(req["goal"].encode()).hexdigest(),
                "raw_source_coverage_complete":True,
            }

        with mock.patch.object(adequacy.live_bound,"run_raw_goal",side_effect=execute):
            out=adequacy.run(
                req,
                repo_root=root,
                verifier_provider=lambda pf:{
                    "verified":False,
                    "producer_independent_verifier":True,
                    "verifier_capability_id":adequacy.VERIFIER,
                },
            )
        self.assertFalse(out["pass"],out)
        self.assertTrue(out["transaction_rolled_back"])
        self.assertEqual(dst.read_bytes(),b"OLD")

    def test_source_mutation_blocks_commit_and_removes_new_output(self):
        td,root,src,dst,req=self.material()
        self.addCleanup(td.cleanup)

        def execute(request):
            src.write_text("# MUTATED\n",encoding="ascii")
            dst.write_bytes(b"%PDF-NEW\n")
            return {
                "pass":True,
                "compiled_capability_id":adequacy.PRODUCER,
                "raw_goal_sha256":adequacy.sha256(req["goal"].encode()).hexdigest(),
                "raw_source_coverage_complete":True,
            }

        with mock.patch.object(adequacy.live_bound,"run_raw_goal",side_effect=execute):
            out=adequacy.run(
                req,
                repo_root=root,
                verifier_provider=lambda pf:{
                    "verified":True,
                    "producer_independent_verifier":True,
                    "verifier_capability_id":adequacy.VERIFIER,
                },
            )
        self.assertFalse(out["pass"],out)
        self.assertTrue(out["transaction_rolled_back"])
        self.assertFalse(dst.exists())


if __name__=="__main__":
    unittest.main(verbosity=2)
