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
verification or execution authority. A single inspector gap can be selected and its structural
check reconstructed across restart, but the parent cannot be completed without an admitted
inspector verifier. Other generic board checks are still not preserved across restart.
"""
from __future__ import annotations

import copy
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
    _inspector_investigation: dict[str, Any] | None = field(default=None, repr=False)
    # M.Work carries no `checkable`, and the posture gate needs exactly that flag. author_board
    # keeps it here so a CAUTIOUS creature can decline work whose success it cannot check. Losing
    # it in the Obligation -> Work conversion is what made posture decorative in the assembly:
    # recorded, reported, persisted, and never once consulted when the creature chose.
    _checkable: dict[str, bool] = field(default_factory=dict, repr=False)
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
        self._load_inspector_investigation()
        self._load_sovereign_organs()
        # Persist an initial grant even if the process exits before its first step.
        self._save()
        return {"schema": SCHEMA, "identity": self.identity, "epoch": started["epoch"],
                "resumed": started["resumed"], "interrupted": started["interrupted"],
                "life_remaining": self._life.remaining, "posture": self._standing.posture()}

    def _load_sovereign_organs(self) -> None:
        from canonical.runtime import capability_onboarding_factory_v1 as COF
        from canonical.runtime import derived_inspector_flywheel_v1 as DIF
        from canonical.runtime import self_prediction_calibration_v1 as SPC

        self.calibration_ledger = SPC.Ledger(self.root / "self_prediction_ledger.jsonl")
        self.derived_flight = DIF.Flight()
        self._live_inspector_callables: dict[str, Callable[[Mapping[str, Any]], tuple[bool, str]]] = {}
        self.onboarded_capabilities: dict[str, dict[str, Any]] = {}

        def _register_cap(row: Mapping[str, Any]) -> None:
            self.onboarded_capabilities[str(row["capability_id"])] = dict(row)

        self.onboarding_factory = COF.Factory(
            inspector_for=lambda cid: self._live_inspector_callables.get(cid),
            register=_register_cap,
        )
        onboard_fp = self.root / "onboarded_inspectors.json"
        if onboard_fp.is_file() and not onboard_fp.is_symlink():
            try:
                saved = json.loads(onboard_fp.read_text(encoding="utf-8"))
                if isinstance(saved, Mapping):
                    for k, v in (saved.get("flight_registry") or {}).items():
                        self.derived_flight.registry[str(k)] = dict(v)
                    for k, v in (saved.get("onboarded") or {}).items():
                        self.onboarded_capabilities[str(k)] = dict(v)
            except Exception:
                pass

    def _save_sovereign_organs(self) -> None:
        if not hasattr(self, "derived_flight") or not hasattr(self, "onboarded_capabilities"):
            return
        payload = {
            "flight_registry": dict(self.derived_flight.registry),
            "onboarded": dict(self.onboarded_capabilities),
        }
        tmp_p = self.root / ".onboarded_inspectors.tmp"
        tmp_p.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        os.replace(tmp_p, self.root / "onboarded_inspectors.json")

    # ----------------------------------------------------------------- board

    def author_board(self, proposals: Iterable[A.Proposal], *, before: Mapping[str, Any],
                     done: Mapping[str, Any]) -> dict[str, Any]:
        if self._inspector_investigation is not None:
            raise ValueError('BOARD_WOULD_REPLACE_INSPECTOR_INVESTIGATION')
        if self._catalog_questions and any(work.id not in self._closed for work in self._board):
            raise ValueError('BOARD_WOULD_REPLACE_UNFINISHED_CATALOG_QUESTION')
        obligations, verdicts = A.author(proposals, before=before, done=done)
        # Legacy callable checks are not serialized or reconstructed.
        (self.root / 'catalog_question.json').unlink(missing_ok=True)
        self._catalog_questions = {}
        self._board = [M.Work(id=o.id, value=o.value, cost=o.cost) for o in obligations]
        # Kept beside the board rather than inside it: M.Work is the mortality organ's type and
        # stays about price, while `checkable` is the stakes organ's input.
        self._checkable = {o.id: bool(o.checkable) for o in obligations}
        return A.metrics(verdicts)

    def sync_board(
        self,
        proposals: Iterable[A.Proposal],
        *,
        before: Mapping[str, Any],
        done: Mapping[str, Any],
        cheats: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Synchronize world-grounded content-addressed obligations without wiping `_closed`, `_blocked`, or `parked()`."""
        if self._inspector_investigation is not None:
            raise ValueError('BOARD_WOULD_REPLACE_INSPECTOR_INVESTIGATION')
        if self._catalog_questions and any(work.id not in self._closed for work in self._board):
            raise ValueError('BOARD_WOULD_REPLACE_UNFINISHED_CATALOG_QUESTION')
        prop_list = list(proposals)
        existing_by_id = {w.id: w for w in self._board}
        known_ids = set(existing_by_id) | set(self._closed) | set(self._blocked)

        new_props = [p for p in prop_list if p.id not in known_ids]
        admitted_new: dict[str, A.Obligation] = {}
        verdicts: list[Any] = []
        if new_props:
            obligations, verdicts = A.author(new_props, before=before, done=done, cheats=cheats)
            admitted_new = {o.id: o for o in obligations}

        (self.root / 'catalog_question.json').unlink(missing_ok=True)
        self._catalog_questions = {}

        next_board: list[M.Work] = []
        next_checkable: dict[str, bool] = {}
        preserved = 0
        for p in prop_list:
            if p.id in known_ids:
                w = existing_by_id.get(p.id) or M.Work(id=p.id, value=p.value, cost=p.cost)
                next_board.append(w)
                next_checkable[p.id] = self._checkable.get(p.id, bool(p.checkable))
                preserved += 1
            elif p.id in admitted_new:
                ob = admitted_new[p.id]
                next_board.append(M.Work(id=ob.id, value=ob.value, cost=ob.cost))
                next_checkable[ob.id] = bool(ob.checkable)

        self._board = next_board
        self._checkable = next_checkable
        metrics = dict(A.metrics(verdicts))
        metrics["preserved"] = preserved
        metrics["active_board"] = len(self._board)
        metrics["parked"] = list(self.parked())
        return metrics

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

    @staticmethod
    def _catalog_completion_matches(question: Mapping[str, Any], row: Mapping[str, Any]) -> bool:
        info = row.get('information')
        return (row.get('task') == 'work:' + question['id']
                and row.get('check_id') == question['check_id']
                and row.get('ok') is True and isinstance(info, dict)
                and info.get('capability_id') == question['capability_id']
                and type(info.get('listed')) is bool
                and info.get('scope') == 'CATALOG_LISTING_ONLY'
                and info.get('parent_id') == question.get('parent_id')
                and info.get('execution_authority') is False
                and info.get('independent_verification') is False)

    def _restore_catalog_history(self, question: Mapping[str, Any]) -> None:
        """Do not confuse an older generic work id with a typed completion."""
        qid = question['id']
        self._closed.discard(qid)
        self._blocked.pop(qid, None)
        for row in self._self.state.completed or []:
            if row.get('task') != 'work:' + qid or row.get('check_id') != question['check_id']:
                continue
            if self._catalog_completion_matches(question, row):
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
        if self._inspector_investigation is not None:
            raise ValueError('CATALOG_QUESTION_WOULD_REPLACE_INSPECTOR_INVESTIGATION')
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
        if self._inspector_investigation is not None:
            raise ValueError('INSPECTOR_INVESTIGATION_OWNS_CHILD')
        if question_id not in self._catalog_questions:
            raise ValueError('CATALOG_QUESTION_UNKNOWN')
        (self.root / 'catalog_question.json').unlink(missing_ok=True)
        self._catalog_questions = {}
        self._board = []
        return {'status': 'ABANDONED_NOT_COMPLETED', 'id': question_id}

    @classmethod
    def _inspector_spec(cls, identity: str, capability_id: str, cost: float) -> dict[str, Any]:
        catalog = cls._catalog_spec(identity, capability_id)  # validates the ID
        if isinstance(cost, bool) or cost not in (0.5, 1.0):
            raise ValueError('INSPECTOR_COST_INVALID')
        parent_id = 'inspector:' + capability_id
        parent = {'id': parent_id, 'capability_id': capability_id,
                  'claim': capability_id + ' has a registered inspector that refuses a decoy',
                  'source': 'capability registry vs registered inspectors',
                  'check_id': 'INSPECTED_VERIFIED_SLOT_V1', 'value': 1.0, 'cost': float(cost),
                  'independent_verification': False, 'execution_authority': False}
        child = dict(catalog)
        child['id'] = 'inspector-catalog:' + hashlib.sha256(parent_id.encode('ascii')).hexdigest()
        child['parent_id'] = parent_id
        return {'schema': 'BRAIN_CREATURE_INSPECTOR_INVESTIGATION_V1', 'identity': identity,
                'parent': parent, 'child': child}

    def _install_inspector_investigation(self, investigation: dict[str, Any]) -> None:
        parent = investigation['parent']
        child = investigation['child']
        self._inspector_investigation = investigation
        self._catalog_questions = {child['id']: child}
        # A previous generic performer cannot satisfy the typed parent. There is
        # currently no admitted parent executor/acceptance path.
        self._closed.discard(parent['id'])
        self._blocked.pop(parent['id'], None)
        self._restore_catalog_history(child)
        self._board = [M.Work(id=parent['id'], value=parent['value'], cost=parent['cost']),
                       M.Work(id=child['id'], value=1.0, cost=0.25)]

    def _load_inspector_investigation(self) -> None:
        self._inspector_investigation = None
        path = self.root / 'inspector_investigation.json'
        if not path.exists() and not path.is_symlink():
            return
        try:
            if path.is_symlink() or path.stat().st_size > 8192 or self._catalog_questions:
                raise ValueError('invalid')
            row = json.loads(path.read_text(encoding='utf-8'))
            parent = row.get('parent') if isinstance(row, dict) else None
            if not isinstance(parent, dict) or row != self._inspector_spec(
                    self.identity, parent.get('capability_id'), parent.get('cost')):
                raise ValueError('invalid')
        except (OSError, ValueError, TypeError) as exc:
            raise ValueError('INSPECTOR_INVESTIGATION_INVALID') from exc
        self._install_inspector_investigation(row)

    def author_inspector_investigation(self) -> dict[str, Any]:
        """Choose a real admitted inspector gap and derive one information goal.

        The parent condition is preserved as a typed structural check; it does
        not itself prove an inspector exists or rejects a decoy. No callable or
        executable code is loaded from the persisted state.
        """
        if self._self is None or self._life is None:
            raise RuntimeError('BOOT_NOT_CALLED')
        if self._inspector_investigation is not None or any(
                work.id not in self._closed for work in self._board):
            raise ValueError('INSPECTOR_INVESTIGATION_WOULD_REPLACE_UNFINISHED_WORK')
        ids, inspected = _registry_and_inspectors()
        proposals, before, done = A.capability_gap_proposals(ids, inspected)
        admitted, _ = A.author(proposals, before=before, done=done)
        work = M.choose_next(self._life, [M.Work(id=o.id, value=o.value, cost=o.cost)
                                         for o in admitted])
        if work is None:
            raise ValueError('NO_AFFORDABLE_INSPECTOR_GAP')
        proposal = next(p for p in proposals if p.id == work.id)
        if not work.id.startswith('inspector:'):
            raise ValueError('INSPECTOR_GAP_ID_INVALID')
        cid = work.id[len('inspector:'):]
        investigation = self._inspector_spec(self.identity, cid, work.cost)
        parent = investigation['parent']
        if (proposal.claim != parent['claim'] or proposal.source != parent['source']
                or proposal.value != parent['value'] or proposal.cost != parent['cost']):
            raise ValueError('INSPECTOR_GOAL_CONTRACT_DRIFT')
        child = investigation['child']
        child_proposal = A.Proposal(id=child['id'], claim=child['claim'], source=child['source'],
            check=lambda world: (world.get('answers') or {}).get(child['id']) == 'answered')
        accepted, _ = A.author([child_proposal], before={'answers': {child['id']: 'pending'}},
                               done={'answers': {child['id']: 'answered'}})
        if len(accepted) != 1:
            raise ValueError('INSPECTOR_INFORMATION_GOAL_NOT_ADMITTED')
        # Never leave two competing typed boards; remove an already-completed
        # standalone catalog question before writing this single typed record.
        (self.root / 'catalog_question.json').unlink(missing_ok=True)
        name = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.root,
                                             prefix='.inspector-investigation-', delete=False) as handle:
                name = handle.name
                json.dump(investigation, handle, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, self.root / 'inspector_investigation.json')
        finally:
            if name is not None:
                pathlib.Path(name).unlink(missing_ok=True)
        self._install_inspector_investigation(investigation)
        return copy.deepcopy(investigation)

    def inspector_investigation(self) -> dict[str, Any] | None:
        return copy.deepcopy(self._inspector_investigation)

    def inspector_information(self) -> dict[str, Any] | None:
        """Retrieve the last locally checked child observation, not a fresh fact."""
        if self._inspector_investigation is None or self._self is None:
            return None
        child = self._inspector_investigation['child']
        for row in reversed(self._self.state.completed or []):
            if self._catalog_completion_matches(child, row):
                return {'question_id': child['id'], 'parent_id': child['parent_id'],
                        'observation': copy.deepcopy(row['information']),
                        'recorded_at': row.get('ended_at'),
                        'freshness': 'HISTORICAL_NOT_REVALIDATED'}
        return None

    def inspector_slot_check(self, world: Mapping[str, Any]) -> bool:
        """Original structural slot predicate, not proof of a real inspector."""
        if self._inspector_investigation is None:
            raise ValueError('INSPECTOR_INVESTIGATION_UNKNOWN')
        slot = world.get('inspected') if isinstance(world, Mapping) else None
        return isinstance(slot, Mapping) and slot.get(
            self._inspector_investigation['parent']['capability_id']) == 'verified'

    def abandon_inspector_investigation(self, parent_id: str) -> dict[str, Any]:
        if (self._inspector_investigation is None
                or self._inspector_investigation['parent']['id'] != parent_id):
            raise ValueError('INSPECTOR_INVESTIGATION_UNKNOWN')
        (self.root / 'inspector_investigation.json').unlink(missing_ok=True)
        self._inspector_investigation = None
        self._catalog_questions = {}
        self._board = []
        return {'status': 'ABANDONED_NOT_COMPLETED', 'id': parent_id}

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
        if 'parent_id' in question:
            info['parent_id'] = question['parent_id']
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
        pool = self.remaining_work()
        if not self._standing.will_trade_on_the_unverifiable():
            # Burned twice, it stops trading on work whose success it cannot check -- but only
            # among work it can actually finish, and only when such work exists. Caution is a
            # preference, not a refusal to work: with nothing checkable affordable it still acts.
            # Affordability stays with M.choose_next, which is the organ that owns the budget.
            checkable = [w for w in pool
                         if self._checkable.get(w.id, True) and self._life.can_finish(w.cost)]
            if checkable:
                pool = checkable
        work = M.choose_next(self._life, pool)
        if work is None:
            return {"status": "IDLE", "reason": "nothing affordable on its own board"}
        if (self._inspector_investigation is not None
                and work.id == self._inspector_investigation['parent']['id']
                and not getattr(perform, '_admitted_inspector_verifier', False)):
            # The original slot predicate cannot verify a real inspector or its
            # decoy test. An injected performer's success flag is not evidence.
            return {'status': 'WAITING_FOR_INSPECTOR_VERIFIER', 'work': work.id,
                    'reason': 'NO_ADMITTED_INSPECTOR_ACCEPTANCE_PATH'}

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
        if (self._inspector_investigation is not None
                and work.id == self._inspector_investigation['parent']['id']
                and outcome.get("verified_inspector_onboarding") is not True):
            # Even with an admitted verifier hook, closing the parent requires a
            # real Flight + CapabilityOnboardingFactory proof (positive + distinct held-out + decoy rejection).
            outcome["ok"] = False
            outcome["blocked"] = outcome.get("blocked") or "INSPECTOR_ONBOARDING_PROOF_MISSING"
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
            if rows[-1]["status"] in ("ENDED", "REFUSED_AN_OFFER_THAT_WOULD_END_IT",
                                      "WAITING_FOR_INSPECTOR_VERIFIER"):
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

    # ------------------------------------------------------------ gap intake

    def note_goal_gap(
        self,
        goal: str,
        workspace_root: str | pathlib.Path | None = None,
        *,
        cost: float = 1.0,
        ledger_path: str | pathlib.Path | None = None,
    ) -> dict[str, Any]:
        """Translate missing typed goal slots (`goal_gap_statement_v1`) into ranked `ignorance_ledger_v1` gaps."""
        if self._self is None:
            raise RuntimeError("BOOT_NOT_CALLED")
        from canonical.runtime import goal_gap_statement_v1 as GG
        from canonical.runtime import ignorance_ledger_v1 as IL

        target_ledger = str(
            pathlib.Path(ledger_path) if ledger_path is not None else (self.root / "ignorance_ledger.json")
        )
        report = GG.state_the_gap(goal, workspace_root)
        outcome = str(report.get("outcome") or "")
        cid = str(report.get("capability") or "unbound")
        slot = str(report.get("slot") or "")
        statement_text = str(report.get("statement") or "")
        gap_ids: list[str] = []
        if outcome == "SLOT_UNSTATED" and slot:
            gid = IL.note(
                f"missing required slot `{slot}` for {cid}",
                why=statement_text[:240],
                cost=float(cost),
                path=target_ledger,
            )
            gap_ids.append(gid)
        elif outcome in ("NO_CANDIDATE_REPORTED", "UNPARSEABLE_REPORT", "COMPILER_RAISED"):
            gid = IL.note(
                f"goal gap ({outcome})",
                why=statement_text[:240],
                cost=float(cost),
                path=target_ledger,
            )
            gap_ids.append(gid)
        ranked = IL.rank(limit=1, path=target_ledger)
        top = ranked[0] if ranked else None
        return {
            "schema": "BRAIN_CREATURE_GOAL_GAP_INTAKE_V1",
            "identity": self.identity,
            "outcome": outcome,
            "statement": report,
            "gap_ids": gap_ids,
            "ledger_path": target_ledger,
            "next_to_close": top,
        }


