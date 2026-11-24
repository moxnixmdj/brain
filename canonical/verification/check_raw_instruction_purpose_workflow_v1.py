#!/usr/bin/env python3
"""Offline static checker for the iteration-14 finite replay and hard runner."""
from __future__ import annotations

import ast
import pathlib
import textwrap

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/zero-model-raw-instruction-purpose-v1.yml"
SOURCE_PATHS = (
    "canonical/runtime/raw_instruction_purpose_binder_v1.py",
    "canonical/harbor/raw_instruction_purpose_policy_v1.py",
    "canonical/harbor/raw_instruction_purpose_agent_v1.py",
    "canonical/tests/test_raw_instruction_purpose_binder_v1.py",
    "canonical/tests/test_raw_instruction_purpose_harbor_policy_v1.py",
    "canonical/runtime/goal_directed_sufficient_knowing_v1.py",
    "canonical/harbor/select_tb41_cpu_tasks_v1.py",
)
EXPECTED_GIT_BLOBS = (
    "404d97482eae75fc48b88de7c29841dc20e4bd86",
    "3f9797f699e0e0c1c0d78e5c7efbb7b9cd4a11ed",
    "4f4525e878f613133b7b377d55578c7c0f3bec49",
    "e7eaf0cbeda2b6938f7d3aeb5029906496f0a96e",
    "00f2f3a57979ed81fe9eadee2501da7a6c15fe01",
    "21ed2a90d7c2ee5e659ee9a57bff6cefc3a53a68",
)
EXPECTED_SHA256 = (
    "ef2f8e239142ed08d23985b7582b481f66b54c6658a84c1d72b85e6c1e3d389a",
    "f35a8dbdf9235e93d83450bdf14b813594d1e6802a65855f0fd515bc4ce32723",
    "9d733bd875d3012893096f520d5a8aa5744272ee64c699fee7280d2a9ce37b64",
    "58b35e8a6c7aa9661332051c0d2c1378ac4fda77e4985a846c75210e74ad42cd",
    "19a36977629b2cda0bcf8e7158f2bf5d15ef151a028650511cbf6e99910299b4",
    "0b6c5028baf30fc2fb458508bed71a6a06f4df4387af5164accb97555bb54beb",
    "cbdc8db87e756d36587fcdadc91b54e0cf14500263aa37857689b1c3ff38ad5f",
    "190a5786c41b3f6470228013e57943fcc4984a2205c8f71296ca9e66d176f4c9",
)
FORBIDDEN_IMPORT_ROOTS = {
    "urllib", "requests", "httpx", "socket", "http", "openai", "anthropic",
    "litellm", "transformers", "torch", "tensorflow", "boto3", "subprocess",
    "huggingface_hub", "docker", "yaml", "selenium", "playwright", "intake",
}
KNOWN_TASK_NAMES = (
    "math-eval-grader", "html-js-filter", "bun-sourcemap-leak",
    "batched-eval-parity", "layout-config-recreation", "data-anonymization",
)


def _python_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("python3") and "<<'PY'" in stripped:
            body: list[str] = []
            i += 1
            while i < len(lines) and lines[i].strip() != "PY":
                body.append(lines[i])
                i += 1
            if i >= len(lines):
                raise AssertionError("UNTERMINATED_PYTHON_HEREDOC")
            blocks.append(textwrap.dedent("\n".join(body)) + "\n")
        i += 1
    return blocks


def _import_roots(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def main() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "name: Zero-model raw-instruction purpose bridge and hard falsifier" in text
    assert "branches: [arena/6f8ac9ce-brain]" in text
    assert "contents: write" in text and "id-token: write" in text
    assert "  contract_replay:" in text and "  hard_benchmark_attempt:" in text
    assert "    needs: contract_replay" in text
    assert "raw-instruction-purpose-finite-replay" in text
    assert "canonical.harbor.raw_instruction_purpose_agent_v1:RawInstructionPurposeAgent" in text
    assert "brain_zero_model_agent_v1:ZeroModelBrainAgent" not in text
    assert "RAW_INSTRUCTION_PURPOSE_FINITE_REPLAY_RECEIPT_20261124_V1.json" in text
    assert "RAW_INSTRUCTION_PURPOSE_TERMINAL_BENCH_4_1_RUNNER_RECEIPT_20261124_V1.json" in text
    assert "RAW_INSTRUCTION_PURPOSE_TERMINAL_BENCH_4_1_REWARD_LOG_20261124_V1.json" in text
    assert "benchmark_score_authority\": False" in text
    assert "section_6\": \"NOT_MET\"" in text
    for path in SOURCE_PATHS:
        assert path in text, "SOURCE_PATH_MISSING:" + path
    for blob in EXPECTED_GIT_BLOBS:
        assert blob in text, "EXPECTED_GIT_BLOB_MISSING:" + blob
    for digest in EXPECTED_SHA256:
        assert digest in text, "EXPECTED_SHA256_MISSING:" + digest
    blocks = _python_blocks(text)
    assert len(blocks) == 10, "PYTHON_BLOCK_COUNT " + str(len(blocks))
    for i, block in enumerate(blocks):
        ast.parse(block, filename=f"workflow-python-block-{i}.py")
    marked: set[str] = set()
    production_paths = (
        "canonical/runtime/raw_instruction_purpose_binder_v1.py",
        "canonical/harbor/raw_instruction_purpose_policy_v1.py",
        "canonical/harbor/raw_instruction_purpose_agent_v1.py",
        "canonical/runtime/goal_directed_sufficient_knowing_v1.py",
    )
    for rel in SOURCE_PATHS:
        marked |= _import_roots(ROOT / rel) & FORBIDDEN_IMPORT_ROOTS
    for rel in production_paths:
        lowered = (ROOT / rel).read_text(encoding="utf-8").casefold()
        for task_name in KNOWN_TASK_NAMES:
            assert task_name not in lowered, "TASK_SPECIFIC_ANSWER_LEAK:" + rel + ":" + task_name
    assert not marked, "FORBIDDEN_RUNTIME_IMPORTS:" + ",".join(sorted(marked))
    binder = (ROOT / "canonical/runtime/raw_instruction_purpose_binder_v1.py").read_text(encoding="utf-8")
    policy = (ROOT / "canonical/harbor/raw_instruction_purpose_policy_v1.py").read_text(encoding="utf-8")
    assert "deliberately not a natural-language interpreter" in binder
    assert "not a universal natural-language parser" in policy
    assert "EXACT_EVPI" in (ROOT / "canonical/runtime/goal_directed_sufficient_knowing_v1.py").read_text(encoding="utf-8")
    print("RAW_INSTRUCTION_PURPOSE_WORKFLOW_CHECK_PASS")
    print("PYTHON_BLOCKS", len(blocks))
    print("FORBIDDEN_RUNTIME_IMPORTS", sorted(marked))


if __name__ == "__main__":
    main()
