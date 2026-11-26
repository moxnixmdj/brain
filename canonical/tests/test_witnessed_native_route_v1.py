"""Regression checks for measured confounders, NOT hard or transfer scores."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

import pytest
from canonical.runtime.brain_unified_model_v1 import open_model
from canonical.runtime.creature_runtime_v1 import Creature
from canonical.swe_kernel import prior_owned_insertions_v1 as history
from canonical.swe_kernel import repair_input_dependency_gate_v1 as gate
from canonical.swe_kernel import repo_component_petri_v1 as petri
from canonical.swe_kernel.repo_native_test_surface_v1 import test_surface as observe_cases, restored_surface
from canonical.swe_kernel.repair_journal_v1 import RepairJournal


def test_history_requires_strict_ancestry_owner_and_token_rebinding(tmp_path):
    repo=tmp_path/'origin';repo.mkdir()
    def git(*args):return subprocess.check_output(['git','-C',repo,*args],text=True).strip()
    git('init','-q','--template=');git('config','user.name','control');git('config','user.email','control@invalid')
    start="class Alpha:\n    def f(self, x):\n        z = x.strip()\n        return z\nclass Beta:\n    def f(self, x):\n        z = x.strip()\n        return z\n"
    def commit(text):
        (repo/'p.py').write_text(text);git('add','p.py');git('commit','-qm','edit');return git('rev-parse','HEAD')
    root=commit(start);past=commit(start.replace('        return z','        z = z.upper()\n        return z',1));
    base=commit(start.replace('        z = x.strip()', '        z = x.strip()\n        z = z.lower()',2));
    commit((repo/'p.py').read_text().replace('        return z','        z = z.title()\n        return z',1));git('tag','later')
    git('checkout','-q','--detach',root);commit(start.replace('        return z','        z = z.swapcase()\n        return z'));git('tag','sibling');git('checkout','-q','--detach',base)
    index=history.mine(repo,base,['p.py'],100)
    assert {r['from'] for rows in index.values() for r in rows}=={past}
    assert {(k[0],k[1]) for k in index}=={('p.py','Alpha.f')}
    # The matcher refuses inventions (such as a new attribute not in the
    # receiver). Supply it in ordinary source, not via a privileged vocabulary.
    receiver=start.replace('z','cargo').replace('x.strip()', 'x.strip()')+'\ndef sample(other):\n    return other.upper()\n'
    rows=list(history.candidates(receiver,'p.py',[3,7],index));assert len(rows)==1
    patched,witness=rows[0];assert 'cargo = cargo.upper()' in patched and witness['receiver_line']==3
    assert witness['owner']=='Alpha.f' and witness['from']==past
    with pytest.raises(ValueError,match='full receiver HEAD'):history.mine(repo,past,['p.py'],10)
    assert history.H.instantiate({'anchor_holes':['x','y'],'added':['    x = y + "x"  # y']},['y','x'])=='    y = x + "x"  # y\n'


def test_dependency_and_component_identity_are_not_short_name_or_path(tmp_path):
    a='class X:\n def convert(self, a): return a\nclass Y:\n def convert(self, a): return a\n'
    assert gate.gate(a,a.replace('return a','return 7',1))['lost']==[{'function':'X.convert','slot':'pos#1','parameter':'a'}]
    p=tmp_path/'work.py';p.write_text('from helpers import source\n'); helpers=tmp_path/'helpers.py'
    def inventory():return [c.min_arity for c in petri.mine_repo_neighborhood_components(repo_root=tmp_path,
        rel_path=p.name,parsed_tree=ast.parse(p.read_text()),line_no=1)[0] if c.name=='source']
    helpers.write_text('def source(a): return a\n');assert inventory()==[1]
    helpers.write_text('def source(a, b): return a+b\n');assert inventory()==[2]


def test_green_requires_all_original_identities_and_no_lost_skips(tmp_path):
    p=tmp_path/'test_behavior.py'
    p.write_text('def test_a(): assert 0\ndef test_b(): pass\n');red=observe_cases(tmp_path,[p.name],timeout=5)
    assert red['status']=='RED' and len(red['failed'])==1
    p.write_text('def test_c(): pass\ndef test_b(): pass\n');swapped=observe_cases(tmp_path,[p.name],timeout=5)
    assert swapped['status']=='GREEN' and not restored_surface(red,swapped)
    p.write_text('def test_a(): pass\ndef test_b(): pass\n');assert restored_surface(red,observe_cases(tmp_path,[p.name],timeout=5))
    p.write_text('def helper(): return True\n');assert observe_cases(tmp_path,[p.name],timeout=5)['status']=='NO_CASES'


def test_typed_composition_then_disk_reload_actual_template_and_forgetting(tmp_path):
    root=tmp_path/'teacher';root.mkdir(); mem=tmp_path/'brain'/'repair.sqlite'
    # The required conversion has no hand-listed operator; both edges come
    # from the repo and use distinct types. No witness envs or prior demos.
    s='def octets(value: str) -> bytes:\n    return value.encode()\n\ndef measure(data: bytes) -> int:\n    return sum(data)\n\ndef label(value: str) -> int:\n    return len(value)\n'
    check='from local import label\n\ndef test_nonempty(): assert label("ab") == 195\ndef test_empty(): assert label("") == 0\n'
    (root/'local.py').write_text(s);(root/'test_usage.py').write_text(check)
    kw=dict(candidate_files=['local.py'],test_targets=['test_usage.py'],mine_git_history=False,timeout_s=18)
    m=open_model();a=m.solve_swe_repo_native(root,repair_store=mem,**kw)['swe_result']
    assert a['tier']=='LOCAL_TYPED_RETURN_PATH' and a['typed_path']['suppliers_inner_first']==[('octets',1),('measure',4)]
    assert a['typed_path']['owner']=='label' and a['tested_surface_count']==2 and a['model_calls']==0
    assert (root/'local.py').read_text()==s
    teacher=a['teacher_key'];assert RepairJournal(mem).store.query(teacher)['value']['failed_before']==[['test_usage','test_nonempty']]
    # Restart. Rename the public API, leaving the bound supplier vocabulary
    # unchanged. Assert that a verified *stored candidate* won, not that a
    # stage name appeared ahead of a win by some later solver.
    other=tmp_path/'receiver';other.mkdir();(other/'local.py').write_text(s.replace('def label(', 'def scale('));(other/'test_usage.py').write_text(check.replace('label','scale').replace('"ab"','"cd"').replace('195','199'))
    c=Creature('learner',mem.parent,100)
    b=c.solve_swe_repo_native(other,learn_verified=False,**kw)['swe_result']
    assert b['tier']=='IN_RUN_ALPHA_TRANSFER' and b['fired_template_id'] in {r['template_id'] for rows in a['updated_repair_vocab'].values() for r in rows}
    assert b['teacher_ids']==[teacher] and b['candidate_sha256']==hashlib.sha256(b['patches']['local.py'].encode()).hexdigest()
    RepairJournal(mem).forget(teacher)
    d=Creature('another-process',mem.parent,100).solve_swe_repo_native(other,learn_verified=False,**kw)['swe_result']
    assert d['localization']['store_templates_retrieved']==0 and d['tier']=='LOCAL_TYPED_RETURN_PATH'
    assert not (other/'repair.sqlite').exists()


def test_external_link_and_baseline_write_do_not_mutate_caller_workspace(tmp_path):
    root=tmp_path/'r';root.mkdir();p=root/'test_local.py';p.write_text('from pathlib import Path\ndef test_writes(): Path("state").write_text("new")\n')
    model=open_model();out=model.solve_swe_repo_native(root,test_targets=[p.name])['swe_result']
    assert out['status']=='PASS__BASELINE_ALREADY_GREEN' and out['issue_satisfied'] is None
    assert not (root/'state').exists()
    (root/'link').symlink_to(tmp_path)
    assert model.solve_swe_repo_native(root,test_targets=[p.name])['status']=='UNMEASURED__SOURCE_COPY'
