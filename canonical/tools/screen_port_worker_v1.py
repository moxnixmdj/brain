"""Producer side of a synchronous screen port. No toolkit, game ids or game files."""
from __future__ import annotations

import base64
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from canonical.runtime.creature_runtime_v1 import Creature
from canonical.runtime.frame_program_v1 import Screen


def send(msg):
    print(json.dumps(msg, separators=(',', ':')), flush=True)


def read():
    line = sys.stdin.readline()
    if not line:
        raise EOFError('screen port closed')
    return json.loads(line)


class Port:
    def accept(self, packet):
        self.current = Screen(base64.b64decode(packet['pixels'], validate=True), tuple(packet['offered']),
                              packet['advanced'], packet['dead'])

    def state(self):
        return self.current

    def reset(self):
        send({'reset': True})
        self.accept(read())

    def act(self, action):
        send({'act': action})
        self.accept(read())


if __name__ == '__main__':
    p = Port()
    start = read()
    p.accept(start.pop('observation'))
    c = Creature(identity='screen-observer', root=Path('/tmp'), life_grant=1.)
    send({'result': c.explore_screen(p, **start)})