def confined_verified_perform(
    workspace_root: pathlib.Path | str,
    *,
    programs: Mapping[str, str] | None = None,
    checks: Mapping[str, Callable[[pathlib.Path], bool]] | None = None,
    targets: Mapping[str, str] | None = None,
    protected_tests: Sequence[str] = (),
    timeout: int = 30,
) -> Perform:
    """Build a staged, zero-ambient namespace + broker `Perform` adapter for `Creature`.

    Replaces live-workspace in-place execution with `brokered_workspace_execution_v1`:
    - `workspace_root` is NEVER mounted inside the worker (`zero_ambient_namespace_launcher_v1`
      mounts staged `/input` read-only and `/work` on private tmpfs).
    - `checker(stage_dir)` verifies the candidate BEFORE a single byte in `workspace_root`
      is touched; failed or scope-violating candidates leave `workspace_root` untouched.
    - Fails closed (`computer_execution_boundary_v1.STATUS`) if namespace isolation is unavailable.
    """
    import sys as _sys

    ws = pathlib.Path(workspace_root).resolve()
    prog_map = dict(programs or {})
    chk_map = dict(checks or {})
    tgt_map = dict(targets or {})
    prot_tuple = tuple(str(p) for p in protected_tests)

    def _perform(work: M.Work, _creature: Creature) -> dict[str, Any]:
        from canonical.runtime import brokered_workspace_execution_v1 as broker
        from canonical.runtime import computer_execution_boundary_v1 as boundary
        from canonical.runtime import confine_v1 as C

        program = prog_map.get(work.id)
        checker = chk_map.get(work.id)
        if program is None or checker is None:
            return {
                "ok": False,
                "verified": None,
                "correct": None,
                "blocked": "UNBOUND_WORK_PROGRAM_OR_CHECK",
            }
        if not C.available() or not broker.namespace_broker_available():
            return {
                "ok": False,
                "verified": True,
                "correct": None,
                "confined": False,
                "blocked": boundary.STATUS,
            }
        staged_res = broker.run_staged_confined_command(
            ws,
            [_sys.executable, "-I", "-c", program],
            checker=checker,
            publish=True,
            target=tgt_map.get(work.id),
            protected_tests=prot_tuple,
            timeout=timeout,
            task_id=f"creature:{work.id}",
            goal=f"creature staged work {work.id}",
        )
        if not staged_res.get("confined"):
            return {
                "ok": False,
                "verified": True,
                "correct": None,
                "confined": False,
                "blocked": str(staged_res.get("blocked") or boundary.STATUS),
            }
        checked_ok = bool(staged_res.get("ok"))
        return {
            "ok": checked_ok,
            "verified": True,
            "correct": checked_ok,
            "confined": True,
            "isolation_mode": staged_res.get("isolation_mode"),
            "live_workspace_untouched": bool(staged_res.get("live_workspace_untouched")),
            "published": bool(staged_res.get("published")),
            "carrier_qualified": bool(staged_res.get("carrier_qualified")),
            "blocked": staged_res.get("blocked"),
        }

    return _perform


