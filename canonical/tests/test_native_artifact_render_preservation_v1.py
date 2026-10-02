from __future__ import annotations

import base64
from io import BytesIO
import unittest

from docx import Document
from docx.shared import Inches

from canonical.runtime import native_artifact_cross_format_candidate_v1 as candidate
from canonical.runtime import native_artifact_cross_format_proof_v1 as structural
from canonical.runtime import native_artifact_render_preservation_proof_v1 as render


class NativeArtifactRenderPreservationTests(unittest.TestCase):
    def test_all_four_formats_preserve_render_envelope(self):
        out = render.run_grid((2601,))
        self.assertTrue(out["all_pass"], out)
        self.assertEqual(set(out["by_format"]), set(render.FORMATS))

    def test_unchanged_output_is_not_accepted_as_edit(self):
        case = structural.generate_case("pdf", 2602)
        source = base64.b64decode(case["task"]["document_b64"], validate=True)
        out = render.compare_renders(source, source, "pdf")
        self.assertFalse(out["pass"], out)

    def test_large_docx_layout_mutation_is_rejected(self):
        case = structural.generate_case("docx", 2603)
        public = structural.public_task(case)
        solved = candidate.solve(public)
        self.assertEqual(solved["status"], "OK", solved)
        source = base64.b64decode(case["task"]["document_b64"], validate=True)
        edited = base64.b64decode(solved["output_b64"], validate=True)

        d = Document(BytesIO(edited))
        d.sections[0].page_width = Inches(4)
        b = BytesIO()
        d.save(b)
        mutated = b.getvalue()

        out = render.compare_renders(source, mutated, "docx")
        self.assertFalse(out["pass"], out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
