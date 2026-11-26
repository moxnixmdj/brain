"""One-step, model-free grounding on an authorized disposable browser page.

The caller owns the room and fixes the origin and (optional) visible postcondition
before action. No arbitrary scripts, endpoint replay, external fetch or model.
A tool description is input for search, never evidence that it ran or succeeded.
"""
from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import urlsplit

_DISCOVER = '''(async () => {
  const c = document.modelContext, origin = location.origin;
  if (!c || typeof c.getTools !== 'function' || typeof c.executeTool !== 'function')
    return {origin, api:false, tools:[]};
  const tools = (await c.getTools()).filter(t => t.origin===origin && (t.source===window || (t.source===undefined && window.frames.length===0)));
  return {origin, api:true, tools:tools.map(t => ({name:t.name, description:t.description,
    schema:t.inputSchema, annotations:t.annotations || {}}))};
})()'''
_STATE = "({origin:location.origin, path:location.pathname, text:(document.body?.innerText || '').slice(0,32000)})"
_STOP = frozenset('a an the my this that and or for to with on in it of is please i want me you can would could by from as'.split())


def words(text):
    return [w for w in re.findall(r'[a-z0-9]+', re.sub('([a-z])([A-Z])',r'\1 \2',text).lower()) if w not in _STOP]


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _schema(tool):
    schema = tool['schema']
    if isinstance(schema, str):
        schema = json.loads(schema)
    return schema if isinstance(schema, dict) and schema.get('type','object') == 'object' else None


def _enum(prop):
    return prop.get('enum') or [v['const'] for v in prop.get('oneOf', ()) if 'const' in v]


def _accepts(prop, value):
    enum = _enum(prop)
    if enum and not any(type(v) is type(value) and v == value for v in enum):
        return False
    types = {'string':(str,), 'number':(int,float), 'integer':(int,), 'boolean':(bool,)}
    return type(value) in types.get(prop.get('type','string'), ())


def _arguments(goal, schema):
    """Only directly grounded scalar slots. A required ambiguous slot vetoes the call."""
    seq = ' ' + ' '.join(words(goal)) + ' '
    quoted = re.findall(r'''"([^"\n]+)"|'([^'\n]+)' ''', goal+' ', flags=re.X)
    numbers = re.findall(r'(?<!\w)-?\d+(?:\.\d+)?(?!\w)', goal)
    args = {}
    props = schema.get('properties', {})
    for key, prop in props.items():
        choices = _enum(prop)
        options = [v for v in choices if words(str(v)) and (' '+' '.join(words(str(v)))+' ') in seq]
        if not choices and prop.get('type') in ('integer','number') and len(numbers)==1:
            n = float(numbers[0]); options = [int(n) if n.is_integer() else n]
        if not choices and prop.get('type')=='string' and len(quoted)==1 and len(props)==1:
            options = [next(x for x in quoted[0] if x)]
        if len(options)==1 and _accepts(prop, options[0]):
            args[key] = options[0]
        elif options or key in schema.get('required', ()):
            return None
    return args if set(schema.get('required', ())) <= args.keys() else None


def _eligible(tool):
    hints = tool.get('annotations') or {}
    return not hints.get('consequentialHint') and not hints.get('debugging') and bool(tool.get('name'))


def read_question(goal):
    return bool(re.match(r'^\s*(what|where|when|which|who|how (?:many|much)|show|list|inspect|read|describe)\b',goal,re.I))


