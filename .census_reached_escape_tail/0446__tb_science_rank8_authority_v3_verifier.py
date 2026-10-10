from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FILES = {
    "authority": "canonical/governance/TB_SCIENCE_RANK8_ONE_SLOT_EXECUTION_AUTHORITY_20261007_V3.json",
    "ledger": "canonical/governance/TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261007_V5.json",
    "intent": "canonical/action_intents/ACTION_INTENT_TB_SCIENCE_RANK8_ONE_SHOT_20261007_V3.json",
    "replay": "canonical/verification/TB_SCIENCE_RANK8_REACTIVATION_PUBLIC_REPLAY_20261007_V1.json",
    "manifest": "canonical/governance/TB_SCIENCE_TERMINAL_EXECUTION_MANIFEST_V1.json",
    "agent": "canonical/runtime/harbor_science_agent_v1.py",
    "planner": "canonical/runtime/harbor_science_planner_v1.py",
    "raw_contract": "canonical/runtime/lossless_raw_task_contract_v1.py",
    "raw_localizer": "canonical/runtime/raw_task_acceptance_residual_localizer_v1.py",
}
EXPECTED = {
    "ledger": "651a800d1e9f43f15be3447546b2807e1365b42d",
    "intent": "e1c663ccd0090c7d3b3b3e201d1d4e9112496ee1",
    "replay": "be73ef34aece4d1f9e5622a006568653ab2f5c5d",
    "manifest": "6dfa880b1f68881531afbba6ca211681801fd19b",
    "agent": "5bc8ebac26bb7c809d4698f535eff43b667b30df",
    "planner": "c3e36eba57c450f325c8a9476ee048c841bbdbc8",
    "raw_contract": "d54d5a2f7efa76b653d288f4f53da4883644baa6",
    "raw_localizer": "f29616cf7726959aa28db4ed6541a9fc0bc2ac76",
}
SLOT = "terminal-bench-science/linked-cell-suppression::trial-0"
DIGEST = "sha256:34d92f30b75011c93d55caced3a4a58c6f68a7bebdbb601b36cb6561ef4069c0"
EPOCH_SHA = "f95f513b0ad57b8b3398fcabba44beae6fd805f4"
EPOCH_ID = "TBSCI-RANK8-20261007-E3"


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load(key: str) -> dict:
    value = json.loads((ROOT / FILES[key]).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("OBJECT_REQUIRED:" + key)
    return value


def verify() -> dict:
    errors: list[str] = []
    for key, expected in EXPECTED.items():
        path = ROOT / FILES[key]
        if not path.is_file():
            errors.append("MISSING:" + key)
        elif blob_sha(path) != expected:
            errors.append("DRIFT:" + key)
    if errors:
        return {"pass": False, "errors": errors, "execution_authority": False}

    a = load("authority")
    ledger = load("ledger")
    intent = load("intent")
    replay = load("replay")

    if a.get("schema") != "PROJECT_BRAIN_TB_SCIENCE_RANK8_ONE_SLOT_AUTHORITY_V3":
        errors.append("AUTHORITY_SCHEMA")
    if not str(a.get("status", "")).startswith("ACTIVE__LIVE_PUBLIC_EPOCH_PRECHECK_REQUIRED"):
        errors.append("AUTHORITY_STATUS")

    slot = a.get("slot", {})
    if slot.get("id") != SLOT or slot.get("digest") != DIGEST or slot.get("rank") != 8:
        errors.append("AUTHORITY_SLOT")

    truth = ledger.get("truth_repair", {})
    next_slot = truth.get("next_untouched_slot", {})
    consumed = set(truth.get("consumed_slots", []))
    if len(consumed) != 7:
        errors.append("CONSUMED_COUNT")
    if SLOT in consumed:
        errors.append("RANK8_ALREADY_CONSUMED")
    if next_slot.get("slot_id") != SLOT or next_slot.get("task_digest") != DIGEST:
        errors.append("LEDGER_NEXT_SLOT")
    if ledger.get("status", "").find("NEXT_UNTOUCHED_RANK8") < 0:
        errors.append("LEDGER_STATUS")

    exact = a.get("exact_route", {})
    expected_route = {
        "agent": EXPECTED["agent"],
        "planner": EXPECTED["planner"],
        "raw_task_contract": EXPECTED["raw_contract"],
        "raw_task_localizer": EXPECTED["raw_localizer"],
    }
    if exact != expected_route:
        errors.append("AUTHORITY_ROUTE")

    iexact = intent.get("exact_route", {})
    if iexact != expected_route:
        errors.append("INTENT_ROUTE")
    if intent.get("current_ledger", {}).get("git_blob_sha") != EXPECTED["ledger"]:
        errors.append("INTENT_LEDGER")

    epoch = a.get("live_epoch", {})
    if epoch.get("git_blob_sha") != EPOCH_SHA or epoch.get("epoch_id") != EPOCH_ID:
        errors.append("EPOCH_BINDING")
    if epoch.get("required_immediately_before_task_start") is not True:
        errors.append("EPOCH_TIMING")

    canonical = replay.get("canonical_exact_bytes", {})
    replay_route = {
        "agent": canonical.get("harbor_science_agent_v1"),
        "planner": canonical.get("harbor_science_planner_v1"),
        "raw_task_contract": canonical.get("lossless_raw_task_contract_v1"),
        "raw_task_localizer": canonical.get("raw_task_acceptance_residual_localizer_v1"),
    }
    if replay_route != expected_route:
        errors.append("REPLAY_ROUTE")
    if replay.get("reactivation_prerequisites", {}).get("rank8_still_unexposed") is not True:
        errors.append("REPLAY_EXPOSURE")
    if replay.get("accounting", {}).get("incremental_spend_usd") != 0:
        errors.append("REPLAY_SPEND")

    controls = a.get("controls", {})
    if controls.get("exact_slot_count") != 1 or controls.get("attempts") != 1:
        errors.append("ONE_SHOT")
    if controls.get("retries") != 0 or controls.get("replacement_allowed") is not False:
        errors.append("NO_RETRY_REPLACEMENT")
    if controls.get("incremental_spend_usd_max") != 0:
        errors.append("SPEND_CAP")
    if controls.get("precheck_failure_consumes_slot") is not False:
        errors.append("PRECHECK_CONSUMPTION")
    if controls.get("after_task_start_result_is_irreversible") is not True:
        errors.append("IRREVERSIBILITY")

    return {
        "pass": not errors,
        "errors": errors,
        "slot": SLOT if not errors else None,
        "rank": 8 if not errors else None,
        "current_consumed_slots": 7 if not errors else None,
        "public_epoch_blob_required": EPOCH_SHA if not errors else None,
        "public_epoch_id_required": EPOCH_ID if not errors else None,
        "execution_authority": not errors,
        "fresh_reality_units_authorized": 1 if not errors else 0,
        "incremental_spend_usd_max": 0,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
