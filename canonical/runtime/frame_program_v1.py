"""A guarded click/key program from a single observed terminal trajectory.

The only prior is the declared interface family: square indexed displays can be
reflected/rotated and palette names can be bijectively renamed. Those are not
assumed symmetries of the dynamics. Intersect the surviving interpretations on
*every* observation; use them only if they agree on an offered actuator. The
readback (including actual goal feedback) can refute even unanimous predictions.
No game ids, demonstrations from elsewhere, dynamics library or learned weights.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import math
from typing import Protocol
import zlib

from canonical.runtime import systematic_exploration_v1 as sx

VERSION = 'indexed-frame-program/1'


@dataclass(frozen=True)
class Screen:
    pixels: bytes
    offered: tuple[str, ...]
    advanced: bool = False
    dead: bool = False

    @property
    def side(self):
        return math.isqrt(len(self.pixels))

    def __post_init__(self):
        if not (0 < self.side <= 256 and self.side ** 2 == len(self.pixels)):
            raise ValueError('square indexed display required')


class ScreenPort(Protocol):
    def state(self) -> Screen: ...
    def reset(self) -> None: ...
    def act(self, action: str) -> None: ...


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _xy(x, y, n, t):
    if t & 1:
        x, y = y, x
    return (n - 1 - x if t & 2 else x, n - 1 - y if t & 4 else y)


@lru_cache(maxsize=16)
def _indices(n, t):
    return tuple(v * n + u for y in range(n) for x in range(n) for u, v in [_xy(x, y, n, t)])


def _signature(pixels, n, t, names):
    ordered = bytes(pixels[i] for i in _indices(n, t)) if t else pixels
    for colour in dict.fromkeys(ordered):
        names.setdefault(colour, len(names))
    return _sha(ordered.translate(bytes(names.get(i, 0) for i in range(256))))


def _wire(action):
    parts = action.split(':')
    if len(parts) == 4 and parts[0] == 'C' and all(v.isdecimal() for v in parts[1:]):
        return ('C', *map(int, parts[1:]))
    if len(parts) == 1 and action:
        return (action,)
    raise ValueError('unrecognized actuator')


def compile_experience(screens, actions):
    """Called on the final contiguous segment since reset, not on a reference plan."""
    if not actions or len(screens) != 1 + len(actions) or not screens[-1].advanced:
        raise ValueError('no observed terminal transition')
    n = screens[0].side
    if not all(s.side == n for s in screens):
        raise ValueError('display resized during demonstration')
    commands = []
    for s, a in zip(screens, actions):
        if s.advanced or s.dead or a not in s.offered:
            raise ValueError('not a contiguous offered trajectory')
        command = _wire(a)
        if len(command) == 4:
            _, x, y, c = command
            if not (x < n and y < n and s.pixels[y*n+x] == c):
                raise ValueError('unbound teacher click')
        commands.append(list(command[:3]))  # palette number is receiver-local
    concatenated = b''.join(s.pixels for s in screens)
    raw = {'version': VERSION, 'mode': 'raw', 'side': n, 'actions': list(actions),
           'zlib_frames': base64.b64encode(zlib.compress(concatenated, 9)).decode('ascii')}
    names = {}
    compiled = {'version': VERSION, 'mode': 'lifted', 'side': n, 'actions': commands,
                'signatures': [_signature(s.pixels, n, 0, names) for s in screens]}
    return {'teacher_sha256': _sha(json.dumps(raw, separators=(',', ':'), sort_keys=True).encode()),
            'raw': raw, 'lifted': compiled}


def _unpack_frames(program):
    n, count = program['side'], len(program['actions'])
    expected = (count + 1) * n**2
    if not (type(n) is int and 0 < n <= 256 and count > 0 and expected <= 64 * 1024**2):
        raise ValueError('invalid or oversized screen recording')
    stream = zlib.decompressobj()
    raw = stream.decompress(base64.b64decode(program['zlib_frames'], validate=True), expected + 1)
    if not stream.eof or stream.unused_data or len(raw) != expected:
        raise ValueError('invalid packed demonstration')
    return raw


def file_experience(store_path, raw, *, representation, valid_from, source):
    """File a reinstantiable proposal supported by one exact witness in external memory.

    Shortest here means on the observed *picture* graph. Repeated pictures
    need not be the same hidden state. The receiver still has to try the plan.
    A witnessed nondeterministic edge disqualifies this shortcut.
    """
    from contextlib import closing
    from canonical.runtime.environment_learning_v1 import shortest_plan
    from canonical.swe_kernel.witnessed_revision_store_v1 import RevisionStore
    if raw.get('version') != VERSION or raw.get('mode') != 'raw' or representation not in ('raw','lifted','shortened'):
        raise ValueError('expected current single-exposure record and supported representation')
    pixels = _unpack_frames(raw)
    actions = list(raw['actions'])
    size = raw['side']**2
    frames = [pixels[i:i+size] for i in range(0,len(pixels),size)]
    # Do not conflate a goal with an identical nonterminal picture.
    keys = [_sha(b) for b in frames[:-1]] + ['advanced:' + _sha(frames[-1])]
    model, by_key = {}, dict(zip(keys, frames))
    for i, a in enumerate(actions):
        if representation == 'shortened' and model.setdefault(keys[i], {}).setdefault(a, keys[i+1]) != keys[i+1]:
            raise ValueError('contradictory witnessed edge under the picture key')
    chosen = actions
    if representation == 'shortened':
        chosen = shortest_plan({'model':model, 'root':keys[0]}, lambda k: k == keys[-1])
        if not chosen:
            raise ValueError('no observed path to terminal')
        k = keys[0]; frames = [by_key[k]]
        for a in chosen:
            k = model[k][a]; frames.append(by_key[k])
    screens = [Screen(b, (a,), False) for b, a in zip(frames,chosen)] + [Screen(frames[-1], (), True)]
    program = raw if representation == 'raw' else compile_experience(screens,chosen)['lifted']
    witness = _sha(json.dumps(raw,separators=(',', ':'),sort_keys=True).encode())
    store = RevisionStore(store_path)
    with closing(store._connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        def add(op, key, value, **kw):
            return store.append_tx(db,op,key,valid_from=valid_from,source=source,witness=witness,value=value,**kw)
        root = add('set','screen.teacher',witness)
        child = add('revise','screen.program',program,parents=[root['id']])
    return {'teacher':witness,'root_id':root['id'],'program_id':child['id'],'observed_actions':len(actions),
            'planned_actions':len(chosen),'program_bytes':len(json.dumps(program,separators=(',',':')).encode())}


class _Replay:
    def __init__(self, program, side, budget):
        self.p = program
        self.n = side
        self.live = {t: {} for t in range(8)}
        count = len(program['actions'])
        if (program.get('version') != VERSION or program.get('side') != side or
                not 0 < count <= budget):
            raise ValueError('version, display size or remaining budget mismatch')
        if program['mode'] == 'raw':
            self.raw = _unpack_frames(program)
        elif program['mode'] != 'lifted' or len(program['signatures']) != count + 1:
            raise ValueError('unknown or incomplete program')

    def observe(self, screen, index):
        if screen.side != self.n or screen.dead or screen.advanced != (index == len(self.p['actions'])):
            return False
        if self.p['mode'] == 'raw':
            size = self.n**2
            return screen.pixels == self.raw[index*size:(index+1)*size]
        self.live = {t: names for t, names in self.live.items() if
                     _signature(screen.pixels, self.n, t, names) == self.p['signatures'][index]}
        return bool(self.live)

    def action(self, screen, index):
        if self.p['mode'] == 'raw':
            a = self.p['actions'][index]
            return a if a in screen.offered else None
        command = self.p['actions'][index]
        if len(command) == 1:
            key, = command
            return key if key in screen.offered else None
        if len(command) != 3 or command[0] != 'C':
            return None
        _, x, y = command
        if not (type(x) is type(y) is int and 0 <= x < self.n and 0 <= y < self.n):
            return None
        points = {_xy(x, y, self.n, t) for t in self.live}
        if len(points) != 1:  # equal frames but different actions: do not guess
            return None
        u, v = points.pop()
        a = f'C:{u}:{v}:{screen.pixels[v*self.n+u]}'
        return a if a in screen.offered else None


def _action_class(a):
    return 'C:' + a.rsplit(':', 1)[1] if a.startswith('C:') else a


class _Meter:
    """Initial reset is free only while still at the start. Log just the teacher's live segment."""
    def __init__(self, port, record):
        self.port, self.record = port, record
        self.spent, self.dirty = 0, False
        self.screens, self.actions = ([port.state()] if record else []), []

    def state(self):
        return self.port.state()

    def reset(self):
        if self.dirty:
            self.port.reset()
            self.spent += 1
            self.dirty = False
        if self.record:
            self.screens, self.actions = [self.state()], []

    def act(self, a):
        self.port.act(a)
        self.spent += 1
        self.dirty = True
        if self.record:
            self.actions.append(a)
            self.screens.append(self.state())