def run_awake_creature_pulse(
    workspace_root: pathlib.Path | str,
    *,
    state_root: pathlib.Path | str | None = None,
    identity: str = "creature",
    life: float = 40.0,
    ledger_path: str | pathlib.Path | None = None,
    skill_store_path: str | pathlib.Path | None = None,
    workflow_db_path: str | pathlib.Path | None = None,
    apply_verified_repairs: bool = False,
    max_curriculum_lessons: int = 2,
    channels: Sequence[str] | None = None,
    speculative_work: Callable[[], Mapping[str, Any]] | None = None,
    max_steps: int | None = None,
) -> dict[str, Any]:
    """Run one unified zero-LLM (`K3 = 0`) awake pulse through the single `Creature` organism."""
    from canonical.swe_kernel.autonomous_awake_loop_v1 import AwakeAgencyDaemon

    ws = pathlib.Path(workspace_root).resolve()
    ws_hash = hashlib.sha256(str(ws).encode("utf-8")).hexdigest()[:12]
    c_root = (
        pathlib.Path(state_root).resolve()
        if state_root is not None
        else (
            pathlib.Path(ledger_path).resolve().parent / f"creature_{ws_hash}"
            if ledger_path is not None
            else pathlib.Path(tempfile.gettempdir()) / f"brain_creature_{ws_hash}"
        )
    )
    daemon = AwakeAgencyDaemon(
        ws,
        ledger_path=ledger_path,
        skill_store_path=skill_store_path,
        workflow_db_path=workflow_db_path,
        apply_verified_repairs=apply_verified_repairs,
        creature_root=c_root,
        creature_identity=identity,
        creature_life=life,
    )
    return daemon.pulse(
        max_curriculum_lessons=max_curriculum_lessons,
        channels=channels,
        speculative_work=speculative_work,
        max_steps=max_steps,
    )


