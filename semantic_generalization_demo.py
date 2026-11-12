#!/usr/bin/env python3
"""Isolated smoke test of lexical experience retrieval—not a task-solving proof.

All experience files are written under a temporary directory. The engine returns a
candidate strategy suggestion; this script does not execute it or verify its outcome.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.swe_kernel.semantic_generalization_engine_v1 import SemanticGeneralizationEngine


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="brain-semantic-retrieval-") as temp:
        root = Path(temp)
        engine = SemanticGeneralizationEngine(
            experiences_path=root / "experiences.json",
            embeddings_path=root / "embeddings.json",
        )

        examples = [
            (
                "count functions in a source file",
                [{"action": "read file"}, {"action": "parse with ast"}],
                {"type": "synthetic_example", "recommended_actions": ["read", "parse", "traverse"]},
            ),
            (
                "find classes in a Python module",
                [{"action": "read file"}, {"action": "parse with ast"}],
                {"type": "synthetic_example", "recommended_actions": ["read", "parse", "inspect classes"]},
            ),
            (
                "identify methods in a utility script",
                [{"action": "read file"}, {"action": "parse with ast"}],
                {"type": "synthetic_example", "recommended_actions": ["read", "parse", "traverse"]},
            ),
        ]
        for task, trajectory, strategy in examples:
            engine.store_experience(task, trajectory, "success", strategy)

        query = "enumerate subroutines in legacy_code.py"
        result = engine.generalize_and_solve(query, top_k=3)

        print("Lexical retrieval smoke test (synthetic data)")
        print("=" * 52)
        print(f"query: {query}")
        print(f"retrieved candidates: {result['similar_experiences_found']}")
        print(f"similarity scores: {[round(x, 3) for x in result['top_similarities']]}")
        print(f"strategy suggestion returned: {result['adapted_strategy'] is not None}")
        print(f"temporary store only: {root.exists()}")
        print("execution: none")
        print("verification: none")
        print("This smoke test demonstrates retrieval only; it does not establish transfer or correctness.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
