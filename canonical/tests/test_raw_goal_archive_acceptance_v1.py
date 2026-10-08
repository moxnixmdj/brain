import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from canonical.runtime.raw_goal_archive_acceptance_v1 import verify


class VerifyArchiveAcceptance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.member = "canonical/test/source.txt"
        self.manifest = "canonical/test/manifest.json"
        self.output = "canonical/test/out.tar.gz"
        for x in [self.member, self.manifest, self.output]:
            (self.root / x).parent.mkdir(parents=True, exist_ok=True)
        (self.root / self.member).write_text("payload", encoding="utf-8")
        (self.root / self.manifest).write_text(json.dumps({
            "records": [{"verification_paths": [self.member]}]
        }), encoding="utf-8")
        with tarfile.open(self.root / self.output, "w:gz") as a:
            for rel in sorted([self.member, self.manifest]):
                a.add(self.root / rel, arcname=rel)
        self.goal = (
            f"Create a tar.gz archive from the manifest {self.manifest}, "
            f"including all its verification_paths files, and save it to {self.output}."
        )
        digest = hashlib.sha256(self.goal.encode()).hexdigest()
        self.contract = {
            "pass": True, "task_sha256": digest, "task_contract_sha256": "contract",
            "acceptance_contract": {
                "obligations": [{"obligation_id": "one", "task_sha256": digest}],
                "required_obligation_ids": ["one"],
            },
        }
        self.inputs = {"manifest_path": self.manifest, "output_path": self.output}
        self.execution = {
            "pass": True,
            "capability_id": "archive.tar_gz.create_from_manifest",
            "composition_capsule_head_hash": "independent-proof",
            "result": {
                "output_verified": True,
                "output_path": self.output,
                "output_sha256": hashlib.sha256((self.root / self.output).read_bytes()).hexdigest(),
                "members": sorted([self.member, self.manifest]),
                "member_count": 2,
                "source_sha256": {
                    r: hashlib.sha256((self.root / r).read_bytes()).hexdigest()
                    for r in (self.member, self.manifest)
                },
            },
        }

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, **change):
        args = {
            "goal": self.goal,
            "capability_id": "archive.tar_gz.create_from_manifest",
            "inputs": self.inputs,
            "execution": self.execution,
            "raw_contract": self.contract,
            "root": self.root,
        }
        args.update(change)
        return verify(**args)

    def test_explicit_goal_accepts(self):
        self.assertTrue(self.call()["semantic_acceptance_complete"])

    def test_vague_goal_is_not_authenticated(self):
        goal = f"Create a tar.gz archive from {self.manifest} and save it to {self.output}."
        self.assertFalse(self.call(goal=goal)["pass"])

    def test_compiler_input_drift_blocks(self):
        self.assertFalse(self.call(inputs={
            "manifest_path": self.manifest, "output_path": "canonical/test/other.tar.gz"
        })["pass"])

    def test_missing_independent_trace_blocks(self):
        self.assertFalse(self.call(execution={
            **self.execution, "composition_capsule_head_hash": None
        })["pass"])

    def test_corrupt_archive_blocks(self):
        (self.root / self.output).write_bytes(b"not an archive")
        self.assertFalse(self.call()["pass"])

    def test_changed_source_blocks(self):
        (self.root / self.member).write_text("tampered")
        self.assertFalse(self.call()["pass"])

    def test_dropped_obligation_blocks(self):
        contract = {
            **self.contract,
            "acceptance_contract": {
                "obligations": [{"obligation_id": "one"}],
                "required_obligation_ids": ["one", "two"],
            },
        }
        self.assertFalse(self.call(raw_contract=contract)["pass"])

    def test_wrong_capability_blocks(self):
        self.assertFalse(self.call(capability_id="other")["pass"])


if __name__ == "__main__":
    unittest.main()
