"""Semantic Chrome operations for OSWorld 2.1 via the guest's local CDP endpoint.

This module compiles a small declarative browser language into Python source.
It does not expose raw JavaScript or raw Python to the policy provider.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

MAX_TEXT = 1000
MAX_URL = 4096


class BrowserOpsError(ValueError):
    pass


def _text(value: Any, name: str, limit: int = MAX_TEXT) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BrowserOpsError(name + "_REQUIRED")
    value = value.strip()
    if len(value) > limit:
        raise BrowserOpsError(name + "_TOO_LONG")
    return value


def _js_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _expr(op: Mapping[str, Any]) -> str:
    kind = str(op.get("type") or "").strip().upper()

    if kind == "BROWSER_OPEN_URL":
        url = _text(op.get("url"), "URL", MAX_URL)
        if not (url.startswith("http://") or url.startswith("https://") or url.startswith("chrome://")):
            raise BrowserOpsError("URL_SCHEME_NOT_ALLOWED")
        return "location.href=" + _js_string(url) + "; 'NAVIGATED'"

    if kind == "BROWSER_CLICK_TEXT":
        target = _text(op.get("text"), "TEXT")
        t = _js_string(target)
        return f"""(() => {{
const q={t}.toLowerCase();
const els=[...document.querySelectorAll('button,a,input,[role="button"],[role="link"],[aria-label],summary,label')];
const e=els.find(x=>((x.innerText||x.value||x.getAttribute('aria-label')||'').trim().toLowerCase()===q))
      || els.find(x=>((x.innerText||x.value||x.getAttribute('aria-label')||'').trim().toLowerCase().includes(q)));
if(!e) throw new Error('TARGET_TEXT_NOT_FOUND');
e.scrollIntoView({{block:'center',inline:'center'}});
e.click();
return 'CLICKED';
}})()"""

    if kind == "BROWSER_FILL":
        label = _text(op.get("label"), "LABEL")
        value = _text(op.get("value"), "VALUE", 10000)
        l = _js_string(label)
        v = _js_string(value)
        return f"""(() => {{
const q={l}.toLowerCase();
const inputs=[...document.querySelectorAll('input,textarea,[contenteditable="true"]')];
function nameOf(e) {{
  const id=e.id;
  const lab=id?document.querySelector('label[for="'+CSS.escape(id)+'"]'):null;
  return [e.getAttribute('aria-label'),e.getAttribute('placeholder'),e.getAttribute('name'),lab&&lab.innerText]
    .filter(Boolean).join(' ').toLowerCase();
}}
const e=inputs.find(x=>nameOf(x)===q)||inputs.find(x=>nameOf(x).includes(q));
if(!e) throw new Error('FIELD_NOT_FOUND');
e.focus();
if(e.isContentEditable) e.innerText={v}; else e.value={v};
e.dispatchEvent(new Event('input',{{bubbles:true}}));
e.dispatchEvent(new Event('change',{{bubbles:true}}));
return 'FILLED';
}})()"""

    if kind == "BROWSER_SELECT":
        label = _text(op.get("label"), "LABEL")
        value = _text(op.get("value"), "VALUE")
        l = _js_string(label)
        v = _js_string(value)
        return f"""(() => {{
const q={l}.toLowerCase();
const sels=[...document.querySelectorAll('select')];
function nameOf(e) {{
 const id=e.id; const lab=id?document.querySelector('label[for="'+CSS.escape(id)+'"]'):null;
 return [e.getAttribute('aria-label'),e.getAttribute('name'),lab&&lab.innerText].filter(Boolean).join(' ').toLowerCase();
}}
const e=sels.find(x=>nameOf(x)===q)||sels.find(x=>nameOf(x).includes(q));
if(!e) throw new Error('SELECT_NOT_FOUND');
const want={v}.toLowerCase();
const opt=[...e.options].find(o=>o.value.toLowerCase()===want||o.text.toLowerCase()===want)
       || [...e.options].find(o=>o.text.toLowerCase().includes(want));
if(!opt) throw new Error('OPTION_NOT_FOUND');
e.value=opt.value; e.dispatchEvent(new Event('change',{{bubbles:true}})); return 'SELECTED';
}})()"""

    if kind == "BROWSER_SCROLL":
        direction = _text(op.get("direction"), "DIRECTION", 16).lower()
        amount = op.get("amount", 700)
        if direction not in {"up", "down"}:
            raise BrowserOpsError("SCROLL_DIRECTION_INVALID")
        if isinstance(amount, bool) or not isinstance(amount, int) or not 1 <= amount <= 5000:
            raise BrowserOpsError("SCROLL_AMOUNT_INVALID")
        delta = amount if direction == "down" else -amount
        return f"window.scrollBy(0,{delta}); 'SCROLLED'"

    raise BrowserOpsError("BROWSER_OP_UNSUPPORTED:" + kind)


def compile_browser_op(op: Mapping[str, Any]) -> str:
    if not isinstance(op, Mapping):
        raise BrowserOpsError("BROWSER_OP_NOT_OBJECT")
    expr = _expr(op)
    payload = json.dumps({"expression": expr, "awaitPromise": True, "returnByValue": True}, ensure_ascii=False)
    return f"""import asyncio,json,urllib.request,websockets
async def _brain_cdp():
    targets=json.load(urllib.request.urlopen('http://127.0.0.1:1337/json/list',timeout=5))
    pages=[t for t in targets if t.get('type')=='page' and t.get('webSocketDebuggerUrl')]
    if not pages:
        raise RuntimeError('NO_CDP_PAGE')
    wsurl=pages[0]['webSocketDebuggerUrl']
    async with websockets.connect(wsurl,max_size=8*1024*1024) as ws:
        await ws.send(json.dumps({{'id':1,'method':'Runtime.evaluate','params':{payload}}}))
        while True:
            msg=json.loads(await asyncio.wait_for(ws.recv(),timeout=10))
            if msg.get('id')==1:
                if 'error' in msg:
                    raise RuntimeError('CDP_ERROR:'+str(msg['error']))
                res=msg.get('result',{{}}).get('result',{{}})
                if res.get('subtype')=='error':
                    raise RuntimeError('CDP_EVAL_ERROR:'+str(res.get('description') or res))
                print(json.dumps(res,ensure_ascii=False))
                return
asyncio.run(_brain_cdp())"""
