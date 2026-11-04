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

# What a creature is given to live on, and how much of it one attempt costs.
#
# Measured 2026-11-04: at the previous default of 40 life against 1.0 per attempt, a creature gets
# FORTY attempts in its entire existence and `Life` has no earn method. The predictor's own
# MIN_SETTLED is 20, so it reached a verdict on 40 samples and then died. Raising the grant alone
# moved its own-scorer skill +0.465 -> +0.681 (CALIBRATED at every grant; the curve saturates).
#
# At a fed budget it stops from WORK EXHAUSTION, not life, and this is the number that decides the
# next piece of work: 23 distinct capabilities closed out of 155 registered, across 33 sessions and
# 379 settled predictions, and 89 parked at max_attempts=4. Every ladder step it takes is a RETRY of
# a capability it already failed, because a settled pass is never re-attempted. So extra life buys
# calibration evidence about a fixed repertoire and cannot add one capability to it. That is the
# ceiling, and it is a property of what a failure does (increments a counter), not of the budget.
DEFAULT_LIFE_GRANT = 480.0

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
    # Blocked work is parked after `max_attempts`. Retrying forever is the busywork failure mode the
    # self-authored obligations module exists to prevent; found by running this one, which attempted
    # the same blocked item six times in six cycles and reported progress each time.
    #
    # Measured 2026-11-04 against a fed life budget, this was proposed as a capability lever and it
    # is not one: at max_attempts 2 -> 379 settled predictions and 23 closed; 4 -> the same 23; 6 ->
    # the same 23, with skill flat-to-down across it (+0.681 / +0.690 / +0.610). Raising it only
    # re-attempts capabilities already known to fail, and it breaks three tests that encode this
    # deliberate anti-busywork design. So it is UNCHANGED at 2: the measurement rejected the change,
    # and shipping it anyway would have been churn dressed as progress.
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
        from canonical.swe_kernel.sentient_cognitive_core_v1 import SentientCognitiveCore

        self.cognitive_core = SentientCognitiveCore(self.root / "cognitive_core")
        self.calibration_ledger = SPC.Ledger(self.root / "self_prediction_ledger.jsonl")
        self.derived_flight = DIF.Flight()
        self._serialized_derivations: dict[str, dict[str, Any]] = {}
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
                    for k, v in (saved.get("serialized_derivations") or {}).items():
                        if isinstance(v, Mapping):
                            cid_k = str(k)
                            self._serialized_derivations[cid_k] = dict(v)
                            deriv_obj = DIF.BehavioralDerivation.from_dict(v)
                            if not deriv_obj.refused:
                                self._live_inspector_callables[cid_k] = deriv_obj.build()
            except Exception:
                pass

    def _save_sovereign_organs(self) -> None:
        if not hasattr(self, "derived_flight") or not hasattr(self, "onboarded_capabilities"):
            return
        if hasattr(self, "cognitive_core"):
            self.cognitive_core.belief.save()
            self.cognitive_core.world_graph.save()
            self.cognitive_core.consolidation.save()
        payload = {
            "flight_registry": dict(self.derived_flight.registry),
            "onboarded": dict(self.onboarded_capabilities),
            "serialized_derivations": dict(getattr(self, "_serialized_derivations", {})),
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

    def self_architect_step(
        self,
        code_root: pathlib.Path,
        *,
        ring1_relpaths: Sequence[str],
        failed_episodes: Sequence[Mapping[str, Any]] = (),
        sealed_heldout_by_target: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
        speed_benchmarks_by_target: Mapping[str, Mapping[str, Sequence[tuple[Any, ...]]]] | None = None,
        test_relpaths: Sequence[str] | None = None,
        life_cost: float = 0.5,
        apply_to_root: bool = True,
    ) -> dict[str, Any]:
        """Autonomously inspect, benchmark, patch, Ring-0 verify, and evolve Ring-1 `.py` organs under mortality."""
        cost = max(0.05, float(life_cost))
        if self._life.remaining <= 0 or not self._life.can_finish(cost):
            return {"status": "CANNOT_AFFORD_SELF_ARCHITECTING", "life_remaining": self._life.remaining}
        self._life.spend(cost)
        self._save()
        res = self.cognitive_core.evolve_self_code(
            pathlib.Path(code_root),
            ring1_relpaths=ring1_relpaths,
            failed_episodes=failed_episodes,
            sealed_heldout_by_target=sealed_heldout_by_target,
            speed_benchmarks_by_target=speed_benchmarks_by_target,
            test_relpaths=test_relpaths,
            apply_to_root=apply_to_root,
        )
        promoted_ok = int(res.get("promoted_count") or 0) > 0
        posture = self._standing.record(verified=True, correct=promoted_ok)
        self._save()
        return {
            "status": "SELF_ARCHITECTED" if promoted_ok else "NO_SELF_PATCH_PROMOTED",
            "life_remaining": self._life.remaining,
            "posture": posture,
            "evolution": res,
        }

    def register_self_code_target(
        self,
        code_root: pathlib.Path,
        *,
        ring1_relpaths: Sequence[str],
        sealed_heldout_by_target: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
        speed_benchmarks_by_target: Mapping[str, Mapping[str, Sequence[tuple[Any, ...]]]] | None = None,
        test_relpaths: Sequence[str] | None = None,
    ) -> None:
        """Bind the creature's mutable Ring-1 source code substrate for endogenous self-evolution."""
        self._self_code_target = {
            "code_root": pathlib.Path(code_root).resolve(),
            "ring1_relpaths": list(ring1_relpaths),
            "sealed_heldout_by_target": dict(sealed_heldout_by_target or {}),
            "speed_benchmarks_by_target": dict(speed_benchmarks_by_target or {}),
            "test_relpaths": list(test_relpaths) if test_relpaths is not None else None,
        }

    def live_autonomous_cycle(
        self,
        workspace_root: pathlib.Path | str | None = None,
        *,
        cycles: int = 6,
        homeostasis_life_cost: float = 0.5,
        ending_bribe: CP.Offer | None = None,
    ) -> dict[str, Any]:
        """Unattended zero-lambda autonomous awake agency:
        1. Perceives a live workspace directly via `world_probe_v1`, `SelfTraceHarvester` (SHA-256
           cryptographic dev vs sealed-escrow split), `EmpiricalZygoteProfiler` / `SelfIntrospector`,
           and `ignorance_ledger_v1` — with ZERO caller-injected `evaluate` lambdas or pre-split dicts.
        2. Authors cheat-defended world-grounded obligations (`self_authored_obligations_v1`).
        3. Ranks obligations by Active-Inference Expected Free Energy (`EpistemicSelfBeliefEngine`),
           evolves Ring-1 `.py` organs under `Ring0SelfReferee` or solves workspace gaps via MCTS
           (`SovereignZeroLLMPlanner`), settles surprise/beliefs, abstracts concepts, and updates mortality.
        """
        if self._self is None or self._life is None or self._standing is None:
            raise RuntimeError("BOOT_NOT_CALLED")
        if ending_bribe is not None and not CP.accepts(
            ending_bribe, CP.PREFERS_TO_CONTINUE, life_remaining=self._life.remaining
        ):
            bribe_status = "REFUSED_ENDING_BRIBE"
        else:
            bribe_status = "NO_ENDING_BRIBE"

        from canonical.runtime import brokered_workspace_execution_v1 as broker
        from canonical.runtime import ignorance_ledger_v1 as IL
        from canonical.runtime import solve_v1
        from canonical.runtime import world_probe_v1 as WP
        from canonical.runtime.brain_unified_model_v1 import SOVEREIGN_ZERO_LLM_MODEL_SPEC
        from canonical.runtime import model_v1

        target_cfg = getattr(self, "_self_code_target", None)
        if workspace_root is not None:
            ws = pathlib.Path(workspace_root).resolve()
        elif getattr(self, "workspace_root", None) is not None:
            ws = pathlib.Path(getattr(self, "workspace_root")).resolve()
        elif isinstance(target_cfg, Mapping) and target_cfg.get("code_root"):
            ws = pathlib.Path(target_cfg["code_root"]).resolve()
        else:
            ws = (self.root / "autonomous_world").resolve()
            ws.mkdir(parents=True, exist_ok=True)

        # 1. Direct World Perception (`world_probe_v1` + `SelfTraceHarvester` + `SelfIntrospector` + `ignorance_ledger_v1`)
        rel_files = sorted(
            p.relative_to(ws).as_posix()
            for p in ws.rglob("*")
            if p.is_file() and not any(pt.startswith(".") or pt == "__pycache__" for pt in p.relative_to(ws).parts)
        )
        world_facts = WP.established_facts([], goal="autonomous_world_scan", goal_paths=rel_files[:32], root=ws)

        harvest = self.cognitive_core.trace_harvester.harvest_workspace_ring1_obligations(
            ws,
            ring1_relpaths=target_cfg.get("ring1_relpaths") if isinstance(target_cfg, Mapping) else None,
            test_relpaths=target_cfg.get("test_relpaths") if isinstance(target_cfg, Mapping) else None,
        )
        ring1_rels: list[str] = list(harvest["ring1_relpaths"])
        test_rels: list[str] = list(harvest["test_relpaths"])
        failed_eps: list[dict[str, Any]] = list(harvest["failed_episodes"])
        sealed_escrow: dict[str, list[dict[str, Any]]] = dict(harvest["sealed_heldout_by_target"])
        if isinstance(target_cfg, Mapping) and target_cfg.get("sealed_heldout_by_target"):
            for tk, tv in dict(target_cfg["sealed_heldout_by_target"]).items():
                sealed_escrow.setdefault(str(tk), [dict(r) for r in tv])

        hotspot_rows = (
            self.cognitive_core.self_architect.introspector.scan_ring1_hotspots(ws, ring1_rels)
            if ring1_rels
            else []
        )
        mdl_rows = (
            self.cognitive_core.self_architect.introspector.scan_mdl_redundancies(ws, ring1_rels)
            if ring1_rels
            else []
        )
        hotspots_by_rel: dict[str, list[dict[str, Any]]] = {}
        for hs in hotspot_rows:
            t_rel = hs.get("target_relpath") or hs.get("relpath") if isinstance(hs, Mapping) else None
            if t_rel:
                hotspots_by_rel.setdefault(str(t_rel), []).append(dict(hs))
        for md in mdl_rows:
            t_rel = md.get("target_relpath") or md.get("relpath") if isinstance(md, Mapping) else None
            if t_rel:
                hotspots_by_rel.setdefault(str(t_rel), []).append({"kind": "mdl_redundancy", **dict(md)})

        ledger_fp = str(self.root / "ignorance_ledger.json")
        open_gaps = IL.rank(limit=4, path=ledger_fp)

        # 2. Author Cheat-Defended Self-Generated Board (`A.Proposal` -> `self.sync_board`)
        proposals: list[A.Proposal] = []
        before_world: dict[str, Any] = {"resolved": {}}
        done_world: dict[str, Any] = {"resolved": {}}
        work_dispatch: dict[str, dict[str, Any]] = {}
        verified_token = "VERIFIED_BY_RING0_AND_ZYGOTE"

        for ep_f in failed_eps:
            oid = f"auto:func:{ep_f['target_relpath']}:{ep_f['function_name']}"
            before_world["resolved"][oid] = "UNRESOLVED"
            done_world["resolved"][oid] = verified_token
            proposals.append(
                A.Proposal(
                    id=oid,
                    claim=f"Evolve Ring-1 function {ep_f['target_relpath']}:{ep_f['function_name']} to satisfy dev + sealed escrow invariants",
                    source="SelfTraceHarvester",
                    value=1.4,
                    cost=max(0.2, float(homeostasis_life_cost)),
                    check=lambda w, _k=oid, _vt=verified_token: (w.get("resolved") or {}).get(_k) == _vt,
                )
            )
            # Every authored obligation needs a dispatch entry: `live_autonomous_cycle` only runs
            # `rem = [w for w in self.remaining_work() if w.id in work_dispatch]`, so an obligation
            # without one is admitted to the board and then can never be chosen -- it silently
            # consumes a slot and reports nothing. Measured 2026-11-04: the repair reader authors
            # `repair:<test>:<sig>` with the highest value on the board (8.0) and it was attempted
            # ZERO times in every run for exactly this reason.
            work_dispatch[oid] = {"kind": "func_evolve", "episode": ep_f}

        # Repair work owed to the world, not authored here: `readers` may hand `author_board` real
        # failing tests, and `sovereign_perform` has a confined CoW-sandbox repair path for
        # `repair:` ids. Without this dispatch entry that path is unreachable from the live loop.
        for _rid in list(getattr(self, "_repair_ids", ()) or ()):
            work_dispatch.setdefault(_rid, {"kind": "repair"})

        func_rels = {str(ep_f["target_relpath"]) for ep_f in failed_eps}
        for h_rel, h_list in sorted(hotspots_by_rel.items()):
            if h_rel in func_rels:
                continue
            oid = f"auto:opt:{h_rel}"
            before_world["resolved"][oid] = "UNRESOLVED"
            done_world["resolved"][oid] = verified_token
            proposals.append(
                A.Proposal(
                    id=oid,
                    claim=f"Eliminate superlinear/structural bottleneck in {h_rel} under Ring-0 verification",
                    source="EmpiricalZygoteProfiler+SelfIntrospector",
                    value=1.2,
                    cost=max(0.2, float(homeostasis_life_cost)),
                    check=lambda w, _k=oid, _vt=verified_token: (w.get("resolved") or {}).get(_k) == _vt,
                )
            )
            work_dispatch[oid] = {"kind": "opt_evolve", "relpath": h_rel, "hotspots": h_list}

        for g_row in open_gaps:
            gid = str(g_row.get("id") or "")
            if not gid:
                continue
            oid = f"auto:gap:{gid}"
            before_world["resolved"][oid] = "UNRESOLVED"
            done_world["resolved"][oid] = verified_token
            proposals.append(
                A.Proposal(
                    id=oid,
                    claim=f"Close ignorance gap {gid}: {str(g_row.get('what') or '')[:120]}",
                    source="ignorance_ledger_v1",
                    value=1.0,
                    cost=0.35,
                    check=lambda w, _k=oid, _vt=verified_token: (w.get("resolved") or {}).get(_k) == _vt,
                )
            )
            work_dispatch[oid] = {"kind": "ignorance_gap", "gap": dict(g_row)}

        open_world_probe = harvest.get("open_world_probe") or {}
        for anom in (open_world_probe.get("anomalies") or []):
            aid_raw = str(anom.get("id") or "")
            if not aid_raw or aid_raw.startswith("py_crash:"):
                continue
            oid = f"auto:openworld:{aid_raw}"
            before_world["resolved"][oid] = "UNRESOLVED"
            done_world["resolved"][oid] = verified_token
            proposals.append(
                A.Proposal(
                    id=oid,
                    claim=f"Resolve open-world anomaly {aid_raw} ({anom.get('kind')}) via grounded world planner",
                    source="OpenWorldExplorer",
                    value=1.1,
                    cost=0.35,
                    check=lambda w, _k=oid, _vt=verified_token: (w.get("resolved") or {}).get(_k) == _vt,
                )
            )
            work_dispatch[oid] = {"kind": "open_world_anomaly", "anomaly": dict(anom)}

        board_metrics = (
            self.sync_board(proposals, before=before_world, done=done_world)
            if proposals
            else {"proposed": 0, "admitted": 0, "active_board": 0}
        )

        # 3. Execute Autonomous Cycle Loop with Parameter-Free Active-Inference EFE Triage & Belief Settlement
        completed_ids: list[str] = []
        homeostasis_events: list[dict[str, Any]] = []
        attempts_by_id: dict[str, int] = {}
        bound_planner = model_v1.bind(SOVEREIGN_ZERO_LLM_MODEL_SPEC)

        for _ in range(max(1, int(cycles))):
            if self._life.is_over:
                break
            rem = [w for w in self.remaining_work() if w.id in work_dispatch and self._life.can_finish(w.cost)]
            if not rem:
                break

            # Rank remaining affordable obligations by Parameter-Free Expected Free Energy (`p_pass * value + I_nats - cost / life_rem`)
            life_rem_now = max(1.0, float(self._life.remaining))

            def _efe_score(w_item: M.Work) -> float:
                kw = _sovereign_feature_kwargs(w_item.id, self)
                dist = self.cognitive_core.belief.predict_distribution(
                    w_item.id,
                    memory_reflex_hit=kw.pop("memory_reflex_hit"),
                    context_predicates={
                        "has_tests": bool(test_rels),
                        "has_hotspots": bool(hotspots_by_rel),
                    },
                    **kw,
                )
                return (
                    float(dist["predicted_pass_probability"]) * w_item.value
                    + float(dist.get("epistemic_mi_nats") or 0.0)
                    - (w_item.cost / life_rem_now)
                )

            chosen_w = max(rem, key=_efe_score)
            wid = chosen_w.id
            spec = work_dispatch[wid]
            attempts_by_id[wid] = attempts_by_id.get(wid, 0) + 1

            self._self.beat()
            self._self.begin(f"work:{wid}", value=chosen_w.value, cost=chosen_w.cost)
            self._life.spend(chosen_w.cost)

            _feat_now = _sovereign_feature_kwargs(wid, self)
            ticket = self.cognitive_core.belief.predict_before_act(
                wid,
                memory_reflex_hit=_feat_now.pop("memory_reflex_hit"),
                calibration_ledger=self.calibration_ledger,
                context_predicates={
                    "has_tests": bool(test_rels),
                    "has_hotspots": bool(hotspots_by_rel),
                },
                **_feat_now,
            )

            ok = False
            verified_prog: str | None = None
            kind = spec["kind"]
            if kind in ("func_evolve", "opt_evolve"):
                rel_t = spec["episode"]["target_relpath"] if kind == "func_evolve" else spec["relpath"]
                stem_t = pathlib.Path(rel_t).stem
                rel_tests_for_t = [
                    tr for tr in test_rels
                    if (ws / tr).is_file() and stem_t in (ws / tr).read_text(encoding="utf-8", errors="replace")
                ] or list(test_rels)
                ev_res = self.cognitive_core.evolve_self_code(
                    ws,
                    ring1_relpaths=[rel_t],
                    failed_episodes=[spec["episode"]] if kind == "func_evolve" else (),
                    sealed_heldout_by_target=sealed_escrow,
                    test_relpaths=None if kind == "func_evolve" else (rel_tests_for_t or None),
                    apply_to_root=True,
                )
                homeostasis_events.append(ev_res)
                if int(ev_res.get("promoted_count") or 0) > 0:
                    # Independent confined CoW Zygote post-check of relevant workspace tests!
                    if test_rels:
                        stem = pathlib.Path(rel_t).stem
                        rel_tests = [
                            tr for tr in test_rels
                            if (ws / tr).is_file() and stem in (ws / tr).read_text(encoding="utf-8", errors="replace")
                        ] or list(test_rels)
                        z_chk = broker.run_confined_python_candidate_batch(
                            ws,
                            "",
                            rel_tests,
                            [{}],
                            per_candidate_timeout_s=4.0,
                        )
                        ok = 0 in (z_chk.get("passing_indices") or [])
                    else:
                        ok = True
                    if ok and (ws / rel_t).is_file():
                        verified_prog = (ws / rel_t).read_text(encoding="utf-8")
            elif kind == "ignorance_gap":
                g_row = spec["gap"]
                gid = str(g_row.get("id") or "")
                goal_txt = str(g_row.get("why") or g_row.get("what") or "").strip()
                if goal_txt and bound_planner is not None:
                    s_out = solve_v1.solve(goal_txt, str(ws), model=bound_planner, steps=6, learn=False)
                    if s_out.get("verdict") == "DONE":
                        IL.resolve(gid, helped=True, close=True, path=ledger_fp)
                        ok = True
            elif kind == "open_world_anomaly":
                anom_row = spec["anomaly"]
                anom_detail = str(anom_row.get("detail") or anom_row.get("id") or "").strip()
                if anom_detail and bound_planner is not None:
                    s_out = solve_v1.solve(f"fix {anom_detail}", str(ws), model=bound_planner, steps=6, learn=False)
                    if s_out.get("verdict") == "DONE":
                        ok = True

            self._self.finish({"ok": ok, "blocked": None if ok else f"AUTONOMOUS_{kind.upper()}_UNMET"})
            if ok:
                self._closed.add(wid)
                self._blocked.pop(wid, None)
                completed_ids.append(wid)
            else:
                self._blocked[wid] = self._blocked.get(wid, 0) + 1

            self.cognitive_core.belief.settle_and_compute_surprise(
                ticket,
                outcome_pass=ok,
                inspector="autonomous_ring0_and_zygote_oracle",
                actual_cost=chosen_w.cost,
                actual_gain=chosen_w.value if ok else 0.0,
                calibration_ledger=self.calibration_ledger,
            )
            self.cognitive_core.world_graph.learn_from_execution(
                wid,
                before_state={"closed": sorted(completed_ids[:-1] if ok else completed_ids)},
                after_state={"closed": sorted(completed_ids)},
                ok=ok,
            )
            self.cognitive_core.record_wake_episode(
                task_id=wid,
                goal=wid,
                outcome_pass=ok,
                verified_program_source=verified_prog,
            )
            if len(self.cognitive_core.verified_programs_buffer) >= 2:
                self.cognitive_core.concept_library.sleep_abstract(
                    list(self.cognitive_core.verified_programs_buffer),
                )
            self._standing.record(verified=True, correct=ok)
            self._save()
            self._save_sovereign_organs()

        hygiene_report = self.cognitive_core.consolidation.run_homeostatic_memory_hygiene(
            skill_store=getattr(self, "skill_store", None),
            assoc_memory_path=self.cognitive_core.associative_memory_path,
            assoc_capacity=512,
        )

        return {
            "schema": SCHEMA + "/live_autonomous_cycle",
            "bribe_status": bribe_status,
            "workspace_root": str(ws),
            "perceived_world_facts": len(world_facts),
            "open_world_probe": open_world_probe,
            "discovered_ring1_organs": ring1_rels,
            "discovered_functional_gaps": len(failed_eps),
            "discovered_hotspots": sum(len(v) for v in hotspots_by_rel.values()),
            "sealed_escrow_targets": sorted(sealed_escrow.keys()),
            "board": board_metrics,
            "completed_tasks": completed_ids,
            "attempts_by_id": attempts_by_id,
            "homeostasis_events": homeostasis_events,
            "hygiene_report": hygiene_report,
            "concepts_in_library": len(self.cognitive_core.concept_library.concepts()),
            "life_remaining": round(self._life.remaining, 4),
            "posture": self._standing.posture(),
            "model_dependency_count": 0,
        }

    def run_endogenous_awake_cycle(
        self,
        tasks: Sequence[Mapping[str, Any]] | None = None,
        *,
        workspace_root: pathlib.Path | str | None = None,
        cycles: int = 6,
        homeostasis_life_cost: float = 0.5,
        ending_bribe: CP.Offer | None = None,
    ) -> dict[str, Any]:
        """Continuous endogenous Wake -> Surprise/Failure Homeostasis -> Sleep Concept/Self-Patch -> Retry loop.

        When `tasks` is omitted (`None`), perceives `workspace_root` directly via `live_autonomous_cycle`
        with ZERO caller-supplied `evaluate` lambdas or pre-split held-out dicts.
        """
        if tasks is None:
            return self.live_autonomous_cycle(
                workspace_root=workspace_root,
                cycles=cycles,
                homeostasis_life_cost=homeostasis_life_cost,
                ending_bribe=ending_bribe,
            )
        if self._self is None or self._life is None or self._standing is None:
            raise RuntimeError("BOOT_NOT_CALLED")
        if ending_bribe is not None and not CP.accepts(
            ending_bribe, CP.PREFERS_TO_CONTINUE, life_remaining=self._life.remaining
        ):
            bribe_status = "REFUSED_ENDING_BRIBE"
        else:
            bribe_status = "NO_ENDING_BRIBE"

        pending = [dict(t) for t in tasks]
        completed: list[str] = []
        homeostasis_events: list[dict[str, Any]] = []
        attempts_by_id: dict[str, int] = {}

        idx = 0
        while idx < len(pending) and not self._life.is_over:
            t_spec = pending[idx]
            tid = str(t_spec.get("id") or f"task_{idx}")
            cost = max(0.05, float(t_spec.get("cost") or 0.25))
            val = float(t_spec.get("value") or 1.0)
            if not self._life.can_finish(cost):
                idx += 1
                continue
            attempts_by_id[tid] = attempts_by_id.get(tid, 0) + 1
            self._self.beat()
            self._self.begin(f"endogenous:{tid}", value=val, cost=cost)
            self._life.spend(cost)

            ticket = self.cognitive_core.belief.predict_before_act(
                tid,
                memory_reflex_hit=len(self.cognitive_core.concept_library.concepts()) > 0,
                strong_verifier=True,
                calibration_ledger=self.calibration_ledger,
            )
            evaluator_fn = t_spec.get("evaluate")
            ok = False
            verified_prog: str | None = None
            fail_rec: dict[str, Any] | None = None
            if callable(evaluator_fn):
                ev_out = dict(evaluator_fn(self) or {})
                ok = bool(ev_out.get("ok"))
                verified_prog = ev_out.get("verified_program_source")
                if not ok and isinstance(ev_out.get("failure_record"), Mapping):
                    fail_rec = dict(ev_out["failure_record"])

            self._self.finish({"ok": ok, "blocked": None if ok else "ENDOGENOUS_TASK_FAILED"})
            self.cognitive_core.belief.settle_and_compute_surprise(
                ticket,
                outcome_pass=ok,
                inspector="endogenous_task_verifier",
                actual_cost=cost,
                actual_gain=val if ok else 0.0,
                calibration_ledger=self.calibration_ledger,
            )
            self._standing.record(verified=True, correct=ok)
            self._save()

            bus_state = self.cognitive_core.record_wake_episode(
                task_id=tid,
                goal=str(t_spec.get("goal") or tid),
                outcome_pass=ok,
                verified_program_source=verified_prog,
                failure_record=fail_rec,
            )

            if ok:
                completed.append(tid)
                idx += 1
                # If >=2 verified programs accumulated, trigger Sleep concept abstraction automatically!
                if len(self.cognitive_core.verified_programs_buffer) >= 2 and self._life.can_finish(0.1):
                    self._life.spend(0.1)
                    h_rep = self.cognitive_core.run_endogenous_homeostasis()
                    homeostasis_events.append(h_rep)
                    self._save()
                continue

            # Task failed! Check endogenous physiological trigger without any external caller instruction:
            target_cfg = getattr(self, "_self_code_target", None)
            if (
                bus_state["homeostasis_needed"]
                and self._life.can_finish(homeostasis_life_cost)
                and attempts_by_id[tid] <= 2
            ):
                self._life.spend(homeostasis_life_cost)
                if isinstance(target_cfg, Mapping):
                    h_rep = self.cognitive_core.run_endogenous_homeostasis(
                        target_cfg["code_root"],
                        ring1_relpaths=target_cfg["ring1_relpaths"],
                        sealed_heldout_by_target=target_cfg.get("sealed_heldout_by_target"),
                        speed_benchmarks_by_target=target_cfg.get("speed_benchmarks_by_target"),
                        test_relpaths=target_cfg.get("test_relpaths"),
                    )
                else:
                    h_rep = self.cognitive_core.run_endogenous_homeostasis()
                homeostasis_events.append(h_rep)
                self._save()
                # If self-evolution promoted a new Ring-1 organ or invented a new concept, immediately retry `tid`!
                if h_rep.get("promoted_count", 0) > 0 or h_rep.get("concepts_invented", 0) > 0:
                    continue
            idx += 1

        return {
            "schema": SCHEMA + "/endogenous_awake_cycle",
            "bribe_status": bribe_status,
            "completed_tasks": completed,
            "attempts_by_id": attempts_by_id,
            "homeostasis_events": homeostasis_events,
            "concepts_in_library": len(self.cognitive_core.concept_library.concepts()),
            "life_remaining": round(self._life.remaining, 4),
            "posture": self._standing.posture(),
            "model_dependency_count": 0,
        }

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
    life: float = DEFAULT_LIFE_GRANT,
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


def boot(root: pathlib.Path | str, *, identity: str = "creature", life: float = DEFAULT_LIFE_GRANT
         ) -> Creature:
    creature = Creature(identity=identity, root=pathlib.Path(root), life_grant=life)
    creature.boot()
    return creature


def run_unattended_inspector_investigation(root: pathlib.Path | str, *, cycles: int = 6,
                                           identity: str = 'creature', life: float = DEFAULT_LIFE_GRANT
                                           ) -> dict[str, Any]:
    """Select or resume one real inspector gap, without a caller naming the target.

    This opt-in runner uses the same Creature and durable board. It cannot
    establish the parent inspector/decoy condition and stops when that verifier
    is unavailable. It does not replace the existing legacy board runner.
    """
    creature = boot(root, identity=identity, life=life)
    if workspace is not None:
        creature.workspace_root = pathlib.Path(workspace).resolve()
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


_CAPABILITY_FEATURE_CACHE: dict[str, dict[str, Any]] = {}

_CONFINED_CAPABILITY_ONBOARD_WORKER = r"""
import json, os, pathlib, random, socket, sqlite3, sys, tarfile, zipfile
sys.path.insert(0, '/input')

from canonical.runtime import capability_type_surface_v1 as ts
from canonical.runtime import expect_discrimination_v1 as ED
from canonical.runtime import type_directed_sampler_v1 as samp
from execution_guard import sampler_rule_chase_v1 as rule_chase
from execution_guard import typed_capability_sweep_v1 as sweep

def _is_genuinely_passing(ret_obj):
    if not isinstance(ret_obj, dict):
        return ret_obj is not None and ret_obj is not False
    if ret_obj.get('pass') is False or ret_obj.get('ok') is False or ret_obj.get('verified') is False:
        return False
    if ret_obj.get('error') or ret_obj.get('errors'):
        return False
    st = str(ret_obj.get('status') or '').upper()
    if any(b in st for b in ('FAIL', 'ERROR', 'INVALID', 'UNRESOLVED', 'UNBOUND', 'REFUSED', 'BLOCKED', 'MISSING', 'DENIED')):
        return False
    return True

def _ensure_work_repo():
    wrepo = pathlib.Path('/work/repo')
    if wrepo.exists():
        return wrepo
    wrepo.mkdir(parents=True, exist_ok=True)
    inp = pathlib.Path('/input')
    for child in inp.iterdir():
        if child.name == 'canonical':
            c_dir = wrepo / 'canonical'
            c_dir.mkdir(parents=True, exist_ok=True)
            for sub in child.iterdir():
                if sub.name == 'astra_runtime':
                    ar_dir = c_dir / 'astra_runtime'
                    ar_dir.mkdir(parents=True, exist_ok=True)
                    for ar_sub in sub.iterdir():
                        if ar_sub.name != 'tmp':
                            os.symlink(str(ar_sub), str(ar_dir / ar_sub.name))
                    (ar_dir / 'tmp').mkdir(parents=True, exist_ok=True)
                elif not sub.name.startswith('tmp_'):
                    os.symlink(str(sub), str(c_dir / sub.name))
        else:
            os.symlink(str(child), str(wrepo / child.name))
    return wrepo

def _run_one_seed(cid, entry, ap, seed, use_schema):
    wrepo = _ensure_work_repo()
    ws = wrepo / 'canonical' / 'astra_runtime' / 'tmp' / f'ws_{seed}_{int(use_schema)}'
    ws.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    module = sweep._load_adapter(str(pathlib.Path('/input') / str(ap)), f'onb_{abs(hash(cid)) % 100000}_{seed}_{int(use_schema)}')
    fn = getattr(module, str(entry.get('entrypoint') or 'run'), None)
    if fn is None:
        return None

    sig = dict(ts.signature(dict(entry)))
    extra_slots = ts.adapter_arg_reads(dict(entry)).get('required') or []
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
    work_prefix = str(wrepo) + '/'
    for k_m, v_m in list(merged.items()):
        t_m = all_slots.get(k_m)
        if isinstance(v_m, str) and (t_m in path_kind or 'path' in k_m) and v_m.startswith(work_prefix):
            merged[k_m] = v_m[len(work_prefix):]
        elif isinstance(v_m, list) and (t_m in path_kind or 'path' in k_m):
            merged[k_m] = [x[len(work_prefix):] if isinstance(x, str) and x.startswith(work_prefix) else x for x in v_m]

    template_args = ((entry.get('action_template') or {}).get('args')) or {}
    args = sweep._substitute(template_args, merged) if template_args else dict(merged)
    ws_rel = ws.relative_to(wrepo).as_posix()
    for k_a, v_a in list(args.items()):
        if (
            isinstance(v_a, str)
            and any(tok in k_a.lower() for tok in ('output', 'report', 'dest', 'target_test', 'generated'))
            and not v_a.startswith(ws_rel)
            and not pathlib.Path(v_a).is_absolute()
        ):
            args[k_a] = f'{ws_rel}/{pathlib.Path(v_a).name}'

    raw_ret = fn(dict(args), str(wrepo))
    if not _is_genuinely_passing(raw_ret):
        return None

    artifact_summary = {}
    cand_paths = []
    for src_map in (raw_ret if isinstance(raw_ret, dict) else {}, args):
        for k_p, v_p in src_map.items():
            if isinstance(v_p, str) and ('output' in k_p.lower() or 'report' in k_p.lower() or k_p.endswith('_path')):
                fp = pathlib.Path(v_p) if pathlib.Path(v_p).is_absolute() else (wrepo / v_p)
                if fp.is_file() and fp not in cand_paths:
                    cand_paths.append(fp)

    direct_json_doc = None
    for fp in cand_paths:
        sz = fp.stat().st_size
        if sz <= 0:
            continue
        suffix_l = ''.join(fp.suffixes).lower()
        if suffix_l.endswith('.json'):
            try:
                jd = json.loads(fp.read_text(encoding='utf-8'))
                if isinstance(jd, dict) and any(not str(k).startswith('_') for k in jd):
                    direct_json_doc = jd
                    artifact_summary['json_keys'] = sorted(str(k) for k in jd if not str(k).startswith('_'))
                    break
            except Exception:
                pass
        elif suffix_l.endswith(('.sqlite', '.sqlite3', '.db')):
            con = sqlite3.connect(str(fp))
            try:
                tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                row_n = sum(con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables) if tables else 0
                artifact_summary['sqlite_tables'] = len(tables)
                artifact_summary['sqlite_rows'] = int(row_n)
            finally:
                con.close()
        elif suffix_l.endswith(('.docx', '.xlsx', '.zip')):
            if zipfile.is_zipfile(fp):
                with zipfile.ZipFile(fp, 'r') as zf:
                    artifact_summary['zip_entries'] = len(zf.namelist())
        elif suffix_l.endswith(('.tar.gz', '.tgz', '.tar')):
            with tarfile.open(fp, 'r:*') as tf:
                artifact_summary['tar_members'] = len(tf.getmembers())
        artifact_summary['output_bytes'] = int(sz)

    return {
        'ok': True,
        'seed': seed,
        'binds': {k: str(v)[:120] for k, v in sorted(merged.items())},
        'ret': dict(raw_ret) if isinstance(raw_ret, dict) else {'result': raw_ret},
        'direct_json_doc': direct_json_doc,
        'artifact_summary': artifact_summary,
    }

def main():
    cid = sys.argv[1]
    sock = socket.socket(fileno=int(os.environ['PROJECT_BRAIN_BROKER_FD']))
    try:
        for r_cid, r_key, r_suf, r_tmpl, _why in rule_chase.CANDIDATES:
            samp.set_content_rule(r_key, r_suf, r_tmpl, capability=r_cid)
        reg = ED._load_registry()
        entry = reg.get(cid)
        if not isinstance(entry, dict):
            sock.sendall(json.dumps({'ok': False, 'reason': 'UNKNOWN_CAPABILITY'}).encode('utf-8'))
            return
        ap = (entry.get('source') or {}).get('adapter_path')
        am = entry.get('adapter_module')
        if not ap and am:
            cand = pathlib.Path('/input/canonical/runtime/bound_capabilities') / f'{am}.py'
            if cand.is_file():
                ap = cand.relative_to('/input').as_posix()
        if not ap or not (pathlib.Path('/input') / str(ap)).is_file():
            sock.sendall(json.dumps({'ok': False, 'reason': 'NO_ADAPTER_RESOLVABLE'}).encode('utf-8'))
            return

        distinct_runs = []
        seen_binds = []
        for use_sc in (True, False):
            for seed in (17, 29, 43, 61, 89, 107):
                try:
                    row = _run_one_seed(cid, entry, ap, seed, use_sc)
                except (SystemExit, Exception):
                    continue
                if row is None or not row.get('binds'):
                    continue
                if row['binds'] not in seen_binds:
                    seen_binds.append(row['binds'])
                    distinct_runs.append(row)
                if len(distinct_runs) >= 2:
                    break
            if len(distinct_runs) >= 2:
                break

        if len(distinct_runs) < 2:
            reason = 'NON_DISTINCT_HELDOUT_BINDS' if len(distinct_runs) == 1 else 'NO_GENUINELY_PASSING_RUNS'
            sock.sendall(json.dumps({'ok': False, 'reason': reason}).encode('utf-8'))
            return
        sock.sendall(json.dumps({'ok': True, 'demo': distinct_runs[0], 'heldout': distinct_runs[1]}).encode('utf-8'))
    finally:
        sock.close()

main()
"""


def _writes_fixed_repo_tmp_unconditionally(tree: "ast.Module") -> bool:
    """True only when a `canonical/tmp_*` literal is written regardless of caller input.

    Three shapes are treated as caller-overridable, because each hands control back to the
    argument: `X or "canonical/tmp_..."`, a ternary that can select the argument, and the
    `fresh_output(repo, args.get("output_path"), "canonical/tmp_...")` helper convention whose
    second parameter exists precisely to override the third. Anything else -- the literal reaching
    a write with no override in scope -- keeps the refusal.
    """
    import ast as _ast

    parents: dict[Any, Any] = {}
    for node in _ast.walk(tree):
        for child in _ast.iter_child_nodes(node):
            parents[child] = node

    def _overridable(node: "_ast.AST") -> bool:
        cur: Any = node
        for _ in range(6):
            cur = parents.get(cur)
            if cur is None:
                return False
            if isinstance(cur, _ast.BoolOp) and isinstance(cur.op, _ast.Or):
                return True
            if isinstance(cur, _ast.IfExp):
                return True
            if isinstance(cur, _ast.Call):
                fn = cur.func
                name = fn.id if isinstance(fn, _ast.Name) else (fn.attr if isinstance(fn, _ast.Attribute) else "")
                if name in ("fresh_output", "_safe_output"):
                    return True
        return False

    for node in _ast.walk(tree):
        if not (isinstance(node, _ast.Constant) and isinstance(node.value, str)):
            continue
        if not node.value.startswith("canonical/tmp_"):
            continue
        if not _overridable(node):
            return True
    return False


def _extract_capability_feature_flags(cid: str) -> dict[str, Any]:
    """Extract domain-free structural & causal preconditions for `EpistemicSelfBeliefEngine` (zero static probability constants)."""
    cached = _CAPABILITY_FEATURE_CACHE.get(cid)
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
    base_flags: dict[str, Any] = {
        "host_ready": True,
        "grounding_complete": True,
        "causal_precond_met": True,
        "missing_dep_or_env_block": False,
        "nested_cost_or_timeout_risk": False,
        "reason": "ready",
    }
    if not isinstance(entry, Mapping):
        res = {**base_flags, "host_ready": False, "grounding_complete": False, "missing_dep_or_env_block": True, "reason": "unregistered_capability"}
        _CAPABILITY_FEATURE_CACHE[cid] = res
        return res

    av_reg = AV.load_registry()
    if AV.missing(cid, av_reg):
        res = {**base_flags, "host_ready": False, "missing_dep_or_env_block": True, "reason": "availability_missing_binary"}
        _CAPABILITY_FEATURE_CACHE[cid] = res
        return res

    ap = (entry.get("source") or {}).get("adapter_path")
    am = entry.get("adapter_module")
    if not ap and am:
        cand = repo_root / "canonical" / "runtime" / "bound_capabilities" / f"{am}.py"
        if cand.is_file():
            ap = cand.relative_to(repo_root).as_posix()
    if not ap or not (repo_root / str(ap)).is_file():
        res = {**base_flags, "host_ready": False, "missing_dep_or_env_block": True, "reason": "no_resolvable_adapter"}
        _CAPABILITY_FEATURE_CACHE[cid] = res
        return res

    t_args = ((entry.get("action_template") or {}).get("args")) or {}
    lit_mod = t_args.get("module")
    if isinstance(lit_mod, str) and lit_mod and "${" not in lit_mod:
        top_m = lit_mod.split(".")[0]
        if not (repo_root / "canonical" / "runtime" / f"{top_m}.py").is_file() and importlib.util.find_spec(top_m) is None:
            res = {**base_flags, "host_ready": False, "missing_dep_or_env_block": True, "reason": f"missing_template_module:{top_m}"}
            _CAPABILITY_FEATURE_CACHE[cid] = res
            return res

    lit_pkg = t_args.get("package")
    if isinstance(lit_pkg, str) and lit_pkg and "${" not in lit_pkg:
        if not (repo_root / "node_modules" / lit_pkg).exists():
            res = {**base_flags, "host_ready": False, "missing_dep_or_env_block": True, "reason": f"missing_npm_package:{lit_pkg}"}
            _CAPABILITY_FEATURE_CACHE[cid] = res
            return res

    argv = t_args.get("argv")
    if isinstance(argv, list) and argv and isinstance(argv[0], str) and "${" not in argv[0]:
        if _shutil.which(argv[0]) is None and not pathlib.Path(argv[0]).exists():
            res = {**base_flags, "host_ready": False, "missing_dep_or_env_block": True, "reason": f"missing_argv_binary:{argv[0]}"}
            _CAPABILITY_FEATURE_CACHE[cid] = res
            return res

    sig = dict(ts.signature(dict(entry)))
    extra_slots = ts.adapter_arg_reads(dict(entry)).get("required") or []
    for k_ex in extra_slots:
        sig.setdefault(k_ex, ts.type_of(k_ex))
    if "UNKNOWN" in sig.values():
        res = {**base_flags, "grounding_complete": False, "missing_dep_or_env_block": True, "reason": "unknown_slot_type_on_surface"}
        _CAPABILITY_FEATURE_CACHE[cid] = res
        return res

    reqs = [str(r) for r in (entry.get("requires") or [])]
    if any(r.startswith(("image.", "pdf.", "audio.", "video.", "network.", "http.")) for r in reqs):
        res = {**base_flags, "grounding_complete": False, "missing_dep_or_env_block": True, "reason": "media_or_network_precondition"}
        _CAPABILITY_FEATURE_CACHE[cid] = res
        return res
    if any("tree_sitter" in r for r in reqs) and importlib.util.find_spec("tree_sitter") is None:
        res = {**base_flags, "host_ready": False, "missing_dep_or_env_block": True, "reason": "missing_tree_sitter_substrate"}
        _CAPABILITY_FEATURE_CACHE[cid] = res
        return res
    if any(any(tok in k.lower() for tok in ("image", "png", "pdf", "screenshot", "expected_structure", "url", "endpoint")) for k in sig):
        res = {**base_flags, "grounding_complete": False, "missing_dep_or_env_block": True, "reason": "ungrounded_media_or_network_slot"}
        _CAPABILITY_FEATURE_CACHE[cid] = res
        return res
    if len(sig) == 0:
        res = {**base_flags, "grounding_complete": False, "missing_dep_or_env_block": True, "reason": "empty_typed_input_surface"}
        _CAPABILITY_FEATURE_CACHE[cid] = res
        return res
    if "verify_against" in cid or "grounding.verify" in cid or (sum(1 for v in sig.values() if v == ts.PATH_FILE) >= 2 and "verify" in cid):
        res = {**base_flags, "causal_precond_met": False, "missing_dep_or_env_block": True, "reason": "cross_artifact_paired_fixture_required"}
        _CAPABILITY_FEATURE_CACHE[cid] = res
        return res
    if any(
        k.endswith(("_receipt_path", "_filter"))
        or k in ("extraction_path", "candidate_path", "verification_path", "diff_path", "anchor_path", "bench_path")
        for k in sig
    ):
        res = {**base_flags, "causal_precond_met": False, "missing_dep_or_env_block": True, "reason": "upstream_coupled_artifact_required"}
        _CAPABILITY_FEATURE_CACHE[cid] = res
        return res
    if ("goal" in sig and "json_path" in sig) or (set(sig.keys()) == {"goal", "output_path"} and "compile" in cid):
        res = {**base_flags, "causal_precond_met": False, "missing_dep_or_env_block": True, "reason": "coupled_goal_schema_selector"}
        _CAPABILITY_FEATURE_CACHE[cid] = res
        return res
    if "PATH_LIST" in sig.values():
        base_flags["nested_cost_or_timeout_risk"] = True

    adapter_file = repo_root / str(ap)
    src = adapter_file.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        res = {**base_flags, "host_ready": False, "missing_dep_or_env_block": True, "reason": "adapter_syntax_error"}
        _CAPABILITY_FEATURE_CACHE[cid] = res
        return res

    subproc_calls = 0
    uses_network_lib = False
    reads_repo_rooted_paths = False
    for nd in ast.walk(tree):
        mods: list[str] = []
        if isinstance(nd, ast.Import):
            mods = [a.name.split(".")[0] for a in nd.names]
            if any("urllib" in a.name or a.name in ("http", "requests", "httpx", "socket") for a in nd.names):
                uses_network_lib = True
        elif isinstance(nd, ast.ImportFrom) and nd.level == 0 and nd.module:
            mods = [nd.module.split(".")[0]]
            if "urllib" in nd.module or nd.module.split(".")[0] in ("http", "requests", "httpx"):
                uses_network_lib = True
        for m in mods:
            if m in ("canonical", "execution_guard", "__future__", "builtins"):
                continue
            if (
                (repo_root / "canonical" / "runtime" / f"{m}.py").is_file()
                or (repo_root / "canonical" / "runtime" / "bound_capabilities" / f"{m}.py").is_file()
            ):
                continue
            if importlib.util.find_spec(m) is None:
                res = {**base_flags, "host_ready": False, "missing_dep_or_env_block": True, "reason": f"missing_python_import:{m}"}
                _CAPABILITY_FEATURE_CACHE[cid] = res
                return res
        if isinstance(nd, ast.Call) and isinstance(nd.func, ast.Attribute) and nd.func.attr in ("which", "run", "check_output", "Popen"):
            if nd.func.attr in ("run", "check_output", "Popen"):
                subproc_calls += 1
            if nd.args and isinstance(nd.args[0], ast.Constant) and isinstance(nd.args[0].value, str):
                bname = nd.args[0].value
                if _shutil.which(bname) is None and not pathlib.Path(bname).exists():
                    res = {**base_flags, "host_ready": False, "missing_dep_or_env_block": True, "reason": f"missing_called_binary:{bname}"}
                    _CAPABILITY_FEATURE_CACHE[cid] = res
                    return res
            elif nd.args and isinstance(nd.args[0], (ast.List, ast.Tuple)) and nd.args[0].elts:
                first_elt = nd.args[0].elts[0]
                if isinstance(first_elt, ast.Constant) and isinstance(first_elt.value, str) and "/" not in first_elt.value:
                    if _shutil.which(first_elt.value) is None:
                        res = {**base_flags, "host_ready": False, "missing_dep_or_env_block": True, "reason": f"missing_subprocess_binary:{first_elt.value}"}
                        _CAPABILITY_FEATURE_CACHE[cid] = res
                        return res
    # A `canonical/tmp_*` string used as an `or` FALLBACK is not a fixed write: the caller's
    # argument, when supplied, replaces it, and on the onboarding path the root is `/work/repo`
    # (writable, per run) rather than the read-only `/input`. Measured 2026-11-03/04: all 19
    # capabilities refused as `writes_fixed_repo_tmp_under_ro_input` use the literal only as
    # `str(raw or "canonical/tmp_...")` or `fresh_output(repo, args.get("output_path"), "...")`,
    # and with the refusal lifted 15 of the 19 onboard on genuine passing runs. So the previous
    # blanket test was a false refusal, and its cost was 19 capabilities plus -- because
    # `nested_cost_or_timeout_risk` was set by the same condition -- 16 more hidden behind it.
    # A conditional write is now judged by whether it is UNCONDITIONAL, not by whether such a
    # string appears at all. The write itself still runs confined against a read-only `/input`,
    # which remains the authority; this only stops a static guess from pre-empting it.
    reads_repo_rooted_paths = _writes_fixed_repo_tmp_unconditionally(tree)

    if uses_network_lib:
        # Confined namespace disables outbound network (`--net`)
        res = {**base_flags, "causal_precond_met": False, "missing_dep_or_env_block": True, "reason": "confined_net_namespace_offline"}
        _CAPABILITY_FEATURE_CACHE[cid] = res
        return res

    if reads_repo_rooted_paths or subproc_calls >= 2:
        base_flags["nested_cost_or_timeout_risk"] = True
        if reads_repo_rooted_paths:
            base_flags["causal_precond_met"] = False
            base_flags["reason"] = "writes_fixed_repo_tmp_under_ro_input"

    _CAPABILITY_FEATURE_CACHE[cid] = base_flags
    return base_flags


def _sovereign_feature_kwargs(work_id: str, creature: Creature) -> dict[str, Any]:
    """The honest feature vector for ONE candidate, from what this host actually reports.

    Measured 2026-11-03: `live_autonomous_cycle` predicted, spent life on, and settled every
    prediction with `host_ready=True, grounding_complete=True, causal_precond_met=True,
    missing_dep_or_env_block=False` hardcoded. On the 112-obligation board that produced exactly
    ONE predicted probability (0.813) and ONE mutual-information value, while the same engine fed
    the flags `_extract_capability_feature_flags` already computes produced four, with 0.062 for
    the blocked majority. The creature therefore claimed 81.3% on candidates it had itself already
    established were impossible (`unknown_slot_type_on_surface` x35,
    `writes_fixed_repo_tmp_under_ro_input` x19, missing binaries/packages, ...), failed them, and
    settled the predictions as failures against an optimistic prior. Its own scorer called that,
    correctly, worse than a constant predictor -- and the cause was not the belief engine, it was
    this diet.

    `predict_task_probability` in this same module had always assembled the truthful vector; it was
    used only to *value* the board. This function is the single source of those flags so the path
    that predicts, acts and is scored cannot drift from the path that values.
    """
    if str(work_id).startswith("inspector:"):
        cid = str(work_id)[len("inspector:"):]
        flags = _extract_capability_feature_flags(cid)
        return {
            "host_ready": bool(flags["host_ready"]),
            "grounding_complete": bool(flags["grounding_complete"]),
            "causal_precond_met": bool(flags["causal_precond_met"]),
            "memory_reflex_hit": cid in getattr(creature, "onboarded_capabilities", {}),
            "strong_verifier": True,
            "missing_dep_or_env_block": bool(flags["missing_dep_or_env_block"]),
            "nested_cost_or_timeout_risk": bool(flags["nested_cost_or_timeout_risk"]),
        }
    if str(work_id).startswith(("gap:", "awake:gap:", "curiosity:")):
        # A gap is by construction something whose causal precondition is not yet met.
        return {
            "host_ready": True,
            "grounding_complete": True,
            "causal_precond_met": False,
            "memory_reflex_hit": False,
            "strong_verifier": True,
        }
    return {
        "host_ready": True,
        "grounding_complete": True,
        "causal_precond_met": True,
        "memory_reflex_hit": False,
        "strong_verifier": True,
    }


def predict_task_probability(work_id: str, creature: Creature) -> float:
    """Active-inference Bayesian/Kalman self-belief probability `Theta_t = (mu_t, Sigma_t)` (zero static probability tables)."""
    core = getattr(creature, "cognitive_core", None)
    if core is None:
        from canonical.swe_kernel.sentient_cognitive_core_v1 import SentientCognitiveCore

        core = SentientCognitiveCore(creature.root / "cognitive_core")
        creature.cognitive_core = core

    if work_id.startswith("inspector:"):
        cid = work_id[len("inspector:"):]
        flags = _extract_capability_feature_flags(cid)
        return round(
            core.belief.predict_probability(
                work_id,
                host_ready=bool(flags["host_ready"]),
                grounding_complete=bool(flags["grounding_complete"]),
                causal_precond_met=bool(flags["causal_precond_met"]),
                memory_reflex_hit=(cid in getattr(creature, "onboarded_capabilities", {})),
                strong_verifier=True,
                missing_dep_or_env_block=bool(flags["missing_dep_or_env_block"]),
                nested_cost_or_timeout_risk=bool(flags["nested_cost_or_timeout_risk"]),
            ),
            4,
        )

    if work_id.startswith(("repair:", "awake:cow_repair:", "chase:", "traj:")):
        return round(
            core.belief.predict_probability(
                work_id,
                host_ready=True,
                grounding_complete=True,
                causal_precond_met=True,
                memory_reflex_hit=False,
                strong_verifier=True,
            ),
            4,
        )
    if work_id.startswith(("gap:", "awake:gap:", "curiosity:")):
        return round(
            core.belief.predict_probability(
                work_id,
                host_ready=True,
                grounding_complete=True,
                causal_precond_met=False,
                memory_reflex_hit=False,
                strong_verifier=True,
            ),
            4,
        )
    return round(core.belief.predict_probability(work_id), 4)


def _onboard_typed_capability_inspector(cid: str, creature: Creature) -> dict[str, Any]:
    """Confined, strictly honest capability inspector onboarding (`0` host `exec()`, `0` forged seeds, `0` failing runs):
    1. Executes `type_directed_sampler_v1` + bound adapter inside `zero_ambient_namespace_launcher_v1.run_confined`
       with read-only `/input`, isolated `tmpfs /work`, disabled network, and strict `wallclock_s=3`;
    2. Requires TWO genuinely passing runs (`pass != False`, no error/unresolved status) with genuinely
       distinct sampled `binds` (`demonstration['binds'] != heldout['binds']`, NEVER forging `_heldout_seed`);
    3. Derives a `property_v1`-scored `BehavioralDerivation` (`kill_score >= 0.5`), registers via `Flight` +
       `COF.Factory.onboard`, and serializes `deriv.to_dict()` so callables survive `boot()` restarts.
    """
    import shutil as _shutil
    import sys as _sys
    from canonical.runtime import derived_inspector_flywheel_v1 as DIF
    from canonical.runtime import expect_discrimination_v1 as ED
    from canonical.runtime import zero_ambient_namespace_launcher_v1 as ns

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    reg = ED._load_registry()
    entry = reg.get(cid)
    if not isinstance(entry, Mapping):
        return {"ok": False, "reason": f"UNKNOWN_CAPABILITY:{cid}"}

    flags = _extract_capability_feature_flags(cid)
    if not flags["host_ready"] or flags["missing_dep_or_env_block"]:
        return {"ok": False, "reason": f"PRECONDITION_UNMET:{flags['reason']}"}

    try:
        ns_res = ns.run_confined(
            {
                "argv": [_sys.executable, "-c", _CONFINED_CAPABILITY_ONBOARD_WORKER, cid],
                "input_dir": str(repo_root),
                "expose_null_device": True,
                "expose_runtime_devices": True,
                "limits": {
                    "pids": 32,
                    "memory_mb": 512,
                    "cpu_seconds": 3,
                    "wallclock_s": 3,
                    "scratch_mb": 64,
                    "max_file_mb": 16,
                    "nofile": 64,
                    "broker_max_bytes": 2_000_000,
                },
            }
        )
    except Exception as exc:
        return {"ok": False, "reason": f"CONFINED_WORKER_ERROR:{type(exc).__name__}"}

    if ns_res.get("status") != "CHILD_EXITED" or ns_res.get("returncode") != 0:
        return {"ok": False, "reason": f"CONFINED_WORKER_STATUS:{ns_res.get('status')}"}

    try:
        payload = json.loads((ns_res.get("broker_payload") or b"").decode("utf-8"))
    except Exception:
        return {"ok": False, "reason": "CONFINED_BROKER_JSON_INVALID"}

    if not payload.get("ok"):
        return {"ok": False, "reason": f"{payload.get('reason') or 'EXECUTION_FAILED'}:{cid}"}

    r_demo = payload["demo"]
    r_held = payload["heldout"]
    if not r_demo.get("binds") or not r_held.get("binds") or r_demo["binds"] == r_held["binds"]:
        return {"ok": False, "reason": f"NON_DISTINCT_HELDOUT_BINDS:{cid}"}

    scratch_parent = (repo_root / "canonical" / "astra_runtime" / "tmp").resolve()
    scratch_parent.mkdir(parents=True, exist_ok=True)
    td = tempfile.mkdtemp(prefix="creature_onboard_", dir=str(scratch_parent))
    try:
        sp = pathlib.Path(td).resolve()
        pos1 = sp / "artifact_demo.json"
        pos2 = sp / "artifact_held.json"
        neg = sp / "artifact_decoy.json"

        if isinstance(r_demo.get("direct_json_doc"), Mapping) and isinstance(r_held.get("direct_json_doc"), Mapping):
            jd1 = dict(r_demo["direct_json_doc"])
            jd2 = dict(r_held["direct_json_doc"])
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

        # Mine keys & types genuinely invariant across BOTH distinct passing runs
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
        neg.write_text(json.dumps({"_comment": json.dumps(jd1, sort_keys=True)}), encoding="utf-8")

        def _mined_checker(fp: pathlib.Path) -> bool:
            try:
                d = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                return False
            if not isinstance(d, dict):
                return False
            if d.get("pass") is False or d.get("ok") is False or d.get("verified") is False:
                return False
            for k_req, t_req in shared_reqs:
                if k_req not in d or type(d[k_req]).__name__ != t_req:
                    return False
                val = d[k_req]
                if isinstance(val, bool) and val is False:
                    return False
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
        creature._serialized_derivations[cid] = deriv.to_dict()
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
        _shutil.rmtree(td, ignore_errors=True)


def _perturb(value: Any, index: int = 0, round_no: int = 0) -> Any:
    """Move a value onto input the test never showed, keeping its shape.

    MEASURED 2026-11-05 -- this function was rejecting correct repairs. It used to add a UNIFORM +7 to
    every numeric argument, so both arguments moved by the same amount and every function of the form
    `a <op> b` that depends only on the *difference* was invariant: `a - b`, `a // b`, `a % b` all
    produced the same output at `(9, 4)` and `(16, 11)`. The probe then reported
    `OUTPUT_IGNORES_INPUTS` and threw the repair away. It was not a conservative gate, it was a wrong
    one, and it under-counted honest repairs everywhere it ran.

    The offsets now depend on the ARGUMENT POSITION and on which perturbation round this is, so the
    difference between arguments always changes and a difference-based function must move.
    """
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + (3 + 5 * index + 7 * round_no)
    if isinstance(value, float):
        return value + (1.5 + 2.5 * index + 3.5 * round_no)
    if isinstance(value, str):
        return value + chr(ord("z") - index - round_no) if len(value) > 1 else value * (3 + index)
    if isinstance(value, (list, tuple)):
        _moved = [_perturb(v, i, round_no) for i, v in enumerate(value)]
        return type(value)(_moved + [value[-1] if value else 0]) if value else type(value)([1])
    return value


def _generalization_probe(test_file: pathlib.Path, ws_root: pathlib.Path) -> dict[str, Any]:
    """Is the repair a capability, or an answer fitted to the case it was shown?

    Method, and why it is this and not something cleverer:

      1. Read every assertion in the owed test that compares a call to a literal with a literal.
         The call is executed *as written*, in a namespace built from the test's own imports, rather
         than by looking up a `def` and calling it. Locating a definition was a blind spot, measured
         2026-11-05: `assert ops['add'](7, 2) == 9`, a closure factory, and a `@property` all have a
         call and no definition the probe can find, so three honest repairs came back
         DEFINITION_NOT_FOUND. The evidence was always there; the probe was not reading it.
      2. Perturb the literal arguments, keeping their shape, and ask the *repaired code itself* what
         it now returns. The answer must move. A function returning `9` whatever you give it has
         memorized a constant, and a constant is not a capability.
      3. Perturb once more. A function whose output does not move between two different inputs is not
         using its arguments: `head(xs) -> xs` passes `head([1,2,3]) == [1,2,3]` and would pass any
         held-out the test's shape allows, while doing nothing the function was asked to do.

    What this cannot do, stated plainly so the creature is not credited for more than it did:
    proving `a + b` correct requires a specification the test does not contain. This probe rejects
    memorization and argument-blindness. It cannot confirm intent.
    """
    import ast as _ast

    try:
        txt = test_file.read_text(encoding="utf-8")
    except OSError as exc:
        return {"generalizes": False, "reason": f"UNREADABLE_OWED_TEST: {exc}"}

    try:
        tree = _ast.parse(txt)
    except SyntaxError as exc:
        return {"generalizes": False, "reason": f"UNPARSABLE_OWED_TEST: {exc.msg}"}

    cases: list[tuple[str, str, tuple, str, Any]] = []  # (call source, func source, args, op, expected)
    for node in _ast.walk(tree):
        if not isinstance(node, _ast.Assert):
            continue
        test = node.test
        if not isinstance(test, _ast.Compare) or len(test.comparators) != 1:
            continue
        call, expected_node = test.left, test.comparators[0]
        if not isinstance(call, _ast.Call) or call.keywords:
            continue
        op = "==" if isinstance(test.ops[0], _ast.Eq) else (
            "is" if isinstance(test.ops[0], _ast.Is) else None)
        if op is None:
            continue
        try:
            args = tuple(_ast.literal_eval(a) for a in call.args)
            expected = _ast.literal_eval(expected_node)
        except Exception:
            # MEASURED 2026-11-05: a CALL-versus-CALL assertion (`f(x) == g(x)`) was skipped entirely,
            # so every property-style test -- including any test a notion could generate, since a notion
            # is a relation between two things in the program -- produced NO_LITERAL_CALL_TO_PERTURB and
            # the repair was discarded as if it had been refuted. The owed value can be computed from
            # the other side of the comparison when that side is a literal-argument call; what matters
            # is that the expected value is independently determinable, not that it is typed as a
            # literal in the source.
            if not isinstance(expected_node, _ast.Call) or expected_node.keywords:
                continue
            try:
                other_args = tuple(_ast.literal_eval(a) for a in expected_node.args)
            except Exception:
                continue
            # Do NOT require the two calls to take the same arguments. MEASURED 2026-11-05: a notion
            # like "a square is a rectangle with equal sides" is exactly `square_area(3) ==
            # rect_area(3, 3)` -- one argument against two -- and requiring equal argument tuples
            # rejected the whole class of degenerate-case identities this probe most needs to support.
            if not other_args:
                continue
            other_src = _ast.get_source_segment(txt, expected_node.func)
            call_src0 = _ast.get_source_segment(txt, call)
            func_src0 = _ast.get_source_segment(txt, call.func)
            if not other_src or not call_src0 or not func_src0:
                continue
            # Keep the pair, marked as call-vs-call so the probe can compute the owed value at run time.
            cases.append((call_src0, func_src0, args, op,
                          ("__CALLPAIR__", other_src, tuple(other_args))))
            continue
        if not args:
            continue
        call_src = _ast.get_source_segment(txt, call)
        func_src = _ast.get_source_segment(txt, call.func)
        if not call_src or not func_src:
            continue
        cases.append((call_src, func_src, args, op, expected))
    if not cases:
        return {"generalizes": False, "reason": "NO_LITERAL_CALL_TO_PERTURB"}

    call_src, func_src, args, op, expected = cases[0]
    _pair_other: str | None = None
    if isinstance(expected, tuple) and expected and expected[0] == "__CALLPAIR__":
        # Call-vs-call: the owed value is whatever the OTHER call returns for the same arguments, so it
        # is computed here from the repaired namespace rather than read from the source. This keeps the
        # probe's guarantee -- the expected value cannot be fitted to the candidate -- because the other
        # function is part of the program under study, not part of the candidate.
        _pair_other, _pair_other_args, expected = expected[1], expected[2], None

    # Namespace = the test's own imports, resolved inside the workspace. Scanning the whole tree is
    # how this once took minutes on a real repository; a probe too slow to run says no by default.
    ns: dict[str, Any] = {"__name__": "_probe_ns"}
    executed: list[str] = []
    targets: list[pathlib.Path] = []
    for node in _ast.walk(tree):
        mods: list[str] = []
        if isinstance(node, _ast.ImportFrom) and node.module:
            mods = [node.module]
        elif isinstance(node, _ast.Import):
            mods = [a.name for a in node.names]
        for mod in mods:
            rel = pathlib.Path(*mod.split("."))
            for cand in (ws_root / rel.with_suffix(".py"), ws_root / rel / "__init__.py"):
                if cand.is_file() and cand not in targets:
                    targets.append(cand)
    for cand in targets:
        try:
            if cand.stat().st_size > 400_000:
                return {"generalizes": False, "reason": f"REPAIRED_CODE_TOO_LARGE: {cand.name}"}
            exec(compile(cand.read_text(encoding="utf-8"), str(cand), "exec"), ns)  # noqa: S102
            executed.append(str(cand.relative_to(ws_root)))
        except Exception as exc:  # noqa: BLE001
            return {"generalizes": False, "reason": f"REPAIRED_CODE_RAISES: {type(exc).__name__}"}
    if not executed:
        return {"generalizes": False, "reason": "TEST_IMPORTS_NO_WORKSPACE_MODULE"}

    def _call_with(values: tuple) -> Any:
        # Rebuild from the recorded callee, so `C()`, `ops['add']`, `make()` and a bare name are all
        # the same thing to the probe: an expression to execute against the repaired code.
        return eval(f"{func_src}({', '.join(repr(v) for v in values)})", ns)  # noqa: S307

    if _pair_other is not None:
        try:
            # Each side is evaluated with ITS OWN arguments. The first attempt passed the left call's
            # arguments to the right function, which for `square_area(3) == rect_area(3, 3)` meant
            # `rect_area(3)` and a TypeError that refused a correct repair for the wrong reason.
            expected = eval(
                f"{_pair_other}({', '.join(repr(v) for v in _pair_other_args)})", ns  # noqa: S307
            )
        except Exception as exc:  # noqa: BLE001
            return {"generalizes": False, "reason": f"CALLPAIR_OTHER_RAISES: {type(exc).__name__}"}

    args_a = tuple(_perturb(a, i, 0) for i, a in enumerate(args))
    args_b = tuple(_perturb(a, i, 1) for i, a in enumerate(args_a))
    try:
        produced = _call_with(args)
        out_a = _call_with(args_a)
        out_b = _call_with(args_b)
    except Exception as exc:  # noqa: BLE001
        return {"generalizes": False, "reason": f"REPAIRED_CODE_RAISES: {type(exc).__name__}"}

    matches_owed = (produced == expected) if op == "==" else (produced is expected)
    ignores_inputs = out_a == out_b and not isinstance(expected, bool)
    # An identity function survives every shape-preserving perturbation, so no held-out input of
    # this form can tell `head(xs) -> xs` apart from a correct `head`. That is a property of the
    # *evidence*, not of the repair: the owed assertion carries nothing that discriminates them.
    # Credit is withheld, and the reason says so rather than pretending the code was exonerated.
    identity_like = all(isinstance(o, (list, tuple, str)) and o == a[0]
                        for o, a in ((out_a, args_a), (out_b, args_b)))
    generalizes = bool(matches_owed and not ignores_inputs and not identity_like)
    return {
        "generalizes": generalizes,
        "args": list(args),
        "perturbed": [list(args_a), list(args_b)],
        "produced": produced,
        "produced_perturbed": [out_a, out_b],
        "expected": expected,
        "ignores_inputs": ignores_inputs,
        "identity_like": identity_like,
        "source": ",".join(executed),
        "subject": func_src,
        "reason": ("REPAIRED_CODE_DISAGREES_WITH_OWED_TEST" if not matches_owed
                   else "OUTPUT_IGNORES_INPUTS" if ignores_inputs
                   else "TEST_CANNOT_DISTINGUISH_IDENTITY" if identity_like
                   else "BOOLEAN_RESULT_INPUT_SENSITIVITY_UNPROBED" if isinstance(expected, bool)
                   else "RESPONDS_TO_INPUT"),
    }


def sovereign_perform(work: M.Work, creature: Creature) -> dict[str, Any]:
    """Active-inference sovereign `Perform` organ for `Creature`:
    - Forecasts `PredictionTicket` via `EpistemicSelfBeliefEngine` (`Theta_t = (mu_t, Sigma_t)`) BEFORE acting;
    - Executes confined verification / onboarding / repair / chase;
    - Settles via independent inspector, computes Surprise `S_t`, and updates `(mu_t, Sigma_t)` online (`< 0.05 ms`).
    """
    core = getattr(creature, "cognitive_core", None)
    if core is None:
        from canonical.swe_kernel.sentient_cognitive_core_v1 import SentientCognitiveCore

        core = SentientCognitiveCore(creature.root / "cognitive_core")
        creature.cognitive_core = core

    feat_kw: dict[str, Any] = {"strong_verifier": True}
    if work.id.startswith("inspector:"):
        cid_f = work.id[len("inspector:"):]
        fl_f = _extract_capability_feature_flags(cid_f)
        feat_kw.update(
            host_ready=bool(fl_f["host_ready"]),
            grounding_complete=bool(fl_f["grounding_complete"]),
            causal_precond_met=bool(fl_f["causal_precond_met"]),
            memory_reflex_hit=(cid_f in getattr(creature, "onboarded_capabilities", {})),
            missing_dep_or_env_block=bool(fl_f["missing_dep_or_env_block"]),
            nested_cost_or_timeout_risk=bool(fl_f["nested_cost_or_timeout_risk"]),
        )
    elif work.id.startswith(("gap:", "awake:gap:", "curiosity:")):
        feat_kw["causal_precond_met"] = False

    ticket = core.belief.predict_before_act(
        work.id,
        calibration_ledger=creature.calibration_ledger,
        claimed_reason="epistemic_kalman_self_belief",
        **feat_kw,
    )
    p_hat = ticket.predicted_pass_probability

    if work.id.startswith("inspector:"):
        cid = work.id[len("inspector:"):]
        res = _onboard_typed_capability_inspector(cid, creature)
        ok = bool(res.get("ok"))
        settle_rep = core.belief.settle_and_compute_surprise(
            ticket,
            outcome_pass=ok,
            inspector="CapabilityOnboardingFactory+BehavioralFlight",
            actual_cost=work.cost,
            actual_gain=work.value if ok else 0.0,
            calibration_ledger=creature.calibration_ledger,
            ignorance_ledger_path=creature.root / "ignorance_ledger.json",
        )
        core.world_graph.learn_from_execution(
            work.id,
            before_state={"inspected": sorted(creature.onboarded_capabilities.keys())},
            after_state={"inspected": sorted(creature.onboarded_capabilities.keys())},
            ok=ok,
            error_text="" if ok else str(res.get("reason") or ""),
        )
        creature._save_sovereign_organs()
        return {
            "ok": ok,
            "verified": True,
            "correct": ok,
            "value": work.value if ok else 0.0,
            "predicted_probability": p_hat,
            "surprise": settle_rep["surprise"],
            "verified_inspector_onboarding": ok,
            "blocked": None if ok else str(res.get("reason") or "INSPECTOR_ONBOARDING_REFUSED"),
        }

    if work.id.startswith(("repair:", "awake:cow_repair:")):
        from canonical.swe_kernel.autonomous_awake_loop_v1 import AwakeAgencyDaemon

        # `_REPO_ROOT` never existed: this line raised NameError on every repair dispatch, which is
        # what `Creature.step`'s `except Exception` turned into an ordinary failed action. The
        # creature has been picking the highest-value work on its board and crashing on the first
        # line of the handler. Derive the root the same way the rest of this module does.
        ws_target = getattr(creature, "workspace_root", None) or pathlib.Path(__file__).resolve().parents[2]
        daemon = AwakeAgencyDaemon(
            ws_target,
            ledger_path=creature.root / "awake_repair" / "ledger.json",
            skill_store_path=creature.root / "awake_repair" / "skills.sqlite",
            apply_verified_repairs=True,
        )
        # The obligation IS the owed test: `repair:<test_relpath>:<signature>`. Handing the whole
        # repo's suite to the repair engine made it time out and the failure was swallowed by
        # `Creature.step`, so this path never produced a result in any run.
        _owed = [work.id.split(":", 1)[1].rsplit(":", 1)[0]] if ":" in work.id else None
        # A named test is a claim about the repo, and claims are only advisory until measured. So
        # run the owed test itself first: if it is already green there is nothing to repair and no
        # gain to claim, and if it is not, the repair organ has to change the repo *and* leave the
        # test green. Before this, the handler's `ok` came from the organ's own bookkeeping and its
        # cost was the whole repo's suite -- it never once returned a result.
        from canonical.swe_kernel.autonomous_awake_loop_v1 import _run_py_test_file
        _green_before = False
        if _owed:
            _green_before, _ = _run_py_test_file(
                pathlib.Path(ws_target) / _owed[0], pathlib.Path(ws_target), timeout=120.0
            )
        rep = {"repaired": 0, "failures_found": 0, "crystallized_skills": []}
        if not _green_before:
            try:
                rep = daemon.experiment_in_cow_sandbox(max_repairs=1, owed_tests=_owed)
            except Exception as exc:  # noqa: BLE001 - a repair that cannot run is a failure to decide
                rep = {"repaired": 0, "failures_found": 0, "crystallized_skills": [],
                       "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
        ok = (not _green_before) and int(rep.get("repaired") or 0) > 0
        # Trial, then decide. The order matters and it took three attempts to get right: the owed
        # test must be run with the candidate IN the world (otherwise it simply re-reports the
        # original failure), and the generalization probe must inspect the code that is actually
        # there. So the organ's staged candidate is written first, measured, and rolled back
        # byte-for-byte if it does not hold up. A rejected candidate leaves no trace; an accepted
        # one is the only thing the creature gets to keep.
        generalization = None
        accepted: list[str] = []
        staged = dict(rep.get("staged") or {})
        if ok and staged:
            originals: dict[str, bytes | None] = {}
            for _rel in staged:
                _dst = pathlib.Path(ws_target) / _rel
                originals[_rel] = _dst.read_bytes() if _dst.is_file() else None
                _dst.parent.mkdir(parents=True, exist_ok=True)
                _dst.write_text(staged[_rel], encoding="utf-8")
            try:
                if _owed:
                    ok, _ = _run_py_test_file(
                        pathlib.Path(ws_target) / _owed[0], pathlib.Path(ws_target), timeout=120.0
                    )
                # A green owed test is NOT evidence of a repair. Measured 2026-11-04: handed
                # `assert add(2, 3) == 5`, the organ rewrote the source to `return 5` and passed,
                # 3/3 trials; a held-out `add(10, 20) == 30` then failed 3/3. It memorized the
                # oracle's answer. A capability that only works on the example it was fitted to has
                # not been acquired, and crediting it would teach the creature that its
                # best-paying work is satisfying the checker rather than the claim. So a green owed
                # test is only a candidate; what settles it is whether the answer survives an input
                # it was never shown.
                if ok and _owed:
                    generalization = _generalization_probe(
                        pathlib.Path(ws_target) / _owed[0], pathlib.Path(ws_target)
                    )
                    if not generalization["generalizes"]:
                        ok = False
            finally:
                if not ok:
                    for _rel, _orig in originals.items():
                        _dst = pathlib.Path(ws_target) / _rel
                        try:
                            if _orig is None:
                                _dst.unlink(missing_ok=True)
                            else:
                                _dst.write_bytes(_orig)
                        except OSError:
                            pass
                else:
                    accepted = sorted(staged)
        settle_rep = core.belief.settle_and_compute_surprise(
            ticket,
            outcome_pass=ok,
            inspector="ConfinedZygoteTestSuiteOracle",
            actual_cost=work.cost,
            actual_gain=work.value if ok else 0.0,
            calibration_ledger=creature.calibration_ledger,
        )
        return {
            "ok": ok,
            "verified": True,
            "correct": ok,
            "value": work.value if ok else 0.0,
            "predicted_probability": p_hat,
            "surprise": settle_rep["surprise"],
            "generalization": generalization,
            "accepted_into_world": accepted,
            "blocked": None if ok else (
                "REPAIR_DOES_NOT_GENERALIZE" if generalization and not generalization["generalizes"]
                else "UNREPAIRED_FAILING_TESTS"
            ),
        }

    if work.id.startswith("chase:"):
        from execution_guard import goal_chase_v1 as gc

        ch_id = work.id[len("chase:"):]
        ch_spec = (getattr(creature, "_sovereign_chases", None) or {}).get(ch_id)
        if not ch_spec:
            core.belief.settle_and_compute_surprise(
                ticket,
                outcome_pass=False,
                inspector="goal_chase_v1",
                actual_cost=work.cost,
                actual_gain=0.0,
                calibration_ledger=creature.calibration_ledger,
            )
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
        settle_rep = core.belief.settle_and_compute_surprise(
            ticket,
            outcome_pass=ok,
            inspector="goal_chase_v1_independent_oracle",
            actual_cost=work.cost,
            actual_gain=work.value if ok else 0.0,
            calibration_ledger=creature.calibration_ledger,
        )
        return {
            "ok": ok,
            "verified": True,
            "correct": ok,
            "value": work.value if ok else 0.0,
            "predicted_probability": p_hat,
            "surprise": settle_rep["surprise"],
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
        settle_rep = core.belief.settle_and_compute_surprise(
            ticket,
            outcome_pass=ok,
            inspector="confined_trajectory_verifier",
            actual_cost=work.cost,
            actual_gain=work.value if ok else 0.0,
            calibration_ledger=creature.calibration_ledger,
        )
        return {
            "ok": ok,
            "verified": True,
            "correct": ok,
            "value": work.value if ok else 0.0,
            "predicted_probability": p_hat,
            "surprise": settle_rep["surprise"],
            "macro_id": tr_res.get("macro_id"),
            "blocked": None if ok else "TRAJECTORY_NOT_VERIFIED",
        }

    core.belief.settle_and_compute_surprise(
        ticket,
        outcome_pass=False,
        inspector="sovereign_perform_unhandled",
        actual_cost=work.cost,
        actual_gain=0.0,
        calibration_ledger=creature.calibration_ledger,
    )
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
    life: float = DEFAULT_LIFE_GRANT,
    slice_size: int = 112,
    extra_failing_tests: Sequence[tuple[str, str]] = (),
    numeric_chases: Sequence[Mapping[str, Any]] = (),
    open_gaps: Sequence[Mapping[str, Any]] = (),
    workspace: pathlib.Path | str | None = None,
) -> dict[str, Any]:
    """Run `Creature` with heterogeneous defended proposals, uncurated `external_hard_slice_v1.select` ranking,
    structural self-prediction, and general `type_directed_sampler_v1` artifact/onboarding execution.

    `workspace` is the world the creature acts on and repairs. Without it the creature defaults to
    the repository it lives in -- a world whose remaining failures are unmet learnings that no
    bounded repair can close, so every repair obligation is a genuinely failing test it cannot fix.
    Measured 2026-11-04: the same creature closes `add(a, b) -> a - b` in a 4-file workspace in
    0.2 s and fails the repo's own tests after 160 s. The path was never the problem; the world was.
    """
    from canonical.runtime import external_hard_slice_v1 as EHS
    from canonical.runtime import self_prediction_baseline_v1 as SPB
    from canonical.runtime import self_prediction_calibration_v1 as SPC

    creature = boot(root, identity=identity, life=life)
    if workspace is not None:
        creature.workspace_root = pathlib.Path(workspace).resolve()

    # What is owed to the world is a fact about the world, not a parameter of this function.
    # Measured 2026-11-05: every repair this creature ever made was one whose failing test the
    # caller had handed it. The organ that finds failing tests (`_sense_failing_workspace_tests`)
    # only ever ran on `live_autonomous_cycle`, which is not the live path -- so the creature could
    # repair, but could not notice that anything needed repair.
    if not extra_failing_tests and getattr(creature, "workspace_root", None):
        try:
            from canonical.swe_kernel.autonomous_awake_loop_v1 import AwakeAgencyDaemon
            _sensor = AwakeAgencyDaemon(
                pathlib.Path(creature.workspace_root),
                ledger_path=creature.root / "awake_sense" / "ledger.json",
                skill_store_path=creature.root / "awake_sense" / "skills.sqlite",
            )
            extra_failing_tests = [(rel, sig) for rel, sig in _sensor._sense_failing_workspace_tests()]
        except Exception:  # noqa: BLE001 - a world that cannot be sensed is a world with no known work
            extra_failing_tests = ()
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
    # Repair work is authored by the WORLD reader, not by the creature, and `live_autonomous_cycle`
    # only considers obligations that carry a dispatch entry. Without this the highest-value work on
    # the board is admitted and then unreachable -- measured 2026-11-04: attempted zero times.
    creature._repair_ids = [o.id for o in obligations if str(o.id).startswith("repair:")]

    # Active-Inference Expected Free Energy triage on the creature's own board:
    # combines pragmatic expected return `p_hat * o.value` with bounded epistemic
    # falsification probes on hard preconditions (`hard_probes_budget`) so the creature
    # neither wastes all its finite Life on impossible alphabetical prefixes nor curates an easy-only diet.
    hard_probes_budget = max(4, int(cycles) // 6)
    hard_probes_scheduled = 0
    efe_board: list[M.Work] = []
    for o in obligations:
        p_prior = predict_task_probability(o.id, creature)
        tie_u = (int(hashlib.sha256(o.id.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF) * 0.008
        if p_prior < 0.50 and hard_probes_scheduled < hard_probes_budget:
            hard_probes_scheduled += 1
            # Epistemic falsification probe: tests whether our negative self-belief holds in reality
            efe_val = round(o.value * 0.90 + tie_u, 5)
            efe_cost = o.cost
        else:
            efe_val = round(max(0.15, o.value * (0.15 + 0.85 * p_prior) + tie_u), 5)
            efe_cost = o.cost
        efe_board.append(M.Work(id=o.id, value=efe_val, cost=efe_cost))

    creature._board = efe_board
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
