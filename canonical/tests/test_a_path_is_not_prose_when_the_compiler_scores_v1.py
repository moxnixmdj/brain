"""A path is a value, not prose -- the compiler must not be told what to do by a filename.

Measured on main 9f808230, 2026-10-31.  The third clause of the compound audit goal

    "Then create canonical/astra_runtime/tmp/CAPABILITY_AUDIT.pdf from that report
     and verify that the final PDF contains every capability ID."

selected ``python.source.audit.ast``: the OUTPUT FILE'S NAME contains the word AUDIT,
and "audit" is a keyword of the audit row.  The sentence asks for a PDF to be created.

Two facts make this a defect rather than a coincidence:

  * the same clause with a neutral filename is AMBIGUOUS instead of selecting the audit
    row, so the filename was the only thing deciding it; and
  * the repository had already established the law in two places -- ``prose_only``
    (F8 removes URLs and paths, F25 removes quoted literals) and the composer, which
    scores through it.  ``goal_compiler._score`` read the raw sentence.

The law is pinned here without touching the registry, the scorer's weights or any
tolerance: what changes is WHICH TEXT is scored.  Slot binding still reads the whole
sentence, because a path is exactly what a slot needs.
"""
from __future__ import annotations

import pathlib
import unittest

from canonical.runtime import goal_compiler as compiler
from canonical.runtime import live_integrated_brain_v1 as live

ROOT = pathlib.Path(__file__).resolve().parents[2]

AUDIT_GOAL = (
    "Read canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json. "
    "Create canonical/astra_runtime/tmp/CAPABILITY_AUDIT.md containing a table with every "
    "VERIFIED_BOUND_CAPABILITY. "
    "Then create canonical/astra_runtime/tmp/CAPABILITY_AUDIT.pdf from that report and verify "
    "that the final PDF contains every capability ID."
)


def _registry():
    return live.load_verified_registry()


class FileNameDoesNotChooseTheCapabilityTests(unittest.TestCase):
    def setUp(self):
        self.registry = _registry()

    def test_the_compound_goal_converts_the_report_instead_of_auditing_a_filename(self):
        out = compiler.compile_goal(AUDIT_GOAL, self.registry, ROOT)
        selected = [part.get("selected_capability") or part.get("capability_id")
                    for part in out.get("compiled_parts") or []]
        self.assertIn("document.convert.markdown_pdf.pandoc_weasyprint", selected)
        self.assertNotIn("python.source.audit.ast", selected)

    def test_two_sentences_that_differ_only_in_a_path_words_score_the_same(self):
        """The scoring term is the sentence's PROSE; a filename contributes nothing."""
        entry = {"provides": ["document.convert.markdown_pdf"],
                 "requires": [], "keywords": ["pdf", "markdown", "convert", "audit"]}
        with_audit_name = "Create canonical/astra_runtime/tmp/CAPABILITY_AUDIT.pdf from that report."
        with_plain_name = "Create canonical/astra_runtime/tmp/report.pdf from that report."
        a = compiler._score(with_audit_name, "x.y.z", entry)
        b = compiler._score(with_plain_name, "x.y.z", entry)
        self.assertEqual(a[0], b[0], "a filename changed the score: %r vs %r" % (a[0], b[0]))
        self.assertEqual(a[2].get("matched_keywords"), b[2].get("matched_keywords"))

    def test_the_prose_itself_still_decides(self):
        """Negative control: a real difference in the sentence must still move the score."""
        entry = {"provides": ["document.convert.markdown_pdf"],
                 "requires": [], "keywords": ["pdf", "markdown", "convert", "audit"]}
        plain = compiler._score("Create a report.", "x.y.z", entry)[0]
        rich = compiler._score("Convert the markdown to PDF.", "x.y.z", entry)[0]
        self.assertGreater(rich, plain, "the sentence's own words stopped counting")


if __name__ == "__main__":
    unittest.main()
