#!/usr/bin/env python3
"""Teeth for counting DISTINCT requirements instead of spellings.

The measured defect: two real chosen contrasts left survivors
`{manifest.json}` and `{manifest.json, structured.json}`, reported AMBIGUOUS, with the selector
reporting that no reachable state could ever separate them. But the sensor decides `manifest.json`
as "a .json named manifest" and `structured.json` as "a .json", so the first implies the second and
those are ONE requirement. The system claimed ignorance where it had certainty.

The danger of the repair is the opposite error: an UNSOUND implication would delete a real
requirement and let a plan run where it fails. Most of this file attacks that direction, including
falsifying every claimed implication against the real sensor on real directories.
"""
from __future__ import annotations

import itertools
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import applicability_v1 as APP
from canonical.runtime import contrast_selection_v1 as CS
from canonical.runtime import fact_entailment_v1 as FE
from canonical.runtime import world_probe_v1 as WP

MANIFEST = "manifest.json.available"
STRUCTURED = "structured.json.available"
ARCHIVE = "archive.tar_gz.available"


class TheImplicationIsSound(unittest.TestCase):
    """Every claimed implication must survive the real sensor, not just the private matcher."""

    #: A file that makes each kind true. Absent -> the kind is not exercised.
    PAYLOAD = {
        "manifest.json": "manifest.json", "trades.json": "trades.json",
        "python.test.corpus": "test_x.py", "python.source": "x.py",
        "json": "x.json", "structured.json": "x.json",
        "candidate.response_or_fields": "x.json", "archive.tar_gz": "x.tgz",
        "csv": "x.csv", "docx": "x.docx", "html": "x.html", "image": "x.png",
        "markdown": "x.md", "pdf": "x.pdf", "pdf.file.image_only": "x.pdf",
        "sqlite": "x.sqlite", "xlsx": "x.xlsx", "yaml": "x.yaml",
        "artifact.file": "x.any",
    }

    def test_no_claimed_implication_is_falsified_by_the_real_probe(self):
        pairs = [(a, b) for a in sorted(FE.known_facts()) for b in sorted(FE.known_facts())
                 if a != b and FE.implies(a, b)]
        self.assertGreater(len(pairs), 10, "the relation must not be silently empty")
        violations = []
        with tempfile.TemporaryDirectory() as tmp:
            for a, b in pairs:
                subject = a[: -len(".available")]
                name = self.PAYLOAD.get(subject)
                if name is None:
                    continue
                root = Path(tmp) / (subject.replace(".", "_") + "__" + b.replace(".", "_"))
                root.mkdir()
                (root / name).write_bytes(b"{}")
                fa = WP.probe_effect(a, goal="", goal_paths=(), root=root).get("true")
                fb = WP.probe_effect(b, goal="", goal_paths=(), root=root).get("true")
                if fa and not fb:
                    violations.append((a, b))
        self.assertEqual(violations, [], "an implication the sensor contradicts must never be claimed")

    def test_the_weakest_kind_implies_no_narrower_kind(self):
        # The first implementation read an empty suffix set as "matches nothing" and produced 38
        # bogus equivalences including artifact.file == docx. Empty means ANY file.
        self.assertFalse(FE.implies("artifact.file.available", "docx.available"))
        self.assertFalse(FE.implies("structured.json.available", MANIFEST))
        self.assertFalse(FE.implies("python.source.available", "python.test.corpus.available"))

    def test_the_direction_that_matters_holds(self):
        self.assertTrue(FE.implies(MANIFEST, STRUCTURED))
        self.assertTrue(FE.implies("python.test.corpus.available", "python.source.available"))

    def test_the_relation_is_transitive_over_every_triple(self):
        # `_spec_implies` is relied on to be transitive, which is why no closure pass exists.
        # Check the property itself over ALL triples, so a future kind rule that breaks it fails
        # here instead of silently leaving redundant literals un-reduced.
        facts = sorted(FE.known_facts())
        for a in facts:
            for b in facts:
                if not FE.implies(a, b):
                    continue
                for c in facts:
                    if FE.implies(b, c):
                        self.assertTrue(FE.implies(a, c),
                                        "non-transitive relation: %s => %s => %s" % (a, b, c))

    def test_unknown_facts_are_never_reduced_away(self):
        self.assertFalse(FE.implies("z.unknown.available", "a.unknown.available"))
        self.assertEqual(FE.reduce_requirement(["z.unknown.available", "a.unknown.available"]),
                         ("a.unknown.available", "z.unknown.available"))

    def test_mutually_implied_names_collapse_to_one_and_not_to_zero(self):
        row = FE.reduce_requirement(["json.available", STRUCTURED,
                                     "candidate.response_or_fields.available"])
        self.assertEqual(len(row), 1, "three names for one test must become one literal")
        self.assertTrue(row[0])

    def test_reduction_is_idempotent(self):
        once = FE.reduce_requirement([MANIFEST, STRUCTURED, ARCHIVE])
        self.assertEqual(FE.reduce_requirement(once), once)