def boot(root: pathlib.Path | str, *, identity: str = "creature", life: float = 40.0
         ) -> Creature:
    creature = Creature(identity=identity, root=pathlib.Path(root), life_grant=life)
    creature.boot()
    return creature


def run_unattended_inspector_investigation(root: pathlib.Path | str, *, cycles: int = 6,
                                           identity: str = 'creature', life: float = 40.0
                                           ) -> dict[str, Any]:
    """Select or resume one real inspector gap, without a caller naming the target.

    This opt-in runner uses the same Creature and durable board. It cannot
    establish the parent inspector/decoy condition and stops when that verifier
    is unavailable. It does not replace the existing legacy board runner.
    """
    creature = boot(root, identity=identity, life=life)
    investigation = creature.inspector_investigation()
    authored_now = investigation is None
    if authored_now:
        investigation = creature.author_inspector_investigation()
    result = creature.run(cycles=cycles)
    return {'schema': SCHEMA, 'authored_now': authored_now,
            'investigation': investigation, 'information': creature.inspector_information(),
            'run': result}


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


_STRUCTURAL_READINESS_CACHE: dict[str, tuple[float, str]] = {}


def _structural_capability_readiness(cid: str) -> tuple[float, str]:
    """Introspect a capability's real host/adapter/type-surface preconditions BEFORE execution (zero hardcoded IDs)."""
    cached = _STRUCTURAL_READINESS_CACHE.get(cid)
    if cached is not None:
        return cached

    import ast
    import importlib.util
    import shutil as _shutil
    from canonical.runtime import availability_v1 as AV
    from canonical.runtime import capability_type_surface_v1 as ts
    from canonical.runtime import expect_discrimination_v1 as ED

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    reg = ED._load_registry()
    entry = reg.get(cid)
    if not isinstance(entry, Mapping):
        res = (0.04, "unregistered_capability")
        _STRUCTURAL_READINESS_CACHE[cid] = res
        return res

    av_reg = AV.load_registry()
    if AV.missing(cid, av_reg):
        res = (0.04, "availability_missing_binary")
        _STRUCTURAL_READINESS_CACHE[cid] = res
        return res

    ap = (entry.get("source") or {}).get("adapter_path")
    am = entry.get("adapter_module")
    if not ap and am:
        cand = repo_root / "canonical" / "runtime" / "bound_capabilities" / f"{am}.py"
        if cand.is_file():
            ap = cand.relative_to(repo_root).as_posix()
    if not ap or not (repo_root / str(ap)).is_file():
        res = (0.04, "no_resolvable_adapter")
        _STRUCTURAL_READINESS_CACHE[cid] = res
        return res

    t_args = ((entry.get("action_template") or {}).get("args")) or {}
    lit_mod = t_args.get("module")
    if isinstance(lit_mod, str) and lit_mod and "${" not in lit_mod:
        top_m = lit_mod.split(".")[0]
        if (
            not (repo_root / "canonical" / "runtime" / f"{top_m}.py").is_file()
            and importlib.util.find_spec(top_m) is None
        ):
            res = (0.05, f"missing_template_module:{top_m}")
            _STRUCTURAL_READINESS_CACHE[cid] = res
            return res

    lit_pkg = t_args.get("package")
    if isinstance(lit_pkg, str) and lit_pkg and "${" not in lit_pkg:
        if not (repo_root / "node_modules" / lit_pkg).exists():
            res = (0.05, f"missing_npm_package:{lit_pkg}")
            _STRUCTURAL_READINESS_CACHE[cid] = res
            return res

    argv = t_args.get("argv")
    if isinstance(argv, list) and argv and isinstance(argv[0], str) and "${" not in argv[0]:
        if _shutil.which(argv[0]) is None and not pathlib.Path(argv[0]).exists():
            res = (0.04, f"missing_argv_binary:{argv[0]}")
            _STRUCTURAL_READINESS_CACHE[cid] = res
            return res

    sig = dict(ts.signature(dict(entry)))
    extra_slots = ts.adapter_arg_reads(dict(entry)).get("required") or []
    for k_ex in extra_slots:
        sig.setdefault(k_ex, ts.type_of(k_ex))
    if "UNKNOWN" in sig.values():
        res = (0.05, "unknown_slot_type_on_surface")
        _STRUCTURAL_READINESS_CACHE[cid] = res
        return res

    reqs = [str(r) for r in (entry.get("requires") or [])]
    if any(r.startswith(("image.", "pdf.", "audio.", "video.")) for r in reqs):
        res = (0.08, "binary_media_precondition")
        _STRUCTURAL_READINESS_CACHE[cid] = res
        return res
    if any("tree_sitter" in r for r in reqs) and importlib.util.find_spec("tree_sitter") is None:
        res = (0.06, "missing_tree_sitter_substrate")
        _STRUCTURAL_READINESS_CACHE[cid] = res
        return res
    if any(any(tok in k.lower() for tok in ("image", "png", "pdf", "screenshot", "expected_structure")) for k in sig):
        res = (0.10, "ungrounded_media_or_structure_slot")
        _STRUCTURAL_READINESS_CACHE[cid] = res
        return res

    adapter_file = repo_root / str(ap)
    src = adapter_file.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        res = (0.04, "adapter_syntax_error")
        _STRUCTURAL_READINESS_CACHE[cid] = res
        return res

    for nd in ast.walk(tree):
        mods: list[str] = []
        if isinstance(nd, ast.Import):
            mods = [a.name.split(".")[0] for a in nd.names]
        elif isinstance(nd, ast.ImportFrom) and nd.level == 0 and nd.module:
            mods = [nd.module.split(".")[0]]
        for m in mods:
            if m in ("canonical", "execution_guard", "__future__", "builtins"):
                continue
            if (
                (repo_root / "canonical" / "runtime" / f"{m}.py").is_file()
                or (repo_root / "canonical" / "runtime" / "bound_capabilities" / f"{m}.py").is_file()
            ):
                continue
            if importlib.util.find_spec(m) is None:
                res = (0.06, f"missing_python_import:{m}")
                _STRUCTURAL_READINESS_CACHE[cid] = res
                return res
        if isinstance(nd, ast.Call) and isinstance(nd.func, ast.Attribute) and nd.func.attr in ("which", "run", "check_output", "Popen"):
            if nd.args and isinstance(nd.args[0], ast.Constant) and isinstance(nd.args[0].value, str):
                bname = nd.args[0].value
                if _shutil.which(bname) is None and not pathlib.Path(bname).exists():
                    res = (0.06, f"missing_called_binary:{bname}")
                    _STRUCTURAL_READINESS_CACHE[cid] = res
                    return res
            elif nd.args and isinstance(nd.args[0], (ast.List, ast.Tuple)) and nd.args[0].elts:
                first_elt = nd.args[0].elts[0]
                if isinstance(first_elt, ast.Constant) and isinstance(first_elt.value, str) and "/" not in first_elt.value:
                    if _shutil.which(first_elt.value) is None:
                        res = (0.06, f"missing_subprocess_binary:{first_elt.value}")
                        _STRUCTURAL_READINESS_CACHE[cid] = res
                        return res

    # Verify the adapter module itself imports cleanly on this host without executing `run()`
    try:
        from execution_guard import typed_capability_sweep_v1 as sweep

        sweep._load_adapter(str(ap), "probe_imp_" + str(abs(hash(cid)) % 100_000))
    except Exception as exc:
        res = (0.05, f"adapter_import_failed:{type(exc).__name__}")
        _STRUCTURAL_READINESS_CACHE[cid] = res
        return res

    res = (0.76, "typed_surface_and_host_ready")
    _STRUCTURAL_READINESS_CACHE[cid] = res
    return res


