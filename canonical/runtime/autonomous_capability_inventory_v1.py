"""Inventory Python sources without importing, executing, or certifying them.

Run with python3 -m canonical.runtime.autonomous_capability_inventory_v1.
Discovery is not verification: promotion requires separate adapter validation.
"""
from __future__ import annotations

import json
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1"


def build_inventory(root: Path) -> dict:
    capabilities = {}
    for path in sorted((root / "canonical").rglob("*.py")):
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or relative.is_relative_to("canonical/tests") or relative.is_relative_to("canonical/runtime/bound_capabilities") or relative.is_relative_to("canonical/astra_runtime/tmp"):
            continue
        # Full relative paths avoid collisions between same-named source files.
        cid = relative.as_posix() + ".auto.v1"
        capabilities[cid] = {
            "status": "UNVERIFIED_INVENTORY",
            "verification": {"verified": False},
            "source": {"type": "repository_python_source", "path": relative.as_posix()},
            "incremental_spend_usd": None,
        }
    return {"schema": SCHEMA, "capabilities": capabilities}


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    destination = root / "canonical/runtime/AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json"
    old = json.loads(destination.read_text(encoding="utf-8")) if destination.exists() else {"capabilities": {}}
    doc = merge_preserving_promotions(build_inventory(root), old)
    destination.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    kept = sum(1 for e in doc["capabilities"].values() if e.get("status") != "UNVERIFIED_INVENTORY")
    print(f"Inventoried {len(doc['capabilities']) - kept} sources (none certified or executed); kept {kept} promoted entries")


def merge_preserving_promotions(fresh: dict, old: dict) -> dict:
    """Re-inventory without losing promotion work: promoted entries are kept verbatim (their
    verification is re-checked by extended_capability_promoter_v1 --check, not here), and an
    inventory file that a promoted capability reuses keeps its ``promoted_to`` link."""
    caps = dict(fresh["capabilities"])
    for cid, entry in (old.get("capabilities") or {}).items():
        if not isinstance(entry, dict):
            continue
        if entry.get("status") != "UNVERIFIED_INVENTORY":
            caps[cid] = entry
        elif cid in caps and entry.get("promoted_to"):
            caps[cid] = dict(caps[cid], promoted_to=list(entry["promoted_to"]))
    return {"schema": fresh["schema"], "capabilities": dict(sorted(caps.items()))}


if __name__ == "__main__":
    main()
