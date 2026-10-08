from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest import mock

from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as direct


class R2MarkdownPdfDirectIntegrationV1Tests(unittest.TestCase):
    def test_direct_router_selects_markdown_pdf_family_before_generic_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"canonical").mkdir()
            (root/"canonical/source.md").write_text("# TITLE\n\nAlpha 7319.\n",encoding="ascii")
            request={
                "task_id":"router-mdpdf",
                "goal":"Convert canonical/source.md to canonical/output.pdf.",
            }
            pf={
                "schema":"PROJECT_BRAIN_R2_MARKDOWN_PDF_DIRECT_ADEQUACY_V1",
                "status":"DIRECT_MARKDOWN_PDF_ADEQUACY_ROUTE_MATCHED",
                "pass":False,
                "matched":True,
                "capability_id":"document.convert.markdown_pdf.pandoc_weasyprint",
                "policy_id":"BOUND_CAPABILITY_POLICY::document.convert.markdown_pdf.pandoc_weasyprint::RAW_GOAL_SHA256::x",
                "goal_sha256":"g",
                "markdown_path":"canonical/source.md",
                "output_path":"canonical/output.pdf",
            }
            with mock.patch.object(
                direct.markdown_pdf_adequacy,"preflight",return_value=pf
            ), mock.patch.object(
                direct.typed_decision_adequacy,"preflight",
                side_effect=AssertionError("later route must not run"),
            ):
                out=direct.preflight(request)
            self.assertTrue(out["matched"],out)
            self.assertEqual(out["route_id"],direct.MARKDOWN_PDF_ROUTE_ID)
            self.assertEqual(
                out["capability_id"],
                "document.convert.markdown_pdf.pandoc_weasyprint",
            )

    def test_matched_markdown_pdf_failure_never_falls_through(self):
        request={"task_id":"x","goal":"Convert canonical/a.md to canonical/b.pdf."}
        pf={
            "pass":False,
            "matched":True,
            "route_id":direct.MARKDOWN_PDF_ROUTE_ID,
            "capability_id":"document.convert.markdown_pdf.pandoc_weasyprint",
            "goal_sha256":"g",
            "semantic_scope":direct.ROUTES[direct.MARKDOWN_PDF_ROUTE_ID]["scope"],
        }
        failed={
            "pass":False,
            "status":"OPEN__INDEPENDENT_MARKDOWN_PDF_ACCEPTANCE_DID_NOT_VERIFY",
            "reason":"readback mismatch",
        }
        with mock.patch.object(direct,"preflight",return_value=pf), mock.patch.object(
            direct.markdown_pdf_adequacy,"run",return_value=failed
        ), mock.patch.object(
            direct.live_bound,"run_raw_goal",
            side_effect=AssertionError("generic fallback forbidden"),
        ):
            out=direct.run(request)
        self.assertFalse(out["pass"],out)
        self.assertTrue(out["execution_attempted"])
        self.assertFalse(out["retry_by_other_route_authorized"])
        self.assertEqual(out["reason"],"readback mismatch")


if __name__=="__main__":
    unittest.main(verbosity=2)
