from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CROSSWALK=ROOT/"canonical/governance/LEGACY_OPUS19_TO_ASTRA_DEMONSTRATED_TARGET_CROSSWALK_V1.json"
ASTRA=ROOT/"canonical/capabilities/astra/ASTRA_DEMONSTRATED_CAPABILITY_TARGET_UNIVERSE_V1.json"
LEGACY=ROOT/"canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json"

def load(p: Path): return json.loads(p.read_text(encoding="utf-8"))

def verify() -> dict:
    c,a,l=load(CROSSWALK),load(ASTRA),load(LEGACY)
    errors=[]
    a_ids={x["id"] for x in a["target_behaviors"]}
    l_ids={x["id"] for x in l["families"]}
    ca={x["id"] for x in c["astra_targets"]}
    cl={x["id"] for x in c["legacy_rows"]}
    if ca != a_ids: errors.append("ASTRA_TARGET_SET_MISMATCH")
    if cl != l_ids: errors.append("LEGACY_19_SET_MISMATCH")
    for row in c["astra_targets"]:
        unknown=set(row["legacy_support"])-l_ids
        if unknown: errors.append(f"UNKNOWN_LEGACY_SUPPORT:{row['id']}")
    for row in c["legacy_rows"]:
        unknown=set(row["astra_targets"])-a_ids
        if unknown: errors.append(f"UNKNOWN_ASTRA_TARGET:{row['id']}")
    expected_gap={"CYBERSECURITY_PROBLEM_SOLVING"}
    actual_gap={x["id"] for x in c["astra_targets"] if not x["legacy_support"]}
    if actual_gap != expected_gap: errors.append("GAP_SET_CHANGED")
    if c["findings"]["legacy_family_count"] != len(l_ids): errors.append("LEGACY_COUNT")
    if c["findings"]["astra_target_count"] != len(a_ids): errors.append("ASTRA_COUNT")
    return {
        "valid":not errors,
        "errors":errors,
        "legacy_family_count":len(l_ids),
        "astra_target_count":len(a_ids),
        "dedicated_legacy_gap_count":len(actual_gap),
        "dedicated_legacy_gaps":sorted(actual_gap),
        "set_equivalent":False,
        "terminal_credit_delta":0
    }

if __name__=="__main__":
    out=verify()
    print(json.dumps(out,sort_keys=True))
    raise SystemExit(0 if out["valid"] else 1)
