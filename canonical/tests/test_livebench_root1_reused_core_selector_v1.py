from canonical.runtime.livebench_root1_reused_core_selector_v1 import (
    select_minimum_root1_core,
)


FOUR_B = "QWEN3_5_4B_Q4_K_M_EXISTING_CARRIER"
NINE_B = "QWEN3_5_9B_Q4_K_M_EXISTING_CARRIER"
SMAUG = "SMAUG_MINI_BF16_EXTERNAL_ACQUISITION"


def test_reuses_4b_before_any_larger_route():
    out = select_minimum_root1_core()
    assert out["status"] == "QUALIFICATION_REQUIRED"
    assert out["selected"]["id"] == FOUR_B
    assert out["selected"]["action"] == "REUSE_AND_QUALIFY_ROOT1"
    assert out["selected"]["bytes"] == 3013027808
    assert out["capability_credit"] == 0
    assert out["fresh_terminal_reality_authorized"] is False


def test_root1_specific_4b_falsification_advances_to_reused_9b():
    out = select_minimum_root1_core([FOUR_B])
    assert out["selected"]["id"] == NINE_B
    assert out["selected"]["action"] == "REUSE_AND_QUALIFY_ROOT1"
    assert out["selected"]["bytes"] == 5060174144
    assert out["capability_credit"] == 0


def test_two_small_root1_falsifications_are_required_before_smaug_acquisition():
    out = select_minimum_root1_core([FOUR_B, NINE_B])
    assert out["selected"]["id"] == SMAUG
    assert out["selected"]["action"] == "ACQUIRE_AND_QUALIFY_ROOT1"
    assert out["selected"]["bytes"] == 55600000000
    assert out["acceptance_credit"] == 0
    assert out["promotion_authorized"] is False


def test_all_routes_falsified_fails_closed():
    out = select_minimum_root1_core([FOUR_B, NINE_B, SMAUG])
    assert out == {
        "schema": "PROJECT_BRAIN_LIVEBENCH_ROOT1_REUSED_CORE_SELECTOR_V1",
        "status": "BLOCKED",
        "reason": "NO_UNFALSIFIED_CORE_ROUTE",
        "acceptance_credit": 0,
        "capability_credit": 0,
        "ownership_credit": 0,
    }
