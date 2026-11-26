"""MEME format split, blind online producer, and *local* exact-string grader.

Separate processes: split PATH | predict NEW_DIR > frozen.jsonl; only then grade
PATH frozen.jsonl. The predictor is not given the episode path, future dialogue,
question metadata, task type or answers. Works with full flat release as well as
format-compatible fixtures. This is not the authors' semantic judge.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import unicodedata

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))


def split(episodes):
    for e,episode in enumerate(episodes):
        yield {'op':'begin','e':e}
        prev=0
        for phase in ('before','after'):
            qs=episode[phase+'_questions'];cut=qs['position_after_session']+1
            if not prev<=cut<=len(episode['sessions']):raise ValueError('invalid time cutoff')
            for session in episode['sessions'][prev:cut]:
                for t in session['conversation']:
                    yield {'op':'ingest','role':t['role'],'text':t['content']}
            for i,q in enumerate(qs['questions']):
                yield {'op':'ask','phase':phase,'i':i,'question':q['question']}
            prev=cut


def predict(events, root):
    from canonical.runtime.dialogue_revision_reader_v1 import DialogueReader
    root.mkdir(exist_ok=False)
    for event in events:
        if event['op']=='begin':
            e=int(event['e']);reader=DialogueReader(root/(str(e)+'.sqlite'));t=n=0;started=time.monotonic()
        elif event['op']=='ingest':
            t+=1;n+=reader.ingest(event['role'],event['text'],turn=t,source=f'turn:{t}')
        elif event['op']=='ask':
            yield {'e':e,'i':event['i'],'phase':event['phase'],'turns_seen':t,'statements_grounded':n,
                   'seconds_since_start':round(time.monotonic()-started,6),**reader.answer(event['question'])}
        else:raise ValueError('unknown event')


def norm(x):
    return ' '.join(unicodedata.normalize('NFKC',str(x)).casefold().strip(' .\n\t').split())


def grade(episodes, predictions):
    keyed={(r['e'],r['phase'],r['i']):r for r in predictions};rows=[]
    for e,episode in enumerate(episodes):
        pre={}
        for phase in ('before','after'):
            for i,q in enumerate(episode[phase+'_questions']['questions']):
                r=keyed[(e,phase,i)]; gold=q.get('expected_answer') if phase=='before' else q['gold_answer']
                hit=norm(r['answer'])==norm(gold);entity=next(iter(q['entity_values']));kind=q['task_type'].split(' (')[0]
                if phase=='before':pre[entity]=hit
                gated=(hit and pre.get(entity,False)) if phase=='after' and kind in ('Del','Cas','Abs') else hit
                rows.append({'episode':episode['episode_id'],'phase':phase,'i':i,'task':kind,'status':r['status'],
                             'strict_match':hit,'gated_match':gated,'turns_seen':r['turns_seen'],
                             'statements_grounded':r['statements_grounded']})
    return rows


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('op',choices=['split','predict','grade']);p.add_argument('path',type=Path)
    p.add_argument('predictions',type=Path,nargs='?');a=p.parse_args()
    if a.op=='grade':
        print(json.dumps({'kind':'strict normalized string and paired pre/post control; NOT official semantic judge',
                          'dataset_sha256':hashlib.sha256(a.path.read_bytes()).hexdigest(),
                          'prediction_sha256':hashlib.sha256(a.predictions.read_bytes()).hexdigest(),
                          'rows':grade(json.loads(a.path.read_text()),map(json.loads,a.predictions.read_text().splitlines()))},indent=2))
    else:
        rows=split(json.loads(a.path.read_text())) if a.op=='split' else predict(map(json.loads,sys.stdin),a.path)
        for r in rows: print(json.dumps(r),flush=True)
