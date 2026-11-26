"""Evaluator-side only: play a fixed public ARC-AGI-3 protocol, no dynamics inspection.

Run on the pinned Python 3.12 toolkit from a new writable temporary CWD:
    python -m canonical.tools.frame_program_trial_v1 ENVIRONMENT_FILES NEW_OUTPUT
The process playing each room is staged from reviewed Brain sources, in a
separate network/PID/filesystem namespace. Only charged actions cross back.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
from importlib.metadata import version
import json
import logging
from pathlib import Path
import platform
import selectors
import shutil
import subprocess
import tempfile
import time
import zlib

from canonical.tools.arc_agi_3_public_exploration_measure_v1 import click_targets, environment_manifest
from canonical.tools.stage_harbor_runtime_v1 import stage
from canonical.swe_kernel.witnessed_revision_store_v1 import RevisionStore

ROOT = Path(__file__).resolve().parents[2]
ENV_SHA = 'bf57484673964be96b1a3fa160f4d0ba5b731ffd33fa8aa1d074113ad7778152'
SOURCES = ('runtime/creature_runtime_v1', 'runtime/environment_learning_v1',
           'runtime/systematic_exploration_v1', 'runtime/frame_program_v1', 'tools/screen_port_worker_v1',
           'swe_kernel/witnessed_revision_store_v1', 'swe_kernel/revision_head_v1', 'runtime/memory_policy_v1')
TEACHER = 'lp85-305b61c3'


def packed(value):
    return json.dumps(value, separators=(',', ':'), sort_keys=True).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def stage_worker(src):
    manifest = stage(src, sources=('canonical/runtime/brain_unified_model_v1.py',))
    for name in SOURCES:
        path = 'canonical/' + name + '.py'
        file = src / path
        file.parent.mkdir(exist_ok=True, parents=True)
        shutil.copyfile(ROOT / path, file)
        manifest[path] = digest(file.read_bytes())
    return manifest


class Room:
    def __init__(self, env, migrated):
        self.env, self.migrated = env, migrated
        self.raw = env.observation_space
        self.level = self.raw.levels_completed
        self.actions, self.resets = 0, 0

    def packet(self):
        import numpy as np
        frame = np.asarray(self.raw.frame[-1])
        if frame.ndim != 2 or frame.shape[0] != frame.shape[1] or frame.min() < 0 or frame.max() >= 16:
            raise ValueError('unexpected public frame representation')
        # Display driver only. Producer has neither this transform nor its inverse.
        if self.migrated == 'transpose':
            display = 15 - frame.T
        elif self.migrated == 'reflect':
            display = (5 * frame[:, ::-1] + 1) % 16
        else:
            display = frame
        self.side = display.shape[1]
        self.offered = []
        for key in self.raw.available_actions:
            if int(key) == 6:
                self.offered.extend('C:%d:%d:%d' % r for r in click_targets(display.tolist()))
            else:
                self.offered.append('A%d' % int(key))
        return {'pixels': base64.b64encode(display.astype(np.uint8).tobytes()).decode(), 'offered': self.offered,
                'dead': self.raw.state.name == 'GAME_OVER',
                'advanced': self.raw.levels_completed > self.level or self.raw.state.name == 'WIN'}

    def act(self, command):
        from arcengine import GameAction
        if set(command) == {'act'} and command['act'] in self.offered:
            a = command['act']
            if a.startswith('C:'):
                _, x, y, _ = a.split(':')
                x, y = int(x), int(y)
                if self.migrated == 'transpose':
                    x, y = y, x
                elif self.migrated == 'reflect':
                    x = self.side - 1 - x
                self.raw = self.env.step(GameAction.ACTION6, data={'x': x, 'y': y})
            else:
                self.raw = self.env.step(GameAction.from_id(int(a[1:])))
        elif command == {'reset': True}:
            self.raw = self.env.reset()
            self.resets += 1
        else:
            raise ValueError('action not actually offered on the screen')
        self.actions += 1


def play(src, room, budget, program, record, recall=False):
    with tempfile.TemporaryDirectory() as root:
        proc = subprocess.Popen(['unshare', '-Urmpnf', '--kill-child', 'bash', str(Path(__file__).with_name('screen_port_root_v1.sh')),
                                 root, src], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                env={'PATH': '/usr/sbin:/usr/bin:/bin', 'LC_ALL': 'C.UTF-8'})
        try:
            def send(packet):
                proc.stdin.write(packed(packet) + b'\n'); proc.stdin.flush()
            observation = room.packet()
            send({'observation': observation, 'budget': budget, 'record': record,
                  **({'recall': True} if recall else {'program': program})})
            with selectors.DefaultSelector() as sel:
                sel.register(proc.stdout, selectors.EVENT_READ)
                while sel.select(timeout=45):
                    msg = json.loads(proc.stdout.readline())
                    if set(msg) == {'result'}:
                        result = msg['result']
                        if result['spent'] != room.actions or result['advanced'] != observation['advanced']:
                            raise ValueError('producer tally disagrees with engine')
                        proc.stdin.close()
                        if proc.wait(timeout=10):
                            raise ValueError('worker did not exit cleanly')
                        return result
                    if observation['advanced'] or room.actions >= budget:
                        raise ValueError('worker tried to act past terminal/budget')
                    room.act(msg)
                    observation = room.packet()
                    send(observation)
                raise TimeoutError('screen worker did not respond')
        finally:
            if proc.poll() is None:
                proc.kill(); proc.wait()
            proc.stdout.close(); proc.stdin.close()


def first_campaign(out, games, attempt):
    lesson = attempt('empty', 'teacher', TEACHER, learn=True)
    db_path = out/'memory.sqlite'
    mem = RevisionStore(db_path)
    footprint = {}
    if lesson is not None:
        witness = lesson['teacher_sha256']
        root = mem.append('set','screen.teacher', valid_from=1, source='one live episode', witness=witness, value=witness)
        for mode in ('raw', 'lifted'):
            value = lesson[mode]
            mem.append('derive', 'screen.'+mode, valid_from=1, source='observed trajectory', witness=witness,
                       parents=[root['id']], value=value)
            footprint[mode] = {'json_bytes':len(packed(value)), 'zlib_json_bytes':len(zlib.compress(packed(value),9))}
        prep = lesson['raw']['actions']
    else:
        witness, prep = None, ()
    footprint['db_before_retraction'] = db_path.stat().st_size
    conditions = [('exact', TEACHER, ()), ('migrated', TEACHER, ())]
    if prep:
        conditions.append(('next_level', TEACHER, prep))
    conditions.extend(('other_game', game, ()) for game in games if game != TEACHER)
    retrieval = []
    for arm in ('empty','raw','lifted','deleted'):
        if arm == 'deleted' and lesson is not None:
            mem.append('delete','screen.teacher', valid_from=2, source='ablation', witness='single teacher withdrawn')
        for condition, game, prefix in conditions:
            key = 'screen.'+('lifted' if arm=='deleted' else arm)
            query = RevisionStore(db_path, read_only=True).query(key)
            retrieval.append({'arm':arm, 'condition':condition, 'game':game, 'status':query['status']})
            attempt(arm, condition, game, program=query['value'], prep=prefix)
        print(f'{arm}: {len(conditions)} rooms closed', flush=True)
    return witness, prep, footprint, retrieval


def sleep_campaign(out, src, games, attempt, previous):
    from canonical.runtime.creature_runtime_v1 import Creature
    # Evaluator reconstructs the counterfactual stores from the *one* frozen
    # teacher. Neither the receipt, IDs, as-of history, nor a different arm is
    # available to a receiver. Deleted gets latest-only query, not as-of replay.
    before = json.loads((previous/'result.json').read_bytes())
    raw = RevisionStore(previous/'memory.sqlite',read_only=True).query('screen.raw',valid_at=1)['value']
    witness = digest(packed(raw))
    if witness != before['one_teacher'] or before['env_tree_sha256'] != ENV_SHA:
        raise ValueError('teacher or suite mismatch')
    stats = {}
    for arm in ('empty','raw','lifted','shortened','deleted'):
        if arm != 'empty':
            owner = Creature(identity='screen-observer',root=out/arm,life_grant=1.)
            mode = 'shortened' if arm=='deleted' else arm
            t0 = time.perf_counter()
            info = owner.remember_screen(raw,representation=mode,valid_from=1,source='one live episode')
            if info['teacher'] != witness:
                raise ValueError('unexpected second teacher')
            info['file_seconds'] = round(time.perf_counter()-t0,6)
            path = owner.root/'screen.sqlite'
            if arm=='deleted':
                RevisionStore(path).append('delete','screen.teacher',valid_from=2,source='ablation',witness='one teacher withdrawn')
            shutil.copyfile(path, src/'screen.sqlite')
            stats[arm] = {**info,'db_bytes':path.stat().st_size,'db_sha256':digest(path.read_bytes())}
        for game in games:
            attempt(arm,'reflected_start',game,recall=True)
        attempt(arm,'reflected_next_level',TEACHER,prep=raw['actions'],recall=True)
        print(f'{arm}: {len(games)+1} rooms closed', flush=True)
    return witness, raw['actions'], stats, []


def trial(environments, out, previous=None):
    from arc_agi import Arcade, OperationMode
    logging.disable(logging.CRITICAL)
    assert (version('arc-agi'), version('arcengine'), platform.python_version_tuple()[:2]) == ('0.9.9', '0.9.3', ('3','12'))
    files = environment_manifest(environments)
    if files['files'] != 50 or files['tree_sha256'] != ENV_SHA:
        raise ValueError('unrecognized practice release')
    out.mkdir(exist_ok=False)
    src = out / 'src'
    manifest = stage_worker(src)
    arcade = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=str(environments))
    games = sorted(i.game_id for i in arcade.get_environments())
    if len(games) != 25 or TEACHER not in games:
        raise ValueError('incomplete practice release')
    rows = []
    def attempt(arm, condition, game, *, program=None, learn=False, prep=(), recall=False):
        t0 = time.perf_counter()
        cid = arcade.create_scorecard()
        env = arcade.make(game, scorecard_id=cid, seed=0)
        baselines = list(env.info.baseline_actions)
        warmup = Room(env, False)
        for a in prep:
            obs = warmup.packet()
            if obs['advanced']:
                raise ValueError('teacher prefix advanced early')
            warmup.act({'act': a})
        if prep and env.observation_space.levels_completed != 1:
            raise ValueError('teacher prefix did not reach a new level')
        room = Room(env, 'reflect' if previous else 'transpose' if condition == 'migrated' else None)
        budget = 2 * baselines[room.level]
        res = play(src, room, budget, program, learn, recall)
        lesson = res.pop('experience', None)
        card = arcade.close_scorecard(cid)
        single, = card.environments
        if (single.id, int(single.actions), int(single.levels_completed)) != (game, len(prep)+room.actions, room.level+int(res['advanced'])):
            raise RuntimeError('official card disagrees with instrument')
        row = {'arm': arm, 'condition': condition, 'game': game, 'level_at_start': room.level, 'budget': budget,
               'preparation_actions': len(prep), 'actual_resets': room.resets, 'producer': res,
               'scorecard': {'levels_completed': single.levels_completed, 'actions': single.actions, 'score': single.score},
               'wall_seconds': round(time.perf_counter()-t0, 5)}
        rows.append(row)
        with (out/'rows.jsonl').open('a') as f:
            print(packed(row).decode(), file=f, flush=True)
        return lesson

    if previous:
        witness, prep, footprint, retrieval = sleep_campaign(out, src, games, attempt, previous)
    else:
        witness, prep, footprint, retrieval = first_campaign(out, games, attempt)
    result = {'kind':'producer-run on pinned public practice game engine; not a leaderboard or private grade',
              'env_tree_sha256':ENV_SHA, 'toolkit':{'arc-agi':version('arc-agi'),'arcengine':version('arcengine'),
              'toolkit_python':platform.python_version()},'producer_manifest':manifest, 'one_teacher':witness,
              'preparation_plan_length':len(prep), 'storage':footprint, 'retrieval':retrieval, 'rows':rows}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('environments', type=Path); p.add_argument('out', type=Path)
    p.add_argument('--previous', type=Path, help='Run the sleep trial using that prior output directory; do not reteach')
    args = p.parse_args()
    trial(args.environments.resolve(strict=True), args.out.resolve(), args.previous)