def explore_screen(port: ScreenPort, *, budget, program=None, record=False):
    """Reprobe one supported program, then cold-explore with the residual budget."""
    env = _Meter(port, record)
    replay = {'reason': 'NO_ENTRY', 'actions': 0, 'confirmed_transitions': 0, 'terminal_revalidated': False}
    if program is not None:
        try:
            policy = _Replay(program, env.state().side, budget)
            if not policy.observe(env.state(), 0):
                replay['reason'] = 'ENTRY_MISMATCH'
            else:
                for i in range(len(program['actions'])):
                    a = policy.action(env.state(), i)
                    if a is None:
                        replay['reason'] = 'AMBIGUOUS_OR_UNOFFERED'
                        break
                    env.act(a)
                    replay['actions'] += 1
                    if not policy.observe(env.state(), i + 1):
                        replay['reason'] = 'PREDICTION_REFUTED'
                        break
                    replay['confirmed_transitions'] += 1
                else:
                    replay.update(reason='PREDICTED_TERMINAL_OBSERVED', terminal_revalidated=True)
        except (KeyError, ValueError, TypeError, zlib.error) as exc:
            # Data-only records are optional; a damaged or inapplicable record is not an answer.
            replay.update(reason='INAPPLICABLE_PROGRAM', detail=str(exc))
    cold = None
    if not env.state().advanced and env.spent < budget:
        env.reset()  # paid if replay moved; explorer's initial reset below is clean
        before = env.spent
        cold = sx.explore_to_goal(env, (), is_goal=lambda s: s.advanced, is_dead=lambda s: s.dead,
                                  key_of=lambda s: _sha(s.pixels), actions_of=lambda s: s.offered,
                                  action_class=_action_class, effect_prior=True, action_budget=budget-before,
                                  include_model=False)
        if cold['budget_spent'] != env.spent - before:
            raise RuntimeError('cold explorer and charged actions disagree')
        cold = {k: cold[k] for k in ('status', 'budget_spent', 'experiment_acts', 'travel_acts', 'surprises')}
    result = {'advanced': env.state().advanced, 'spent': env.spent, 'replay': replay, 'cold': cold}
    if record and env.state().advanced and env.actions:
        result['experience'] = compile_experience(env.screens, env.actions)
    return result
