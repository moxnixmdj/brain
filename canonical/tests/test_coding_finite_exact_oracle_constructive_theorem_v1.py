import itertools, json
from pathlib import Path
from canonical.runtime.coding_finite_candidate_exact_oracle_solver_v1 import solve

ROOT=Path(__file__).resolve().parents[2]
THM=ROOT/"canonical/governance/CODING_FINITE_EXACT_ORACLE_CONSTRUCTIVE_ADEQUACY_THEOREM_20261009_V1.json"

def rows(n):
    return [{"candidate_id":f"C{i}","value":i} for i in range(n)]

def test_exhaustive_boolean_checker_patterns_through_eight_candidates():
    checked=0
    for n in range(1,9):
        for bits in itertools.product((False,True),repeat=n):
            out=solve(rows(n),lambda c,bits=bits:bits[c["value"]],max_checks=n)
            checked+=1
            if any(bits):
                first=bits.index(True)
                assert out["pass"] is True
                assert out["selected_candidate_index"]==first
                assert out["check_calls"]==first+1
            else:
                assert out["pass"] is False
                assert out["reason"]=="NO_ACCEPTED_CANDIDATE"
                assert out["detail"]["check_calls"]==n
    assert checked==510

def test_theorem_has_all_six_load_bearing_premises_and_no_target_transfer():
    t=json.loads(THM.read_text(encoding="utf-8"))
    atoms=[x["id"] for x in t["condition"]["args"]]
    assert len(atoms)==6 and len(set(atoms))==6
    assert t["adequacy"]["adequate_for_every_member"] is True
    assert t["adequacy"]["constructive_liveness"] is True
    assert t["adequacy"]["empirical_generalization_used"] is False
    assert t["boundary"]["target_membership_self_certified"] is False
    assert t["boundary"]["arbitrary_cursorbench_membership_proved"] is False
    assert t["boundary"]["whole_cursorbench_cover_proved"] is False
    assert t["accounting"]["terminal_credit_delta"]==0
