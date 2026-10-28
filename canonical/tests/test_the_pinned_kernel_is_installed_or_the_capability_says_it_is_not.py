#!/usr/bin/env python3
"""The pinned kernel is either installed or the capability says it is not.

Measured on `c8a3d34` (2026-10-28):

    code.multilanguage.parse.tree_sitter.v1
      without the pinned kernel -> output_verified: true, tree_sitter_available: false

The adapter was falling back to `ast` for Python and calling that a multilanguage tree-sitter
parse. `python.source.audit.ast` already exists for that effect, and the sibling adapter
`code_tree_sitter_incremental_index_v1` already refuses with `TREE_SITTER_SUBSTRATE_MISSING`
in exactly this situation — so this row was the one still reporting success.

The two behavioural tests below are complementary: whichever interpreter runs them, exactly
one of them executes, and the structural invariant runs everywhere. Install the substrate to
run the second:

    pip install --require-hashes -r requirements/software_engineering_kernel_v1.txt
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import pathlib
import shutil
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
REGISTRY = REPO_ROOT / "canonical" / "runtime" / "BOUND_CAPABILITY_REGISTRY_V1.json"
CAPABILITY = "code.multilanguage.parse.tree_sitter.v1"

HAVE_KERNEL = importlib.util.find_spec("tree_sitter") is not None


class SubstrateHonestyTest(unittest.TestCase):
    """Shared fixture: one tiny python file, invoked the way the door invokes it."""

    def setUp(self):
        # The adapter resolves source_root against the caller's root, which the door sets to
        # the repository, so the fixture lives in the gitignored scratch directory.
        self._tmp = tempfile.mkdtemp(prefix="brain_ts_substrate_",
                                     dir=str(REPO_ROOT / "canonical" / "astra_runtime" / "tmp"))
        self.root = pathlib.Path(self._tmp).resolve()
        self.addCleanup(shutil.rmtree, self._tmp, True)
        (self.root / "sample.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        self.out = self.root / "out.json"

    def _invoke(self):
        from canonical.runtime import live_brain_route_admission_v1 as admission

        row = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"][CAPABILITY]
        entry = {"capability_id": CAPABILITY, "adapter_module": row["adapter_module"],
                 "entrypoint": row["entrypoint"], "source": row["source"],
                 "incremental_spend_usd": 0}
        action = {"type": "invoke_capability",
                  "args": {"capability_id": CAPABILITY,
                           "source_root": str(self.root.relative_to(REPO_ROOT)),
                           "output_path": str(self.out.relative_to(REPO_ROOT))},
                  "expect": row["action_template"]["expect"]}
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                return "PASS", admission.run_adapter_locally(entry, action)
            except BaseException as exc:  # the refusal is the expected shape for one of these
                return "REFUSED", str(exc)

    def _artifact(self):
        return json.loads(self.out.read_text(encoding="utf-8"))

    # ---------------------------------------------------------------- invariants

    def test_verified_implies_the_substrate_was_present(self):
        """The structural law, whichever interpreter runs it.

        `verified` is allowed to be false for other reasons (no files, parse errors); what it
        may never be is true while the parser it is named after was absent.
        """
        verdict, _ = self._invoke()
        artifact = self._artifact()
        self.assertEqual(
            artifact["verified"] and not artifact["tree_sitter_available"], False,
            "verified a tree-sitter parse while tree_sitter was absent: %s" % (artifact,),
        )
        self.assertEqual(artifact["substrate_missing"], not artifact["tree_sitter_available"])
        if artifact["substrate_missing"]:
            self.assertEqual(artifact["reason"], "TREE_SITTER_SUBSTRATE_MISSING")
            self.assertEqual(verdict, "REFUSED", "a missing substrate must not reach the door as a pass")
        else:
            self.assertIsNone(artifact["reason"])

    # ------------------------------------------------ the two measured behaviours

    @unittest.skipIf(HAVE_KERNEL, "the pinned kernel is installed, so absence cannot be observed")
    def test_without_the_pinned_kernel_the_capability_refuses(self):
        verdict, detail = self._invoke()
        self.assertEqual(verdict, "REFUSED")
        self.assertIn("output_verified", detail)
        self.assertFalse(self._artifact()["verified"])

    @unittest.skipUnless(HAVE_KERNEL, "install requirements/software_engineering_kernel_v1.txt")
    def test_with_the_pinned_kernel_it_reports_a_real_parse(self):
        verdict, result = self._invoke()
        self.assertEqual(verdict, "PASS", "with the substrate installed the skill must work")
        self.assertTrue(result["output_verified"])
        self.assertTrue(self._artifact()["tree_sitter_available"])
        self.assertFalse(self._artifact()["substrate_missing"])


if __name__ == "__main__":
    unittest.main()
