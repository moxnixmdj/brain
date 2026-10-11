from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from canonical.runtime import chartography_qwen3vl4b_adapter_v1 as a


class AdapterTests(unittest.TestCase):
    def sample(self):
        return {
            "task_id": "sample-1",
            "prompt": "Read the chart and answer.",
            "chart_path": "/tmp/chart.png",
        }

    def test_command_is_image_prompt_only(self):
        cmd = a.build_command(
            self.sample(),
            llama_cli_path="/tmp/llama-mtmd-cli",
            model_path="/tmp/model.gguf",
            projector_path="/tmp/mmproj.gguf",
        )
        self.assertIn("--image", cmd)
        self.assertIn("/tmp/chart.png", cmd)
        self.assertIn("Read the chart and answer.", cmd)
        joined = " ".join(cmd).lower()
        self.assertNotIn("golden", joined)
        self.assertNotIn("answer_key", joined)

    def test_rejects_golden_answer_leakage(self):
        s = self.sample()
        s["golden_answer"] = "secret"
        with self.assertRaisesRegex(
            a.ChartographyAdapterError, "UNMODELED_OR_LEAKY_SAMPLE_FIELDS"
        ):
            a.validate_sample(s)

    def test_rejects_invalid_limits(self):
        with self.assertRaisesRegex(a.ChartographyAdapterError, "THREADS_INVALID"):
            a.build_command(
                self.sample(),
                llama_cli_path="x",
                model_path="y",
                projector_path="z",
                threads=0,
            )
        with self.assertRaisesRegex(a.ChartographyAdapterError, "MAX_TOKENS_INVALID"):
            a.build_command(
                self.sample(),
                llama_cli_path="x",
                model_path="y",
                projector_path="z",
                max_tokens=0,
            )

    @patch.object(a.Path, "is_file", return_value=True)
    @patch.object(a, "_sha256_file")
    @patch.object(a.subprocess, "run")
    def test_run_binds_exact_subject_and_receipt(self, run, sha, _is_file):
        sha.side_effect = [
            a.MODEL_SHA256,
            a.PROJECTOR_SHA256,
            "1" * 64,
        ]
        run.return_value = subprocess.CompletedProcess(
            args=["fake"], returncode=0, stdout="350C\n", stderr="diag"
        )
        out = a.run_sample(
            self.sample(),
            llama_cli_path="/tmp/llama",
            model_path="/tmp/model",
            projector_path="/tmp/projector",
        )
        self.assertEqual(out["status"], "PASS__PINNED_SUBJECT_IMAGE_PROMPT_EXECUTION")
        self.assertEqual(out["subject"]["model_sha256"], a.MODEL_SHA256)
        self.assertEqual(out["subject"]["projector_sha256"], a.PROJECTOR_SHA256)
        self.assertEqual(out["output"]["completion"], "350C")
        self.assertFalse(out["score_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    @patch.object(a.Path, "is_file", return_value=True)
    @patch.object(a, "_sha256_file")
    def test_model_hash_mismatch_fails_closed(self, sha, _is_file):
        sha.return_value = "0" * 64
        with self.assertRaisesRegex(
            a.ChartographyAdapterError, "MODEL_SHA256_MISMATCH"
        ):
            a.run_sample(
                self.sample(),
                llama_cli_path="/tmp/llama",
                model_path="/tmp/model",
                projector_path="/tmp/projector",
            )

    @patch.object(a.Path, "is_file", return_value=True)
    @patch.object(a, "_sha256_file")
    @patch.object(a.subprocess, "run")
    def test_empty_completion_rejected(self, run, sha, _is_file):
        sha.side_effect = [a.MODEL_SHA256, a.PROJECTOR_SHA256]
        run.return_value = subprocess.CompletedProcess(
            args=["fake"], returncode=0, stdout="   ", stderr=""
        )
        with self.assertRaisesRegex(a.ChartographyAdapterError, "EMPTY_COMPLETION"):
            a.run_sample(
                self.sample(),
                llama_cli_path="/tmp/llama",
                model_path="/tmp/model",
                projector_path="/tmp/projector",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
