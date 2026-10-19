"""The channel that lets the machine say 'I don't have the data' and then get it.

The gate is the point. One source answering is exactly how "one paper said
YouTube" becomes a conclusion, so fewer than the required number of
INDEPENDENT sources is not a thin pass -- it is refused, and the refusal says
the data is incomplete.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from canonical.runtime import jit_knowledge_v1 as jit

# a goal the machine genuinely cannot compile, so the gap path actually runs
GAP_GOAL = "write the text hello to out.txt"


def _boom(query, limit, timeout):
    """A source that is down. Raises the way a real unreachable host would."""
    raise OSError("down")


class _Stub:
    """Deterministic sources. Network tests are separate and tolerate failure."""

    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp(prefix="brain-jit-test-")
        self._state = jit.STATE_PATH
        jit.STATE_PATH = os.path.join(self._tmp, "value.json")
        self._sources = dict(jit.SOURCES)
        jit.SOURCES.clear()
        jit.SOURCES.update({
            "alpha": {"fetch": lambda q, l, t: [{"kind": "k", "id": "a1", "title": "A one",
                                                 "summary": "s", "url": "u"}], "cost": 1.0},
            "beta": {"fetch": lambda q, l, t: [{"kind": "k", "id": "b1", "title": "B one",
                                                "summary": "s", "url": "u"}], "cost": 1.0},
            "empty": {"fetch": lambda q, l, t: [], "cost": 0.5},
            "broken": {"fetch": _boom, "cost": 0.5},
        })

    def tearDown(self) -> None:
        jit.SOURCES.clear()
        jit.SOURCES.update(self._sources)
        jit.STATE_PATH = self._state
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)


# --------------------------------------------------------------------------- #
# the gate -- one source is not knowledge
# --------------------------------------------------------------------------- #
class CompletenessGateTests(_Stub, unittest.TestCase):
    def test_two_independent_sources_are_required_by_default(self):
        self.assertEqual(jit.DEFAULT_MIN_SOURCES, 2)

    def test_one_answering_source_cannot_conclude(self):
        """This is the 'one paper said YouTube' failure, refused structurally."""
        r = jit.resolve("q", only=["alpha"], min_sources=2)
        self.assertFalse(r["pass"])
        self.assertEqual(r["status"], jit.OPEN_THIN)
        self.assertIn("only 1 of 2", r["gap"])

    def test_two_answering_sources_can_conclude(self):
        r = jit.resolve("q", only=["alpha", "beta"], min_sources=2)
        self.assertTrue(r["pass"], r.get("gap"))
        self.assertEqual(r["status"], jit.PASS)

    def test_a_thin_result_still_returns_what_was_found(self):
        """Refusing to conclude is not the same as throwing the data away."""
        r = jit.resolve("q", only=["alpha"], min_sources=2)
        self.assertEqual(r["document_count"], 1)
        self.assertFalse(r["complete"])

    def test_a_thin_result_refuses_the_knowledge_authority_label(self):
        r = jit.resolve("q", only=["alpha"], min_sources=2)
        self.assertEqual(r["authority"], "INCOMPLETE_DATA_NO_CONCLUSION_DRAWN")

    def test_a_complete_result_claims_only_external_evidence(self):
        r = jit.resolve("q", only=["alpha", "beta"], min_sources=2)
        self.assertEqual(r["authority"], "EXTERNAL_PUBLIC_EVIDENCE_FETCHED")

    def test_no_source_answering_is_a_failure_not_a_pass(self):
        r = jit.resolve("q", only=["empty", "broken"], min_sources=2)
        self.assertFalse(r["pass"])
        self.assertEqual(r["status"], jit.FAIL_NO_SOURCE)

    def test_an_empty_query_fails_closed(self):
        r = jit.resolve("   ")
        self.assertEqual(r["status"], jit.FAIL_EMPTY)
        self.assertFalse(r["pass"])


# --------------------------------------------------------------------------- #
# provenance and honesty
# --------------------------------------------------------------------------- #
class ProvenanceTests(_Stub, unittest.TestCase):
    def test_every_document_carries_where_it_came_from(self):
        r = jit.resolve("q", only=["alpha", "beta"], min_sources=2)
        for doc in r["documents"]:
            self.assertIn(doc["source"], ("alpha", "beta"))
            self.assertTrue(doc["sha256"])
            self.assertEqual(doc["authority"], "EXTERNAL_PUBLIC_EVIDENCE_FETCHED")

    def test_a_source_that_returns_nothing_is_reported_as_not_answering(self):
        r = jit.resolve("q", only=["alpha", "beta", "empty"], min_sources=2)
        self.assertNotIn("empty", r["sources_answered"])
        self.assertIn("empty", r["sources_failed"])

    def test_a_source_that_raises_does_not_break_the_resolve(self):
        r = jit.resolve("q", only=["alpha", "beta", "broken"], min_sources=2)
        self.assertTrue(r["pass"])
        self.assertIn("broken", r["sources_failed"])

    def test_an_unknown_source_is_a_closed_failure(self):
        r = jit.fetch_source("no_such_source", "q")
        self.assertFalse(r["ok"])
        self.assertEqual(r["reason"], "UNKNOWN_SOURCE")

    def test_failed_sources_are_named_in_the_detail(self):
        r = jit.resolve("q", only=["alpha", "beta", "broken"], min_sources=2)
        detail = {d["source"]: d for d in r["detail"]}
        self.assertFalse(detail["broken"]["ok"])
        self.assertTrue(detail["broken"]["reason"])


# --------------------------------------------------------------------------- #
# earned order -- not a strict sequence
# --------------------------------------------------------------------------- #
class EarnedOrderTests(_Stub, unittest.TestCase):
    def test_a_source_that_keeps_delivering_rises(self):
        before = jit.ordered_sources()
        for _ in range(8):
            jit.credit("beta", True)
        after = jit.ordered_sources()
        self.assertEqual(after[0], "beta")
        self.assertNotEqual(before, after)

    def test_a_source_that_keeps_coming_back_empty_falls(self):
        for _ in range(8):
            jit.credit("alpha", False)
        self.assertEqual(jit.ordered_sources()[-1], "alpha")

    def test_credit_persists(self):
        jit.credit("beta", True)
        self.assertEqual(jit._load_state()["beta"]["helped"], 1)
        self.assertEqual(jit._load_state()["beta"]["trials"], 1)

    def test_an_untried_source_starts_on_the_same_prior(self):
        self.assertAlmostEqual(jit.source_value("alpha"), jit.source_value("beta"),
                               places=6)

    def test_cheaper_sources_win_before_any_experience(self):
        # equal prior, so value is decided by cost alone: cheaper ranks higher
        self.assertGreater(jit.source_value("empty"), jit.source_value("alpha"))

    def test_resolve_asks_in_the_earned_order(self):
        for _ in range(8):
            jit.credit("beta", True)
        # capture BEFORE resolving: resolve credits the sources it used, so the
        # order it reports is the order as it stood when it asked
        expected = jit.ordered_sources(["alpha", "beta"])
        r = jit.resolve("q", only=["alpha", "beta"], min_sources=2)
        self.assertEqual(r["sources_asked"], expected)
        self.assertEqual(expected[0], "beta")


# --------------------------------------------------------------------------- #
# live network -- proven against real traffic, tolerated if the net is down
# --------------------------------------------------------------------------- #
class LiveSourceTests(unittest.TestCase):
    """These hit github, pypi and npm. Skipped, never faked, if unreachable."""

    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp(prefix="brain-jit-live-")
        self._state = jit.STATE_PATH
        jit.STATE_PATH = os.path.join(self._tmp, "value.json")

    def tearDown(self) -> None:
        jit.STATE_PATH = self._state
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _skip_if_offline(self) -> None:
        try:
            import urllib.request
            urllib.request.urlopen("https://pypi.org/pypi/requests/json", timeout=15).close()
        except Exception as exc:  # noqa: BLE001
            self.skipTest("network unreachable: %s" % type(exc).__name__)

    def test_real_sources_return_real_documents(self):
        self._skip_if_offline()
        r = jit.resolve("pdf text extraction", only=["pypi"], min_sources=1)
        self.assertTrue(r["pass"], r)
        self.assertGreater(r["document_count"], 0)
        for doc in r["documents"]:
            self.assertEqual(doc["source"], "pypi")

    def test_multiple_real_sources_satisfy_the_gate(self):
        self._skip_if_offline()
        r = jit.resolve("pdf text extraction", only=["pypi", "npm"], min_sources=2)
        self.assertTrue(r["pass"], r.get("gap"))
        self.assertGreaterEqual(len(r["sources_answered"]), 2)

    def test_the_machine_learns_which_live_source_delivered(self):
        self._skip_if_offline()
        jit.resolve("pdf text extraction", only=["pypi"], min_sources=1)
        state = jit._load_state()
        self.assertIn("pypi", state)
        self.assertGreaterEqual(state["pypi"]["trials"], 1)


# --------------------------------------------------------------------------- #
# wired into the live path
# --------------------------------------------------------------------------- #
class LivePathWiringTests(_Stub, unittest.TestCase):
    def test_a_compilation_gap_now_consults_knowledge(self):
        from canonical.runtime import live_brain_route_admission_v1 as ra

        r = ra.solve_or_learn({"task_id": "t", "goal": GAP_GOAL})
        self.assertEqual(r["status"], "FAIL__RAW_GOAL_COMPILATION_GAP")
        learned = r.get("learning") or {}
        self.assertIn("knowledge", learned, learned)
        self.assertIn("status", learned["knowledge"])

    def test_knowledge_reports_how_many_sources_answered(self):
        from canonical.runtime import live_brain_route_admission_v1 as ra

        r = ra.solve_or_learn({"task_id": "t", "goal": GAP_GOAL})
        k = (r.get("learning") or {}).get("knowledge") or {}
        self.assertIn("sources_answered", k)
        self.assertIsInstance(k["sources_answered"], list)

    def test_the_machine_only_uses_a_program_that_is_actually_here(self):
        """Knowledge naming a program is not enough; it must exist on disk."""
        from canonical.runtime import live_brain_route_admission_v1 as ra

        self.assertTrue(ra._is_executable("python3"))          # present
        self.assertFalse(ra._is_executable("definitely_not_a_program_xyz"))

    def test_a_successful_goal_does_not_consult_knowledge(self):
        from canonical.runtime import live_brain_route_admission_v1 as ra

        r = ra.solve_or_learn({"task_id": "t", "goal": "run shell command echo hello"})
        self.assertTrue(r.get("pass") is True, r.get("status"))
        self.assertNotIn("learning", r)


if __name__ == "__main__":
    unittest.main()
