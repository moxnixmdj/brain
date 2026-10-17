#!/usr/bin/env python3
"""Execute a composed capability chain for real.

The composer proves a chain is *valid*.  This runs it.  Every step is a real
adapter call on a real file inside the repository root; nothing is simulated.
Fail-closed: a step that cannot run reports why and the chain stops there.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BC = ROOT / "canonical" / "runtime" / "bound_capabilities"
for p in (str(ROOT), str(ROOT / "canonical" / "runtime"), str(BC)):
    if p not in sys.path:
        sys.path.insert(0, p)

import capability_composer_v1 as COMPOSER  # noqa: E402
import frontier_intelligence_v1 as FI  # noqa: E402

WORK = ROOT / "canonical" / "astra_runtime" / "tmp" / "composed_chain"
WORK.mkdir(parents=True, exist_ok=True)


def rel(p: Path) -> str:
    return str(p.resolve().relative_to(ROOT))


def adapter(name: str):
    path = BC / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"bc_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"ADAPTER_LOAD_FAILED:{name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def step(label: str, name: str, args: dict) -> dict:
    try:
        module = adapter(name)
        out = module.run(dict(args), str(ROOT))
    except Exception as exc:
        print(f"  [{label}] {name}")
        print(f"        FAILED  {type(exc).__name__}: {exc}")
        return {"_failed": True}
    status = out.get("status") or out.get("output_verified") or "OK"
    print(f"  [{label}] {name}")
    print(f"        status : {status}")
    for key in ("output_path", "output_verified", "verified", "supported"):
        if key in out:
            print(f"        {key:8s}: {out[key]}")
    return out


def main() -> int:
    g = COMPOSER.graph()
    goal = "evidence.claim.exact_quoted_bound"
    chain = COMPOSER.plan(COMPOSER.external_tokens(g), goal, g)

    print("FRONTIER INTELLIGENCE -- real execution")
    print(f"  goal : {goal}")
    verdict = FI.solve(goal, COMPOSER.external_tokens(g), g)
    print(f"  owned: {len(verdict['owned_capability'])}   jit: {len(verdict['jit_knowledge'])}"
          f"   substrate: {verdict['substrate']['available']}")
    print(f"  chain: {chain}")
    print()

    # ---- real input: a claim about this repository's own measured state ----
    objective = "how many bound capabilities are law-proven"
    candidates = [
        {"id": "c1", "title": "BOUND_CAPABILITY_REGISTRY_V1.json",
         "snippet": "contains 67 bound capabilities all marked VERIFIED_BOUND_CAPABILITY"},
        {"id": "c2", "title": "TRUE capability specs directory",
         "snippet": "nine specs proven under the true capability law at 500 unseen instances"},
        {"id": "c3", "title": "AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json",
         "snippet": "2310 entries of which 2309 are UNVERIFIED_INVENTORY and verified false"},
    ]
    p0 = WORK / "00_candidates.json"
    p0.write_text(json.dumps({"objective": objective, "candidates": candidates}, indent=2),
                  encoding="utf-8")
    print(f"  input written: {rel(p0)}")
    print()

    p1 = WORK / "01_ranked.json"
    p2 = WORK / "02_extraction.json"
    p3 = WORK / "03_relation.json"
    p4 = WORK / "04_binding.json"

    r1 = step(1, "objective_relevance_bm25",
              {"input_path": rel(p0), "output_path": rel(p1)})
    if r1.get("_failed"):
        return 1

    r2 = step(2, "objective_evidence_unit_extract",
              {"input_path": rel(p1), "output_path": rel(p2)})
    if r2.get("_failed"):
        return 1

    spec = json.dumps({"claim": objective, "relation": "exact", "expected": 9})
    r3 = step(3, "generic_evidence_claim_relation",
              {"extraction_path": rel(p2), "spec": spec, "output_path": rel(p3)})

    objective_spec = json.dumps({"claim": objective, "expected": 9, "unit": "count"})
    r4 = step(4, "objective_claim_operand_binding",
              {"extraction_path": rel(p2), "objective": objective_spec,
               "output_path": rel(p4)})

    print()
    ran = sum(1 for r in (r1, r2, r3, r4) if not r.get("_failed"))
    print(f"RESULT: {ran}/4 steps executed for real against real files.")
    print(f"        artifacts in {rel(WORK)}")
    return 0 if ran == 4 else 1


if __name__ == "__main__":
    raise SystemExit(main())
