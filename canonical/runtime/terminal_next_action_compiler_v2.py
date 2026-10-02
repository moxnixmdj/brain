"""Terminal next-action compiler v2.

Minimal reconciliation wrapper over the independently tested v1 scheduling logic.
The v1 algorithm is generic; v2 binds it to the active private-route-safe
OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2 instead of stale V1.

Zero-credit scheduling only. No evidence, semantic, execution, or promotion authority.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.terminal_next_action_compiler_v1 import (
    compile_next_frontier as _compile_v1,
)

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
EVIDENCE = ROOT / "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
HYPERGRAPH = ROOT / "canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"

SCHEMA = "PROJECT_BRAIN_TERMINAL_NEXT_ACTION_COMPILED_V2"


def compile_next_frontier_v2(
    registry: Mapping[str, Any],
    evidence: Mapping[str, Any],
    hypergraph: Mapping[str, Any],
) -> dict[str, Any]:
    out = dict(_compile_v1(registry, evidence, hypergraph))
    out["schema"] = SCHEMA
    out["source_hypergraph"] = "OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2"
    out["rule"] = (
        "ACTIVE_HYPERGRAPH_V2_ONLY__"
        "PRIMARY_IS_NEXT_EXECUTABLE_ACTION_NEVER_A_BLOCKED_EDGE__"
        "HIGHEST_LEVERAGE_BLOCKED_ACTION_REPORTED_SEPARATELY__"
        "NO_SEMANTIC_INFERENCE_NO_NEW_EVIDENCE_NO_PROMOTION"
    )
    return out


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    hypergraph = json.loads(HYPERGRAPH.read_text(encoding="utf-8"))
    out = compile_next_frontier_v2(registry, evidence, hypergraph)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if str(out.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
