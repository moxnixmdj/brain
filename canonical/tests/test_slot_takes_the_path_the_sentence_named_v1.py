#!/usr/bin/env python3
"""A slot takes the path the sentence introduced for it, not whichever came first.

MEASURED 2026-10-27, before this file existed.  One plain sentence:

    "Verify the tar.gz archive <dir>/x.tar.gz against the manifest <dir>/M.json"

`extract_paths` returns ['tar.gz', '<dir>/x.tar.gz', '<dir>/M.json'] -- the prose
words "tar.gz" are path-shaped and stand first -- and `bind` gave every path slot
`paths[0]`:

    manifest_path = "tar.gz"          -> the adapter raised MANIFEST_INPUT_REQUIRED
    output_path   = "<dir>/M.json"    -> the manifest, bound as the thing to write

Both real paths were in the sentence.  The composition that the composer had
just planned therefore died on its first step, so a chain that was valid could
never run.

Two facts decide the slot, and neither is a hand-written table:

  * the word the sentence put in FRONT of the path -- "the ... archive <A>",
    "the manifest <M>" -- matched against the slot's own name;
  * existence -- an input must be readable, an output is the file that is not
    there yet.

Each rule answers only when it is unambiguous: exactly one candidate matches the
slot's word, or exactly one repository path exists / is missing.  Every other
sentence keeps the historical order rule byte for byte, which the controls below
pin (`compress notes.txt into notes.txt.gz` is the canonical one).
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import capability_composer_v1 as composer  # noqa: E402
from canonical.runtime import capability_type_surface_v1 as TS  # noqa: E402
from canonical.runtime import composer_route_v1 as route  # noqa: E402

MANIFEST = "canonical/astra_runtime/tmp/ARCHIVE_VERIFY_MANIFEST.json"
WORK = "canonical/astra_runtime/tmp/bind_unit_tests"
CREATE = "archive.tar_gz.create_from_manifest"
VERIFY = "archive.verify.tar_gz.gnu"


def _signature(capability_id: str) -> dict[str, str]:
    entry = dict(composer.load_registry()[capability_id])
    entry["capability_id"] = capability_id
    return dict(TS.signature(entry))


class ASlotTakesThePathTheSentenceIntroducedForIt(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(REPO_ROOT / WORK, ignore_errors=True)
        (REPO_ROOT / WORK).mkdir(parents=True, exist_ok=True)
        self.archive = f"{WORK}/built.tar.gz"

    def tearDown(self):
        shutil.rmtree(REPO_ROOT / WORK, ignore_errors=True)

    def _goal(self):
        return (f"Verify the tar.gz archive {self.archive} "
                f"against the manifest {MANIFEST}.")

    def test_the_prose_word_is_never_a_path_a_slot_takes(self):
        """'tar.gz' appears in the sentence and is not a file anyone named."""
        bound = route.bind(_signature(CREATE), self._goal())
        self.assertNotIn("tar.gz", set(bound.values()))

    def test_the_manifest_binds_to_the_manifest_slot(self):
        bound = route.bind(_signature(CREATE), self._goal())
        self.assertEqual(bound.get("manifest_path"), MANIFEST)

    def test_the_archive_that_does_not_exist_binds_to_the_output_slot(self):
        bound = route.bind(_signature(CREATE), self._goal())
        self.assertEqual(bound.get("output_path"), self.archive)

    def test_the_verifier_takes_the_archive_and_the_manifest_apart(self):
        """Both files exist by then, so only the sentence's own nouns can decide."""
        (REPO_ROOT / WORK / "built.tar.gz").write_bytes(b"\x1f\x8bplaceholder")
        bound = route.bind(_signature(VERIFY), self._goal())
        self.assertEqual(bound.get("archive_path"), self.archive)
        self.assertEqual(bound.get("manifest_path"), MANIFEST)

    def test_a_slot_word_shared_by_two_paths_decides_nothing(self):
        """Ambiguity must fall back, not guess."""
        goal = (f"Verify the archive {self.archive} "
                f"against the archive {WORK}/other.tar.gz.")
        self.assertIsNone(route._noun_matched_path("archive_path",
                                                   route.extract_paths(goal), goal))


class TheOrderRuleIsUnchangedWhereNothingDisambiguates(unittest.TestCase):
    """The controls: sentences that already bound correctly must bind as before."""

    def test_compression_keeps_input_first_and_output_last(self):
        work = REPO_ROOT / WORK
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True, exist_ok=True)
        (work / "notes.txt").write_text("payload", encoding="utf-8")
        goal = f"Compress the file {WORK}/notes.txt into {WORK}/notes.txt.gz."
        bound = route.bind({"source_path": "PATH_FILE",
                            "output_path": "PATH_OUTPUT"}, goal)
        self.assertEqual(bound.get("source_path"), f"{WORK}/notes.txt")
        self.assertEqual(bound.get("output_path"), f"{WORK}/notes.txt.gz")
        shutil.rmtree(work, ignore_errors=True)

    def test_a_single_named_output_still_binds(self):
        goal = "Write the text 'hello' to the file canonical/astra_runtime/tmp/out.txt."
        bound = route.bind({"content": "STRING", "output_path": "PATH_OUTPUT"}, goal)
        self.assertEqual(bound.get("output_path"),
                         "canonical/astra_runtime/tmp/out.txt")

    def test_no_paths_means_no_binding(self):
        self.assertEqual(route.bind({"output_path": "PATH_OUTPUT"},
                                    "Summarise this repository."), {})


class TheChainThatCouldNotRunNowRuns(unittest.TestCase):
    """The measurement this file exists for, executed rather than asserted."""

    def setUp(self):
        shutil.rmtree(REPO_ROOT / WORK, ignore_errors=True)
        (REPO_ROOT / WORK).mkdir(parents=True, exist_ok=True)
        self.archive = f"{WORK}/composed.tar.gz"
        self.goal = (f"Verify the tar.gz archive {self.archive} "
                     f"against the manifest {MANIFEST}.")

    def tearDown(self):
        shutil.rmtree(REPO_ROOT / WORK, ignore_errors=True)

    def test_the_planner_asks_for_two_steps(self):
        routed = route.route(self.goal)
        self.assertTrue(routed.get("pass"), routed)
        self.assertEqual(routed.get("chain"), [CREATE, VERIFY])

    def test_both_steps_run_with_the_arguments_the_sentence_stated(self):
        routed = route.route(self.goal)
        executed = route.execute_chain(routed["chain"], self.goal)
        self.assertTrue(executed.get("pass"), executed)
        steps = executed["steps"]
        self.assertEqual([step["capability_id"] for step in steps],
                         [CREATE, VERIFY])
        self.assertEqual(steps[0]["args"]["manifest_path"], MANIFEST)
        self.assertEqual(steps[0]["args"]["output_path"], self.archive)
        self.assertEqual(steps[1]["args"]["archive_path"], self.archive)
        self.assertEqual(steps[1]["args"]["manifest_path"], MANIFEST)

    def test_the_verifier_really_checked_the_bytes_that_were_written(self):
        routed = route.route(self.goal)
        executed = route.execute_chain(routed["chain"], self.goal)
        verdict = executed["steps"][1]["result"]
        self.assertTrue(verdict.get("verified"), verdict)
        self.assertTrue((REPO_ROOT / self.archive).is_file())


if __name__ == "__main__":
    unittest.main()
