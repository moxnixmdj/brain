import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"
raw = path.read_text(encoding="utf-8")

assert not raw.endswith("\\n"), "authority ends with literal backslash-n"
doc = json.loads(raw)
assert doc["schema"] == "PROJECT_BRAIN_CURRENT_TERMINAL_AUTHORITY_V1"
assert doc["truth"]["achieved"] is False
assert doc["truth"]["opus55_acceptance"] == "2/19_PASS__17/19_OPEN"

print("test_current_terminal_authority_json_integrity: PASS")
