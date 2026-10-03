import json
from pathlib import Path
from canonical.runtime.root3_target_population_coalescence_verifier_v1 import evaluate,ROOT,CAND

def test_current_passes():
 out=evaluate()
 assert out["pass"] is True,out
 assert out["formal_root3_target_count"]==7
 assert out["population_group_count"]==4
 assert out["shared_multi_predicate_population_group_count"]==3
 assert out["duplicate_population_definitions_eliminated"]==3
 assert out["scope_completeness_predicates_closed"]==0
 assert out["acceptance_credit_delta"]==0
 assert out["fresh_reality_authority"] is False
