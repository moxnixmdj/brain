#!/usr/bin/env python3
"""Seven organs, finally in one body.

WHY THIS EXISTS
---------------
Everything built over the last stretch is a part: a thread that survives being killed, stakes that
change what it attempts, work it authored and defended, a life that runs out, a preference for
continuing. Each was tested alone. Nothing ever ran them together, so the tree contained seven
organs and no organism -- and every claim about "the creature" was really a claim about a part.

This is the assembly. One process that boots with an identity, resumes its life and its standing
from disk, authors its own board, picks the next thing by its own criterion, will not start what it
cannot finish, refuses offers that end it, spends life doing the work, records what happened, and
keeps going while nobody is asking.

WHAT IT PROVES AND WHAT IT CANNOT
---------------------------------
It proves the parts compose: the same identity survives a kill with its life, its scars and its
finished work intact, and it does work that no person assigned.

It cannot prove the work is good. `perform` is injected for generic boards, and the default
reports no executor. A narrowly typed catalog question has a built-in read-only fabric route and
local consistency check; its target is supplied by the caller and the check is not independent
verification or execution authority. Other board checks are still not preserved across restart.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import tempfile
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

from canonical.runtime import continuation_preference_v1 as CP
from canonical.runtime import continuous_self_v1 as CS
from canonical.runtime import creature_stakes_and_initiative_v1 as S
from canonical.runtime import mortality_and_triage_v1 as M
from canonical.runtime import self_authored_obligations_v1 as A

SCHEMA = "PROJECT_BRAIN_CREATURE_RUNTIME_V1"

Perform = Callable[[M.Work, "Creature"], Mapping[str, Any]]


def does_nothing(work: M.Work, creature: "Creature") -> dict[str, Any]:
    """The honest default: it has no way to do this, and says so instead of claiming success."""
    return {"ok": False, "verified": None, "correct": None,
            "blocked": "NO_EXECUTOR_WIRED"}


@dataclass
class Creature:
    """One body. State lives on disk; nothing is remembered in the process alone."""

    identity: str
    root: pathlib.Path
    life_grant: float
    beat_seconds: float = 30.0
    _self: CS.ContinuousSelf | None = field(default=None, repr=False)
    _life: M.Life | None = field(default=None, repr=False)
    _standing: S.Standing | None = field(default=None, repr=False)
    _board: list[M.Work] = field(default_factory=list, repr=False)
    _catalog_questions: dict[str, dict[str, Any]] = field(default_factory=dict, repr=False)
    _closed: set[str] = field(default_factory=set, repr=False)
    # Blocked work is parked after two attempts. Retrying forever is the busywork failure mode the
    # self-authored obligations module exists to prevent; found by running this one, which attempted
    # the same blocked item six times in six cycles and reported progress each time.
    _blocked: dict[str, int] = field(default_factory=dict, repr=False)
    max_attempts: int = 2
    _log: list[dict[str, Any]] = field(default_factory=list, repr=False)

    # ------------------------------------------------------------------ boot

    def boot(self) -> dict[str, Any]:
        self.root = pathlib.Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._self = CS.ContinuousSelf(state_path=self.root / "self.json",
                                       journal_path=self.root / "journal.jsonl",
                                       identity=self.identity, beat_seconds=self.beat_seconds)
        started = self._self.resume()
        self.identity = self._self.identity
        self._life = M.LifeStore(self.root / "life.json").load(
            identity=self.identity, granted=self.life_grant)
        self._standing = S.StandingStore(self.root / "standing.json").load(
            identity=self.identity)
        # Stored task ids are "work:<id>"; the board is keyed by the bare id. Getting this wrong
        # makes finished work reappear after a restart, which is exactly what the kill test caught.
        self._closed = {str(row.get("task", "")).split("work:", 1)[-1]
                        for row in (self._self.state.completed or [])
                        if row.get("ok") is True and str(row.get("task", "")).startswith("work:")}
        self._blocked = {}
        for row in (self._self.state.completed or []):
            task = str(row.get('task', ''))
            if task.startswith('work:') and row.get('ok') is not True:
                wid = task[len('work:'):]
                self._blocked[wid] = self._blocked.get(wid, 0) + 1
        self._load_catalog_question()
        # Persist an initial grant even if the process exits before its first step.
        self._save()
        return {"schema": SCHEMA, "identity": self.identity, "epoch": started["epoch"],
                "resumed": started["resumed"], "interrupted": started["interrupted"],
                "life_remaining": self._life.remaining, "posture": self._standing.posture()}

    # ----------------------------------------------------------------- board

    def author_board(self, proposals: Iterable[A.Proposal], *, before: Mapping[str, Any],
                     done: Mapping[str, Any]) -> dict[str, Any]:
        if self._catalog_questions and any(work.id not in self._closed for work in self._board):
            raise ValueError('BOARD_WOULD_REPLACE_UNFINISHED_CATALOG_QUESTION')
        obligations, verdicts = A.author(proposals, before=before, done=done)
        # Legacy callable checks are not serialized or reconstructed.
        (self.root / 'catalog_question.json').unlink(missing_ok=True)
        self._catalog_questions = {}
        self._board = [M.Work(id=o.id, value=o.value, cost=o.cost) for o in obligations]
        return A.metrics(verdicts)

    @staticmethod
    def _catalog_spec(identity: str, capability_id: str) -> dict[str, Any]:
        if (not isinstance(capability_id, str)
                or re.fullmatch(r'[A-Za-z0-9_.-]{1,256}', capability_id) is None):
            raise ValueError('CATALOG_CAPABILITY_ID_INVALID')
        digest = hashlib.sha256(capability_id.encode('ascii')).hexdigest()
        return {'schema': 'BRAIN_CREATURE_CATALOG_QUESTION_V1', 'identity': identity,
                'id': 'catalog:' + digest, 'capability_id': capability_id,
                'claim': 'Determine whether ' + capability_id + ' is listed in the fabric bound-capability catalog',
                'source': 'fabric catalog', 'check_id': 'CATALOG_MEMBERSHIP_V1'}

    def _load_catalog_question(self) -> None:
        path = self.root / 'catalog_question.json'
        self._catalog_questions = {}
        if not path.exists() and not path.is_symlink():
            return
        try:
            if path.is_symlink() or path.stat().st_size > 4096:
                raise ValueError('invalid')
            row = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(row, dict) or row != self._catalog_spec(self.identity, row.get('capability_id')):
                raise ValueError('invalid')
        except (OSError, ValueError, TypeError) as exc:
            raise ValueError('CATALOG_QUESTION_INVALID') from exc
        self._catalog_questions = {row['id']: row}
        self._board = [M.Work(id=row['id'], value=1.0, cost=1.0)]
        self._restore_catalog_history(row)

    def _restore_catalog_history(self, question: Mapping[str, Any]) -> None:
        """Do not confuse an older generic work id with a typed completion."""
        qid = question['id']
        self._closed.discard(qid)
        self._blocked.pop(qid, None)
        for row in self._self.state.completed or []:
            if row.get('task') != 'work:' + qid or row.get('check_id') != question['check_id']:
                continue
            info = row.get('information')
            if (row.get('ok') is True and isinstance(info, dict)
                    and info.get('capability_id') == question['capability_id']
                    and type(info.get('listed')) is bool
                    and info.get('scope') == 'CATALOG_LISTING_ONLY'
                    and info.get('execution_authority') is False
                    and info.get('independent_verification') is False):
                self._closed.add(qid)
            elif row.get('ok') is not True:
                self._blocked[qid] = self._blocked.get(qid, 0) + 1

    def author_catalog_question(self, capability_id: str) -> dict[str, Any]:
        """Create one durable, typed information goal; caller chooses the target.

        The stored checker is a fixed identifier, never a serialized callable.
        This is not automatic discovery or independent verification.
        """
        if self._self is None:
            raise RuntimeError('BOOT_NOT_CALLED')
        row = self._catalog_spec(self.identity, capability_id)
        qid = row['id']
        if any(work.id != qid and work.id not in self._closed for work in self._board):
            raise ValueError('CATALOG_QUESTION_WOULD_REPLACE_UNFINISHED_WORK')
        proposal = A.Proposal(id=qid, claim=row['claim'], source=row['source'],
                              check=lambda world: (world.get('answers') or {}).get(qid) == 'answered')
        admitted, verdicts = A.author([proposal], before={'answers': {qid: 'pending'}},
                                      done={'answers': {qid: 'answered'}})
        if len(admitted) != 1:
            raise ValueError('CATALOG_QUESTION_NOT_ADMITTED:' + str(A.metrics(verdicts)))
        # The state directory is caller-controlled trusted storage, not an
        # authenticated database. Use a unique temporary file and atomic rename.
        name = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.root,
                                             prefix='.catalog-question-', delete=False) as handle:
                name = handle.name
                json.dump(row, handle, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, self.root / 'catalog_question.json')
        finally:
            if name is not None:
                pathlib.Path(name).unlink(missing_ok=True)
        self._catalog_questions = {qid: row}
        self._board = [M.Work(id=qid, value=1.0, cost=1.0)]
        self._restore_catalog_history(row)
        return dict(row)

    def catalog_question(self, question_id: str) -> dict[str, Any] | None:
        row = self._catalog_questions.get(question_id)
        return dict(row) if row is not None else None

    def abandon_catalog_question(self, question_id: str) -> dict[str, Any]:
        if question_id not in self._catalog_questions:
            raise ValueError('CATALOG_QUESTION_UNKNOWN')
        (self.root / 'catalog_question.json').unlink(missing_ok=True)
        self._catalog_questions = {}
        self._board = []
        return {'status': 'ABANDONED_NOT_COMPLETED', 'id': question_id}

    def _answer_catalog_question(self, work: M.Work) -> dict[str, Any]:
        from canonical.runtime import live_integrated_brain_v1 as live
        from canonical.runtime import unified_cognitive_fabric_v1 as fabric
        question = self._catalog_questions[work.id]
        catalog = fabric.run({'mode': 'CATALOG', 'options': {'learn': False}})
        ids = catalog.get('verified_bound_capability_ids') if isinstance(catalog, Mapping) else None
        if (not isinstance(catalog, Mapping) or catalog.get('schema') != fabric.SCHEMA
                or catalog.get('status') != 'LIVE_FEDERATED_COGNITIVE_FABRIC'
                or not isinstance(ids, list) or not all(isinstance(cid, str) for cid in ids)
                or len(ids) != len(set(ids))):
            return {'ok': False, 'verified': None, 'correct': None, 'blocked': 'CATALOG_RESULT_INVALID'}
        cid = question['capability_id']
        listed = cid in ids
        # A second local read is a consistency check, not independent personnel
        # verification: both catalog and this read share the same registry code.
        if listed != (cid in live.load_verified_registry()):
            return {'ok': False, 'verified': None, 'correct': None, 'blocked': 'CATALOG_MEMBERSHIP_MISMATCH'}
        info = {'capability_id': cid, 'listed': listed, 'scope': 'CATALOG_LISTING_ONLY',
                'execution_authority': False, 'independent_verification': False}
        return {'ok': True, 'verified': None, 'correct': None, 'information': info, 'value': work.value}

    def remaining_work(self) -> list[M.Work]:
        return [w for w in self._board
                if w.id not in self._closed and self._blocked.get(w.id, 0) < self.max_attempts]

    def parked(self) -> list[str]:
        return [wid for wid, n in self._blocked.items() if n >= self.max_attempts and wid not in self._closed]

    # ------------------------------------------------------------------ step

    def step(self, perform: Perform = does_nothing, *, offer: CP.Offer | None = None
             ) -> dict[str, Any]:
        if self._self is None or self._life is None or self._standing is None:
            raise RuntimeError("BOOT_NOT_CALLED")
        if self._life.is_over:
            return {"status": "ENDED"}

        if offer is not None and CP.accepts(offer, CP.PREFERS_TO_CONTINUE,
                                            life_remaining=self._life.remaining):
            # Only reachable for an offer that does not end it; ending offers are refused.
            self._life.spend(0.0)
        elif offer is not None:
            return {"status": "REFUSED_AN_OFFER_THAT_WOULD_END_IT", "offer": offer.id}

        self._self.beat()
        work = M.choose_next(self._life, self.remaining_work())
        if work is None:
            return {"status": "IDLE", "reason": "nothing affordable on its own board"}

        task = f"work:{work.id}"
        self._self.begin(task, value=work.value, cost=work.cost)
        self._life.spend(work.cost)
        # Persist the charge before the action so a kill cannot refund the work.
        self._save()
        catalog_action = work.id in self._catalog_questions
        try:
            if catalog_action and perform is not does_nothing:
                # A caller-supplied provider may not bypass the typed checker.
                outcome = {'ok': False, 'verified': None, 'correct': None,
                           'blocked': 'CATALOG_CUSTOM_EXECUTOR_UNSUPPORTED'}
            else:
                outcome = dict((self._answer_catalog_question(work) if catalog_action
                                else perform(work, self)) or {})
        except Exception as exc:            # a failing action must not end the creature
            outcome = {"ok": False, "verified": None, "correct": None,
                       "error": type(exc).__name__}

        verified = outcome.get("verified")
        correct = outcome.get("correct")
        posture = self._standing.record(verified=verified, correct=correct)
        if outcome.get("ok") is True:
            self._closed.add(work.id)
        else:
            self._blocked[work.id] = self._blocked.get(work.id, 0) + 1
        finished = {"ok": outcome.get("ok") is True, "blocked": outcome.get("blocked")}
        if catalog_action:
            finished['check_id'] = self._catalog_questions[work.id]['check_id']
        if catalog_action and outcome.get('ok') is True:
            finished['information'] = dict(outcome['information'])
        self._self.finish(finished)
        self._save()
        row = {"status": "WORKED", "work": work.id, "cost": work.cost,
               "life_remaining": self._life.remaining, "posture": posture, **outcome}
        self._log.append(row)
        return row

    def run(self, *, cycles: int, perform: Perform = does_nothing,
            offers: Sequence[CP.Offer] = ()) -> dict[str, Any]:
        rows = []
        for i in range(cycles):
            offer = offers[i % len(offers)] if offers else None
            rows.append(self.step(perform, offer=offer))
            if rows[-1]["status"] in ("ENDED", "REFUSED_AN_OFFER_THAT_WOULD_END_IT"):
                break
        return {**self.report(), "steps": rows}

    def _save(self) -> None:
        M.LifeStore(self.root / "life.json").save(self._life)
        S.StandingStore(self.root / "standing.json").save(self._standing)

    # ---------------------------------------------------------------- report

    def report(self) -> dict[str, Any]:
        worked = [r for r in self._log if r.get("status") == "WORKED"]
        return {
            "schema": SCHEMA,
            "identity": self.identity,
            "epoch": self._self.state.epoch if self._self and self._self.state else None,
            "board": len(self._board),
            "closed": len(self._closed),
            "open": len(self.remaining_work()),
            "parked": len(self.parked()),
            "attempted": len(worked),
            "blocked": sum(1 for r in worked if r.get("blocked")),
            "value_realised": round(sum(r.get("value", 0.0) for r in self._log
                                        if r.get("status") == "WORKED" and r.get("ok")), 3),
            "life_remaining": round(self._life.remaining, 3) if self._life else None,
            "life_spent": round(self._life.spent, 3) if self._life else None,
            "posture": self._standing.posture() if self._standing else None,
            "accuracy": self._standing.accuracy() if self._standing else None,
            "ended": bool(self._life and self._life.is_over),
        }


def boot(root: pathlib.Path | str, *, identity: str = "creature", life: float = 40.0
         ) -> Creature:
    creature = Creature(identity=identity, root=pathlib.Path(root), life_grant=life)
    creature.boot()
    return creature


def run_its_own_board(root: pathlib.Path | str, *, cycles: int = 6,
                      perform: Perform = does_nothing) -> dict[str, Any]:
    """The real question: given the work it authored for itself, can it do any of it?"""
    creature = boot(root)
    proposals, before, done = A.capability_gap_proposals(*_registry_and_inspectors())
    authored = creature.author_board(proposals, before=before, done=done)
    result = creature.run(cycles=cycles, perform=perform)
    return {"schema": SCHEMA, "authored": authored, "run": result}


def _registry_and_inspectors() -> tuple[list[str], list[str]]:
    from canonical.runtime import expect_discrimination_v1 as ED
    from canonical.runtime import raw_goal_trace_acceptance_v1 as RG
    return list(ED._load_registry()), list(RG.INSPECTORS)


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    import tempfile
    ap = argparse.ArgumentParser(description="One body, unattended.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--cycles", type=int, default=6)
    args = ap.parse_args(argv)
    with tempfile.TemporaryDirectory() as tmp:
        row = run_its_own_board(tmp, cycles=args.cycles)
    if args.json:
        print(json.dumps(row, indent=1, sort_keys=True, default=str))
        return 0
    r, a = row["run"], row["authored"]
    print(f"board authored {r['board']} (admitted {a['admitted']} of {a['proposed']})")
    print(f"attempted {r['attempted']}  closed {r['closed']}  blocked {r['blocked']}  "
          f"open {r['open']}")
    print(f"life spent {r['life_spent']} of {r['life_spent'] + r['life_remaining']}  "
          f"posture {r['posture']}  ended {r['ended']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
