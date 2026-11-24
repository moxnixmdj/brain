#!/usr/bin/env python3
"""Offline static checker for the goal-directed sufficient-knowing runner."""
from __future__ import annotations

import ast
import pathlib
import textwrap

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/zero-model-goal-directed-sufficient-knowing-v1.yml"
MODULE = ROOT / "canonical/runtime/goal_directed_sufficient_knowing_v1.py"
EXPECTED_BLOBS = (
    "e64204cffb1a7ae5043a77c1be153687fd63371e",
    "03d195285cc60ec470566c993b6635410ea1a063",
    "7c9c70db9fa4ec28bc01ff9442108ede2e168c92",
)
FORBIDDEN_IMPORT_ROOTS = {
    "urllib", "requests", "httpx", "socket", "http", "openai", "anthropic",
    "litellm", "transformers", "torch", "tensorflow", "boto3", "subprocess",
    "huggingface_hub", "docker", "yaml", "selenium", "playwright",
}


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


def main() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "name: Zero-model goal-directed sufficient-knowing runner" in text
    assert "branches: [arena/6f8ac9ce-brain]" in text
    assert "contents: write" in text and "id-token: write" in text
    assert "canonical/runtime/goal_directed_sufficient_knowing_v1.py" in text
    assert "canonical/tests/test_goal_directed_sufficient_knowing_v1.py" in text
    assert "canonical/astra_runtime/state/GOAL_DIRECTED_SUFFICIENT_KNOWLEDGE_STORE_V1.json" in text
    assert "GOAL_DIRECTED_SUFFICIENT_KNOWING_RUNNER_RECEIPT_20261124_V1.json" in text
    for blob in EXPECTED_BLOBS:
        assert blob in text, "EXPECTED_BLOB_MISSING:" + blob
    blocks = _python_blocks(text)
    assert len(blocks) == 4, "PYTHON_BLOCK_COUNT " + str(len(blocks))
    for i, block in enumerate(blocks):
        ast.parse(block, filename=f"workflow-python-block-{i}.py")
    tree = ast.parse(MODULE.read_text(encoding="utf-8"), filename=str(MODULE))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    marked = roots & FORBIDDEN_IMPORT_ROOTS
    assert not marked, "FORBIDDEN_RUNTIME_IMPORTS:" + ",".join(sorted(marked))
    assert "EXACT_EVPI" in MODULE.read_text(encoding="utf-8")
    print("GOAL_DIRECTED_SUFFICIENT_KNOWING_WORKFLOW_CHECK_PASS")
    print("PYTHON_BLOCKS", len(blocks))
    print("FORBIDDEN_RUNTIME_IMPORTS", sorted(marked))


if __name__ == "__main__":
    main()
