"""Find registry-presence composers that claim verified in an empty workspace.

The source-pattern filter identifies a bounded, auditable family, not every
possible composer. Each identified adapter receives a temporary root containing
only a copy of the registry and an output directory. No source tree, tests,
issue, diff, or PR is supplied to the adapter.
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PATTERN = re.compile(r"(?:verified|registry_ready)\s*=\s*all\(found\.values\(\)\)")


def measure() -> dict:
    directory = ROOT / "canonical/runtime/bound_capabilities"
    modules = [path for path in sorted(directory.glob("*.py"))
               if PATTERN.search(path.read_text(encoding="utf-8"))]
    registry = (ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_bytes()
    rows = []
    with tempfile.TemporaryDirectory(prefix="brain-composition-audit-") as temporary:
        root = Path(temporary)
        path = root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
        path.parent.mkdir(parents=True)
        path.write_bytes(registry)
        for source in modules:
            row = {"adapter": source.stem}
            try:
                module = importlib.import_module("canonical.runtime.bound_capabilities." + source.stem)
                result = module.run({"output_path": f"out/{source.stem}.json"}, root)
                artifact = json.loads((root / result["output_path"]).read_text(encoding="utf-8"))
                row.update({"result_verified": result.get("verified") is True,
                            "output_verified": result.get("output_verified") is True,
                            "artifact_verified": artifact.get("verified") is True})
            except Exception as exc:  # diagnostic: report failures, don't hide them
                row["error"] = type(exc).__name__ + ":" + str(exc)
            rows.append(row)
    verified = sum(any(row.get(key) is True for key in
                       ("result_verified", "output_verified", "artifact_verified")) for row in rows)
    errors = sum("error" in row for row in rows)
    status = ("FAIL__REGISTRY_ONLY_VERIFIED_CLAIMS" if verified else
              "INCONCLUSIVE__PROBE_ERRORS_OR_NO_MATCHES" if errors or not rows else
              "NO_VERIFIED_CLAIM_OBSERVED")
    return {
        "schema": "BRAIN_REGISTRY_ONLY_COMPOSITION_PROBE_V1",
        "status": status,
        "source_pattern_matches": len(modules), "verified_claims": verified, "errors": errors, "rows": rows,
        "scope": "source-pattern family; registry-only disposable workspace; not all composers",
        "terminal_authority": False,
    }


def main() -> int:
    report = measure()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "NO_VERIFIED_CLAIM_OBSERVED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