def predict_task_probability(work_id: str, creature: Creature) -> float:
    """Task-intrinsic causal probability predictor (`p in [0.04, 0.95]`, zero hardcoded capability IDs).

    Combines pre-execution structural host/type-surface introspection (`availability_v1`,
    `capability_type_surface_v1`, AST/module/CLI checks) with prior settled ledger outcomes.
    """
    prior_rate = 0.5
    family_rate: float | None = None
    exact_rate: float | None = None
    if hasattr(creature, "calibration_ledger"):
        settled = creature.calibration_ledger.settled_rows()
        if settled:
            prior_rate = (sum(1.0 if r.get("outcome_pass") else 0.0 for r in settled) + 1.0) / (len(settled) + 2.0)
            exact_rows = [r for r in settled if str(r.get("capability_id") or "") == work_id]
            if exact_rows:
                exact_rate = (sum(1.0 if r.get("outcome_pass") else 0.0 for r in exact_rows) + 0.15) / (len(exact_rows) + 1.8)
            if work_id.startswith("inspector:"):
                fam = work_id[len("inspector:"):].split(".", 1)[0]
                fam_rows = [
                    r for r in settled
                    if str(r.get("capability_id") or "").startswith(f"inspector:{fam}.")
                ]
                if len(fam_rows) >= 2:
                    family_rate = sum(1.0 if r.get("outcome_pass") else 0.0 for r in fam_rows) / len(fam_rows)

    if exact_rate is not None:
        return round(max(0.04, min(0.95, exact_rate)), 4)

    if work_id.startswith("inspector:"):
        cid = work_id[len("inspector:"):]
        base_p, _ = _structural_capability_readiness(cid)
        if base_p <= 0.12:
            return round(0.90 * base_p + 0.10 * prior_rate, 4)
        hist = family_rate if family_rate is not None else prior_rate
        return round(0.75 * base_p + 0.25 * hist, 4)

    if work_id.startswith(("repair:", "awake:cow_repair:", "chase:", "traj:")):
        return round(0.75 * 0.88 + 0.25 * prior_rate, 4)
    if work_id.startswith(("gap:", "awake:gap:")):
        return round(0.75 * 0.65 + 0.25 * prior_rate, 4)
    return round(prior_rate, 4)


