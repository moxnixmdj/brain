"""One act has one owner, a verb has many spellings, and a NAME is its act and its object.

WHY THIS FILE EXISTS

Three separate defects made the machine answer a different act than the one it was asked
for, and each one was invisible to the benchmark because the benchmark's own goals happen
to spell the act the way the registry does.  The measured cases, all from the archive
verification family:

1. THE SPELLINGS WERE UNKNOWN.  ``archive.tar_gz.verify_manifest_members`` declares the act
   words verify / manifest / members.  Nothing in the machine knew that check, audit,
   inspect, validate and confirm name the SAME act, so "Check the tar.gz archive A against
   the manifest M." reached ``archive.tar_gz.create_from_manifest`` and the family scored 4
   of 6.  ``_ACT_SYNONYMS`` declares those classes and ``_declared_act_words`` expands them.

2. THE NAME RULE READ HALF A NAME.  ``_name_words`` drops the verb segment, so the "whole
   name" of the creator was only its OBJECT {archive, tar, gz, manifest}.  A sentence that
   used a different verb therefore counted as naming the creator and was pinned above the
   verifier that declares the verb: the creator ranked 47 first and the verifier 61 second,
   and the front door answered a check by building a new archive.

3. THE ACT FLAG WAS AN ABSOLUTE PRIORITY.  The first fix for (1) let a candidate whose
   ``_score`` recorded ``matched_head_verb`` lead the BM25 order unconditionally.  On the
   sentences the reachability instrument builds from a capability's OWN declaration words,
   the opening word is a declaration ("behavior", "cegis") that a weaker capability
   declares, and a capability scoring 25 outranked one scoring 88: REACHED_AND_BOUND fell
   454 to 450.  The flag may protect an advantage the pinned score already granted -- it may
   not create one.

WHAT THIS FILE PINS

Everything below is measured against the live registry, so a registry edit that reintroduces
any of the three shapes fails here rather than in production.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import tarfile
import unittest
import uuid

from canonical.runtime import goal_compiler as gc
from canonical.runtime import goal_front_compiler_v1 as front
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry

ROOT = pathlib.Path(__file__).resolve().parents[2]
TMP = ROOT / "canonical" / "astra_runtime" / "tmp" / "test_act_owner_name_rule"

VERIFIER = "archive.verify.tar_gz.gnu"
CREATOR = "archive.tar_gz.create_from_manifest"


def _registry():
    return dict(load_verified_registry(include_extended=True))


class TheSpellingsOfAnActAreDeclared(unittest.TestCase):
    def test_every_declared_class_is_itself_an_act_some_capability_performs(self):
        """The table may name only acts the registry already declares.

        A synonym class whose left-hand act nobody declares is a claim about English, not
        about this machine -- it would add vocabulary to no capability and hide a typo.
        """
        reg = _registry()
        declared = set()
        for entry in reg.values():
            declared |= gc._declared_act_words(entry)
        missing = sorted(set(gc._ACT_SYNONYMS) - declared)
        self.assertEqual(missing, [], missing)

    def test_expansion_only_adds_spellings_of_an_act_the_entry_declares(self):
        """A capability cannot acquire an act it does not perform."""
        entry = {"provides": ["archive.tar_gz.verify_manifest_members"]}
        words = gc._declared_act_words(entry)
        self.assertIn("verify", words)
        self.assertIn("check", words)
        self.assertIn("audit", words)
        # nothing from an unrelated class leaks in
        self.assertNotIn("create", words)
        self.assertNotIn("delete", words)

    def test_an_entry_that_declares_no_synonym_class_is_unchanged(self):
        entry = {"provides": ["archive.tar_gz.create_from_manifest"]}
        self.assertEqual(gc._declared_act_words(entry), {"create", "manifest"})


class TheActFlagProtectsAnAdvantageAndDoesNotCreateOne(unittest.TestCase):
    """Pinned on rows whose relevance is CHOSEN, because BM25 weights are corpus statistics.

    Row shape: (declares_act, relevance, score, specificity, capability_id, item).
    """

    @staticmethod
    def _row(declares, relevance, score, cid):
        return (declares, relevance, score, 1, cid, (score, 1, cid, {}))

    def test_a_weaker_act_declarer_does_not_displace_a_stronger_candidate(self):
        """The reachability regression, exactly: an absolute act-first sort made 25 lead 88 and
        four capabilities lost the only sentence that reached them."""
        rows = [self._row(True, 0.0, 25, "weak.declares.act"),
                self._row(False, 0.9, 88, "strong.other.act")]
        ordered = gc._order_with_act_flag(rows)
        self.assertEqual([r[2] for r in ordered], ["strong.other.act", "weak.declares.act"])

    def test_an_act_declarer_that_out_scores_the_field_still_leads(self):
        """And the gain it was added for: 42 leads 30 even though BM25 prefers the 30."""
        rows = [self._row(False, 6.25, 30, "other.act"),
                self._row(True, 5.72, 42, "declares.act")]
        ordered = gc._order_with_act_flag(rows)
        self.assertEqual([r[2] for r in ordered], ["declares.act", "other.act"])

    def test_bm25_still_decides_when_nobody_declares_the_goal_verb(self):
        rows = [self._row(False, 0.4, 60, "high.score.low.relevance"),
                self._row(False, 9.1, 40, "low.score.high.relevance")]
        ordered = gc._order_with_act_flag(rows)
        self.assertEqual([r[2] for r in ordered],
                         ["low.score.high.relevance", "high.score.low.relevance"])


class TheNameRuleReadsTheActAsWellAsTheObject(unittest.TestCase):
    def test_a_rival_that_owns_the_verb_and_outscores_strips_the_name_pin(self):
        """Creator 47 named by name; the verifier 61 declares the sentence's verb.

        Read from the real registry: before the fix the front door answered this sentence
        with the creator, i.e. it was asked to CHECK an archive and built a new one.
        """
        reg = _registry()
        work = TMP / uuid.uuid4().hex[:10]
        work.mkdir(parents=True, exist_ok=True)
        try:
            (work / "a.txt").write_text("x", encoding="utf-8")
            rel_manifest = work.relative_to(ROOT).as_posix() + "/manifest.json"
            (work / "manifest.json").write_text(
                json.dumps({"records": [{"verification_paths": [
                    work.relative_to(ROOT).as_posix() + "/a.txt"]}]}),
                encoding="utf-8",
            )
            with tarfile.open(work / "bundle.tar.gz", "w:gz") as tf:
                tf.add(work / "a.txt", arcname="a.txt")
            rel_bundle = work.relative_to(ROOT).as_posix() + "/bundle.tar.gz"
            for verb in ("Verify", "Check", "Audit", "Inspect", "Validate"):
                goal = (f"{verb} the tar.gz archive {rel_bundle} "
                        f"against the manifest {rel_manifest}.")
                compiled = front.compile_goal(goal, reg, str(ROOT))
                self.assertEqual(compiled.get("selected_capability"), VERIFIER, (verb, goal))
            goal = (f"Create the tar.gz archive {rel_bundle} "
                    f"from the manifest {rel_manifest}.")
            compiled = front.compile_goal(goal, reg, str(ROOT))
            self.assertEqual(compiled.get("selected_capability"), CREATOR, goal)
        finally:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
