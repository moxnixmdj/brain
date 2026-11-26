"""Same harness, separate processes/checkouts. Input: original file indices and prompts only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from concurrent.futures import ThreadPoolExecutor


def main():
    p=argparse.ArgumentParser();p.add_argument('--checkout',type=Path,required=True);p.add_argument('--original',action='store_true')
    for name in ('prompts','pages','exe','output'):p.add_argument(name,type=Path)
    a=p.parse_args();sys.path.insert(0,str(a.checkout.resolve()))
    from canonical.tools.live_interface_trial_v1 import serving, fresh_room, open_model, Creature
    m=open_model();c=Creature('fresh',a.output.parent,100);rows=json.loads(a.prompts.read_text())
    with serving(a.pages) as site, ThreadPoolExecutor(max_workers=2) as pool:
        def perform(row):
            s=row['suite'];i=row['index'];goal=row['goal'];start=time.monotonic()
            base={**row,'arm':'original' if a.original else 'scoped','steps':[],'transitions':[]}
            try:
                if not goal: raise ValueError('not a standalone user instruction')
                face=c if i%2 else m
                with fresh_room(str(a.exe),site+'/demos/'+s+('/dist/' if s=='pixel-art-studio' else '/')) as room:
                    if a.original:base['steps']=[face.live_browser_step(goal,room=room,origin=site)]
                    else:base.update(face.live_browser_episode(goal,room=room,origin=site))
            except (RuntimeError,OSError,ValueError) as exc:base.update(status='UNMEASURED',error=str(exc)[:300])
            return {**base,'elapsed_s':round(time.monotonic()-start,3)}
        out=list(pool.map(perform,rows))
    a.output.write_text(json.dumps(out,indent=2)+'\n')


if __name__=='__main__':main()
