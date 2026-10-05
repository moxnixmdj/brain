from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import tempfile
import unittest

from canonical.runtime.composition_runtime_channel_guard_v1 import (
    CompositionChannelError,
    capture_runtime_channels,
)


class Tests(unittest.TestCase):
    def test_file_inputs_and_mutations_are_content_bound(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            source = root / "source.txt"
            source.write_text("alpha", encoding="utf-8")
            out = root / "out.txt"

            with capture_runtime_channels(root, strict=True) as cap:
                value = source.read_text(encoding="utf-8")
                list(root.iterdir())
                out.write_text(value + "-beta", encoding="utf-8")

            receipt = cap.finish()
            self.assertEqual(receipt["status"], "PASS", receipt)
            reads = {row["path"]: row for row in receipt["file_reads"]}
            self.assertEqual(
                reads["repo:source.txt"]["sha256"],
                hashlib.sha256(b"alpha").hexdigest(),
            )
            mutations = {row["path"]: row for row in receipt["mutations"]}
            self.assertFalse(mutations["repo:out.txt"]["pre"]["exists"])
            self.assertEqual(
                mutations["repo:out.txt"]["post"]["sha256"],
                hashlib.sha256(b"alpha-beta").hexdigest(),
            )
            self.assertTrue(receipt["file_and_ambient_inputs_content_bound"])
            self.assertTrue(receipt["closed_world_observed_subset"])
            self.assertRegex(receipt["channel_manifest_sha256"], r"^[0-9a-f]{64}$")

    def test_ambient_environment_is_content_bound_without_exposing_values(self):
        with tempfile.TemporaryDirectory() as td:
            with capture_runtime_channels(td, strict=True) as cap:
                pass
            receipt = cap.finish()
            ambient = receipt["ambient_input"]
            self.assertRegex(ambient["environment_sha256"], r"^[0-9a-f]{64}$")
            self.assertNotIn("environment", ambient)

    def test_process_spawn_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(
                CompositionChannelError,
                "UNMEDIATED_RUNTIME_CHANNEL:process.spawn",
            ):
                with capture_runtime_channels(td, strict=True):
                    subprocess.run(
                        ["definitely-not-executed-because-audit-hook-blocks"],
                        check=False,
                    )

    def test_non_strict_mode_reports_but_does_not_promote_forbidden_event(self):
        with tempfile.TemporaryDirectory() as td:
            with capture_runtime_channels(td, strict=False) as cap:
                cap.observe("socket.connect", (None, ("example.test", 443)))
            receipt = cap.finish()
            self.assertEqual(receipt["status"], "FAIL_CLOSED")
            self.assertFalse(receipt["network_response_evidence_complete"])
            self.assertFalse(receipt["closed_world_observed_subset"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
