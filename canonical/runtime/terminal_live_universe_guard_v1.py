import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

AUTH = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"
FRONTIER = ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V6.json"
HYPERGRAPH = ROOT / "canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V3.json"

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def authority_unresolved_count(authority):
    src = authority.get("sources", {}).get("acceptance_predicate_evidence_bindings_reconciled", {})
    status = str(src.get("status", ""))
    m = re.search(r"(\d+)_PROVED__(\d+)_UNRESOLVED", status)
    if not m:
        raise AssertionError("live authority does not expose parseable atomic acceptance counts")
    return int(m.group(1)), int(m.group(2))

def validate():
    authority = load(AUTH)
    frontier = load(FRONTIER)
    hypergraph = load(HYPERGRAPH)
    proved, unresolved = authority_unresolved_count(authority)
    live = set(frontier["unresolved_predicates"])
    coverage = set()
    for action in hypergraph["actions"]:
        coverage.update(action.get("target_predicates", []))
    if unresolved != len(live):
        raise AssertionError(f"authority unresolved={unresolved} frontier={len(live)}")
    missing = live - coverage
    stale = coverage - live
    if missing or stale:
        raise AssertionError(f"coverage mismatch missing={sorted(missing)} stale={sorted(stale)}")
    if "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR" in live or "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR" in coverage:
        raise AssertionError("proved delegation predicate remains schedulable")
    if authority["truth"]["contracts"].split("/",1)[0] != "12":
        raise AssertionError("P1-restored 12/12 contract truth not active")
    return {"proved": proved, "unresolved": unresolved, "frontier": len(live), "coverage": len(coverage)}

if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
