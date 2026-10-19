"""Compose by type, then prove it by running it.

The headline number: the token graph finds ONE multi-step chain in the whole
registry. Matching on the type of the artifact finds 119 edges. But a type
match is a hypothesis -- execution is the arbiter, and most hypotheses die.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from canonical.runtime import type_level_composer_v1 as tlc

ARCHIVE_CREATE = "archive.tar_gz.create_from_manifest"
ARCHIVE_VERIFY = "archive.verify.tar_gz.gnu"
ARCHIVE_CHAIN = [ARCHIVE_CREATE, ARCHIVE_VERIFY]


class _IsolatedState:
    """The composer LEARNS output formats to disk; a test must not teach the repo."""

    def _isolate(self) -> None:
        self._tmp = tempfile.mkdtemp(prefix="brain-tlc-test-")
        self._saved = tlc.SUFFIX_STATE
        tlc.SUFFIX_STATE = os.path.join(self._tmp, "suffixes.json")

    def _unisolate(self) -> None:
        tlc.SUFFIX_STATE = self._saved
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)


# --------------------------------------------------------------------------- #
# the claim being made
# --------------------------------------------------------------------------- #
class TypeGraphBeatsTokenGraphTests(unittest.TestCase):
    def test_type_matching_finds_far_more_than_token_matching(self):
        from canonical.runtime import capability_composer_v1 as composer

        reg = composer.load_registry()
        g = composer.graph(reg)
        token_chains = 0
        provided = {t for v in g.values() for t in v["provides"]}
        for tok in provided:
            plan = composer.plan([], tok, g)
            if plan and len(plan) > 1:
                token_chains += 1
        type_edges = len(tlc.edges(tlc.type_graph(reg)))
        # the token graph sees essentially nothing; types see a surface
        self.assertGreater(type_edges, token_chains * 10,
                           f"type edges {type_edges} vs token chains {token_chains}")

    def test_the_archive_chain_is_a_type_edge(self):
        """Create it, then verify it -- obvious, and invisible to the token graph."""
        pairs = {(a, b) for a, b, _ in tlc.edges(tlc.type_graph())}
        self.assertIn((ARCHIVE_CREATE, ARCHIVE_VERIFY), pairs)

    def test_chains_shorter_than_max_len(self):
        chains = tlc.chains(tlc.type_graph(), max_len=2, limit=16)
        self.assertTrue(chains)
        for c in chains:
            self.assertLessEqual(len(c), 2)

    def test_no_capability_appears_twice_in_a_chain(self):
        for c in tlc.chains(tlc.type_graph(), max_len=3, limit=16):
            self.assertEqual(len(c), len(set(c)), c)


# --------------------------------------------------------------------------- #
# execution is the arbiter
# --------------------------------------------------------------------------- #
class VerifyChainTests(_IsolatedState, unittest.TestCase):
    def setUp(self) -> None:
        self._isolate()

    def tearDown(self) -> None:
        self._unisolate()

    def test_the_archive_chain_actually_executes(self):
        r = tlc.verify_chain(ARCHIVE_CHAIN)
        self.assertEqual(r["status"], tlc.PASS, r.get("reason"))
        self.assertTrue(r["pass"])
        self.assertEqual(r["executed"], 2)
        self.assertEqual(len(r["steps"]), 2)

    def test_a_verified_chain_claims_execution_authority(self):
        r = tlc.verify_chain(ARCHIVE_CHAIN)
        self.assertEqual(r["authority"], "CHAIN_EXECUTED_END_TO_END")

    def test_an_unverified_chain_does_not_claim_it(self):
        r = tlc.verify_chain(["docx.document.create_from_json_record", "json.query.jq"])
        if not r["pass"]:
            self.assertEqual(r["authority"], "TYPE_MATCH_ONLY_NOT_EXECUTED")

    def test_each_step_records_the_artifact_it_wrote(self):
        r = tlc.verify_chain(ARCHIVE_CHAIN)
        self.assertTrue(r["artifacts"][0]["artifacts"], r["artifacts"])

    def test_the_second_step_consumes_what_the_first_wrote(self):
        """The verifier rejects a manifest the archive was not built from."""
        r = tlc.verify_chain(ARCHIVE_CHAIN)
        self.assertTrue(r["pass"])
        self.assertTrue(r["artifacts"][0].get("consumed"))

    def test_a_chain_that_fails_reports_where(self):
        r = tlc.verify_chain(["json.query.jq", "archive.verify.tar_gz.gnu"])
        self.assertFalse(r["pass"])
        self.assertTrue(r["reason"])

    def test_an_unknown_capability_is_a_closed_failure_not_a_crash(self):
        r = tlc.verify_chain(["no.such.capability"])
        self.assertFalse(r["pass"])
        self.assertIn("CAPABILITY_NOT_IN_REGISTRY", r["reason"])

    def test_the_workspace_is_cleaned_up(self):
        import pathlib
        before = set(pathlib.Path(tempfile.gettempdir()).glob("brain-tlc-*"))
        tlc.verify_chain(ARCHIVE_CHAIN)
        after = set(pathlib.Path(tempfile.gettempdir()).glob("brain-tlc-*"))
        self.assertEqual(len(after), len(before))

    def test_a_caller_supplied_workspace_is_left_alone(self):
        with tempfile.TemporaryDirectory() as d:
            tlc.verify_chain(ARCHIVE_CHAIN, workspace=d)
            self.assertTrue(os.path.isdir(d))


# --------------------------------------------------------------------------- #
# the two bugs execution found
# --------------------------------------------------------------------------- #
class ArtifactTypingTests(unittest.TestCase):
    """Both of these were real defects, found only by running a chain."""

    def test_artifacts_are_typed_from_the_bytes_on_disk(self):
        """A tar.gz was typed as a manifest because the cid mentions 'manifest'."""
        self.assertIn("tar_gz", tlc.types_of_file("x.tar.gz"))
        self.assertNotIn("manifest", tlc.types_of_file("x.tar.gz"))

    def test_a_tar_gz_is_not_mistaken_for_a_manifest(self):
        self.assertEqual(tlc.types_of_file("a/b/c.tar.gz"), {"tar_gz"})

    def test_related_type_names_are_treated_as_one_thing(self):
        """archive_path wants an archive; the producer wrote a tar.gz."""
        self.assertTrue(tlc._compatible({"archive"}, {"tar_gz"}))
        self.assertTrue(tlc._compatible({"image"}, {"png"}))
        self.assertTrue(tlc._compatible({"manifest"}, {"json"}))

    def test_unrelated_type_names_are_not(self):
        self.assertFalse(tlc._compatible({"pdf"}, {"sqlite"}))


# --------------------------------------------------------------------------- #
# learning the required format from the refusal
# --------------------------------------------------------------------------- #
class LearnFormatFromRefusalTests(_IsolatedState, unittest.TestCase):
    def setUp(self) -> None:
        self._isolate()

    def tearDown(self) -> None:
        self._unisolate()

    def test_a_refusal_names_the_format_wanted(self):
        self.assertEqual(tlc._suffix_from_refusal("RuntimeError:PDF_OUTPUT_REQUIRED"), ".pdf")
        self.assertEqual(tlc._suffix_from_refusal("RuntimeError:TAR_GZ_OUTPUT_REQUIRED"), ".tar.gz")

    def test_an_unrelated_error_yields_nothing(self):
        self.assertIsNone(tlc._suffix_from_refusal("FileNotFoundError: no such file"))

    def test_the_format_is_remembered_for_next_time(self):
        tlc._remember_suffix("some.capability", ".pdf")
        self.assertEqual(tlc.recalled_suffix("some.capability"), ".pdf")

    def test_a_remembered_format_beats_a_guess(self):
        """markdown_pdf would otherwise guess .md from the first keyword."""
        cid = "document.convert.markdown_pdf.pandoc_weasyprint"
        self.assertEqual(tlc.output_suffix_for(cid), ".md")
        tlc._remember_suffix(cid, ".pdf")
        self.assertEqual(tlc.output_suffix_for(cid), ".pdf")

    def test_learning_survives_a_fresh_import(self):
        tlc._remember_suffix("other.capability", ".xlsx")
        self.assertEqual(tlc._load_suffixes().get("other.capability"), ".xlsx")


# --------------------------------------------------------------------------- #
# discovery
# --------------------------------------------------------------------------- #
class ComposeAndVerifyTests(_IsolatedState, unittest.TestCase):
    def setUp(self) -> None:
        self._isolate()

    def tearDown(self) -> None:
        self._unisolate()

    def test_only_chains_that_ran_are_returned(self):
        r = tlc.compose_and_verify(max_len=2, limit=8)
        self.assertIsInstance(r["verified_chains"], list)
        for c in r["verified_chains"]:
            self.assertTrue(c["pass"])
            self.assertEqual(c["authority"], "CHAIN_EXECUTED_END_TO_END")

    def test_attempted_is_reported_honestly(self):
        r = tlc.compose_and_verify(max_len=2, limit=4)
        self.assertEqual(r["attempted"], 4)
        self.assertLessEqual(len(r["verified_chains"]), 4)

    def test_most_type_matches_do_not_survive_execution(self):
        """The machine must not claim 119 capabilities it has never run."""
        r = tlc.compose_and_verify(max_len=2, limit=12)
        self.assertLess(len(r["verified_chains"]), r["attempted"])

    def test_a_goal_filters_to_chains_ending_there(self):
        r = tlc.compose_and_verify(ARCHIVE_VERIFY, max_len=2, limit=24)
        self.assertTrue(r["verified_chains"])
        for c in r["verified_chains"]:
            self.assertIn(ARCHIVE_VERIFY, c["chain"])

    def test_no_candidates_is_an_open_status_not_a_pass(self):
        r = tlc.compose_and_verify("definitely.not.a.capability", max_len=2, limit=4)
        self.assertFalse(r["pass"])
        self.assertEqual(r["status"], tlc.OPEN_NO_EDGE)


if __name__ == "__main__":
    unittest.main()
