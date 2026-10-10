import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def test_scheduler_cost_direction_truth():
    a=json.loads((ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json").read_text())
    live=a["live_truth"]
    assert live["universal_trace_not_x_required_for_terminal"] is False
    assert live["universal_trace_not_x_optional_stronger_route"] is True
    assert live["terminal_autopilot_adaptive_route_rankable_by_wall_clock"] is False
    assert live["terminal_autopilot_adaptive_route_verified_wall_clock_cost_ub"] is None
    assert live["terminal_autopilot_adaptive_route_leverage_lower_bound"] is None
    assert live["terminal_autopilot_adaptive_route_leverage_upper_bound_from_cost_lower_bound"] == 13
