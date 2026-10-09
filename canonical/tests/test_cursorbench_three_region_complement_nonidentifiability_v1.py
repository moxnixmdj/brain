from canonical.runtime.cursorbench_three_region_complement_nonidentifiability_v1 import covered, verify

T=["t1","t2"]
F=["f1","f2"]
R=["r1","r2"]
REGIONS=[T,F,R]

def test_union_covered_when_any_region_true():
    for region in REGIONS:
        v={a:False for group in REGIONS for a in group}
        for a in region: v[a]=True
        assert covered(v,REGIONS) is True

def test_complement_when_each_region_has_a_false_atom():
    v={a:True for group in REGIONS for a in group}
    v[T[0]]=False; v[F[0]]=False; v[R[0]]=False
    assert covered(v,REGIONS) is False

def test_bound_current_evidence_does_not_identify_three_region_complement():
    out=verify()
    assert out["pass"] is True, out
    assert out["region_atom_counts"]==[5,6,7]
    assert out["total_distinct_condition_atoms"]==18
    assert out["world_cover_union_membership"] is True
    assert out["world_escape_union_membership"] is False
    assert out["current_evidence_identifies_complement_emptiness"] is False
    assert out["actual_complement_empty_claimed"] is False
    assert out["actual_complement_nonempty_claimed"] is False
    assert out["terminal_credit_delta"]==0
