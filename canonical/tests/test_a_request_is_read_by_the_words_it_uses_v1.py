"""A request is bound by the words it uses, not by the names a contract declares.

"Write the text 'hello patch' to the file out.txt" states a content and a destination
but names neither by its declared key: it says "text" where the contract says
`content`, and "to the file" where it says `output_path`.  The binder looked for the
declared keys, found nothing, and reported

    GOAL_INPUT_BINDING_REQUIRED: content:not_stated

while composer_route_v1.extract_content -- which already carries that synonym set --
read the value from the same sentence without difficulty.  Two doors disagreed about
one sentence, and the disagreement was a missing row in a table that already existed.

Separately the ranker scored that sentence zero for all 367 capabilities: stripping
the values leaves "Write the text to the file", three generic tokens, and a generic
token may refine a match but never create one.

Both fixes are gated on the sentence QUOTING its value, and each gate is earned by a
measured failure, not by caution.  With the synonym ungated, "Write the text hello
world to the file X" found a tail, bound the slot to None, and never reached the
composer that reads a bare value.  With the contract fallback ungated, the same
sentence reached auto.apt.zint -- a barcode generator whose input is literally named
`text`, so it bound every declared input -- and was ranked for an ordinary write.
Three acceptance suites went red each way.
"""

import shutil
import time
import unittest

from canonical.runtime import capability_selection_retrieval_v1 as retrieval
from canonical.runtime import goal_front_compiler_v1 as front
from canonical.runtime import live_brain_route_admission_v1 as admission
from canonical.runtime import live_integrated_brain_v1 as live

_ROOT = front.ROOT_FOR_NAMING
_SCRATCH = "canonical/astra_runtime/tmp/words1"


def _admissible():
    registry = live.load_verified_registry(include_extended=True)
    return live.goal_compiler._platform_admissible_registry(dict(registry))


def _solve(goal):
    return admission.solve({"task_id": "w%d" % time.perf_counter_ns(), "goal": goal})


class TestAStatedValueIsBoundUnderTheWordTheRequestUsed(unittest.TestCase):

    GOAL = "Write the text 'hello patch' to the file c/x/out.txt"

    def test_the_binder_reads_the_content_the_sentence_states(self):
        bound = front.bind_all_inputs(self.GOAL, _admissible()["text.file.write"], _ROOT,
                                      produced_paths=None, cycle=0, spool=set())
        self.assertEqual(bound.get("content"), "hello patch")
        self.assertEqual(bound.get("output_path"), "c/x/out.txt")

    def test_the_typed_gate_admits_the_sentence_it_used_to_refuse(self):
        admissible = _admissible()
        result = retrieval.admit(self.GOAL, "text.file.write",
                                 admissible["text.file.write"], _ROOT)
        self.assertIs(result.get("admitted"), True,
                      "still refused: %s" % result.get("reason"))

    def test_the_synonyms_are_the_composers_not_a_second_vocabulary(self):
        from canonical.runtime import composer_route_v1 as composer
        for word in ("text", "string", "message", "line"):
            self.assertIn(word, front._KEY_ALIASES.get("content", ()),
                          "%r is a synonym the composer knows and the binder did not" % word)
            goal = "Write the %s 'hello patch' to the file c/x/out.txt" % word
            self.assertEqual(composer.extract_content(goal), "hello patch",
                             "the composer stopped reading %r" % word)


class TestARequestWhoseOnlyEvidenceIsItsShapeIsStillRanked(unittest.TestCase):

    GOAL = "Write the text 'hello patch' to the file c/x/out.txt"

    def test_the_stated_write_has_a_candidate_at_all(self):
        ranked = front.ranked_candidates(self.GOAL,
                                         front.routable_registry(_admissible()))
        self.assertTrue(ranked, "no candidate at all for an ordinary stated write")

    def test_the_writer_outranks_the_generators_that_share_its_contract(self):
        """text.file.write, auto.apt.zint and image.qr.generate.qrencode all declare
        exactly {STRING, PATH_OUTPUT} and all three bind both values, so the shape
        cannot decide.  What separates them is what each declares it PRODUCES."""
        ranked = front.ranked_candidates(self.GOAL,
                                         front.routable_registry(_admissible()))
        order = [cid for _s, _p, cid, _e in ranked]
        self.assertEqual(order[0], "text.file.write",
                         "a generator sharing the contract outranked the writer: %s" % order[:4])
        for generator in ("auto.apt.zint", "image.qr.generate.qrencode"):
            if generator in order:
                self.assertGreater(order.index(generator), order.index("text.file.write"),
                                   "%s outranked the writer" % generator)

    def test_a_sentence_prose_already_ranks_is_untouched_by_the_fallback(self):
        ranked = front.ranked_candidates("Query a JSON table",
                                         front.routable_registry(_admissible()))
        self.assertTrue(ranked)
        self.assertEqual(ranked[0][2], "json.query.jq")
        for _s, _p, _cid, evidence in ranked[:3]:
            self.assertNotEqual(evidence.get("ranked_by"), "DECLARED_CONTRACT_FULLY_BOUND",
                                "the fallback fired where prose could already rank")


class TestTheGateCannotManufactureAValueTheSentenceNeverDelimited(unittest.TestCase):
    """Both fixes are gated on a quoted value.  Each gate is a measured regression."""

    def test_an_unquoted_sentence_never_reaches_the_contract_fallback(self):
        """auto.apt.zint declares an input literally named `text`, so it binds every
        input of an unquoted write and was ranked for it."""
        ranked = front.ranked_candidates("Write the text hello world to the file c/x/out.txt",
                                         front.routable_registry(_admissible()))
        self.assertEqual(ranked, [],
                         "the fallback fired on a sentence that delimits no value: %s"
                         % [c[2] for c in ranked][:4])

    def test_an_unquoted_sentence_never_binds_content_to_nothing(self):
        self.assertEqual(
            front._after_key("Write the text hello world to the file c/x/out.txt", "content"),
            [],
            "the synonym fired on a sentence that quotes nothing",
        )

    def test_an_unquoted_write_still_reaches_the_disk(self):
        root = _ROOT / _SCRATCH
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        out = "%s/bare.txt" % _SCRATCH
        result = _solve("Write the text hello world to the file %s." % out)
        self.assertTrue((_ROOT / out).is_file(),
                        "unquoted write stopped reaching the disk: %s" % result.get("status"))
        self.assertEqual((_ROOT / out).read_text(encoding="utf-8"), "hello world")


class TestAnOrdinaryStatedWriteIsExecutedEndToEnd(unittest.TestCase):
    """The measured effect: this sentence was refused R3_WEAK_EVIDENCE."""

    def test_the_quoted_write_is_executed_and_verified(self):
        root = _ROOT / _SCRATCH
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        out = "%s/one.txt" % _SCRATCH
        result = _solve("Write the text 'hello patch' to the file %s." % out)
        self.assertIs(result.get("pass"), True,
                      "refused: %s / %s" % (result.get("status"), result.get("failure_class")))
        self.assertEqual((_ROOT / out).read_text(encoding="utf-8"), "hello patch")


if __name__ == "__main__":
    unittest.main()