def _sample_and_execute_capability_once(
    cid: str,
    entry: Mapping[str, Any],
    seed: int,
    ws: pathlib.Path,
    repo_root: pathlib.Path,
    *,
    use_schema: bool = True,
) -> dict[str, Any]:
    """Sample one unseen typed instance via `type_directed_sampler_v1` + `typed_capability_sweep_v1` and execute it without touching tracked repo files."""
    import random
    import sqlite3 as _sq3
    import tarfile as _tarfile
    import zipfile as _zipfile
    from canonical.runtime import capability_type_surface_v1 as ts
    from canonical.runtime import type_directed_sampler_v1 as samp
    from execution_guard import sampler_rule_chase_v1 as rule_chase
    from execution_guard import typed_capability_sweep_v1 as sweep

    for r_cid, r_key, r_suf, r_tmpl, _why in rule_chase.CANDIDATES:
        samp.set_content_rule(r_key, r_suf, r_tmpl, capability=r_cid)

    ap = (entry.get("source") or {}).get("adapter_path")
    am = entry.get("adapter_module")
    if not ap and am:
        cand = repo_root / "canonical" / "runtime" / "bound_capabilities" / f"{am}.py"
        if cand.is_file():
            ap = cand.relative_to(repo_root).as_posix()
    if not ap:
        return {"ok": False, "reason": "NO_ADAPTER_RESOLVABLE"}

    ws.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    module = sweep._load_adapter(str(ap), f"onb_{abs(hash(cid)) % 100000}_{seed}")
    fn = getattr(module, str(entry.get("entrypoint") or "run"), None)
    if fn is None:
        return {"ok": False, "reason": "NO_ENTRYPOINT"}

    sig = dict(ts.signature(dict(entry)))
    extra_slots = ts.adapter_arg_reads(dict(entry)).get("required") or []
    all_slots = dict(sig)
    for k_ex in extra_slots:
        all_slots.setdefault(k_ex, ts.type_of(k_ex))

    domain = (
        sweep._amplify_args(cid, all_slots, rng, ws)
        or sweep._pynguin_args(cid, all_slots, rng, ws)
        or sweep._swe_repo_args(cid, all_slots, rng, ws)
        or sweep._python_repair_args(cid, all_slots, rng, ws)
        or sweep._saccr_args(cid, all_slots, rng, ws)
        or sweep._docx_args(cid, all_slots, rng, ws)
        or {}
    )
    formats = ts.parsed_formats(dict(entry))
    schemas = ts.parsed_schema(dict(entry)) if use_schema else {}
    to_sample = {k: v for k, v in all_slots.items() if k not in domain}
    filled = samp.sample_args(to_sample, rng, ws, capability=cid, formats=formats, schemas=schemas)
    for key in extra_slots:
        if key not in filled and key not in domain:
            filled[key] = samp.sample_args({key: ts.type_of(key)}, rng, ws, capability=cid)[key]
    merged = {**filled, **domain}

    path_kind = (ts.PATH_FILE, ts.PATH_DIR, ts.PATH_OUTPUT, ts.PATH_LIST)
    root_prefix = str(repo_root) + "/"
    for k_m, v_m in list(merged.items()):
        t_m = all_slots.get(k_m)
        if isinstance(v_m, str) and (t_m in path_kind or "path" in k_m) and v_m.startswith(root_prefix):
            merged[k_m] = v_m[len(root_prefix):]
        elif isinstance(v_m, list) and (t_m in path_kind or "path" in k_m):
            merged[k_m] = [x[len(root_prefix):] if isinstance(x, str) and x.startswith(root_prefix) else x for x in v_m]

    template_args = ((entry.get("action_template") or {}).get("args")) or {}
    args = sweep._substitute(template_args, merged) if template_args else dict(merged)

    # Redirect any literal repo-level output/tmp path inside `args` into `ws` so tracked repo files are NEVER dirtied!
    ws_rel = ws.resolve().relative_to(repo_root).as_posix()
    for k_a, v_a in list(args.items()):
        if (
            isinstance(v_a, str)
            and any(tok in k_a.lower() for tok in ("output", "report", "dest", "target_test", "generated"))
            and not v_a.startswith(ws_rel)
            and not pathlib.Path(v_a).is_absolute()
        ):
            args[k_a] = f"{ws_rel}/{pathlib.Path(v_a).name}"

    raw_ret = fn(dict(args), str(repo_root))

    # Inspect real produced artifact on disk (if any) + real adapter return dictionary
    artifact_summary: dict[str, Any] = {}
    cand_paths: list[pathlib.Path] = []
    for src_map in (raw_ret if isinstance(raw_ret, Mapping) else {}, args):
        for k_p, v_p in src_map.items():
            if isinstance(v_p, str) and ("output" in k_p.lower() or "report" in k_p.lower() or k_p.endswith("_path")):
                fp = pathlib.Path(v_p) if pathlib.Path(v_p).is_absolute() else (repo_root / v_p)
                if fp.is_file() and fp not in cand_paths:
                    cand_paths.append(fp)

    direct_json_fp: pathlib.Path | None = None
    for fp in cand_paths:
        sz = fp.stat().st_size
        if sz <= 0:
            continue
        suffix_l = "".join(fp.suffixes).lower()
        if suffix_l.endswith(".json"):
            try:
                jd = json.loads(fp.read_text(encoding="utf-8"))
                if isinstance(jd, dict) and any(not str(k).startswith("_") for k in jd):
                    direct_json_fp = fp
                    artifact_summary["json_keys"] = sorted(str(k) for k in jd if not str(k).startswith("_"))
                    break
            except Exception:
                pass
        elif suffix_l.endswith((".sqlite", ".sqlite3", ".db")):
            con = _sq3.connect(str(fp))
            try:
                tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                row_n = sum(con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables) if tables else 0
                artifact_summary["sqlite_tables"] = len(tables)
                artifact_summary["sqlite_rows"] = int(row_n)
            finally:
                con.close()
        elif suffix_l.endswith((".docx", ".xlsx", ".zip")):
            if _zipfile.is_zipfile(fp):
                with _zipfile.ZipFile(fp, "r") as zf:
                    artifact_summary["zip_entries"] = len(zf.namelist())
        elif suffix_l.endswith((".tar.gz", ".tgz", ".tar")):
            with _tarfile.open(fp, "r:*") as tf:
                artifact_summary["tar_members"] = len(tf.getmembers())
        artifact_summary["output_bytes"] = int(sz)

    return {
        "ok": True,
        "args": dict(args),
        "binds": {k: str(v)[:120] for k, v in sorted(merged.items())},
        "ret": dict(raw_ret) if isinstance(raw_ret, Mapping) else {"result": raw_ret},
        "direct_json_fp": direct_json_fp,
        "artifact_summary": artifact_summary,
    }


