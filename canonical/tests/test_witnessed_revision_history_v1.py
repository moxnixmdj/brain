"""Point-in-time truth versus support multiplicity. Not a MEME grade."""
import os
import random
import sqlite3
import subprocess
import sys

import pytest
from canonical.runtime.dialogue_revision_reader_v1 import DialogueReader
from canonical.swe_kernel.witnessed_revision_store_v1 import RevisionStore


def write(s, op, key, vf, value=None, parents=()):
    return s.append(op,key,value=value,valid_from=vf,parents=parents,witness=f'reading:{key}:{vf}',source='meter')


def test_late_correction_and_alternate_proof_after_restart(tmp_path):
    path=tmp_path/'room.sqlite'; s=RevisionStore(path)
    t=write(s,'set','switch',2,'on'); b=write(s,'set','backup',1,True)
    a=write(s,'derive','power',3,'live',[t['id']]); alt=write(s,'derive','power',4,'live',[b['id']]);
    c=write(s,'derive','lamp',4,'lit',[a['id']]); write(s,'derive','lamp',5,'lit',[alt['id']]);
    cut=write(s,'delete','switch',8)
    assert cut['head_delta']['retracted_weights']==3
    assert len(s.query('lamp')['support'])==1 and s.query('lamp')['value']=='lit'
    late=write(s,'set','switch',3,'off')
    assert late['head_delta']['inserted_weights']==0  # already hidden at latest valid time
    s=RevisionStore(path)
    assert s.query('switch',valid_at=4,known_at=cut['tx'])['value']=='on'
    assert s.query('switch',valid_at=4,known_at=late['tx'])['value']=='off'
    assert s.query('lamp',valid_at=4,known_at=c['tx'])['value']=='lit'
    assert s.query('lamp',valid_at=4)['status']=='UNKNOWN_LOST_SUPPORT'
    assert s.query('switch')['status']=='DELETED'
    assert write(s,'delete','backup',9)['head_delta']['retracted_weights']==3
    assert s.query('lamp')['status']=='UNKNOWN_LOST_SUPPORT'
    assert s.query('lamp',valid_at=6)['value']=='lit'
    assert s.query('lamp')['events_considered']==2
    with pytest.raises(ValueError,match='stale support'):
        write(s,'derive','new',10,True,[t['id']])


def test_unsupported_replacement_never_revives_previous_value(tmp_path):
    s=RevisionStore(tmp_path/'r');write(s,'set','binding',1,'stale');p=write(s,'set','observation',2,'seen')
    write(s,'revise','binding',3,'new',[p['id']]);assert s.query('binding')['value']=='new'
    write(s,'delete','observation',4)
    assert s.query('binding')['status']=='UNKNOWN_LOST_SUPPORT'
    assert s.query('binding',valid_at=1)['value']=='stale'


def test_materialization_matches_historical_walk_on_disordered_updates(tmp_path):
    rng=random.Random(310);s=RevisionStore(tmp_path/'mixed');keys=[f'fact:{i}' for i in range(9)]
    for i in range(140):
        at=rng.randrange(12);k=rng.choice(keys);par=s.query(rng.choice(keys),valid_at=at)['support']
        if i%3 and par: op=rng.choice(['revise','derive']);ps=[rng.choice(par)['id']]
        else:op=rng.choice(['set','delete']);ps=[]
        ev=s.append(op,k,valid_from=at,witness=str(i),source='interleaved',parents=ps,
                    value=None if op=='delete' else rng.randrange(3))
        for key in keys:
            live=s.query(key);audit=s.query(key,known_at=ev['tx'])
            assert {k:v for k,v in live.items() if k not in ('events_considered','view')}=={
                k:v for k,v in audit.items() if k not in ('events_considered','view')}


def test_aborted_transaction_is_not_visible_and_reopen_rebuilds_old_format(tmp_path):
    path=tmp_path/'room';s=RevisionStore(path);p=write(s,'set','u',1,'one');write(s,'derive','v',1,'two',[p['id']])
    script="""import os,sys
from canonical.swe_kernel.witnessed_revision_store_v1 import RevisionStore
s=RevisionStore(sys.argv[1]);db=s._connect();db.execute('BEGIN IMMEDIATE')
s.append_tx(db,'delete','u',valid_from=9,source='crash',witness='x');os._exit(21)"""
    result=subprocess.run([sys.executable,'-c',script,str(path)])
    assert result.returncode==21
    assert RevisionStore(path).query('v')['value']=='two'
    # Old schema held just event + its indices, without materialized support.
    with sqlite3.connect(path) as db:
        for table in ('head','incidence','revision_meta'):db.execute('DROP TABLE '+table)
    s=RevisionStore(path); assert s.query('v')['value']=='two'
    assert write(s,'delete','u',2)['head_delta']['retracted_weights']==2


def test_dialogue_uses_assertions_not_suggestions_or_future_turns(tmp_path):
    p=tmp_path/'dialogue';r=DialogueReader(p)
    def ingest(n,text,role='user'):return r.ingest(role,text,turn=n,source=f't{n}')
    assert ingest(1,'My lamp is yellow.','assistant')==0
    assert ingest(2,'If my switch is up, then my lamp is red.')==1
    assert ingest(3,'My switch is up.')==2
    assert DialogueReader(p).answer('What is my lamp?')['answer']=='red'
    ingest(4,'My switch is sideways.')
    assert r.answer('What is my lamp?')['status']=='UNKNOWN_LOST_SUPPORT'
    ingest(5,'Forget my switch.')
    assert r.answer('What is my switch?')['status']=='DELETED'
    assert r.answer('What is my serial number?')['answer']=='Uncertain'


def test_both_front_doors_see_one_committed_turn_and_its_as_of_answer(tmp_path):
    from canonical.runtime.brain_unified_model_v1 import open_model
    from canonical.runtime.creature_runtime_v1 import Creature
    c = Creature('reader', tmp_path, 20); m=open_model(); path=tmp_path/'revisions.sqlite'
    rules=('If my switch is up, then my lamp is red. If my backup is on, then my lamp is red.')
    assert c.revision_memory('ingest_turn',role='user',text=rules,turn=1,source='s')=={'statements_grounded':2}
    for i,statement in enumerate(['My switch is up.', 'My backup is on.', 'Forget my switch.'],2):
        m.revision_memory(path,'ingest_turn',role='user',text=statement,turn=i,source=f's{i}')
    both=c.revision_memory('answer_question',question='What is my lamp?',valid_at=3)
    assert both['answer']=='red' and len(both['evidence_ids'])==2
    assert len(c.revision_memory('answer_question',question='What is my lamp?')['evidence_ids'])==1
    # A new, longer slot must not change which key an old question designates.
    c.revision_memory('ingest_turn',role='user',text='My backup lamp is green.',turn=5,source='s5')
    assert c.revision_memory('answer_question',question='What is my backup lamp?',valid_at=2)['answer']=='red'
    assert c.revision_memory('answer_question',question='What is my backup lamp?')['answer']=='green'
