from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "canonical/capabilities/astra/ASTRA_DEMONSTRATED_CAPABILITY_TARGET_UNIVERSE_V1.json"

def load_registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))

def verify(registry: dict | None = None) -> dict:
    r = load_registry() if registry is None else registry
    errors: list[str] = []
    if r.get("target_rule") != "CAPABILITY_BEHAVIOR_IS_THE_TARGET__BENCHMARKS_PREDICATES_MODEL_NAMES_AND_SCORES_ARE_EVIDENCE_ONLY":
        errors.append("TARGET_RULE")
    sources = r.get("source_corpus", [])
    source_ids = [x.get("id") for x in sources]
    if not source_ids or len(source_ids) != len(set(source_ids)):
        errors.append("SOURCE_IDS")
    targets = r.get("target_behaviors", [])
    target_ids = [x.get("id") for x in targets]
    if not target_ids or len(target_ids) != len(set(target_ids)):
        errors.append("TARGET_IDS")
    known = set(source_ids)
    for row in targets:
        if not row.get("behavior"):
            errors.append(f"EMPTY_BEHAVIOR:{row.get('id')}")
        refs = row.get("source_ids", [])
        if not refs:
            errors.append(f"NO_SOURCE:{row.get('id')}")
        unknown = sorted(set(refs) - known)
        if unknown:
            errors.append(f"UNKNOWN_SOURCE:{row.get('id')}:{','.join(unknown)}")
    own = r.get("ownership_rule", {})
    if own.get("opaque_astra_runtime_counts_as_owned") is not False:
        errors.append("OPAQUE_ASTRA_OWNERSHIP")
    if own.get("donor_independent_brain_route_required") is not True:
        errors.append("DONOR_INDEPENDENCE")
    if own.get("knowledge_external_jit") is not True:
        errors.append("KNOWLEDGE_RULE")
    if own.get("incremental_spend_usd") != 0:
        errors.append("SPEND_RULE")
    if r.get("terminal_credit_delta") != 0 or r.get("ownership_credit_delta") != 0:
        errors.append("ZERO_CREDIT")
    return {
        "valid": not errors,
        "errors": errors,
        "source_count": len(sources),
        "target_behavior_count": len(targets),
        "target_comparator_separated": "BENCHMARKS_PREDICATES" in r.get("target_rule", ""),
        "activation_authority": False,
        "terminal_credit_delta": 0,
    }

if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, sort_keys=True))
    raise SystemExit(0 if out["valid"] else 1)
