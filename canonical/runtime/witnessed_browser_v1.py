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


def propose(goal, tools, *, lesson=None, arm='empty'):
    if arm not in ('empty','raw','lifted'):
        raise ValueError('unknown comparison arm')
    active = [t for t in tools if _eligible(t)]
    if lesson and arm != 'empty':
        tool = [t for t in active if t['name']==lesson['tool'] and digest(_schema(t))==lesson['schema']]
        if len(tool)==1:
            args = None
            if arm=='raw' and goal==lesson['goal']:
                args = lesson['args']
            if arm=='lifted' and lesson.get('slot'):
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
    if trial['status'] != 'VERIFIED_VISIBLE_TRANSITION' or trial['channel'] != 'webmcp':
        raise ValueError('no witnessed teacher transition')
    action = trial['action']; args = action['args']
    row = dict(goal=goal, tool=action['name'], schema=trial['schema_digest'], args=args,
               source=trial['origin'], witness=[trial['before'],trial['after']], status='TEACHER_ONLY')
    if len(args)==1:
        key, value = next(iter(args.items()))
        if isinstance(value,str) and value and goal.count(value)==1:
            row.update(slot=key, literal_context=goal.split(value))
    return row


def _invoke(room, origin, tool, args):
    # Re-discover the actual RegisteredTool handle, never execute by an old name
    # across a navigation, schema change, duplicate or detached frame.
    payload = json.dumps([origin,tool['name'],tool['schema'],args])
    return room.evaluate('''(async ([origin,name,schema,args]) => {
      if (location.origin!==origin) throw Error('ORIGIN_CHANGED');
      const c=document.modelContext;
      const matches=(await c.getTools()).filter(t => t.origin===origin && (t.source===window || (t.source===undefined && window.frames.length===0)) && t.name===name);
      if (matches.length!==1 || JSON.stringify(matches[0].inputSchema)!==JSON.stringify(schema) ||
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
            returned = _invoke(room, origin, tool, act['args'])
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
