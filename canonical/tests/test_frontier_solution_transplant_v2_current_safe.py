from canonical.runtime.frontier_solution_transplant_v2 import compile_plan

A='a'*64
B='b'*64
LOCK={
    'S1': {'sha256': A, 'available_exact_bytes': True},
    'S2': {'sha256': B, 'available_exact_bytes': True},
}
DONORS=[
    {'donor_id':'D_AB','invariants':['A','B'],'strength':10,'source_id':'S1','source_sha256':A},
    {'donor_id':'D_C','invariants':['C'],'strength':5,'source_id':'S2','source_sha256':B},
]

def test_existing_donors_cover_internal_frontier_without_invention():
    out=compile_plan([
        {'frontier_id':'F1','required_invariants':['A','B','C'],'external_invariants':[],
         'apply_delta':['fine_tune'], 'acceptance':['all']}
    ], DONORS, LOCK)
    assert out['pass'] is True
    assert out['frontiers_requiring_new_internal_mechanism']==[]
    row=out['frontiers'][0]
    assert row['fine_tune_only'] is True
    assert row['internal_uncovered_invariants']==[]
    assert {x['donor_id'] for x in row['selected_donors']}=={'D_AB','D_C'}


def test_external_only_residual_does_not_authorize_new_mechanism():
    out=compile_plan([
        {'frontier_id':'F_EXT','required_invariants':['A','EXTERNAL_FACT'],
         'external_invariants':['EXTERNAL_FACT']}
    ], DONORS, LOCK)
    assert out['pass'] is True
    assert out['frontiers_with_external_residual_only']==['F_EXT']
    row=out['frontiers'][0]
    assert row['external_residual_invariants']==['EXTERNAL_FACT']
    assert row['internal_uncovered_invariants']==[]
    assert row['new_mechanism_invention_required'] is False
    assert out['new_mechanism_invention_authority'] is False


def test_true_internal_gap_fails_closed_and_is_explicit():
    out=compile_plan([
        {'frontier_id':'F_GAP','required_invariants':['A','UNOWNED_INTERNAL'],
         'external_invariants':[]}
    ], DONORS, LOCK)
    assert out['pass'] is False
    assert out['frontiers_requiring_new_internal_mechanism']==['F_GAP']
    assert out['frontiers'][0]['internal_uncovered_invariants']==['UNOWNED_INTERNAL']
    assert out['new_mechanism_invention_authority'] is True


def test_donor_without_exact_locked_source_is_rejected():
    bad=[dict(DONORS[0], source_sha256='c'*64)]
    out=compile_plan([{'frontier_id':'F','required_invariants':['A']}], bad, LOCK)
    assert out['pass'] is False
    assert out['reason']=='DONOR_SOURCE_NOT_EXACTLY_AVAILABLE'
    assert out['new_mechanism_invention_authority'] is False