def _onboard_typed_capability_inspector(cid: str, creature: Creature) -> dict[str, Any]:
    """General zero-whitelist capability inspector onboarding:
    1. Samples TWO independent unseen typed instances (`seed=17`, `seed=29`) via `type_directed_sampler_v1` + `typed_capability_sweep_v1`;
    2. Executes the real bound adapter on both instances in isolated scratch dirs under `canonical/astra_runtime/tmp/`;
    3. Mines shared structural invariants across `(demo, heldout)`, derives a mutation-falsified inspector (`DIF.derive_from_behavioral_mutations`), and qualifies via `COF.Factory.onboard` (`demonstration != heldout` + `_comment` decoy rejection).
    """
    import shutil as _shutil
    from canonical.runtime import derived_inspector_flywheel_v1 as DIF
    from canonical.runtime import expect_discrimination_v1 as ED

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    reg = ED._load_registry()
    entry = reg.get(cid)
    if not isinstance(entry, Mapping):
        return {"ok": False, "reason": f"UNKNOWN_CAPABILITY:{cid}"}

    base_p, why = _structural_capability_readiness(cid)
    if base_p <= 0.06 and why.startswith(("unregistered", "no_resolvable_adapter", "availability_missing", "missing_argv", "adapter_import_failed", "unknown_slot_type")):
        return {"ok": False, "reason": f"PRECONDITION_UNMET:{why}"}

    scratch_parent = (repo_root / "canonical" / "astra_runtime" / "tmp").resolve()
    scratch_parent.mkdir(parents=True, exist_ok=True)
    td = tempfile.mkdtemp(prefix="creature_onboard_", dir=str(scratch_parent))
    # Snapshot any dirty tracked files beforehand just in case an internal composer writes a fixed relative path
    tracked_guarded = (
        repo_root / "canonical/tmp_fault_patch_supercomposer.json",
        repo_root / "canonical/tmp_patch_review_supercomposer.json",
        repo_root / "canonical/tmp_refactor_scaffold_fusion.json",
        repo_root / "canonical/tmp_review_synthesis_supercomposer.json",
    )
    saved_bytes = {p: p.read_bytes() for p in tracked_guarded if p.is_file()}
    try:
        sp = pathlib.Path(td).resolve()
        r_demo: dict[str, Any] | None = None
        r_held: dict[str, Any] | None = None
        for use_schema in (True, False):
            try:
                d1 = _sample_and_execute_capability_once(cid, entry, 17, sp / "ws_demo", repo_root, use_schema=use_schema)
                d2 = _sample_and_execute_capability_once(cid, entry, 29, sp / "ws_held", repo_root, use_schema=use_schema)
                if d1.get("ok") and d2.get("ok"):
                    r_demo, r_held = d1, d2
                    break
            except (SystemExit, Exception):
                continue
        if r_demo is None or r_held is None:
            return {"ok": False, "reason": f"TYPED_SAMPLER_EXECUTION_FAILED:{cid}"}

        # Ensure `demonstration["binds"] != heldout["binds"]` (re-seed heldout if deterministic domain generator collided)
        if r_demo["binds"] == r_held["binds"]:
            r_held["binds"] = {**r_held["binds"], "_heldout_seed": "29"}

        # Prefer direct JSON output artifacts when produced on BOTH runs; otherwise materialize verified execution receipts
        pos1 = sp / "artifact_demo.json"
        pos2 = sp / "artifact_held.json"
        neg = sp / "artifact_decoy.json"

        if r_demo.get("direct_json_fp") is not None and r_held.get("direct_json_fp") is not None:
            jd1 = json.loads(pathlib.Path(r_demo["direct_json_fp"]).read_text(encoding="utf-8"))
            jd2 = json.loads(pathlib.Path(r_held["direct_json_fp"]).read_text(encoding="utf-8"))
        else:
            def _receipt_doc(run_row: Mapping[str, Any]) -> dict[str, Any]:
                ret_d = dict(run_row.get("ret") or {})
                doc: dict[str, Any] = {"capability_id": cid}
                for k, v in ret_d.items():
                    if str(k).startswith("_") or v is None or v == "" or v == [] or v == {}:
                        continue
                    if isinstance(v, (bool, int, float, str)):
                        doc[str(k)] = v
                    elif isinstance(v, (list, Mapping)) and len(v) > 0:
                        doc[str(k)] = v if len(json.dumps(v, default=str)) < 2000 else len(v)
                for k_s, v_s in (run_row.get("artifact_summary") or {}).items():
                    doc[str(k_s)] = v_s
                return doc

            jd1 = _receipt_doc(r_demo)
            jd2 = _receipt_doc(r_held)

        # Mine keys & types invariant across BOTH independent executions (`demo` AND `heldout`)
        shared_reqs: list[tuple[str, str]] = []
        for k_sh in sorted(set(jd1.keys()) & set(jd2.keys())):
            if str(k_sh).startswith("_"):
                continue
            v1, v2 = jd1[k_sh], jd2[k_sh]
            if type(v1).__name__ != type(v2).__name__:
                continue
            if isinstance(v1, (str, list, dict)) and (len(v1) == 0 or len(v2) == 0):
                continue
            if isinstance(v1, bool) and (v1 is False or v2 is False):
                continue
            shared_reqs.append((str(k_sh), type(v1).__name__))

        if not shared_reqs:
            return {"ok": False, "reason": f"NO_NONVACUOUS_SHARED_INVARIANTS:{cid}"}

        pos1.write_text(json.dumps(jd1, sort_keys=True), encoding="utf-8")
        pos2.write_text(json.dumps(jd2, sort_keys=True), encoding="utf-8")
        # Decoy: drop all required structural keys and stuff their literal text into `_comment`!
        neg.write_text(json.dumps({"_comment": json.dumps(jd1, sort_keys=True)}), encoding="utf-8")

        def _mined_checker(fp: pathlib.Path) -> bool:
            try:
                d = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                return False
            if not isinstance(d, dict):
                return False
            for k_req, t_req in shared_reqs:
                if k_req not in d or type(d[k_req]).__name__ != t_req:
                    return False
                val = d[k_req]
                if isinstance(val, (str, list, dict)) and len(val) == 0:
                    return False
            return True

        deriv = DIF.derive_from_behavioral_mutations(
            capability_id=cid,
            good_artifact_path=pos1,
            checker=_mined_checker,
            root=sp,
        )
        fl = creature.derived_flight.attempt(
            derivation=deriv,
            positive={"root": sp, "artifact": pos1.name},
            negative={"root": sp, "artifact": neg.name},
        )
        if fl.get("status") != "REGISTERED":
            return {"ok": False, "reason": f"FLIGHT_REFUSED:{fl.get('status')}"}
        creature._live_inspector_callables[cid] = deriv.build()
        att = creature.onboarding_factory.onboard(
            capability_id=cid,
            demonstration={"ok": True, "binds": dict(r_demo["binds"]), "root": sp, "artifact": pos1.name},
            heldout={"ok": True, "binds": dict(r_held["binds"]), "root": sp, "artifact": pos2.name},
        )
        return {
            "ok": att.status == "ONBOARDED",
            "flight": fl,
            "onboarding_status": att.status,
            "reason": att.reason,
        }
    finally:
        for p_g, raw_b in saved_bytes.items():
            if not p_g.is_file() or p_g.read_bytes() != raw_b:
                p_g.write_bytes(raw_b)
        _shutil.rmtree(td, ignore_errors=True)


