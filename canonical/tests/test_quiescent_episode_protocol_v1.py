from __future__ import annotations

import json
import os
import pathlib
import tempfile
import unittest

from canonical.runtime.quiescent_episode_protocol_v1 import (
    EpisodeProtocolError,
    classify_snapshot,
    inject_response_once,
    make_outcome,
    make_response,
)


def write_outcome(root: pathlib.Path, outcome: dict) -> None:
    path = root / ".brain" / "episode_outcome.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(outcome, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )


class QuiescentEpisodeProtocolTests(unittest.TestCase):
    def test_request_classifies(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            out = make_outcome(
                episode_id="ep-1",
                sequence=0,
                kind="REQUEST",
                payload={
                    "request_type": "GLOBAL_RETRIEVAL_PLAN",
                    "request_id": "r-1",
                    "request": {"q": "needle"},
                },
            )
            write_outcome(root, out)
            got = classify_snapshot(
                root, expected_episode_id="ep-1", expected_sequence=0
            )
            self.assertEqual(got["kind"], "REQUEST")
            self.assertFalse(got["parent_action_authorized"])

    def test_tampered_outcome_hash_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            out = make_outcome(
                episode_id="ep-1",
                sequence=0,
                kind="FAIL",
                payload={"error_code": "X", "reason": "x"},
            )
            out["payload"]["reason"] = "tampered"
            write_outcome(root, out)
            with self.assertRaisesRegex(
                EpisodeProtocolError, "OUTCOME_CONTENT_OR_HASH_MISMATCH"
            ):
                classify_snapshot(
                    root, expected_episode_id="ep-1", expected_sequence=0
                )

    def test_outcome_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as outside:
            root = pathlib.Path(td)
            target = pathlib.Path(outside) / "episode_outcome.json"
            target.write_text("{}", encoding="utf-8")
            (root / ".brain").symlink_to(pathlib.Path(outside), target_is_directory=True)
            with self.assertRaisesRegex(
                EpisodeProtocolError, "JOURNAL_PATH_SYMLINK_REJECTED"
            ):
                classify_snapshot(
                    root, expected_episode_id="ep-1", expected_sequence=0
                )

    def test_complete_duplicate_artifact_id_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            out = make_outcome(
                episode_id="ep-1",
                sequence=0,
                kind="COMPLETE",
                payload={"result": {"ok": True}, "declared_artifact_ids": ["a", "a"]},
            )
            write_outcome(root, out)
            with self.assertRaisesRegex(
                EpisodeProtocolError, "DECLARED_ARTIFACT_IDS_INVALID"
            ):
                classify_snapshot(
                    root, expected_episode_id="ep-1", expected_sequence=0
                )

    def test_fail_classifies(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            out = make_outcome(
                episode_id="ep-1",
                sequence=3,
                kind="FAIL",
                payload={"error_code": "NO_ROUTE", "reason": "no admissible route"},
            )
            write_outcome(root, out)
            got = classify_snapshot(
                root, expected_episode_id="ep-1", expected_sequence=3
            )
            self.assertEqual(got["kind"], "FAIL")

    def test_response_injection_is_content_bound_and_single_use(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            root.mkdir(exist_ok=True)
            env = make_response(
                episode_id="ep-1",
                sequence=1,
                request_id="r-1",
                request_outcome_sha256="a" * 64,
                response={"status": "ok", "value": 7},
            )
            path = inject_response_once(root, env)
            self.assertTrue(path.is_file())
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(stored, env)
            with self.assertRaisesRegex(
                EpisodeProtocolError, "RESPONSE_ALREADY_EXISTS"
            ):
                inject_response_once(root, env)

    def test_response_path_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as outside:
            root = pathlib.Path(td)
            (root / ".brain").symlink_to(pathlib.Path(outside), target_is_directory=True)
            env = make_response(
                episode_id="ep-1",
                sequence=1,
                request_id="r-1",
                request_outcome_sha256="a" * 64,
                response={"status": "ok"},
            )
            with self.assertRaisesRegex(
                EpisodeProtocolError, "RESPONSE_PATH_SYMLINK_REJECTED"
            ):
                inject_response_once(root, env)
            self.assertEqual(list(pathlib.Path(outside).iterdir()), [])

    def test_tampered_response_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            env = make_response(
                episode_id="ep-1",
                sequence=1,
                request_id="r-1",
                request_outcome_sha256="a" * 64,
                response={"status": "ok"},
            )
            env["response"]["status"] = "tampered"
            with self.assertRaisesRegex(
                EpisodeProtocolError, "RESPONSE_CONTENT_OR_HASH_MISMATCH"
            ):
                inject_response_once(root, env)
            self.assertFalse((root / ".brain").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
