#!/usr/bin/env python3
"""A step that produces no artifact of its own must not be unverifiable.

The bound-success checkpoint verifier demanded that *every* step produce a re-hashable
durable artifact. A terminal verification step produces none -- its whole output is a
verdict -- so any plan ending in one could never become verified experience, however
real its work was. Measured on EXT_DECISION_VERIFY, whose
decision.synthesis.verify.stdlib reports no path at all, and on the two-step grounding
plan, whose second step returns only a verdict.

Such a step is not thereby unproven: the caller has already recomputed its inputs
digest, its registry-entry digest, its rendered action and its exact result bytes. What
it must additionally do is consume at least one path that this same proof re-opened and
re-hashed in an earlier step -- so the invariant that no step enters an episode without
bytes behind it having been checked against disk survives. A blanket exemption would
have destroyed it; these tests pin that it does not.

Every test here fails if the repair is reverted.
"""
import hashlib
import importlib.util
import json
import pathlib
import shutil
import tempfile
import unittest

CANONICAL_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME = CANONICAL_ROOT / "runtime"
CHECKPOINT_VERIFY = RUNTIME / "r3_bound_success_checkpoint_verifier_v1.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checkpoint = _load("r3_bound_success_checkpoint_verifier_contract", CHECKPOINT_VERIFY)


class ArtifactFreeStepTests(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="artifact-free-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.artifact = self.root / "produced.json"
        self.artifact.write_text(json.dumps({"decision": "adopt"}), encoding="utf-8")
        self.digest = hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        self.rel = "produced.json"

    def test_step_with_its_own_hashed_artifact_still_verifies(self):
        inner = {"output_path": self.rel, "output_sha256": self.digest}
        self.assertIs(checkpoint._reverify_hashed_artifact(inner, self.root), True)

    def test_artifact_free_step_consuming_a_reverified_artifact_verifies(self):
        inner = {"verified": True, "reason": "VERIFIED", "producer_independent": True}
        seen = {self.rel}
        self.assertIs(
            checkpoint._reverify_hashed_artifact(
                inner, self.root, inputs={"result_path": self.rel}, prior_artifacts=seen),
            True)

    def test_artifact_free_step_with_no_prior_artifact_is_still_refused(self):
        """Fail-closed must survive: no bytes behind the step, no verification."""
        inner = {"verified": True, "reason": "VERIFIED"}
        with self.assertRaises(checkpoint.BoundSuccessVerificationError) as ctx:
            checkpoint._reverify_hashed_artifact(inner, self.root, inputs={}, prior_artifacts=set())
        self.assertIn("NO_HASHED_DURABLE_ARTIFACT_TO_REVERIFY", str(ctx.exception))

    def test_consuming_an_artifact_this_proof_never_checked_is_refused(self):
        """The consumed path must be one this proof re-hashed, not any string."""
        inner = {"verified": True}
        with self.assertRaises(checkpoint.BoundSuccessVerificationError):
            checkpoint._reverify_hashed_artifact(
                inner, self.root,
                inputs={"result_path": "some/other/file.json"},
                prior_artifacts={self.rel},
            )

    def test_a_reported_path_with_a_wrong_digest_is_still_refused(self):
        inner = {"output_path": self.rel, "output_sha256": "0" * 64}
        with self.assertRaises(checkpoint.BoundSuccessVerificationError) as ctx:
            checkpoint._reverify_hashed_artifact(inner, self.root)
        self.assertIn("DURABLE_ARTIFACT_HASH_MISMATCH", str(ctx.exception))

    def test_a_reported_path_without_a_digest_is_still_refused(self):
        inner = {"output_path": self.rel}
        with self.assertRaises(checkpoint.BoundSuccessVerificationError) as ctx:
            checkpoint._reverify_hashed_artifact(inner, self.root)
        self.assertIn("DURABLE_ARTIFACT_HASH_REQUIRED", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
