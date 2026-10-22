#!/usr/bin/env python3
"""Independent verification of the source-candidate enumeration, and the resolver
fix that verification exposed.

The verifier's independence is a different implementation, not a different opinion:
the file set comes from the git index (`git ls-files`), the digests from the external
`sha256sum` binary, and the pattern from `fnmatch`. Each negative control below breaks
exactly one of those agreements and must be refused.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import astra_runtime  # noqa: E402


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, str(ROOT / rel))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ENUM = "canonical/runtime/bound_capabilities/source_candidates_enumerate.py"
VERIFY = "canonical/runtime/bound_capabilities/source_candidates_verify_git_index.py"


class IndependentVerificationTests(unittest.TestCase):
    """Run against a throwaway git repository so the git index is genuinely separate."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = pathlib.Path(self.tmp)
        (self.root / "pkg").mkdir()
        for i in range(3):
            (self.root / "pkg" / f"m{i}.py").write_text(f"VALUE = {i}\n", encoding="utf-8")
        (self.root / "pkg" / "notes.txt").write_text("not python\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=self.tmp, check=True)
        subprocess.run(["git", "add", "-A"], cwd=self.tmp, check=True)
        self.enum = _load("t_enum", ENUM)
        self.verify = _load("t_verify", VERIFY)
        self.out = "pkg/enum.json"
        self.produced = self.enum.run(
            {"search_root": "pkg", "glob": "**/*.py", "objective": "x", "output_path": self.out},
            self.tmp,
        )
        self.assertTrue(self.produced["output_verified"])
        # the enumeration itself must be in the index or the two mechanisms disagree
        subprocess.run(["git", "add", "-A"], cwd=self.tmp, check=True)
        self.produced = self.enum.run(
            {"search_root": "pkg", "glob": "**/*.py", "objective": "x", "output_path": self.out},
            self.tmp,
        )
        subprocess.run(["git", "add", "-A"], cwd=self.tmp, check=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _payload(self):
        return json.loads((self.root / self.out).read_text(encoding="utf-8"))

    def _rewrite(self, payload):
        (self.root / self.out).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def test_two_independent_mechanisms_agree(self):
        result = self.verify.run({"enumeration_path": self.out}, self.tmp)
        self.assertTrue(result["verified"])
        self.assertEqual(result["candidate_count"], 3)
        self.assertIn("git ls-files", result["independent_enumeration_source"])
        self.assertIn("sha256sum", result["independent_digest_source"])

    def test_a_forged_digest_is_refused(self):
        payload = self._payload()
        payload["candidates"][0]["sha256"] = "0" * 64
        self._rewrite(payload)
        with self.assertRaises(RuntimeError) as ctx:
            self.verify.run({"enumeration_path": self.out}, self.tmp)
        self.assertIn("CANDIDATE_DIGEST_MISMATCH", str(ctx.exception))

    def test_an_invented_candidate_is_refused(self):
        payload = self._payload()
        payload["candidates"].append(
            {"title": "pkg/ghost.py", "record_title": "ghost.py", "snippet": "",
             "bytes": 0, "sha256": "1" * 64}
        )
        payload["candidate_count"] = len(payload["candidates"])
        self._rewrite(payload)
        with self.assertRaises(RuntimeError) as ctx:
            self.verify.run({"enumeration_path": self.out}, self.tmp)
        self.assertIn("CANDIDATE_SET_MISMATCH", str(ctx.exception))

    def test_a_wrong_byte_count_is_refused(self):
        payload = self._payload()
        payload["candidates"][0]["bytes"] = 999999
        self._rewrite(payload)
        with self.assertRaises(RuntimeError) as ctx:
            self.verify.run({"enumeration_path": self.out}, self.tmp)
        self.assertIn("CANDIDATE_SIZE_MISMATCH", str(ctx.exception))

    def test_a_missing_enumeration_is_refused(self):
        with self.assertRaises(RuntimeError) as ctx:
            self.verify.run({"enumeration_path": "pkg/absent.json"}, self.tmp)
        self.assertIn("ENUMERATION_INPUT_REQUIRED", str(ctx.exception))


class ResultReferenceThroughBoundAdapterTests(unittest.TestCase):
    """An upgraded chain could not read its first step's output_path.

    The verified bound adapter nests the capability's own result under `result`;
    the resolver only knew the flat registry-template shape, so upgrading a plan
    made it die with RESULT_REFERENCE_FIELD_MISSING -- measured on
    EXT_EVIDENCE_RANK, which went from FAIL__LIVE_CONTROLLER_EXECUTION to
    PASS__...CHECKPOINTED when this was fixed.
    """

    ENVELOPE = {
        "schema": "PROJECT_BRAIN_VERIFIED_BOUND_CAPABILITY_EXECUTION_ADAPTER_V1",
        "status": "PASS__PROMOTED_BOUND_CAPABILITY_EXECUTED_AND_TRACE_VERIFIED",
        "pass": True,
        "capability_id": "source.candidates.enumerate.stdlib",
        "result": {"status": "SOURCE_CANDIDATES_ENUMERATED", "output_path": "pkg/out.json"},
    }

    def test_field_is_found_through_the_wrapper(self):
        trace = [{"result": self.ENVELOPE}]
        got = astra_runtime._resolve_result_refs(
            {"$result": {"cycle": 0, "field": "output_path"}}, trace
        )
        self.assertEqual(got, "pkg/out.json")

    def test_the_wrappers_own_keys_still_win(self):
        """A union, not a rewrite: the envelope's `status` must not be shadowed."""
        trace = [{"result": self.ENVELOPE}]
        got = astra_runtime._resolve_result_refs({"$result": {"cycle": 0, "field": "status"}}, trace)
        self.assertEqual(got, "PASS__PROMOTED_BOUND_CAPABILITY_EXECUTED_AND_TRACE_VERIFIED")

    def test_a_flat_row_is_unaffected(self):
        trace = [{"result": {"output_path": "flat.json"}}]
        got = astra_runtime._resolve_result_refs(
            {"$result": {"cycle": 0, "field": "output_path"}}, trace
        )
        self.assertEqual(got, "flat.json")

    def test_a_genuinely_absent_field_still_raises(self):
        """The fix must not turn a real missing field into a silent None."""
        trace = [{"result": self.ENVELOPE}]
        with self.assertRaises(Exception) as ctx:
            astra_runtime._resolve_result_refs(
                {"$result": {"cycle": 0, "field": "no_such_field"}}, trace
            )
        self.assertIn("RESULT_REFERENCE_FIELD_MISSING", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