def propose(goal, tools, *, lesson=None, arm='empty'):
    if arm not in ('empty','raw','lifted'):
        raise ValueError('unknown comparison arm')
    active = [t for t in tools if _eligible(t) and
              (not read_question(goal) or (t.get('annotations') or {}).get('readOnlyHint') is True)]
    if lesson and arm != 'empty':
        tool = [t for t in active if t['name']==lesson['tool'] and digest(_schema(t))==lesson['schema']]
        if len(tool)==1:
            args = None
            if arm=='raw' and goal==lesson['goal']:
                args = lesson['args']
            if arm=='lifted' and lesson.get('slot') and lesson.get('slot_evidence'):
                a,b = lesson['literal_context']
                if goal.startswith(a) and goal.endswith(b) and len(goal)>len(a)+len(b):
                    value = goal[len(a):len(goal)-len(b) if b else None]
                    if _accepts(_schema(tool[0])['properties'][lesson['slot']],value):
                        args = {lesson['slot']:value}
            if args is not None:
                return {'name':lesson['tool'],'args':args,'route':arm}
    text = set(words(goal)); ranked = []
    for tool in active:
        name = set(words(tool['name'])); desc = set(words(tool.get('description') or ''))
        score = (len(text&name), len(text&desc))
        schema = _schema(tool)
        if schema is None or not any(score):
            continue
        args = _arguments(goal, schema)
        if args == {} and schema.get('properties') and not (tool.get('annotations') or {}).get('readOnlyHint'):
            args = None  # unbound optional write slots are not an instruction to reset to defaults
        ranked.append((score,tool['name'],args))
    ranked.sort(key=lambda r:r[0], reverse=True)
    if not ranked or (len(ranked)>1 and ranked[0][0]==ranked[1][0]) or ranked[0][2] is None:
        return None
    _, name, args = ranked[0]
    if sum(t['name']==name for t in active)!=1:
        return None
    return {'name':name,'args':args,'route':'schema'}


def induce(goal, trial):
    """Store a teacher-only proposal. Do not count repeat recall as transfer."""
    if (trial['status'] != 'VERIFIED_VISIBLE_TRANSITION' or trial['channel'] != 'webmcp'
            or goal!=trial.get('goal') or not trial.get('changed') or not trial.get('executed')):
        raise ValueError('no witnessed teacher transition')
    action = trial['action']; args = action['args']
    row = dict(goal=goal, tool=action['name'], schema=trial['schema_digest'], args=args,
               source=trial['origin'], witness=[trial['before'],trial['after']], status='TEACHER_ONLY')
    if len(args)==1:
        key, value = next(iter(args.items()))
        if isinstance(value,str) and value and goal.count(value)==1:
            row.update(slot=key, literal_context=goal.split(value))
    return row


def admit_slot(row, contrast):
    """Only eliminate the literal hypothesis in the teacher's declared space.

    Changing a value at one observed coordinate is NOT a universal rule. The
    receiver still has to rediscover a matching handle and recheck the effect.
    """
    if 'slot' not in row or contrast.get('status')!='IDENTIFIED_IN_DECLARED_SPACE':return row
    value=row['args'][row['slot']]
    evidence=[p for p in contrast.get('executed_probes',[]) if p['input']!=value
              and p['observed_output']==p['input'] and p['surviving_worlds']==['slot']]
    if evidence and contrast.get('surviving_worlds')==['slot']:
        return {**row,'slot_evidence':evidence,'status':'SLOT_OVER_LITERAL_IN_TEACHER_SPACE'}
    return row


def _invoke(room, origin, tool, args, *, read_only=False):
    # Re-discover the actual RegisteredTool handle, never execute by an old name
    # across a navigation, schema change, duplicate or detached frame.
    payload = json.dumps([origin,tool['name'],tool['schema'],args,read_only])
    return room.evaluate('''(async ([origin,name,schema,args,readOnly]) => {
      if (location.origin!==origin) throw Error('ORIGIN_CHANGED');
      const c=document.modelContext;
      const matches=(await c.getTools()).filter(t => t.origin===origin && (t.source===window || (t.source===undefined && window.frames.length===0)) && t.name===name);
      if (matches.length!==1 || JSON.stringify(matches[0].inputSchema)!==JSON.stringify(schema) ||
          (readOnly && matches[0].annotations?.readOnlyHint!==true) ||
          matches[0].annotations?.consequentialHint || matches[0].annotations?.debugging) throw Error('TOOL_CHANGED');
      const result=await c.executeTool(matches[0],args,{signal:AbortSignal.timeout(1800)});
      return {returned:true, applicationError: !!(result && (result.isError || result.error)),
              output: JSON.stringify(result)?.length <= 8192 ? result : undefined};
    })('''+payload+')')


