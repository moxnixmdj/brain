from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_verified_skill_memory_v1 as memory


class R3VerifiedSkillMemoryTests(unittest.TestCase):
    def skill(self):
        return {
            "candidate_sha256": "sha256:" + "a" * 64,
            "source_episode_ids": ["ep-1", "ep-2"],
            "source_episode_receipts": [],
            "source_scopes": ["scope-1"],
            "steps": [{
                "index": 0,
                "op": "cap.test",
                "inputs": [],
                "outputs": ["goal"],
            }],
            "preconditions": [],
            "postconditions": ["goal"],
            "invalidators": [],
            "scope_relation": "EXACT",
            "scope_predicate": None,
            "verification_receipt": "SKVR:test",
            "verification_binding": {
                "receipt": {"path": "r.json", "git_blob_sha": "1" * 40},
                "verification": {"path": "v.json", "git_blob_sha": "2" * 40},
            },
            "independent_verifier_id": "TEST",
            "verified_skill": True,
            "reuse_authorized": True,
            "candidate_only": False,
        }

    def record(self):
        skill = self.skill()
        sid = memory._skill_id(skill)
        family = memory._family_id(skill)
        return sid, {
            "skill": skill,
            "family_id": family,
            "pareto_metrics": memory._pareto_row(sid, skill),
            "active": True,
            "dominated_by": None,
            "compression": {},
        }

    def verifier(self, record, *, repo_root):
        return {"pass": True, "verified_skill": dict(record)}

    def test_snapshot_contains_only_reauthenticated_capability_memory(self):
        sid, record = self.record()
        state = learning._empty_state()
        state["skills"][sid] = record
        state["observations"]["obs"] = {"payload": "must-not-persist"}
        state["failures"]["failure"] = {"context": "must-not-persist"}
        state["improvement_queue"]["work"] = {"payload": "must-not-persist"}
        state["reuse"][sid] = {"attempts": 99}

        with mock.patch.object(memory, "reauthenticate_record", side_effect=self.verifier):
            doc = memory.document_from_state(state, repo_root=Path("."))
            checked = memory.validate_document(doc, repo_root=Path("."))

        self.assertEqual(set(doc), {
            "schema", "version", "skills", "pareto_frontiers", "memory_sha256"
        })
        self.assertIn(sid, doc["skills"])
        self.assertEqual(checked["skills"][sid]["active"], True)
        serialized = json.dumps(doc, sort_keys=True)
        self.assertNotIn("must-not-persist", serialized)
        self.assertNotIn("observations", serialized)
        self.assertNotIn("failures", serialized)
        self.assertNotIn("improvement_queue", serialized)

    def test_tampered_memory_digest_is_rejected(self):
        sid, record = self.record()
        state = learning._empty_state()
        state["skills"][sid] = record
        with mock.patch.object(memory, "reauthenticate_record", side_effect=self.verifier):
            doc = memory.document_from_state(state, repo_root=Path("."))
            doc["skills"][sid]["active"] = False
            with self.assertRaises(memory.SkillMemoryError):
                memory.validate_document(doc, repo_root=Path("."))

    def test_invalid_active_skill_cannot_be_persisted(self):
        sid, record = self.record()
        state = learning._empty_state()
        state["skills"][sid] = record
        with mock.patch.object(
            memory,
            "reauthenticate_record",
            return_value={"pass": False, "reason": "test"},
        ):
            with self.assertRaises(memory.SkillMemoryError):
                memory.document_from_state(state, repo_root=Path("."))

    def test_fresh_default_runtime_merges_canonical_skill_memory(self):
        sid, record = self.record()
        with TemporaryDirectory() as td:
            root = Path(td)
            local = root / "SELF_IMPROVEMENT_STATE_V1.json"
            canonical = root / "R3_VERIFIED_SKILL_MEMORY_V1.json"
            state = learning._empty_state()
            state["skills"][sid] = record

            with mock.patch.object(memory, "reauthenticate_record", side_effect=self.verifier):
                memory.write_file(state, memory_path=canonical, repo_root=root)
                with (
                    mock.patch.object(learning, "DEFAULT_STATE_PATH", local),
                    mock.patch.object(learning, "DEFAULT_SKILL_MEMORY_PATH", canonical),
                    mock.patch.object(learning, "ROOT", root),
                ):
                    loaded = learning.load_state(local)

            self.assertFalse(local.exists())
            self.assertIn(sid, loaded["skills"])
            self.assertTrue(loaded["skills"][sid]["active"])
            self.assertEqual(loaded["stats"]["active_skill_count"], 1)

    def test_default_state_write_updates_only_canonical_skill_snapshot(self):
        sid, record = self.record()
        with TemporaryDirectory() as td:
            root = Path(td)
            local = root / "SELF_IMPROVEMENT_STATE_V1.json"
            canonical = root / "R3_VERIFIED_SKILL_MEMORY_V1.json"
            state = learning._empty_state()
            state["skills"][sid] = record
            state["observations"]["obs"] = {"private_task_material": "local-only"}

            with mock.patch.object(memory, "reauthenticate_record", side_effect=self.verifier):
                with (
                    mock.patch.object(learning, "DEFAULT_STATE_PATH", local),
                    mock.patch.object(learning, "DEFAULT_SKILL_MEMORY_PATH", canonical),
                    mock.patch.object(learning, "ROOT", root),
                ):
                    learning._write_state(state, local)

            local_doc = json.loads(local.read_text())
            canonical_doc = json.loads(canonical.read_text())
            self.assertIn("observations", local_doc)
            self.assertNotIn("observations", canonical_doc)
            self.assertNotIn("local-only", json.dumps(canonical_doc))

    def test_nondefault_state_never_imports_canonical_memory(self):
        sid, record = self.record()
        with TemporaryDirectory() as td:
            root = Path(td)
            default_local = root / "default.json"
            other_local = root / "other.json"
            canonical = root / "memory.json"
            state = learning._empty_state()
            state["skills"][sid] = record
            with mock.patch.object(memory, "reauthenticate_record", side_effect=self.verifier):
                memory.write_file(state, memory_path=canonical, repo_root=root)
                with (
                    mock.patch.object(learning, "DEFAULT_STATE_PATH", default_local),
                    mock.patch.object(learning, "DEFAULT_SKILL_MEMORY_PATH", canonical),
                    mock.patch.object(learning, "ROOT", root),
                ):
                    loaded = learning.load_state(other_local)
            self.assertEqual(loaded["skills"], {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
