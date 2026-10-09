# stdlib-only deterministic verification
import json
import math
from pathlib import Path

from canonical.runtime.tb_science_postslot_reducer_v1 import (
    TBSciencePostSlotError,
    reduce_postslot,
)

ROOT = Path(__file__).resolve().parents[2]
LEDGER = json.loads((ROOT / "canonical/governance/TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261009_V30.json").read_text())
MANIFEST = json.loads((ROOT / "canonical/governance/TB_SCIENCE_TERMINAL_EXECUTION_MANIFEST_V1.json").read_text())
SLOT = "terminal-bench-science/sparse-network-assimilation::trial-0"
DIGEST = "sha256:52ba7089dc32952df08c478af76b732fa82468c125431388adbf9798d869826f"


def receipt(status, reward, *, started=True):
    return {
        "slot_id": SLOT,
        "task_digest": DIGEST,
        "status": status,
        "reward": reward,
        "task_started": started,
        "benchmark_trials_consumed": 1 if started else 0,
        "execution_authority_consumed": started,
        "consumed_successes_delta": 1 if status == "SUCCESS" else 0,
        "consumed_final_failures_delta": 1 if status == "FINAL_ZERO" else 0,
        "rerun_credit": False,
        "start_cas_replay_authority": False if started else None,
        "start_cas_replacement_carrier_authority": False if started else None,
    }


def expect_error(label, fn):
    try:
        fn()
    except TBSciencePostSlotError as exc:
        assert label in str(exc), (label, str(exc))
    else:
        raise AssertionError("expected TBSciencePostSlotError:" + label)


def test_rank16_final_zero_advances_exactly_to_rank17():
    out = reduce_postslot(LEDGER, receipt("FINAL_ZERO", 0.0), MANIFEST)
    c = out["current_counts"]
    assert out["terminal_result"] == "FINAL_ZERO"
    assert c["consumed_slots"] == 16
    assert c["consumed_successes"] == 0
    assert c["consumed_final_failures"] == 16
    assert c["successes_remaining_for_pass_lock"] == 124
    assert c["additional_failures_before_fail_lock"] == 71
    assert c["maximum_possible_successes_remaining"] == 194
    assert math.isclose(c["minimum_required_success_rate_over_remaining_slots"], 124 / 194)
    assert c["next_unconsumed_slot"] == {
        "ledger_schedule_rank": 17,
        "frozen_manifest_schedule_order": 16,
        "task_rank": 16,
        "slot_id": "terminal-bench-science/variable-star-vetting::trial-0",
        "task_digest": "sha256:51bf2b9d8e87a428772d92c6765d83ad3edc7c24283d2ff75af5f050aaee0c67",
    }


def test_rank16_success_advances_exactly_to_rank17():
    out = reduce_postslot(LEDGER, receipt("SUCCESS", 1.0), MANIFEST)
    c = out["current_counts"]
    assert out["terminal_result"] == "SUCCESS"
    assert c["consumed_slots"] == 16
    assert c["consumed_successes"] == 1
    assert c["consumed_final_failures"] == 15
    assert c["successes_remaining_for_pass_lock"] == 123
    assert c["additional_failures_before_fail_lock"] == 72
    assert c["maximum_possible_successes_remaining"] == 194
    assert math.isclose(c["minimum_required_success_rate_over_remaining_slots"], 123 / 194)


def test_preexposure_abort_is_nonconsuming_and_does_not_advance():
    out = reduce_postslot(
        LEDGER,
        receipt("PREEXPOSURE_ABORT_NONCONSUMING", None, started=False),
        MANIFEST,
    )
    assert out["consumed_delta"] == 0
    assert out["current_counts"] == LEDGER["current_counts"]
    assert out["next_unconsumed_slot"] == LEDGER["current_counts"]["next_unconsumed_slot"]


def test_out_of_order_slot_is_rejected():
    r = receipt("FINAL_ZERO", 0.0)
    r["slot_id"] = "terminal-bench-science/variable-star-vetting::trial-0"
    expect_error("RECEIPT_SLOT_OUT_OF_ORDER", lambda: reduce_postslot(LEDGER, r, MANIFEST))


def test_retry_credit_is_rejected():
    r = receipt("FINAL_ZERO", 0.0)
    r["rerun_credit"] = True
    expect_error("RERUN_CREDIT_MUST_BE_FALSE", lambda: reduce_postslot(LEDGER, r, MANIFEST))


def test_started_nonterminal_receipt_is_rejected():
    r = receipt("POSTSTART_ABORT__IRREVERSIBLE", 0.0)
    expect_error("TERMINAL_RECEIPT_STATUS_INVALID", lambda: reduce_postslot(LEDGER, r, MANIFEST))


if __name__ == "__main__":
    tests = [
        test_rank16_final_zero_advances_exactly_to_rank17,
        test_rank16_success_advances_exactly_to_rank17,
        test_preexposure_abort_is_nonconsuming_and_does_not_advance,
        test_out_of_order_slot_is_rejected,
        test_retry_credit_is_rejected,
        test_started_nonterminal_receipt_is_rejected,
    ]
    for test in tests:
        test()
    print("PASS__TB_SCIENCE_POSTSLOT_REDUCER__6_OF_6")