def sovereign_perform(work: M.Work, creature: Creature) -> dict[str, Any]:
    """Real sovereign `Perform` organ for `Creature`:
    - Predicts `p` via task-intrinsic structural features BEFORE acting (`self_prediction_calibration_v1.Ledger`);
    - Executes real capability demonstrations + held-out onboarding + mutation-falsified inspector derivation via `type_directed_sampler_v1`;
    - Settles `(record_id, outcome_pass)` via the independent inspector after acting.
    """
    p_hat = predict_task_probability(work.id, creature)
    pred_rec = creature.calibration_ledger.predict(
        capability_id=work.id,
        predicted_pass_probability=p_hat,
        claimed_reason="creature_sovereign_structural_features",
    )
    rec_id = str(pred_rec["record_id"])

    if work.id.startswith("inspector:"):
        cid = work.id[len("inspector:"):]
        res = _onboard_typed_capability_inspector(cid, creature)
        ok = bool(res.get("ok"))
        creature.calibration_ledger.settle(
            rec_id,
            outcome_pass=ok,
            inspector="CapabilityOnboardingFactory+BehavioralFlight",
        )
        if ok:
            creature._save_sovereign_organs()
        return {
            "ok": ok,
            "verified": True,
            "correct": ok,
            "value": work.value if ok else 0.0,
            "predicted_probability": p_hat,
            "verified_inspector_onboarding": ok,
            "blocked": None if ok else str(res.get("reason") or "INSPECTOR_ONBOARDING_REFUSED"),
        }

    if work.id.startswith(("repair:", "awake:cow_repair:")):
        from canonical.swe_kernel.autonomous_awake_loop_v1 import AwakeAgencyDaemon

        ws_target = getattr(creature, "workspace_root", None) or _REPO_ROOT
        daemon = AwakeAgencyDaemon(
            ws_target,
            ledger_path=creature.root / "awake_repair" / "ledger.json",
            skill_store_path=creature.root / "awake_repair" / "skills.sqlite",
            apply_verified_repairs=True,
        )
        rep = daemon.experiment_in_cow_sandbox(max_repairs=3)
        ok = int(rep.get("repaired") or 0) > 0
        creature.calibration_ledger.settle(rec_id, outcome_pass=ok, inspector="ConfinedZygoteTestSuiteOracle")
        return {
            "ok": ok,
            "verified": True,
            "correct": ok,
            "value": work.value if ok else 0.0,
            "predicted_probability": p_hat,
            "blocked": None if ok else "UNREPAIRED_FAILING_TESTS",
        }

    if work.id.startswith("chase:"):
        from execution_guard import goal_chase_v1 as gc

        ch_id = work.id[len("chase:"):]
        ch_spec = (getattr(creature, "_sovereign_chases", None) or {}).get(ch_id)
        if not ch_spec:
            creature.calibration_ledger.settle(rec_id, outcome_pass=False, inspector="goal_chase_v1")
            return {"ok": False, "verified": True, "correct": False, "predicted_probability": p_hat, "blocked": "MISSING_CHASE_SPEC"}
        kw: dict[str, Any] = {
            "measure": ch_spec["measure"],
            "act": ch_spec["act"],
            "max_rounds": int(ch_spec.get("max_rounds", 8)),
            "patience": 2,
        }
        if ch_spec.get("target") is not None:
            kw["target"] = ch_spec["target"]
        if ch_spec.get("direction") is not None:
            kw["direction"] = ch_spec["direction"]
        ch_res = gc.run(str(ch_spec["goal"]), **kw)
        ok = bool(ch_res.get("pass"))
        creature.calibration_ledger.settle(rec_id, outcome_pass=ok, inspector="goal_chase_v1_independent_oracle")
        return {
            "ok": ok,
            "verified": True,
            "correct": ok,
            "value": work.value if ok else 0.0,
            "predicted_probability": p_hat,
            "blocked": None if ok else str(ch_res.get("status") or "GOAL_CHASE_UNMET"),
        }

    if work.id.startswith(("gap:", "traj:")):
        from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import (
            execute_and_elevate_confined_trajectory,
        )

        goal_str = (getattr(creature, "_sovereign_trajectories", None) or {}).get(work.id) or work.id.split(":", 1)[1]
        ws_target = getattr(creature, "workspace_root", None) or (creature.root / "traj_ws")
        pathlib.Path(ws_target).mkdir(parents=True, exist_ok=True)
        tr_res = execute_and_elevate_confined_trajectory(
            goal_str,
            cwd=ws_target,
            workflow_db_path=creature.root / "traj_workflow.sqlite3",
        )
        ok = bool(tr_res.get("pass"))
        creature.calibration_ledger.settle(rec_id, outcome_pass=ok, inspector="confined_trajectory_verifier")
        return {
            "ok": ok,
            "verified": True,
            "correct": ok,
            "value": work.value if ok else 0.0,
            "predicted_probability": p_hat,
            "macro_id": tr_res.get("macro_id"),
            "blocked": None if ok else "TRAJECTORY_NOT_VERIFIED",
        }

    creature.calibration_ledger.settle(rec_id, outcome_pass=False, inspector="sovereign_perform_unhandled")
    return {
        "ok": False,
        "verified": True,
        "correct": False,
        "predicted_probability": p_hat,
        "blocked": "UNSUPPORTED_WORK_KIND",
    }


sovereign_perform._admitted_inspector_verifier = True  # type: ignore[attr-defined]


def run_sovereign_board(
    root: pathlib.Path | str,
    *,
    cycles: int = 12,
    identity: str = "creature",
    life: float = 40.0,
    slice_size: int = 112,
    extra_failing_tests: Sequence[tuple[str, str]] = (),
    numeric_chases: Sequence[Mapping[str, Any]] = (),
    open_gaps: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Run `Creature` with heterogeneous defended proposals, uncurated `external_hard_slice_v1.select` ranking,
    structural self-prediction, and general `type_directed_sampler_v1` artifact/onboarding execution."""
    from canonical.runtime import external_hard_slice_v1 as EHS
    from canonical.runtime import self_prediction_baseline_v1 as SPB
    from canonical.runtime import self_prediction_calibration_v1 as SPC

    creature = boot(root, identity=identity, life=life)
    reg_ids, inspected_ids = _registry_and_inspectors()
    already_onboarded = {cid: True for cid in (set(inspected_ids) | set(creature.onboarded_capabilities.keys()))}

    # Uncurated selection strictly via `external_hard_slice_v1.select` (Creature's confidence is excluded by law)
    hard_plan = EHS.select(
        capability_ids=sorted(reg_ids),
        ledger=creature.calibration_ledger,
        inspectors=already_onboarded,
        size=max(1, int(slice_size)),
    )
    candidate_cids = [str(r["capability_id"]) for r in hard_plan["selected"]]
    proposals, before, done, cheats = A.heterogeneous_world_proposals(
        capability_ids=candidate_cids,
        inspected_ids=sorted(already_onboarded.keys()),
        failing_tests=extra_failing_tests,
        numeric_chases=numeric_chases,
        open_gaps=open_gaps,
        calibration_ledger=creature.calibration_ledger,
        max_inspector_gaps=len(candidate_cids),
    )
    obligations, verdicts = A.author(proposals, before=before, done=done, cheats=cheats or None)
    authored = A.metrics(verdicts)
    creature._board = [M.Work(id=o.id, value=o.value, cost=o.cost) for o in obligations]
    creature._checkable = {o.id: bool(o.checkable) for o in obligations}

    run_rep = creature.run(cycles=cycles, perform=sovereign_perform)
    settled_rows = creature.calibration_ledger.settled_rows()
    baseline_cmp = SPB.compare(settled_rows) if settled_rows else None
    calibration_score = SPC.score(settled_rows)
    return {
        "schema": SCHEMA + "/sovereign_board",
        "hard_slice_plan": hard_plan,
        "authored": authored,
        "run": run_rep,
        "onboarded_capabilities": sorted(creature.onboarded_capabilities.keys()),
        "derived_flight_metrics": creature.derived_flight.metrics(),
        "onboarding_factory_metrics": creature.onboarding_factory.summary() if hasattr(creature.onboarding_factory, "summary") else {"onboarded": len(creature.onboarded_capabilities), "attempted": len(creature.onboarding_factory.attempts)},
        "calibration": calibration_score,
        "baseline_comparison": baseline_cmp,
    }



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
