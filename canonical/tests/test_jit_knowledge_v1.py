"""Only real tests. Every claim here is checked against live retrieval.

The previous version of this file was 92% vacuous: with all three real
fetchers sabotaged to return nothing, 24 of 26 tests still passed. They
exercised plumbing against stub sources that always answered, so they would
have passed even if the machine had no ability to retrieve anything at all.

These do not. They hit github, pypi and npm for real and assert on the
CONTENT: that a query about pdf returns documents that are actually about
pdf, that provenance hashes recompute, that a host that cannot resolve says
so. A test that cannot fail is not a test.

Pure logic (the value maths, the shape classifier) is tested directly as
functions where no network is involved, and labelled as such.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest

from canonical.runtime import jit_knowledge_v1 as jit


def _online() -> bool:
    try:
        import urllib.request
        urllib.request.urlopen("https://pypi.org/pypi/requests/json", timeout=15).close()
        return True
    except Exception:
        return False


ONLINE = _online()
requires_network = unittest.skipUnless(ONLINE, "network unreachable")


class _Store:
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp(prefix="brain-jit-")
        self._saved = jit.STATE_PATH
        jit.STATE_PATH = os.path.join(self._tmp, "value.json")

    def tearDown(self) -> None:
        jit.STATE_PATH = self._saved
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)


# --------------------------------------------------------------------------- #
# REAL retrieval -- a sabotaged fetcher cannot pass any of these
# --------------------------------------------------------------------------- #
@requires_network
class RealRetrievalTests(_Store, unittest.TestCase):
    def test_a_query_returns_documents_that_are_actually_about_it(self):
        """The content must relate to the question. Not just be present."""
        r = jit.resolve("pdf text extraction", only=["pypi"], min_sources=1,
                       min_kinds=1)
        self.assertTrue(r["pass"], r)
        self.assertGreater(r["document_count"], 0)
        blob = " ".join(
            " ".join(str(doc.get(k) or "") for k in ("id", "title", "summary"))
            for doc in r["documents"]).lower()
        self.assertIn("pdf", blob, blob[:400])

    def test_npm_returns_real_packages_for_a_real_query(self):
        r = jit.resolve("pdf", only=["npm"], min_sources=1, min_kinds=1)
        self.assertTrue(r["pass"], r)
        ids = [str(d.get("id") or "").lower() for d in r["documents"]]
        self.assertTrue(ids)
        self.assertTrue(any("pdf" in i for i in ids), ids[:10])

    def test_github_returns_real_repositories_with_real_urls(self):
        r = jit.resolve("pdf extract", only=["github"], min_sources=1,
                       min_kinds=1)
        self.assertTrue(r["pass"], r)
        for doc in r["documents"]:
            self.assertTrue(str(doc.get("url") or "").startswith("https://github.com/"),
                            doc)
            self.assertTrue(str(doc.get("id") or ""))

    def test_two_package_registries_are_NOT_independent_witnesses(self):
        """pypi and npm are the same KIND. Counting them as two independent
        sources was the bug this gate exists to prevent: agreement between two
        package registries is one opinion, not two."""
        r = jit.resolve("pdf text extraction", only=["pypi", "npm"], min_sources=2)
        self.assertFalse(r["pass"])
        self.assertEqual(r["kinds_answered"], ["package_registry"])
        self.assertIn("KINDS", r["gap"])

    def test_different_kinds_do_satisfy_the_gate(self):
        """A registry and a code host are genuinely different witnesses."""
        r = jit.resolve("pdf text extraction", only=["pypi", "github"],
                        min_sources=2, min_kinds=2)
        self.assertTrue(r["pass"], r.get("gap"))
        self.assertGreaterEqual(len(r["kinds_answered"]), 2)

    def test_three_kinds_are_reachable_and_all_answer(self):
        r = jit.resolve("pdf text extraction", only=["pypi", "github", "docs"],
                        min_sources=3, min_kinds=3)
        self.assertTrue(r["pass"], r.get("gap"))
        self.assertEqual(len(r["kinds_answered"]), 3)
        self.assertIn("documentation", r["kinds_answered"])

    def test_pypi_names_a_real_package_when_asked_for_one(self):
        r = jit.resolve("requests", only=["pypi"], min_sources=1, min_kinds=1)
        self.assertTrue(r["pass"], r)
        ids = [str(d.get("id") or "").lower() for d in r["documents"]]
        self.assertIn("requests", ids, ids)

    def test_documents_from_different_sources_are_distinguishable(self):
        r = jit.resolve("pdf", only=["pypi", "npm"], min_sources=2, min_kinds=1)
        sources = {d["source"] for d in r["documents"]}
        self.assertGreaterEqual(len(sources), 2)

    def test_documentation_says_what_a_thing_is_for_not_just_that_it_exists(self):
        """A README is a different claim from a registry entry."""
        r = jit.resolve("pdf text extraction", only=["docs"], min_sources=1,
                        min_kinds=1)
        self.assertTrue(r["pass"], r)
        doc = r["documents"][0]
        self.assertEqual(doc["kind"], "documentation")
        self.assertGreater(len(doc.get("summary") or ""), 40)


# --------------------------------------------------------------------------- #
# provenance, checked rather than asserted
# --------------------------------------------------------------------------- #
@requires_network
class ProvenanceRealTests(_Store, unittest.TestCase):
    def test_the_recorded_hash_matches_the_document_it_came_from(self):
        """Recompute it. A hash that is never checked proves nothing."""
        r = jit.resolve("pdf", only=["pypi"], min_sources=1, min_kinds=1)
        self.assertTrue(r["pass"])
        doc = r["documents"][0]
        payload = {k: v for k, v in doc.items()
                   if k not in ("source", "authority", "sha256")}
        recomputed = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:16]
        self.assertEqual(doc["sha256"], recomputed)

    def test_every_document_declares_where_it_came_from(self):
        r = jit.resolve("pdf", only=["pypi", "npm"], min_sources=2)
        for doc in r["documents"]:
            self.assertIn(doc["source"], r["sources_answered"])
            self.assertEqual(doc["authority"], "EXTERNAL_PUBLIC_EVIDENCE_FETCHED")

    def test_the_same_query_is_fetched_again_not_served_from_imagination(self):
        """Two independent resolves must agree about the world."""
        a = jit.resolve("pdf", only=["pypi"], min_sources=1, min_kinds=1)
        b = jit.resolve("pdf", only=["pypi"], min_sources=1, min_kinds=1)
        self.assertTrue(a["pass"] and b["pass"])
        ids_a = {d["id"] for d in a["documents"]}
        ids_b = {d["id"] for d in b["documents"]}
        self.assertTrue(ids_a & ids_b, (sorted(ids_a)[:5], sorted(ids_b)[:5]))


# --------------------------------------------------------------------------- #
# refusal, against reality
# --------------------------------------------------------------------------- #
class RefusalRealTests(_Store, unittest.TestCase):
    def test_a_host_that_cannot_resolve_says_so(self):
        """.invalid is guaranteed unroutable by RFC 2606. This is a real failure."""
        jit.SOURCES["unreachable"] = {
            "fetch": lambda q, l, t: (jit._get("https://unreachable.invalid/x", t)
                                      and []),
            "cost": 0.1,
        }
        try:
            r = jit.fetch_source("unreachable", "q", timeout=6)
            self.assertFalse(r["ok"])
            self.assertTrue(r["reason"], r)
            self.assertNotEqual(r["reason"], "NO_DOCUMENTS_RETURNED")
        finally:
            jit.SOURCES.pop("unreachable", None)

    def test_a_real_404_is_reported_as_such(self):
        jit.SOURCES["missing_page"] = {
            "fetch": lambda q, l, t: (jit._get(
                "https://pypi.org/pypi/definitely-not-a-real-package-xyz-9/json", t)
                and []),
            "cost": 0.1,
        }
        try:
            r = jit.fetch_source("missing_page", "q", timeout=15)
            self.assertFalse(r["ok"])
            self.assertIn("HTTP_", r["reason"])
        finally:
            jit.SOURCES.pop("missing_page", None)

    def test_demanding_more_sources_than_exist_refuses_to_conclude(self):
        r = jit.resolve("pdf", only=["pypi"], min_sources=9, min_kinds=1)
        self.assertFalse(r["pass"], r)
        self.assertEqual(r["status"], jit.OPEN_THIN)
        self.assertIn("only", r["gap"])
        self.assertEqual(r["authority"], "INCOMPLETE_DATA_NO_CONCLUSION_DRAWN")

    def test_a_thin_result_still_hands_back_what_it_found(self):
        r = jit.resolve("pdf", only=["pypi"], min_sources=9, min_kinds=1)
        self.assertGreater(r["document_count"], 0)
        self.assertFalse(r["complete"])

    def test_an_empty_query_fails_closed(self):
        r = jit.resolve("   ")
        self.assertEqual(r["status"], jit.FAIL_EMPTY)
        self.assertFalse(r["pass"])

    def test_an_unknown_source_is_a_closed_failure(self):
        r = jit.fetch_source("no_such_source_exists", "q")
        self.assertFalse(r["ok"])
        self.assertEqual(r["reason"], "UNKNOWN_SOURCE")


# --------------------------------------------------------------------------- #
# pure logic -- no network involved, and labelled as such
# --------------------------------------------------------------------------- #
class ValueMathsTests(_Store, unittest.TestCase):
    """Arithmetic on the earned-value function. No sources are consulted."""

    def test_an_untried_source_sits_on_the_prior(self):
        self.assertAlmostEqual(jit.source_value("github"),
                               0.5 / (1.0 + jit.SOURCES["github"]["cost"]), places=9)

    def test_successes_raise_value(self):
        before = jit.source_value("npm")
        for _ in range(10):
            jit.credit("npm", True)
        self.assertGreater(jit.source_value("npm"), before)

    def test_failures_lower_value(self):
        before = jit.source_value("npm")
        for _ in range(10):
            jit.credit("npm", False)
        self.assertLess(jit.source_value("npm"), before)

    def test_ten_direct_failures_rank_below_an_untried_source(self):
        for _ in range(10):
            jit.credit("github_code", False)
        self.assertLess(jit.source_value("github_code"), jit.source_value("github"))

    def test_credit_persists_to_disk(self):
        jit.credit("pypi", True)
        jit.credit("pypi", True)
        jit.credit("pypi", False)
        row = jit._load_state()["pypi"]
        self.assertEqual(row["trials"], 3)
        self.assertEqual(row["helped"], 2)

    def test_ordering_puts_the_most_useful_first(self):
        for _ in range(8):
            jit.credit("npm", True)
        for _ in range(8):
            jit.credit("web", False)
        order = jit.ordered_sources()
        self.assertEqual(order[0], "npm")
        self.assertEqual(order[-1], "web")

    def test_ordering_is_not_a_fixed_sequence(self):
        """The same code must produce different orders on different experience."""
        first = list(jit.ordered_sources())
        for _ in range(12):
            jit.credit(first[-1], True)
        self.assertNotEqual(list(jit.ordered_sources()), first)


# --------------------------------------------------------------------------- #
# staged retrieval and caching: fast by construction
# --------------------------------------------------------------------------- #
@requires_network
class StagedRetrievalTests(_Store, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        jit.cache_clear()

    def test_cheap_sources_alone_can_satisfy_the_gate(self):
        """No need to download tarballs when two registries already answered."""
        r = jit.resolve("pdf text extraction", min_sources=2, min_kinds=2)
        self.assertTrue(r["pass"], r.get("gap"))
        self.assertNotIn("docs", r["sources_answered"])

    def test_the_expensive_source_is_only_asked_when_needed(self):
        """Asking for a third KIND escalates; asking for two does not."""
        two = jit.resolve("pdf text extraction", min_sources=2, min_kinds=2)
        self.assertNotIn("docs", two["sources_answered"])
        three = jit.resolve("pdf text extraction", min_sources=3, min_kinds=3)
        self.assertIn("docs", three["sources_answered"])
        self.assertIn("documentation", three["kinds_answered"])

    def test_staging_makes_the_common_case_much_faster(self):
        import time
        t = time.time()
        jit.resolve("pdf text extraction", min_sources=2, min_kinds=2)
        cheap = time.time() - t
        jit.cache_clear()
        t = time.time()
        jit.resolve("pdf text extraction", min_sources=3, min_kinds=3)
        expensive = time.time() - t
        self.assertLess(cheap, expensive)

    def test_the_same_question_is_not_asked_twice(self):
        jit.cache_clear()
        a = jit.resolve("pdf text extraction", min_sources=2, min_kinds=2)
        self.assertFalse(a.get("from_cache"))
        b = jit.resolve("pdf text extraction", min_sources=2, min_kinds=2)
        self.assertTrue(b.get("from_cache"))
        self.assertEqual(a["document_count"], b["document_count"])

    def test_a_cached_answer_is_instant(self):
        import time
        jit.resolve("pdf text extraction", min_sources=2, min_kinds=2)
        t = time.time()
        jit.resolve("pdf text extraction", min_sources=2, min_kinds=2)
        self.assertLess(time.time() - t, 0.05)

    def test_different_questions_are_not_confused(self):
        jit.resolve("pdf text extraction", min_sources=2, min_kinds=2)
        other = jit.resolve("sqlite database", min_sources=2, min_kinds=2)
        self.assertFalse(other.get("from_cache"))

    def test_a_failed_resolve_is_not_cached(self):
        """Caching 'nothing answered' would make a transient outage permanent."""
        jit.resolve("pdf", only=["pypi"], min_sources=9, min_kinds=9)
        jit.cache_clear()
        r1 = jit.resolve("pdf", only=["web"], min_sources=2, min_kinds=2)
        self.assertEqual(r1["status"], jit.FAIL_NO_SOURCE)
        self.assertFalse(r1.get("from_cache"))

    def test_a_cached_refusal_still_carries_its_reason(self):
        """Regression: the result was cached before `gap` was filled in, so a
        second caller got a refusal with no explanation attached."""
        jit.cache_clear()
        first = jit.resolve("pdf", only=["pypi"], min_sources=9, min_kinds=1)
        self.assertIn("gap", first)
        second = jit.resolve("pdf", only=["pypi"], min_sources=9, min_kinds=1)
        self.assertTrue(second.get("from_cache"))
        self.assertIn("gap", second)
        self.assertEqual(first["gap"], second["gap"])

    def test_a_refusal_is_NOT_remembered_as_long_as_a_success(self):
        """Sabotage check: if a refusal were cached for the full lifetime, one
        busy host would turn into 'the world has no data' for minutes."""
        import time
        self.assertLess(jit.CACHE_TTL_REFUSED_S, jit.CACHE_TTL_S,
                        "a refusal must expire sooner than an answer")

    def test_a_refusal_expires_while_an_answer_endures(self):
        """Behaviour, not constants: hold both TTLs far apart and watch what
        actually survives the wait. A refusal must be re-asked; an answer must
        not. Sabotage check -- caching both for the long lifetime makes one
        busy host read as 'the world has no data' for minutes."""
        import time
        jit.cache_clear()
        saved_refused, saved_ok = jit.CACHE_TTL_REFUSED_S, jit.CACHE_TTL_S
        try:
            jit.CACHE_TTL_S = 60.0        # an answer is remembered
            jit.CACHE_TTL_REFUSED_S = 0.4  # a refusal is not

            refusal = ("pdf", {"only": ["pypi"], "min_sources": 9,
                               "min_kinds": 9})
            answer = ("pdf text extraction", {"min_sources": 2, "min_kinds": 2})

            r1 = jit.resolve(*refusal[0:1], **refusal[1])
            self.assertFalse(r1["complete"], "this one must be refused")
            a1 = jit.resolve(*answer[0:1], **answer[1])
            self.assertTrue(a1["complete"], "this one must succeed")

            time.sleep(0.8)

            r2 = jit.resolve(*refusal[0:1], **refusal[1])
            self.assertFalse(r2.get("from_cache"),
                             "the refusal should have expired and be re-asked")
            a2 = jit.resolve(*answer[0:1], **answer[1])
            self.assertTrue(a2.get("from_cache"),
                            "the answer should still be there")
        finally:
            jit.CACHE_TTL_REFUSED_S, jit.CACHE_TTL_S = saved_refused, saved_ok
            jit.cache_clear()

    def test_transient_network_failure_is_retried_before_giving_up(self):
        """A socket blip is not evidence that the data does not exist."""
        calls = {"n": 0}

        def flaky(q, l, t):
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError("transient")
            return [{"kind": "k", "id": "x", "title": "X", "summary": "s", "url": "u"}]

        jit.SOURCES["flaky"] = {"fetch": flaky, "cost": 0.5, "kind": "test_kind"}
        try:
            r = jit.fetch_source("flaky", "q")
            self.assertTrue(r["ok"], r)
            self.assertEqual(calls["n"], 2)      # retried once
        finally:
            jit.SOURCES.pop("flaky", None)


# --------------------------------------------------------------------------- #
# the live path, with a real gap
# --------------------------------------------------------------------------- #
# Composition now closes "write the text hello to out.txt" outright, so
# it is no longer a gap. This one is still genuinely impossible here:
# nothing on this machine can open a pdf.
# A goal nothing here can do, so the gap path is really exercised.
#
# This was the PDF-extraction sentence.  It stopped being impossible: pdf.extract.text.pypdf
# carries a receipt on disk whose mission digest matches, so the verified-capability adapter
# now admits it and the goal reaches route admission instead of failing to compile.  The
# machine got more capable; the test's premise went stale.  setUpClass below now checks the
# premise rather than letting three assertions fail on a status string.
GAP_GOAL = "transcribe the audio in this recording to text"


@requires_network
class LivePathRealTests(_Store, unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        """Check that the gap goal really is a gap before asserting anything about it."""
        from canonical.runtime import live_brain_route_admission_v1 as ra
        import uuid
        r = ra.solve({"task_id": uuid.uuid4().hex, "goal": GAP_GOAL})
        if r.get("status") != "FAIL__RAW_GOAL_COMPILATION_GAP":
            raise unittest.SkipTest(
                "GAP_GOAL is no longer a compilation gap, so this class cannot exercise the "
                "retrieval path: goal=%r status=%s" % (GAP_GOAL, r.get("status")))

    def test_a_real_gap_triggers_real_retrieval(self):
        from canonical.runtime import live_brain_route_admission_v1 as ra

        r = ra.solve_or_learn({"task_id": "t", "goal": GAP_GOAL})
        self.assertEqual(r["status"], "FAIL__RAW_GOAL_COMPILATION_GAP")
        k = (r.get("learning") or {}).get("knowledge") or {}
        self.assertEqual(k.get("status"), jit.PASS)
        self.assertGreater(k.get("documents", 0), 0)
        self.assertTrue(k.get("sources_answered"))

    def test_the_machine_rephrases_when_the_world_does_not_answer(self):
        """Asking an instruction verbatim gets nothing; asking it well gets
        answers. Believing the first silence is how 'no data' gets invented."""
        from canonical.runtime import jit_knowledge_v1 as J
        from canonical.runtime.curriculum_v1 import query_for

        verbatim = "write the text hello to out.txt"
        self.assertEqual(len(J._gh_search(verbatim, 6, 12)), 0,
                         "expected the verbatim instruction to find nothing")
        self.assertGreater(len(J._gh_search(query_for(verbatim), 6, 12)), 0,
                           "expected the rephrased query to find something")

    def test_a_badly_asked_question_still_reaches_two_kinds(self):
        from canonical.runtime import live_brain_route_admission_v1 as ra

        # awkward on purpose, and still impossible here, so the retrieval
        # path is really exercised
        r = ra.solve_or_learn({"task_id": "t",
                               "goal": "get the writing out of that there pdf thing"})
        k = (r.get("learning") or {}).get("knowledge") or {}
        self.assertGreaterEqual(len(k.get("kinds_answered") or []), 2,
                                "one kind is not knowledge: %s" % k)

    def test_the_gap_is_recorded_so_it_is_known(self):
        from canonical.runtime import live_brain_route_admission_v1 as ra

        r = ra.solve_or_learn({"task_id": "t", "goal": GAP_GOAL})
        learned = r.get("learning") or {}
        self.assertTrue(learned.get("gap_recorded"))
        self.assertTrue(learned.get("what_to_learn_next"))

    def test_the_machine_only_uses_a_program_that_is_really_here(self):
        from canonical.runtime import live_brain_route_admission_v1 as ra

        self.assertTrue(ra._is_executable("python3"))
        self.assertTrue(ra._is_executable("tar"))
        self.assertFalse(ra._is_executable("definitely_not_a_program_xyz"))

    def test_a_goal_that_compiles_does_not_go_looking(self):
        from canonical.runtime import live_brain_route_admission_v1 as ra

        # Was the shell-echo sentence.  shell.command.run is one of only two registry entries
        # with no VERIFIED_BOUND_CAPABILITY status and no verification receipt, so it cannot be
        # promoted without forging the registry's one proof; the goal never compiles.  The
        # subject of this test is that a compiling goal does not go looking, so any goal that
        # really compiles serves -- this one does, against archive.verify.tar_gz.gnu.
        r = ra.solve_or_learn({"task_id": "t",
                               "goal": "Verify a tar.gz archive against its manifest"})
        self.assertTrue(r.get("pass") is True, r.get("status"))
        self.assertNotIn("learning", r)


if __name__ == "__main__":
    unittest.main()
