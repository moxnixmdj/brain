"""Blind producer. Input JSON is {suite:[user prompt or null,...]} only. Use under
`unshare -Urn` with loopback enabled. No evaluator, expected calls, site source or
models are read by the decision function. The HTTP server is test apparatus.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, closing
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Thread
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from canonical.runtime.brain_unified_model_v1 import open_model
from canonical.runtime.creature_runtime_v1 import Creature
from canonical.runtime.gui_room_v1 import GuiRoom
from canonical.runtime.witnessed_browser_v1 import digest, induce, admit_slot
from canonical.swe_kernel.witnessed_revision_store_v1 import RevisionStore

CALIBRATION = '''<!doctype html><main><h1>Label editor</h1><output>blank</output></main><script>
document.modelContext.registerTool({name:'stamp',description:'Stamp a visible label',
 inputSchema:{type:'object',properties:{text:{type:'string'}},required:['text']},
 execute:({text})=>{document.querySelector('output').innerText=text;return 'accepted';}})
</script>'''


@contextmanager
def serving(root):
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self,*args): pass
        def list_directory(self, path):
            self.send_error(404); return None
    with ThreadingHTTPServer(('127.0.0.1',0), partial(Quiet,directory=root)) as server:
        worker = Thread(target=server.serve_forever, daemon=True); worker.start()
        try: yield 'http://127.0.0.1:'+str(server.server_port)
        finally: server.shutdown(); worker.join()


@contextmanager
def fresh_room(exe, url):
    # The packaged headless shell needs --no-sandbox inside this throwaway
    # user/net namespace. Refuse to run it with a non-loopback interface.
    if {name for _, name in socket.if_nameindex()} != {'lo'}:
        raise RuntimeError('an isolated loopback-only network namespace is required')
    with tempfile.TemporaryDirectory(prefix='interface_profile_') as td:
        log = Path(td)/'stderr'
        with log.open('wb') as stderr, subprocess.Popen([exe,'--no-sandbox','--disable-gpu',
                '--disable-dev-shm-usage','--disable-background-networking','--enable-unsafe-swiftshader',
                '--enable-experimental-web-platform-features','--remote-debugging-address=127.0.0.1',
                '--remote-debugging-port=0','--user-data-dir='+td,'about:blank'],
                stdout=subprocess.DEVNULL,stderr=stderr) as chrome:
            try:
                portfile = Path(td)/'DevToolsActivePort'; deadline = time.monotonic()+8
                while not portfile.exists():
                    if chrome.poll() is not None or time.monotonic()>=deadline:
                        raise RuntimeError('browser startup: '+log.read_text(errors='replace')[-400:])
                    time.sleep(.02)
                port=portfile.read_text().splitlines()[0]
                with closing(GuiRoom(url,debug_url='http://127.0.0.1:'+port,settle_s=.05)) as room:
                    yield room
            finally:
                chrome.terminate()
                try: chrome.wait(timeout=2)
                except subprocess.TimeoutExpired: chrome.kill()


def run(prompts, pages, exe, database, workers=2):
    model = open_model(); creature = Creature('interface-trial', database.parent, 100)
    memory = RevisionStore(database)
    if memory.query('interface.lesson')['status']!='UNKNOWN_UNSEEN':
        raise ValueError('fresh trial database required')
    contrast = None
    with tempfile.TemporaryDirectory() as td:
        (Path(td)/'index.html').write_text(CALIBRATION)
        with serving(td) as site, fresh_room(exe, site) as room:
            goal = 'Stamp "cedar"'; teacher = model.live_browser_step(goal,room=room,origin=site,expected_text='cedar')
            if teacher['goal_verified']:
                row = induce(goal, teacher)
                # Distinguish the literal and slot hypotheses on one changed
                # feature; predictions fork from the same Python state. Read
                # the real result in a new profile instead of asking the learner.
                def observe(value):
                    with fresh_room(exe, site) as probe:
                        result = creature.live_browser_step('Stamp "'+value+'"',room=probe,origin=site)
                        if not result['executed']: raise ValueError('no observed call')
                        return probe.evaluate('document.querySelector("output").innerText')
                contrast = model.minimax_interrogate_version_space(
                    hypotheses={'literal':lambda v:'cedar','slot':lambda v:v},
                    candidate_probes=[{'id':'unchanged','input':'cedar'},{'id':'change_value','input':'lilac'}],
                    true_oracle=observe)
                row = admit_slot(row,contrast)
                row['contrast'] = contrast.get('executed_probes',[])
                ev = memory.append('set','interface.lesson',valid_from=1,source='teacher',value=row,witness=digest(teacher))
            else:
                ev = None
    rows = []
    with serving(pages) as site, ThreadPoolExecutor(max_workers=workers) as pool:
        def one(job):
            (suite,i,prompt,arm,lesson) = job
            start=time.monotonic(); result = {}
            try:
                if prompt is None: raise ValueError('no standalone user instruction')
                path = 'demos/'+suite+('/dist/' if suite=='pixel-art-studio' else '/')
                with fresh_room(exe, site+'/'+path) as room:
                    face = creature if i%2 else model
                    result = face.live_browser_step(prompt,room=room,origin=site,arm=arm,lesson=lesson)
            except (ValueError,OSError,RuntimeError,subprocess.SubprocessError) as exc:
                result = {'status':'UNMEASURED','error':str(exc)[:400],'executed':False,'action':None}
            return {'suite':suite,'index':i,'arm':arm,'front_door':'creature' if i%2 else 'model',
                    'elapsed_s':round(time.monotonic()-start,3),**result}
        def wave(arms):
            jobs = [(suite,i,prompt,arm, memory.query('interface.lesson')['value'] if arm!='empty' else None)
                    for suite,items in prompts.items() for i,prompt in enumerate(items) for arm in arms]
            rows.extend(pool.map(one,jobs))
        wave(('empty','raw','lifted'))
        if ev:
            memory.append('delete','interface.lesson',valid_from=2,source='control',witness=ev['id'])
        start=len(rows); wave(('lifted',))
        for r in rows[start:]: r['arm']='deleted'
    return {'teacher':teacher,'teacher_id':ev,'contrast':contrast,'after_delete':memory.query('interface.lesson'), 'rows':rows}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('prompts', type=Path);p.add_argument('pages',type=Path)
    p.add_argument('exe');p.add_argument('output',type=Path);p.add_argument('--workers',type=int,default=2);a=p.parse_args()
    result=run(json.loads(a.prompts.read_text()),a.pages,a.exe,a.output.with_suffix('.sqlite'),a.workers)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print('finished',len(result['rows']),'rows')
