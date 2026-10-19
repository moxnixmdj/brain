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
        r = jit.resolve("pdf text extraction", only=["pypi"], min_sources=1)
        self.assertTrue(r["pass"], r)
        self.assertGreater(r["document_count"], 0)
        blob = " ".join(
            " ".join(str(doc.get(k) or "") for k in ("id", "title", "summary"))
            for doc in r["documents"]).lower()
        self.assertIn("pdf", blob, blob[:400])

    def test_npm_returns_real_packages_for_a_real_query(self):
        r = jit.resolve("pdf", only=["npm"], min_sources=1)
        self.assertTrue(r["pass"], r)
        ids = [str(d.get("id") or "").lower() for d in r["documents"]]
        self.assertTrue(ids)
        self.assertTrue(any("pdf" in i for i in ids), ids[:10])

    def test_github_returns_real_repositories_with_real_urls(self):
        r = jit.resolve("pdf extract", only=["github"], min_sources=1)
        self.assertTrue(r["pass"], r)
        for doc in r["documents"]:
            self.assertTrue(str(doc.get("url") or "").startswith("https://github.com/"),
                            doc)
            self.assertTrue(str(doc.get("id") or ""))

    def test_two_real_independent_sources_satisfy_the_gate(self):
        r = jit.resolve("pdf text extraction", only=["pypi", "npm"], min_sources=2)
        self.assertTrue(r["pass"], r.get("gap"))
        self.assertGreaterEqual(len(r["sources_answered"]), 2)
        self.assertEqual(set(r["sources_answered"]), {"pypi", "npm"})

    def test_pypi_names_a_real_package_when_asked_for_one(self):
        r = jit.resolve("requests", only=["pypi"], min_sources=1)
        self.assertTrue(r["pass"], r)
        ids = [str(d.get("id") or "").lower() for d in r["documents"]]
        self.assertIn("requests", ids, ids)

    def test_documents_from_different_sources_are_distinguishable(self):
        r = jit.resolve("pdf", only=["pypi", "npm"], min_sources=2)
        sources = {d["source"] for d in r["documents"]}
        self.assertGreaterEqual(len(sources), 2)


# --------------------------------------------------------------------------- #
# provenance, checked rather than asserted
# --------------------------------------------------------------------------- #
@requires_network
class ProvenanceRealTests(_Store, unittest.TestCase):
    def test_the_recorded_hash_matches_the_document_it_came_from(self):
        """Recompute it. A hash that is never checked proves nothing."""
        r = jit.resolve("pdf", only=["pypi"], min_sources=1)
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
        a = jit.resolve("pdf", only=["pypi"], min_sources=1)
        b = jit.resolve("pdf", only=["pypi"], min_sources=1)
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
        r = jit.resolve("pdf", only=["pypi"], min_sources=9)
        self.assertFalse(r["pass"], r)
        self.assertEqual(r["status"], jit.OPEN_THIN)
        self.assertIn("only", r["gap"])
        self.assertEqual(r["authority"], "INCOMPLETE_DATA_NO_CONCLUSION_DRAWN")

    def test_a_thin_result_still_hands_back_what_it_found(self):
        r = jit.resolve("pdf", only=["pypi"], min_sources=9)
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
# the live path, with a real gap
# --------------------------------------------------------------------------- #
GAP_GOAL = "write the text hello to out.txt"


@requires_network
class LivePathRealTests(_Store, unittest.TestCase):
    def test_a_real_gap_triggers_real_retrieval(self):
        from canonical.runtime import live_brain_route_admission_v1 as ra

        r = ra.solve_or_learn({"task_id": "t", "goal": GAP_GOAL})
        self.assertEqual(r["status"], "FAIL__RAW_GOAL_COMPILATION_GAP")
        k = (r.get("learning") or {}).get("knowledge") or {}
        self.assertEqual(k.get("status"), jit.PASS)
        self.assertGreater(k.get("documents", 0), 0)
        self.assertTrue(k.get("sources_answered"))

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

        r = ra.solve_or_learn({"task_id": "t", "goal": "run shell command echo hello"})
        self.assertTrue(r.get("pass") is True, r.get("status"))
        self.assertNotIn("learning", r)


if __name__ == "__main__":
    unittest.main()
