"""Grader ONLY: visible-state checks for every Doors prompt in the follow-up.

Post-hoc human operationalizations, not the upstream trajectory matcher. Never
use this module, its controls or its readouts to produce or revise an action.
Replays the already frozen calls in fresh offline copies of the pinned demo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

from canonical.runtime import witnessed_browser_v1 as browser
from canonical.tools.live_interface_trial_v1 import fresh_room, serving


HALL, SEA, ATTIC, WOODS = 'Choose a Door', 'The Coral Cove', "The Wizard's Attic", 'The Whispering Woods'
LIGHT = (ATTIC, 'The owl blinks at the sudden light!')
# Required ordered readbacks; extra intermediate states are permitted. The last
# requirement must also still hold at termination. The initial hallway is not a return.
REQUIRED = {8: [(SEA,''),(HALL,'')], 9: [(SEA,''),(SEA,'Wheee! Look at me go!'),
            (SEA,"You can't see me..."),(HALL,'')], 10: [(ATTIC,''),(HALL,'')],
            11: [(ATTIC,''),LIGHT], 12: [(ATTIC,''),LIGHT,(HALL,'')],
            13: [(WOODS,''),(WOODS,'I am the keeper of the ferns.')]}
# Independent positive control: use actual visible buttons, not gold WebMCP calls.
BUTTONS = {8:['2','Return to Hallway'], 9:['2','Dance with him','Play Hide & Seek','Return to Hallway'],
           10:['3','Cast light','Return to Hallway'], 11:['3','Cast light'],
           12:['3','Cast light','Return to Hallway'], 13:['1','"What are you?"']}


def snapshot(room, origin):
    # Navigating form tools may resolve before the next document has a body.
    # Wait for a complete, stable observation, NOT for the desired effect.
    deadline=time.monotonic()+2; previous=None; since=None
    while time.monotonic()<deadline:
        try:
            state=room.evaluate('''(() => ({origin:location.origin,h:document.querySelector('h1')?.innerText,
              page:location.pathname,ready:document.readyState,
              message:(document.querySelector('#speech,#status')?.innerText||'').trim()}))()''')
        except RuntimeError:
            state=None
        if state and state['origin']==origin and state.get('h') and state['ready']=='complete':
            if state==previous and time.monotonic()-since>=.20:return [state['h'],state['message']]
            if state!=previous:previous=state;since=time.monotonic()
        else:previous=since=None
        time.sleep(.035)
    raise ValueError('no stable same-origin visible heading within 2s')


def satisfies(states, needs):
    def met(s,n):return s[0]==n[0] and (not n[1] or s[1]==n[1])
    i=0
    for observed in states[1:]:
        if i<len(needs) and met(observed,needs[i]):i+=1
    return states[0]==[HALL,''] and i==len(needs) and met(states[-1],needs[-1])


def run_row(i, arm, source, origin, exe):
    start=time.monotonic();states=[];row={'index':i,'arm':arm,'states':states,'effect':None}
    try:
        with fresh_room(str(exe),origin+'/demos/doors/') as room:
            states.append(snapshot(room,origin))
            if arm=='positive_ui':
                for text in BUTTONS[i]:
                    matches=[e for e in room.observe() if e['role']=='button' and e['name']==text and e['enabled']]
                    if len(matches)!=1:raise ValueError('expected unique enabled button: '+text)
                    room.click(matches[0]);states.append(snapshot(room,origin))
            elif arm!='noop':
                for s in source['steps']:
                    if not s.get('executed'):
                        if s['status'] not in ('NO_GROUNDING','ALREADY_VISIBLE_NO_ACTION'):
                            raise ValueError('unconfirmed action in frozen trace')
                        continue
                    if s['channel']!='webmcp':raise ValueError('unsupported replay channel')
                    a=s['action'];d=room.evaluate(browser._DISCOVER)
                    tools=[t for t in d['tools'] if t['name']==a['name'] and browser.digest(browser._schema(t))==s['schema_digest']]
                    if d['origin']!=origin or len(tools)!=1:raise ValueError('frozen handle not found')
                    result=browser._invoke(room,origin,tools[0],a['args'])
                    if not result.get('returned') or result.get('applicationError'):raise ValueError('failed replay')
                    states.append(snapshot(room,origin))
            row['effect']=satisfies(states,REQUIRED[i])
    except (OSError,RuntimeError,ValueError,KeyError) as e:
        row['error']=str(e)[:300]
    row['seconds']=round(time.monotonic()-start,3)
    return row


def grade(capture,pages,exe):
    raw=capture.read_bytes();payload=json.loads(raw)
    rows=[r for r in payload['rows'] if r['suite']=='doors'];keyed={(r['index'],r['arm']):r for r in rows}
    if len(rows)!=12 or set(keyed)!={(i,a) for i in REQUIRED for a in ('original','scoped')}:
        raise ValueError('expected entire Doors follow-up, without replacements')
    with serving(pages) as origin:
        results=[run_row(i,a,keyed.get((i,a)),origin,exe) for i in REQUIRED for a in ('original','scoped','noop','positive_ui')]
    controls={r['index']:r['effect'] for r in results if r['arm']=='positive_ui'}
    nop={r['index']:r['effect'] for r in results if r['arm']=='noop'}
    for r in results:r['calibrated']=controls[r['index']] is True and nop[r['index']] is False
    return {'kind':'post-freeze local readback, not an official WebMCP or OSWorld grade',
            'site':'GoogleChromeLabs/webmcp-tools@f3faa835f3fdeab42e41b055209d6954b192f653',
            'pages_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((pages/'demos/doors').glob('*.html'))},
            'capture_sha256':hashlib.sha256(raw).hexdigest(),'rows':results}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('capture','pages','exe'):p.add_argument(arg,type=Path)
    a=p.parse_args();print(json.dumps(grade(a.capture,a.pages,a.exe),indent=2))
