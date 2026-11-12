#!/usr/bin/env python3
"""Teeth for three repairs that turn experience into knowledge.

Each class protects a behaviour that was MEASURED BROKEN on this base, and each is written to fail
if that behaviour is reintroduced:

  * the world index was memoised on the root path and never invalidated -- create a file and the
    probe still said False, delete it and it still said True;
  * bound adapters always executed against the repository ROOT while the caller had sensed and
    bound against a different root, so no other environment could be acted in at all;
  * with successes only, the query selector had no hypothesis space to choose against, so the live
    path reported zero survivors after three real successes and could never propose a contrast.

The store-reading tests assert on what was WRITTEN, not on what a return field claims.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import applicability_v1 as APP
from canonical.runtime import chain_v1 as C
from canonical.runtime import contrast_selection_v1 as CS
from canonical.runtime import macro_v1 as MC
from canonical.runtime import world_probe_v1 as WP

GOAL = (
    "verify the docx canonical/astra_runtime/tmp/DOCX_INTENT_VERIFY.docx "
    "and create a tar.gz archive from the manifest"
)


class TheWorldIsResensedNotRemembered(unittest.TestCase):
    """A cached listing that cannot notice a new file makes every new environment the old one."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        WP._INDEX_CACHE.clear()
        WP._MATCH_CACHE.clear()
        WP._INDEX_STAMP.clear()

    def tearDown(self):
        self._tmp.cleanup()
        WP._INDEX_CACHE.clear()
        WP._MATCH_CACHE.clear()
        WP._INDEX_STAMP.clear()

    def _present(self):
        return bool(WP.probe_effect(
            "manifest.json.available", goal="", goal_paths=(), root=self.root).get("true"))

    def test_a_file_created_after_the_first_look_is_seen(self):
        self.assertFalse(self._present())
        (self.root / "manifest.json").write_text("{}", encoding="utf-8")
        self.assertTrue(self._present(), "a created file must become visible without a new process")

    def test_a_deleted_file_stops_being_seen(self):
        (self.root / "manifest.json").write_text("{}", encoding="utf-8")
        self.assertTrue(self._present())
        (self.root / "manifest.json").unlink()
        self.assertFalse(self._present(), "a deleted file must stop satisfying the fact")

    def test_a_renamed_file_stops_satisfying_the_kind(self):
        (self.root / "manifest.json").write_text("{}", encoding="utf-8")
        self.assertTrue(self._present())
        (self.root / "manifest.json").rename(self.root / "other.json")
        self.assertFalse(self._present())

    def test_a_nested_creation_is_seen(self):
        self.assertFalse(self._present())
        sub = self.root / "canonical" / "deep"
        sub.mkdir(parents=True)
        (sub / "manifest.json").write_text("{}", encoding="utf-8")
        self.assertTrue(self._present(), "the fingerprint must cover subdirectories, not just the root")

    def test_the_token_does_not_depend_on_timestamp_resolution(self):
        # This filesystem left the parent mtime bit-identical across a create. A token built from
        # mtimes alone passed no test here; entry names are resolution-independent.
        import os

        before = os.stat(self.root).st_mtime_ns
        (self.root / "manifest.json").write_text("{}", encoding="utf-8")
        after = os.stat(self.root).st_mtime_ns
        self.assertTrue(self._present())
        if before == after:
            self.assertTrue(self._present(), "sensed correctly even though mtime never changed")

    def test_an_unchanged_tree_reuses_the_cached_listing(self):
        WP._index(self.root)
        cached = WP._INDEX_CACHE[str(self.root)]
        WP._index(self.root)
        self.assertIs(WP._INDEX_CACHE[str(self.root)], cached,
                      "correctness must not cost a reindex on every probe")