class RedundancyIsNotAmbiguity(unittest.TestCase):
    def test_the_measured_pair_is_now_identified(self):
        evidence = [({MANIFEST, STRUCTURED, ARCHIVE}, True),
                    ({STRUCTURED, ARCHIVE}, False),
                    ({MANIFEST, STRUCTURED}, True)]
        boundary = APP.learn(evidence)
        self.assertEqual(boundary.status, APP.IDENTIFIED)
        self.assertEqual(boundary.survivor_count, 1)
        self.assertEqual(boundary.required, (MANIFEST,))

    def test_genuine_ambiguity_is_still_reported(self):
        # Two independent facts, only ever seen together: nothing licenses choosing between them.
        evidence = [({"a.free.available", "b.free.available"}, True), (set(), False)]
        boundary = APP.learn(evidence)
        self.assertEqual(boundary.status, APP.AMBIGUOUS)
        self.assertIsNone(boundary.required)
        self.assertGreater(boundary.survivor_count, 1)

    def test_successes_alone_still_license_nothing(self):
        boundary = APP.learn([({MANIFEST, STRUCTURED}, True)])
        self.assertEqual(boundary.status, APP.UNDETERMINED)
        self.assertIsNone(boundary.required)

    def test_reduction_never_admits_a_state_the_full_requirement_refused(self):
        # The load-bearing safety property: on every world the sensor can actually produce, the
        # reduced requirement and the unreduced one must give the SAME verdict.
        requirement = frozenset({MANIFEST, STRUCTURED})
        reduced = frozenset(FE.reduce_requirement(requirement))
        with tempfile.TemporaryDirectory() as tmp:
            for size in range(3):
                for combo in itertools.combinations(sorted(self_files()), size):
                    root = Path(tmp) / ("env_%d_%s" % (size, abs(hash(combo))))
                    root.mkdir()
                    for name in combo:
                        (root / name).write_bytes(b"{}")
                    facts = frozenset(
                        f for f in (MANIFEST, STRUCTURED, ARCHIVE)
                        if WP.probe_effect(f, goal="", goal_paths=(), root=root).get("true"))
                    self.assertEqual(requirement <= facts, reduced <= facts,
                                     "reduction changed a real admission decision")

    def test_the_selector_stops_because_it_is_settled_not_because_it_is_stuck(self):
        evidence = [({MANIFEST, STRUCTURED, ARCHIVE}, True),
                    ({STRUCTURED, ARCHIVE}, False),
                    ({MANIFEST, STRUCTURED}, True)]
        choice = CS.select_contrast(evidence, [{MANIFEST, STRUCTURED}, {STRUCTURED}])
        self.assertEqual(choice.status, CS.ALREADY_SETTLED)

    def test_the_space_shrinks_without_losing_the_true_requirement(self):
        evidence = [({MANIFEST, STRUCTURED}, True)]
        space = APP.candidate_requirements(evidence)
        self.assertIn((MANIFEST,), space)
        self.assertNotIn((MANIFEST, STRUCTURED), space,
                         "the redundant spelling must not occupy a second slot")
        self.assertEqual(len(space), len(set(space)))


def self_files():
    return ("manifest.json", "data.json", "bundle.tgz")


if __name__ == "__main__":
    unittest.main()
