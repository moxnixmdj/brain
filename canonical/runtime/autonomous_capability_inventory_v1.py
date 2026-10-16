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
        if "__pycache__" in relative.parts or relative.is_relative_to("canonical/tests") or relative.is_relative_to("canonical/runtime/bound_capabilities"):
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
    if destination.exists():
        old = json.loads(destination.read_text(encoding="utf-8"))
        if any(entry.get("status") != "UNVERIFIED_INVENTORY" for entry in old["capabilities"].values()):
            raise ValueError("Refusing to overwrite promoted entries")
    doc = build_inventory(root)
    destination.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"Inventoried {len(doc['capabilities'])} sources; none certified or executed")


if __name__ == "__main__":
    main()
