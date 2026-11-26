"""External, bitemporal memory for version-bound observations and hypotheses.

A SET (or DELETE) starts a new functional version. DERIVE adds an alternative
justification, a conjunction of *particular event ids*, not strings that could
become true again later. Retraction of a root therefore also invalidates its
consequences; surviving alternatives still count. The valid-time ordering is
(valid_from, tx), tx being local commit order. A correction received late does
not rewrite what we knew at an earlier tx. No wall-clock ordering assumption.

The view is evaluated on demand using the key index and reachable support DAG,
not a claim of O(1) updates + O(1) queries, full DBSP, or natural-language QA.
Witnesses are attributable observations, not signatures of an independent
judge. Deletion here is logical retraction, NOT erasure of the audit history.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping, Sequence


def _encode(x: Any) -> str:
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def _time(value: int) -> int:
    if type(value) is not int or not 0 <= value < 2**63:
        raise ValueError('expected a nonnegative integer time')
    return value


class RevisionStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS event(
                tx INTEGER PRIMARY KEY, id TEXT NOT NULL UNIQUE, key TEXT NOT NULL,
                vf INTEGER NOT NULL, op TEXT NOT NULL, value TEXT NOT NULL,
                parents TEXT NOT NULL, source TEXT NOT NULL, witness TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS visible_key ON event(key, vf DESC, tx DESC);''')

    def _connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _visible(db, key, valid, tx):
        # Stop at the first explicit version boundary; no fallback to an older
        # value if the new one is unsupported. Also bounds body retrieval.
        for r in db.execute('SELECT * FROM event WHERE key=? AND vf<=? AND tx<=? '
                            'ORDER BY vf DESC, tx DESC', (key, valid, tx)):
            yield r
            if r['op'] != 'derive':
                break

    @classmethod
    def _view(cls, db, key: str, valid: int, tx: int):
        eligible: dict[str, dict] = {}
        live: dict[str, bool] = {}

        def versions(k):
            if k not in eligible:
                eligible[k] = {r['id']: r for r in cls._visible(db, k, valid, tx)}
            return eligible[k]

        # Evaluate only the ancestor cone, in transaction order (parents were
        # required to exist before their child). No recursion depth limit.
        roots = list(versions(key).values())
        rows, todo = {}, list(roots)
        while todo:
            r = todo.pop()
            if r['id'] in rows:
                continue
            rows[r['id']] = r
            if r['id'] not in versions(r['key']):
                continue
            for pid in json.loads(r['parents']):
                if pid not in rows:
                    parent = db.execute('SELECT * FROM event WHERE id=?', (pid,)).fetchone()
                    if parent is not None:
                        todo.append(parent)
        for r in sorted(rows.values(), key=lambda row: row['tx']):
            live[r['id']] = (r['id'] in versions(r['key']) and r['op'] != 'delete'
                             and all(live.get(p, False) for p in json.loads(r['parents'])))
        return roots, live

    def query(self, key: str, *, valid_at: int = 2**63-1, known_at: int = 2**63-1) -> dict:
        with closing(self._connect()) as db:
            db.execute('BEGIN')  # one consistent read even if another writer commits
            roots, live = self._view(db, key, _time(valid_at), _time(known_at))
        proofs = [r for r in roots if live[r['id']]]
        values = sorted(set(r['value'] for r in proofs))
        status = ('SUPPORTED' if len(values) == 1 else 'UNKNOWN_CONFLICT' if values
                  else 'UNKNOWN_UNSEEN' if not roots else 'DELETED' if roots[0]['op'] == 'delete'
                  else 'UNKNOWN_LOST_SUPPORT')
        return {'status': status, 'value': json.loads(values[0]) if status == 'SUPPORTED' else None,
                'support': [{'id': r['id'], 'parents': json.loads(r['parents']), 'tx': r['tx'],
                             'valid_from': r['vf'], 'source': r['source']} for r in proofs],
                'invalidated': [r['id'] for r in roots if not live[r['id']]],
                'events_considered': len(live)}

    def append(self, op: str, key: str, *, valid_from: int, source: str, witness: str,
               value: Any = None, parents: Sequence[str] = ()) -> dict:
        if op not in ('set', 'delete', 'derive') or not all(
                isinstance(x, str) and x.strip() for x in (key, source, witness)):
            raise ValueError('operation, key, source and concrete witness required')
        if isinstance(parents, (str, bytes)) or not all(isinstance(p, str) and p for p in parents):
            raise ValueError('parents must be event ids')
        parents = sorted(set(parents))
        if (op == 'derive') != bool(parents) or (op == 'delete' and value is not None):
            raise ValueError('only derivations have parents; deletion carries no value')
        valid_from = _time(valid_from)
        pid = hashlib.sha256(_encode([op,key,valid_from,source,witness,value,parents]).encode()).hexdigest()
        with closing(self._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT tx FROM event WHERE id=?', (pid,)).fetchone()
            if old is not None:
                return {'id': pid, 'tx': old['tx'], 'inserted': False}
            for p in parents:
                parent = db.execute('SELECT key FROM event WHERE id=?', (p,)).fetchone()
                if parent is None or not self._view(db, parent['key'], valid_from, 2**63-1)[1].get(p):
                    raise ValueError('missing or stale support at write: '+p)
            cursor = db.execute('INSERT INTO event(id,key,vf,op,value,parents,source,witness) '
                                'VALUES(?,?,?,?,?,?,?,?)', (pid,key,valid_from,op,_encode(value),
                                                            _encode(parents),source,witness))
            return {'id': pid, 'tx': cursor.lastrowid, 'inserted': True}

    def apply(self, operation: str, payload: Mapping[str, Any]) -> dict:
        if operation == 'query':
            return self.query(**payload)
        return self.append(operation, **payload)
