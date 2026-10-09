import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V22_PATH = ROOT / "canonical/runtime/r2_direct_end_to_end_adequacy_v22.py"
FP_PATH = ROOT / "canonical/runtime/general_adequate_decision_fixed_point_v2.py"


def _load_v22(*, matched):
    prior = types.ModuleType("canonical.runtime.r2_direct_end_to_end_adequacy_v21")
    prior.ROUTES = {"PRIOR_ROUTE": {"capability_id": "prior"}}
    prior.preflight_calls = 0
    prior.run_calls = 0

    def prior_preflight(request, *, repo_root=None):
        prior.preflight_calls += 1
        return {"matched": False, "status": "V21_FALLBACK", "request": request}

    def prior_run(request, *, repo_root=None):
        prior.run_calls += 1
        return {"pass": True, "matched": True, "status": "V21_RUN", "request": request}

    prior.preflight = prior_preflight
    prior.run = prior_run

    local = types.ModuleType("canonical.runtime.r2_regcap_contextual_fact_direct_adequacy_v1")
    local.ROUTE_ID = "DIRECT_ADEQUACY::REGCAP_BOUNDED_CONTEXTUAL_FACT_EXTRACTION_V1"
    local.CAPABILITY_ID = "finance.regcap.contextual_fact.extract.source_aligned"
    local.preflight_calls = 0
    local.run_calls = 0

    def local_preflight(request, *, repo_root=None):
        local.preflight_calls += 1
        if matched:
            return {"matched": True, "status": "DIRECT_ADEQUACY_ROUTE_MATCHED", "route_id": local.ROUTE_ID}
        return {"matched": False, "status": "NOT_APPLICABLE"}

    def local_run(request, *, repo_root=None):
        local.run_calls += 1
        return {
            "pass": True,
            "matched": True,
            "status": "PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",
            "route_id": local.ROUTE_ID,
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "terminal_authority": False,
        }

    local.preflight = local_preflight
    local.run = local_run

    sys.modules["canonical.runtime.r2_direct_end_to_end_adequacy_v21"] = prior
    sys.modules["canonical.runtime.r2_regcap_contextual_fact_direct_adequacy_v1"] = local
    spec = importlib.util.spec_from_file_location("v22_under_test", V22_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module, local, prior


def test_v22_selects_verified_contextual_fact_route_before_v21():
    v22, local, prior = _load_v22(matched=True)
    request = {"task_id": "x", "goal": "bounded regcap contextual fact"}
    pf = v22.preflight(request)
    assert pf["matched"] is True
    assert pf["route_id"] == local.ROUTE_ID
    assert prior.preflight_calls == 0
    out = v22.run(request)
    assert out["pass"] is True
    assert out["route_id"] == local.ROUTE_ID
    assert out["terminal_authority"] is False
    assert local.run_calls == 1
    assert prior.run_calls == 0
    assert local.ROUTE_ID in v22.ROUTES
    assert "PRIOR_ROUTE" in v22.ROUTES


def test_v22_falls_back_exactly_to_v21_when_local_route_does_not_match():
    v22, local, prior = _load_v22(matched=False)
    request = {"task_id": "x", "goal": "unrelated"}
    pf = v22.preflight(request)
    assert pf["status"] == "V21_FALLBACK"
    assert prior.preflight_calls == 1
    out = v22.run(request)
    assert out["status"] == "V21_RUN"
    assert prior.run_calls == 1
    assert local.run_calls == 0


def test_fixed_point_live_import_points_to_v22():
    source = FP_PATH.read_text(encoding="utf-8")
    assert "r2_direct_end_to_end_adequacy_v22 as direct_adequacy" in source
    assert "r2_direct_end_to_end_adequacy_v21 as direct_adequacy" not in source
