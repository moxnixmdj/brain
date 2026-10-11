"""Thin owner-submission entrypoint for the frozen Brain OSWorld 2.1 subject.

Place this module where the pinned OSWorld-V2 checkout can import
scripts/python/run_multienv.py and the Project Brain canonical package.
It changes only agent construction and the pre-task environment binding hook.
Task loading, DesktopEnv stepping, env.evaluate(), result files, and aggregation
remain the upstream implementation.
"""
from __future__ import annotations

import json
import os
import signal
from pathlib import Path
from typing import Any

from canonical.runtime.osworld_v21_brain_subject_v1 import SUBJECT_ID, build_subject
from canonical.runtime.osworld_v21_runner_binding_v1 import install as install_binding

SCHEMA = "PROJECT_BRAIN_OSWORLD_V21_SUBMISSION_ENTRYPOINT_V1"
FIXED_PROTOCOL = {
    "action_space": "pyautogui",
    "observation_type": "screenshot",
    "max_steps": 500,
    "screen_width": 1920,
    "screen_height": 1080,
    "eval_version": "v2",
}


class SubmissionEntrypointError(RuntimeError):
    pass


def _factory(*_args: Any, **_kwargs: Any):
    return build_subject()


def _freeze_protocol(args: Any) -> None:
    for key, value in FIXED_PROTOCOL.items():
        setattr(args, key, value)
    args.model = SUBJECT_ID


def _write_subject_receipt(args: Any) -> Path:
    result_root = Path(args.result_dir)
    result_root.mkdir(parents=True, exist_ok=True)
    path = result_root / "brain_osworld_subject_receipt.json"
    payload = {
        "schema": SCHEMA,
        "subject_id": SUBJECT_ID,
        "fixed_protocol": FIXED_PROTOCOL,
        "native_evaluator_replaced": False,
        "native_lib_run_single_preserved": True,
        "reference_trajectory_execution_input": False,
        "external_generation_provider": False,
        "incremental_spend_usd": 0,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main() -> int:
    # Importing upstream parses exactly its normal CLI. We then freeze only
    # comparator-critical subject/protocol fields.
    import run_multienv as upstream

    _freeze_protocol(upstream.args)
    upstream.PromptAgent = _factory
    binding = install_binding(upstream.lib_run_single)
    if binding.get("status") not in {"INSTALLED", "ALREADY_INSTALLED"}:
        raise SubmissionEntrypointError("RUNNER_BINDING_INSTALL_FAILED")
    _write_subject_receipt(upstream.args)

    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    signal.signal(signal.SIGINT, upstream.signal_handler)
    signal.signal(signal.SIGTERM, upstream.signal_handler)

    config_file_path = upstream.args.test_all_meta_path
    with open(config_file_path, "r", encoding="utf-8") as f:
        test_all_meta = json.load(f)
    if upstream.args.domain != "all":
        test_all_meta = {upstream.args.domain: test_all_meta[upstream.args.domain]}

    remaining = upstream.get_unfinished(
        upstream.args.action_space,
        upstream.args.model,
        upstream.args.observation_type,
        upstream.args.result_dir,
        test_all_meta,
    )
    upstream.get_result(
        upstream.args.action_space,
        upstream.args.model,
        upstream.args.observation_type,
        upstream.args.result_dir,
        test_all_meta,
    )
    upstream.test(upstream.args, remaining)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