def step(room, goal, *, origin, arm='empty', lesson=None, expected_text=None):
    """One action maximum. For use only on local disposable, explicitly supplied rooms."""
    url = urlsplit(origin)
    if url.scheme != 'http' or url.hostname not in ('127.0.0.1','localhost','::1') or url.path or url.query or url.fragment or url.username:
        raise ValueError('explicit loopback origin required')
    result = {'pass':False,'goal':goal,'status':'NO_GROUNDING','origin':origin,'channel':None,
              'action':None,'executed':False,'model_calls':0,'goal_verified':False}
    before = room.evaluate(_STATE)
    if before['origin'] != origin:
        return {**result,'status':'WRONG_ORIGIN'}
    discover = room.evaluate(_DISCOVER)
    if discover['origin'] != origin:
        return {**result,'status':'ORIGIN_CHANGED'}
    tools = discover['tools']; result.update(api=discover['api'], tool_count=len(tools), before=digest(before))
    if expected_text and expected_text in before['text'].splitlines():
        return {**result, 'status':'ALREADY_VISIBLE_NO_ACTION'}
    act = propose(goal, tools, arm=arm, lesson=lesson)
    if act:
        tool = next(t for t in tools if t['name']==act['name'])
        result.update(channel='webmcp',action=act,schema_digest=digest(_schema(tool)))
        try:
            returned = _invoke(room, origin, tool, act['args'],read_only=read_question(goal))
        except RuntimeError as exc:
            return {**result,'status':'UNCONFIRMED_INVOCATION','error':str(exc)[:300]}
        result['executed'] = returned.get('returned') is True
        if 'output' in returned:
            result['output'] = returned['output']
        if returned.get('applicationError'):
            return {**result, 'status':'APPLICATION_ERROR'}
    else:
        # A live DOM fallback, restricted to a unique enabled control named in
        # the request. No CSS selector, page-specific synonym or coordinates in memory.
        if read_question(goal):
            return result
        elements = room.observe(); phrase = ' '+' '.join(words(goal))+' '
        options = [e for e in elements if e['enabled'] and e['role']=='button' and words(e['name'])
                   and ' '+' '.join(words(e['name']))+' ' in phrase]
        if len(options)!=1 or not set(words(goal)).intersection({'click','press','select'}):
            return result
        if room.evaluate('location.origin') != origin:
            return {**result,'status':'ORIGIN_CHANGED'}
        room.click(options[0]); result.update(channel='dom',action={'name':options[0]['name']},executed=True)
    after = room.evaluate(_STATE)
    result.update(after=digest(after), changed=after!=before)
    ok = bool(after['origin']==origin and expected_text and expected_text in after['text'].splitlines())
    return {**result,'status':'VERIFIED_VISIBLE_TRANSITION' if ok else 'ACTION_WITHOUT_VERIFIED_GOAL',
            'pass':ok,'goal_verified':ok}


def episode(room, goal, *, origin, expected_text=None, max_actions=3):
    """Follow only explicit ordering. An action authorizes a dependent step
    only on a changed page with a newly groundable next handle. No arbitrary
    executable tool lists, and no claim that a changed page satisfies a goal.
    """
    if not 1 <= max_actions <= 3:
        raise ValueError('expected an action budget from 1 to 3')
    # Do not split a quoted argument, e.g. a title containing 'then'.
    parts = re.split(r'("[^"\n]*"|\'[^\'\n]*\')',goal)
    clauses = ['']
    for i, part in enumerate(parts):
        pieces = [part] if i % 2 else re.split(r'[,.;]?\s+(?:and\s+)?then\s+', part, flags=re.I)
        clauses[-1] += pieces[0]
        clauses.extend(pieces[1:])
    steps = []; transitions = []
    for i, clause in enumerate(clauses[:max_actions]):
        before = room.evaluate(_DISCOVER)
        last = i == len(clauses)-1
        res = step(room,clause,origin=origin,expected_text=expected_text if last else None)
        steps.append(res)
        if not res['executed'] or not res.get('changed') or last:
            break
        after = room.evaluate(_DISCOVER)
        if after['origin']!=origin or before['origin']!=origin:
            break
        next_goal=clauses[i+1]; nxt=propose(next_goal,after['tools'])
        if not nxt:break
        def contracts(tools):
            return {(t['name'],digest(_schema(t))) for t in tools if _eligible(t)}
        arrived=contracts(after['tools'])-contracts(before['tools'])
        if not any(name==nxt['name'] for name,_ in arrived):break
        transitions.append({'before':res['before'],'after':res['after'],'newly_available':nxt['name']})
    return {'pass':bool(steps and len(steps)==len(clauses) and steps[-1]['goal_verified']),
            'steps':steps,'transitions':transitions,'clause_count':len(clauses),'model_calls':0}
