from canonical.runtime.coverage_closure_gate_v1 import close_coverage
A='a'*64; B='b'*64; C='c'*64

def test_fixed_point_generates_and_covers_obligations():
    rules=[{'rule_id':'r1','when_all':['A'],'add':['B'],'receipt_sha256':A},{'rule_id':'r2','when_all':['B'],'add':['C'],'receipt_sha256':B}]
    receipts={x:{'independently_verified':True,'sha256':C,'obligation':x} for x in ['A','B','C']}
    out=close_coverage(mission_scope_sha256=A,seeds=['A'],rules=rules,
        operator_set_completeness_receipt={'independently_verified':True,'sha256':B},coverage_receipts=receipts)
    assert out['pass'] is True and out['universe']==['A','B','C']
def test_missing_derived_coverage_fails():
    out=close_coverage(mission_scope_sha256=A,seeds=['A'],rules=[{'rule_id':'r','when_all':['A'],'add':['B'],'receipt_sha256':A}],
        operator_set_completeness_receipt={'independently_verified':True,'sha256':B},
        coverage_receipts={'A':{'independently_verified':True,'sha256':C,'obligation':'A'}})
    assert out['pass'] is False and 'B' in out['uncovered_obligations']
