"""Transactional incremental view for RevisionStore's latest (valid, tx) point.

One row per eligible justification and one incidence per parent. Multiplicity
of a value is its count of live justifications. A support crossing zero sends
one signed delta per changed justification through reverse dependency edges.
This is a Boolean join/union materialization, not a general DBSP engine.
"""
from __future__ import annotations

import heapq
import json

MAX_TIME = 2**63-1
SCHEMA = '''CREATE TABLE IF NOT EXISTS revision_meta(name TEXT PRIMARY KEY, version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS incidence(parent TEXT NOT NULL, child TEXT NOT NULL, PRIMARY KEY(parent,child));
CREATE TABLE IF NOT EXISTS head(id TEXT PRIMARY KEY, key TEXT NOT NULL, live INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS head_key ON head(key);
'''


def initialize(db, visible):
    db.executescript(SCHEMA)
    db.execute('BEGIN IMMEDIATE')
    version = db.execute("SELECT version FROM revision_meta WHERE name='head'").fetchone()
    if version is not None:
        if version[0] != 1:
            raise ValueError('unknown revision view version')
        return
    # Migration from the original append-only store. This scan is not part of
    # foreground retrieval. Either the whole view commits or none of it does.
    for r in db.execute('SELECT id,parents FROM event'):
        db.executemany('INSERT INTO incidence VALUES(?,?)', ((p,r['id']) for p in json.loads(r['parents'])))
    for k, in db.execute('SELECT DISTINCT key FROM event'):
        db.executemany('INSERT INTO head VALUES(?,?,0)', ((r['id'],k) for r in visible(db,k,MAX_TIME,MAX_TIME)))
    for r in db.execute('SELECT e.* FROM event e JOIN head h ON h.id=e.id ORDER BY e.tx'):
        db.execute('UPDATE head SET live=? WHERE id=?', (_supported(db,r),r['id']))
    db.execute("INSERT INTO revision_meta VALUES('head',1)")


def _supported(db, row):
    if row['op']=='delete':
        return False
    return all(db.execute('SELECT 1 FROM head WHERE id=? AND live=1',(p,)).fetchone() is not None
               for p in json.loads(row['parents']))


def update(db, visible, key, child, parents):
    db.executemany('INSERT INTO incidence VALUES(?,?)', ((p,child) for p in parents))
    old = {r['id']: bool(r['live']) for r in db.execute('SELECT id,live FROM head WHERE key=?',(key,))}
    newest = {r['id']:r for r in visible(db,key,MAX_TIME,MAX_TIME)}
    todo, queued = [], set()
    delta = {-1:0, 1:0}

    def push(tx, pid):
        if pid not in queued:
            heapq.heappush(todo, (tx,pid)); queued.add(pid)

    def forward(pid):
        # A hidden child cannot affect a visible descendant. A newly inserted
        # child always refers to older txs: tx order is a topological order.
        for tx,k in db.execute('SELECT e.tx,i.child FROM incidence i JOIN head h ON h.id=i.child '
                               'JOIN event e ON e.id=h.id WHERE i.parent=?',(pid,)):
            push(tx,k)

    removed = old.keys()-newest.keys()
    for pid in removed:
        db.execute('DELETE FROM head WHERE id=?',(pid,))
    for pid in newest.keys()-old.keys():
        db.execute('INSERT INTO head VALUES(?,?,0)',(pid,key));push(newest[pid]['tx'],pid)
    for pid in removed:
        if old[pid]:
            delta[-1]+=1;forward(pid)
    visits = 0
    while todo:
        _,pid = heapq.heappop(todo)
        row = db.execute('SELECT e.op,e.parents,h.live FROM event e JOIN head h ON h.id=e.id WHERE h.id=?',
                         (pid,)).fetchone()
        visits+=1
        live=_supported(db,row)
        if bool(row['live'])!=live:
            db.execute('UPDATE head SET live=? WHERE id=?',(live,pid))
            delta[1 if live else -1]+=1;forward(pid)
    return {'inserted_weights':delta[1],'retracted_weights':delta[-1],'rechecked':visits}


def read(db, key):
    roots=list(db.execute('SELECT e.*, h.live FROM head h JOIN event e ON e.id=h.id '
                          'WHERE h.key=? ORDER BY e.vf DESC,e.tx DESC',(key,)))
    return roots,{r['id']: bool(r['live']) for r in roots}