class AdaptersRunInTheEnvironmentTheyWereBoundIn(unittest.TestCase):
    """Sensing one world and executing in another makes every contrast impossible."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self._state = MC.STATE
        self._saved = self._state.read_bytes() if self._state.is_file() else None
        MC.STATE = self.base / "macros.json"

    def tearDown(self):
        MC.STATE = self._state
        if self._saved is not None:
            self._state.write_bytes(self._saved)
        self._tmp.cleanup()

    def _env(self, name, *, manifest):
        root = self.base / name
        tmp = root / "canonical/astra_runtime/tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        src = Path(__file__).resolve().parents[2] / "canonical/astra_runtime/tmp"
        for item in ("DOCX_INTENT_VERIFY.docx", "DOCX_INTENT_VERIFY.docx.intent.json"):
            if (src / item).is_file():
                (tmp / item).write_bytes((src / item).read_bytes())
        if manifest:
            (root / "canonical/manifest.json").write_text('{"records": []}', encoding="utf-8")
        return root

    def test_a_manifest_that_exists_only_in_the_target_root_is_used(self):
        from canonical.runtime import astra_runtime

        root = self._env("with_manifest", manifest=True)
        out = astra_runtime._invoke_bound_capability({
            "capability_id": "archive.tar_gz.create_from_manifest",
            "manifest_path": "canonical/manifest.json",
            "output_path": "canonical/astra_runtime/tmp/probe_out.tar.gz",
        }, root=root)
        self.assertEqual(out.get("capability_id"), "archive.tar_gz.create_from_manifest")
        self.assertTrue((root / "canonical/astra_runtime/tmp/probe_out.tar.gz").is_file(),
                        "the artifact must be written in the CALLER's root")

    def test_the_same_call_in_an_empty_root_fails_rather_than_borrowing_the_repository(self):
        from canonical.runtime import astra_runtime

        root = self._env("empty", manifest=False)
        with self.assertRaises(Exception) as caught:
            astra_runtime._invoke_bound_capability({
                "capability_id": "archive.tar_gz.create_from_manifest",
                "manifest_path": "canonical/manifest.json",
                "output_path": "canonical/astra_runtime/tmp/probe_out.tar.gz",
            }, root=root)
        self.assertIn("MANIFEST_INPUT_REQUIRED", str(caught.exception))

    def test_omitting_root_preserves_the_previous_behaviour(self):
        import inspect
        from canonical.runtime import astra_runtime

        sig = inspect.signature(astra_runtime._invoke_bound_capability)
        self.assertIsNone(sig.parameters["root"].default,
                          "46 existing callers pass no root; the default must stay the repository")

    def test_a_real_chain_produces_a_real_contrast_across_two_roots(self):
        rich = self._env("rich", manifest=True)
        poor = self._env("poor", manifest=False)
        yes = C.run(GOAL, root=rich, memory=True)
        no = C.run(GOAL, root=poor, memory=True)
        self.assertTrue(yes["ok"], "the equipped environment must succeed")
        self.assertFalse(no["ok"], "the unequipped environment must fail")
        key = MC.signature(C.decompose(GOAL))
        entry = (MC._load().get("macros") or {}).get(key) or {}
        rows = [(tuple(sorted(r.get("facts") or ())), r.get("ok"))
                for r in (entry.get("evidence") or [])]
        self.assertTrue(any(ok for _, ok in rows), "the STORE must hold the success")
        self.assertTrue(any(not ok for _, ok in rows), "the STORE must hold the failure")
        boundary = MC.applicability(key)
        self.assertNotEqual(boundary.status, APP.UNDETERMINED,
                            "a real success and a real failure must license a boundary")
        self.assertTrue(boundary.most_general, "and that boundary must scope the plan")


class ChoosingBeatsRepeating(unittest.TestCase):
    """The selector must choose a splitting state, and admit when none exists."""

    def test_successes_alone_define_a_space_even_though_they_license_no_boundary(self):
        evidence = [(("a", "b", "c"), True)]
        self.assertEqual(APP.learn(evidence).status, APP.UNDETERMINED,
                         "the refusal to license a boundary from successes must NOT weaken")
        self.assertEqual(len(APP.candidate_requirements(evidence)), 8,
                         "but the space of still-possible requirements must be available")

    def test_a_fact_absent_from_a_success_cannot_be_a_requirement(self):
        space = APP.candidate_requirements([(("a", "b"), True), (("a",), True)])
        self.assertTrue(space)
        self.assertFalse(any("b" in need for need in space))

    def test_the_chosen_state_splits_the_survivors(self):
        evidence = [(("a", "b", "c"), True)]
        choice = CS.select_contrast(evidence, [("a", "b", "c"), ("a",), ()])
        self.assertEqual(choice.status, CS.SELECTED)
        self.assertGreater(choice.guaranteed_elimination(), 0)
        self.assertLess(choice.worst_case_survivors_after, choice.survivors_before)

    def test_repeating_a_state_where_all_survivors_agree_is_refused(self):
        evidence = [(("a", "b"), True)]
        choice = CS.select_contrast(evidence, [("a", "b")])
        self.assertEqual(choice.status, CS.NO_INFORMATIVE_STATE)
        self.assertFalse(choice.informative)
        self.assertEqual(choice.gain_log_terms, {}, "zero gain must be recognised exactly")

    def test_the_most_even_split_wins_over_a_state_that_kills_only_one(self):
        evidence = [(("a", "b", "c"), True)]
        # (): only the empty requirement admits it -> kills 1. ('a',): admits 2 of 8 -> kills 2.
        choice = CS.select_contrast(evidence, [(), ("a",)])
        self.assertEqual(choice.state, ("a",))

    def test_no_success_yields_no_space_and_no_choice(self):
        self.assertEqual(APP.candidate_requirements([(("a",), False)]), ())
        self.assertEqual(CS.select_contrast([(("a",), False)], [("a",)]).status, CS.NO_SPACE)

    def test_an_identified_requirement_needs_no_further_query(self):
        evidence = [(("a",), True), ((), False)]
        self.assertTrue(APP.learn(evidence).identified)
        self.assertEqual(CS.select_contrast(evidence, [(), ("a",)]).status, CS.ALREADY_SETTLED)

    def test_the_selector_invents_no_state(self):
        evidence = [(("a", "b"), True)]
        choice = CS.select_contrast(evidence, [("a",)])
        self.assertEqual(choice.state, ("a",), "only a supplied reachable state may be returned")
        self.assertEqual(CS.select_contrast(evidence, []).status, CS.NO_POOL)

    def test_discriminating_facts_exclude_what_all_survivors_share(self):
        requirements = [frozenset({"a"}), frozenset({"a", "b"})]
        self.assertEqual(CS.discriminating_facts(requirements), ("b",))

    def test_the_live_path_reports_a_next_contrast(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = MC.STATE
            saved = state.read_bytes() if state.is_file() else None
            try:
                MC.STATE = Path(tmp) / "m.json"
                result = C.run(GOAL, memory=True)
                self.assertIn("next_contrast", result)
                row = result["next_contrast"]
                self.assertIsNotNone(row, "a remembered multi-step run must report advice")
                self.assertEqual(row["schema"], CS.SCHEMA)
                self.assertTrue(row["status"])
            finally:
                MC.STATE = state
                if saved is not None:
                    state.write_bytes(saved)

    def test_the_store_reader_and_the_selector_see_the_same_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = MC.STATE
            saved = state.read_bytes() if state.is_file() else None
            try:
                MC.STATE = Path(tmp) / "m.json"
                clauses = ["verify the docx a.docx", "create a tar.gz archive from the manifest"]
                key = MC.signature(clauses)
                steps = [{"capability_id": "x.one", "verified": True},
                         {"capability_id": "x.two", "verified": True}]
                MC.record(clauses, steps, context=frozenset({"a", "b"}))
                MC.note_failure(key, context=frozenset({"a"}))
                rows = MC._evidence_rows((MC._load().get("macros") or {}).get(key) or {})
                direct = CS.select_contrast(rows, [frozenset(s) for s, _ in rows])
                stored = MC.next_contrast(key)
                self.assertEqual(direct.status, stored.status)
                self.assertEqual(direct.state, stored.state)
            finally:
                MC.STATE = state
                if saved is not None:
                    state.write_bytes(saved)


if __name__ == "__main__":
    unittest.main()
