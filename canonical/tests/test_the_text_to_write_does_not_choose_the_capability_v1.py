"""The text a request wants written must not choose the capability that writes it.

F25 already removes a QUOTED literal from the prose a capability is scored on,
because "a value's own words were being read as the task's words".  The same
sentence written without quote marks states the value just as plainly, and was
not covered.

Measured on d2887c5 over thirteen ordinary "write this text to that file"
requests: **4 reached the file**.  The other nine were routed by the words of the
text to be written:

    "rank the source candidates by objective relevance"
        -> source.objective_relevance.rank.bm25
    "the archive manifest listing"
        -> archive.tar_gz.create_from_manifest
    "compile the semantic behavior of this module"
        -> python.software.request.semantic_behavior.compile.v1
    "a plain sentence about nothing in particular"
        -> a capability whose id begins plain_goal

`text.file.write` scores 0 on every one of those sentences BY DESIGN -- write,
text and file are all in GENERIC_MATCH_TOKENS, and a generic token may refine a
match but never create one -- so it is only reached when nothing else claims the
sentence.  A value's distinctive words therefore did not merely outrank the right
capability; they stopped the request from being a write at all, and the file was
never created.

After the change, 7 of the 13 reach the file and are independently verified.  The
six that still fail name a task the sentence never asked for ("audit the python
source", "convert the markdown document to pdf") or a tool that is not installed;
none of them is routed by the value any more.

Selection now reads the sentence with the stated value blanked.  BINDING still
reads the untouched sentence, so the value reaches the capability verbatim --
a value may be delivered, it may not choose the deliverer.  Over all 367
admissible capabilities driven from prose: pass 223 / fail 144 and failure kinds
CONTRACT_REFUSAL 138 / ENVIRONMENT_BLOCKER 3 / UNKNOWN 3, all unchanged, and the
compilation benchmark is unchanged at 23/23 compiled and 22/23 selected.

Tests 1-4 pin the stripping rule, including the two cases it must NOT touch.
Test 5 is the negative control on selection: a sentence that legitimately names
a capability must still select it.  Test 6 drives the three measured hijacks end
to end and fails on d2887c5.
"""

from __future__ import annotations

import pathlib
import shutil
import sys
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "canonical" / "runtime") not in sys.path:
    sys.path.insert(0, str(ROOT / "canonical" / "runtime"))

from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime.live_brain_route_admission_v1 import solve  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import (  # noqa: E402
    load_verified_registry,
)

# The three measured hijacks: content whose words are another capability's
# distinctive tokens.  Chosen by measurement on d2887c5, not by guess.
# None of these begins with "the": the text binder strips a leading article from
# a stated value, so "the archive manifest listing" is delivered as "archive
# manifest listing".  That is pre-existing behaviour of _extract_text_argument,
# not something this change introduces, and asserting the full string here would
# have pinned it as intended.  Recorded rather than silently asserted.
_HIJACKS = (
    "compile the semantic behavior of this module",
    "archive manifest listing",
    "objective relevance ranking sample",
)


class TestTheTextToWriteDoesNotChooseTheCapabilityV1(unittest.TestCase):
    def _fresh_rel(self, tag: str) -> str:
        """A repository-relative directory that is empty when it is returned.

        Its name is free of dictionary words on purpose.  Measured: a directory
        called composed_acceptance_e2e makes an identical sentence fail with
        FAIL_CLOSED__ROUTE_ADMISSION_REJECTED, because a path's own components
        become goal tokens and match capability names.
        """
        rel = "canonical/astra_runtime/tmp/twv_%s_%x" % (tag, time.perf_counter_ns())
        absolute = ROOT / rel
        shutil.rmtree(absolute, ignore_errors=True)
        absolute.mkdir(parents=True, exist_ok=True)
        return rel

    # ---- the stripping rule ---------------------------------------------

    def test_a_stated_value_is_removed_and_the_role_words_are_kept(self) -> None:
        out = front.without_stated_text_value(
            "Write the text compile the semantic behavior to the file out.txt")
        self.assertEqual(out, "Write the text  to the file out.txt")

    def test_the_tail_form_is_covered_too(self) -> None:
        out = front.without_stated_text_value(
            "Create the file out.txt containing the text rank the source candidates")
        self.assertEqual(out, "Create the file out.txt containing the text ")

    def test_a_sentence_that_extracts_text_is_left_alone(self) -> None:
        # The negative control that keeps the rule narrow.  Here "from the pdf"
        # IS the task; the lookahead requires a destination before it strips.
        goal = "Extract the text from the pdf canonical/astra_runtime/tmp/d.pdf"
        self.assertEqual(front.without_stated_text_value(goal), goal)

    def test_a_sentence_with_no_stated_text_is_unchanged(self) -> None:
        for goal in ("Run the python source audit ast with source_root canonical/runtime.",
                     "Enumerate the source candidates for brain capability code."):
            self.assertEqual(front.without_stated_text_value(goal), goal)

    # ---- selection --------------------------------------------------------

    def test_a_capability_the_sentence_legitimately_names_is_still_selected(self) -> None:
        """Negative control on selection: stripping must not break a real match."""
        registry = dict(load_verified_registry())
        rel = self._fresh_rel("sel")
        (ROOT / rel / "a.py").write_text("x = 1\n", encoding="utf-8")
        goal = ("Run the python source audit ast with source_root %s/src "
                "and output_path %s/audit.json" % (rel, rel))
        # the directory must exist for source_root to bind
        (ROOT / rel / "src").mkdir(exist_ok=True)
        (ROOT / rel / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
        compiled = front.compile_goal(goal, registry, ROOT)
        self.assertEqual(compiled.get("selected_capability"), "python.source.audit.ast")

    # ---- end to end --------------------------------------------------------

    def test_the_measured_hijacks_now_write_the_file(self) -> None:
        """On d2887c5 all three are routed elsewhere and no file is written."""
        for index, content in enumerate(_HIJACKS):
            rel = self._fresh_rel("hj%d" % index)
            path = "%s/out.txt" % rel
            result = solve({
                "task_id": "TEXTVALUE_%d_%x" % (index, time.perf_counter_ns()),
                "goal": "Write the text %s to the file %s" % (content, path)})
            self.assertIs(
                result.get("status"),
                "PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED",
                "content %r -> %s (selected %s)" % (
                    content, result.get("status"),
                    result.get("compiled_capability_id")))
            # and the bytes on disk are the text that was asked for, not a
            # different tool's idea of the answer
            self.assertEqual((ROOT / path).read_text(encoding="utf-8"), content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
