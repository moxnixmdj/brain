"""Goal-local, externally stored repair proposals. No training or raw trajectory archive.

Wake enqueues only a patch which the native solver has actually rechecked. Sleep
atomically files compact templates by needed syntax and their supporting teacher
event. A killed worker leaves either the job or its result, never half a proof.
A recalled template always faces the receiver's own tests, even after a prior win.
"""
from __future__ import annotations

import ast
from contextlib import closing
import hashlib
import json

from canonical.swe_kernel.witnessed_revision_store_v1 import RevisionStore
from canonical.swe_kernel.repo_native_test_surface_v1 import merge_vocab


def _json(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)


def token(obj):
    return hashlib.sha256(_json(obj).encode()).hexdigest()


class RepairJournal:
    def __init__(self,path):
        self.store=RevisionStore(path)
        with closing(self.store._connect()) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS repair_queue(id TEXT PRIMARY KEY, payload TEXT NOT NULL)')

    def enqueue(self, certificate, vocabulary):
        if not certificate['failed_before'] or not certificate['restored_surface_sha256']:
            raise ValueError('missing measured repair')
        rows=[]
        for kind,templates in sorted(vocabulary.items()):
            for t in templates:
                if kind not in ('node','leaf') or t.kind=='NON_EXECUTABLE':continue
                row=t.as_dict();row.pop('support');row.pop('taught_by')
                body=_json(row)
                if len(body)<=2048 and len(rows)<32:
                    rows.append([kind, row])
        if not rows:return None
        payload={'certificate':certificate,'rows':rows};key='repair-evidence:'+token(payload)
        with closing(self.store._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            # An already retracted ticket cannot be resurrected by a replay.
            if not db.execute('SELECT 1 FROM event WHERE key=? LIMIT 1',(key,)).fetchone():
                db.execute('INSERT OR IGNORE INTO repair_queue VALUES(?,?)',(key,_json(payload)))
        return key

    def sleep(self,limit=8):
        if type(limit) is not int or not 0<=limit<=128:raise ValueError('invalid consolidation budget')
        filed=[]
        with closing(self.store._connect()) as db:
            for _ in range(limit):
                with db:
                    db.execute('BEGIN IMMEDIATE')
                    r=db.execute('SELECT id,payload FROM repair_queue ORDER BY rowid LIMIT 1').fetchone()
                    if r is None:break
                    key,payload=r['id'],json.loads(r['payload'])
                    if key!='repair-evidence:'+token(payload):raise ValueError('changed pending ticket')
                    if not db.execute('SELECT 1 FROM event WHERE key=? LIMIT 1',(key,)).fetchone():
                        cert=payload['certificate']; kw=dict(valid_from=0,source=key,witness=token(cert))
                        parent=self.store.append_tx(db,'set',key,value=cert,**kw)
                        for kind,row in payload['rows']:
                            root=row['root_type' if kind=='node' else 'node_type']
                            name=f"repair-template:{root}:{kind}:{row['template_id']}"
                            self.store.append_tx(db,'derive',name,value=[kind,row],parents=[parent['id']],**kw)
                        filed.append(key)
                    db.execute('DELETE FROM repair_queue WHERE id=?',(key,))
        return filed

    def recall(self, sources, limit=32):
        needed=set(); vocab={'node':[], 'leaf':[]}
        for source,lines in sources:
            try:tree=ast.parse(source)
            except SyntaxError:continue
            needed.update(type(n).__name__ for n in ast.walk(tree) if getattr(n,'lineno',None) in lines)
        with closing(self.store._connect()) as db:
            db.execute('BEGIN');keys=[]
            for t in sorted(needed):
                prefix=f'repair-template:{t}:'
                keys.extend(r[0] for r in db.execute('SELECT DISTINCT key FROM head WHERE key>=? AND key<? AND live=1 '
                            'ORDER BY key LIMIT ?', (prefix,prefix[:-1]+';',limit-len(keys))))
                if len(keys)>=limit:break
            for key in keys:
                proofs=list(db.execute('SELECT e.source,e.value FROM head h JOIN event e ON h.id=e.id '
                                 'WHERE h.key=? AND h.live=1 ORDER BY e.source',(key,)))
                if len({r['value'] for r in proofs})!=1:continue
                kind,row=json.loads(proofs[0]['value']);row['taught_by']=sorted({r['source'] for r in proofs})
                row['support']=len(row['taught_by']);vocab[kind].append(row)
        return merge_vocab({},vocab)

    def forget(self,key):
        if not key.startswith('repair-evidence:'):raise ValueError('expected teacher key')
        return self.store.append('delete',key,valid_from=0,source='forget',witness=key)
