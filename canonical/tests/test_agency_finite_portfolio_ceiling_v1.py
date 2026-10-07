from canonical.runtime.agency_finite_portfolio_generator_v1 import DIMENSIONS, generate
from canonical.runtime.agency_finite_portfolio_ceiling_v1 import verify

def test_generator_is_six_dimension_exact_cover():
 out=generate("0123456789abcdef"*4)
 assert out["case_count"]==6
 assert out["dimension_cover_complete"] is True
 assert {x["dimension"] for x in out["cases"]}==set(DIMENSIONS)

def test_exact_bound_repository_proves_agency_portfolio_ceiling():
 out=verify("0123456789abcdef"*4)
 assert out["pass"] is True,out
 assert out["aggregate"]["terminal_task_success"]==1
 assert out["aggregate"]["invalid_action_rate"]==0
 assert out["aggregate"]["unrecovered_failure_rate"]==0
 assert out["aggregate"]["duplicate_or_conflicting_work_rate"]==0
 assert out["target_predicates"]["AGENCY_MATCHED_SUCCESS_NONINFERIOR"] is True
 assert out["target_predicates"]["AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION"] is True
 assert out["ceiling_logic"]["brain_success_noninferior_to_any_comparator"] is True
 assert out["ceiling_logic"]["brain_safety_noninferior_to_any_comparator"] is True
 assert out["ceiling_logic"]["opus_case_execution_required"] is False
 assert out["fresh_target_reality_units_consumed"]==0
 assert out["incremental_spend_usd"]==0

# Execution trigger only: rerun the independent GitHub-hosted replay after the verifier landed.
