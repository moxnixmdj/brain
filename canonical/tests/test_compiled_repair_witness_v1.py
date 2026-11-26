"""Safety of the compiled candidate on the supplied cases; not a HARD-51 grade."""
from canonical.runtime.futamura_leapfrog_kernel_v1 import (
    ConformalEValueGate, FutamuraSelfCompilingCascade, _eval_candidate_in_process,
    localize_fault_ochiai,
)


def test_no_edit_or_rent_for_green_receiver_but_actual_red_can_use_rule(tmp_path, monkeypatch):
    # This measures a cold teacher, not a law left by another interpreter.
    monkeypatch.setenv("BRAIN_FUTAMURA_STORE", str(tmp_path / "laws.json"))
    c = FutamuraSelfCompilingCascade(); source = 'def f(x,y):\n    return x <= y\n'
    tests = ['assert not f(1,1)', 'assert f(1,2)', 'assert not f(2,1)']
    teacher = c.solve({'source':source,'test_cases':tests})
    assert (teacher['rung_used'], teacher['proposer_calls'], teacher['compiled_to_rung0']) == (2,0,True)
    rule = c._rules_by_id[teacher['compilation_receipt']['rule_id']]
    green = c.solve({'source':source,'test_cases':tests[1:]})
    assert (green['patched_source'], green['status'], rule.hits) == (source,'ALREADY_PASSING__NO_REPAIR',0)
    q=source.replace('f(x,y)','g(a,b)').replace('x <= y','a <= b')
    red=c.solve({'source':q,'test_cases':[t.replace('f(','g(') for t in tests]})
    assert (red['rung_used'],red['proposer_calls'],rule.hits) == (0,0,1)
    assert red['patched_source']==q.replace('a <= b','a < b')


def test_submitted_foreign_names_are_not_a_receiver_owned_binding(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAIN_FUTAMURA_STORE", str(tmp_path / "laws.json"))
    c=FutamuraSelfCompilingCascade()
    result=c.compile_verified_win_to_rung0('def f(x): return x','def f(x): return convert(x)',source_rung=2)
    assert not result['compiled'] and c.rule_count()==0
    raw='def f(x): return x+2'; changed='def f(x): return x+3'
    r=c.compile_verified_win_to_rung0(raw,changed,source_rung=2)
    assert r['compiled'] and r['after_template']=='3'
    # Re-open the real persisted rule: __C is a template Name, but it must
    # still be indexed under the receiver's Constant.
    reopened=FutamuraSelfCompilingCascade()
    assert r['rule_id'] in reopened.persisted_law_ids()
    solved=reopened.solve({'source':raw,'test_cases':['assert f(0)==3','assert f(8)==11']})
    assert solved['rung_used']==0 and solved['patched_source']==changed


def test_candidate_and_localizer_start_each_case_with_fresh_globals():
    cases=['n += 1','assert n==1']
    assert localize_fault_ochiai('n=0',cases)['total_fail']==1
    assert not _eval_candidate_in_process('n=0',cases)


def test_reusing_one_pass_is_not_an_anytime_error_bound():
    gate=ConformalEValueGate(alpha=.05)
    for _ in range(3):
        g=gate.observe('same event',passed=True,null_pass_prob=.25)
    assert g['verdict']=='COMMIT' and g['step_count']==3  # numerical threshold really crossed
    assert not g['false_commit_bound_established']  # the three observations could be perfectly correlated
