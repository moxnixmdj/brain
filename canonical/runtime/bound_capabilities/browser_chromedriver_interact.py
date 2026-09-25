#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, pathlib, socket, subprocess, time, urllib.request


def _safe_path(root, raw):
    p=(pathlib.Path(root)/str(raw)).resolve()
    rr=pathlib.Path(root).resolve()
    if p!=rr and rr not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _json_request(method,url,payload=None,timeout=30):
    data=None if payload is None else json.dumps(payload).encode("utf-8")
    req=urllib.request.Request(url,data=data,method=method,headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        raw=r.read(20_000_000)
    return json.loads(raw.decode("utf-8")) if raw else {}


def _free_port():
    s=socket.socket()
    s.bind(("127.0.0.1",0))
    port=s.getsockname()[1]
    s.close()
    return port


def _execute(sbase, script, args=None, timeout=20):
    out=_json_request("POST",sbase+"/execute/sync",{"script":script,"args":args or []},timeout=timeout)
    return out.get("value")


def _wait_ready(sbase, timeout_s=20):
    end=time.monotonic()+timeout_s
    last=None
    while time.monotonic()<end:
        try:
            last=_execute(sbase,"return document.readyState",timeout=5)
            if last=="complete":
                return last
        except Exception:
            pass
        time.sleep(0.2)
    return last


_ACTION_SCRIPT=r"""
const action=arguments[0] || {};
const norm=s => (s||'').replace(/\s+/g,' ').trim().toLowerCase();
function controlFor(labelText, kinds) {
  const wanted=norm(labelText);
  const labels=[...document.querySelectorAll('label')];
  for (const lab of labels) {
    const txt=norm(lab.innerText || lab.textContent);
    if (!txt.includes(wanted)) continue;
    let el=null;
    if (lab.htmlFor) el=document.getElementById(lab.htmlFor);
    if (!el) el=lab.querySelector('input,select,textarea,button');
    if (el && (!kinds || kinds.includes((el.tagName||'').toLowerCase()))) return el;
  }
  const nodes=[...document.querySelectorAll('input,select,textarea,button')];
  for (const el of nodes) {
    const blob=norm([
      el.name,el.id,el.placeholder,el.getAttribute('aria-label'),
      el.value,el.innerText,el.textContent
    ].filter(Boolean).join(' '));
    if (blob.includes(wanted) && (!kinds || kinds.includes((el.tagName||'').toLowerCase()))) return el;
  }
  return null;
}
function fire(el,name){ el.dispatchEvent(new Event(name,{bubbles:true})); }
if (action.type==='set_text') {
  const el=controlFor(action.target,['input','textarea']);
  if (!el) return {ok:false,error:'TEXT_TARGET_NOT_FOUND',action};
  el.focus();
  const proto=el.tagName.toLowerCase()==='textarea' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  const setter=Object.getOwnPropertyDescriptor(proto,'value')?.set;
  if (setter) setter.call(el,String(action.value??'')); else el.value=String(action.value??'');
  fire(el,'input'); fire(el,'change');
  return {ok:true,type:action.type,target:action.target,value:el.value,name:el.name||null,id:el.id||null};
}
if (action.type==='select_option') {
  const wanted=norm(action.value);
  const el=controlFor(action.target,['select']) || document.querySelector('select');
  if (el) {
    const opt=[...el.options].find(o=>norm(o.textContent)===wanted || norm(o.value)===wanted || norm(o.textContent).includes(wanted));
    if (!opt) return {ok:false,error:'SELECT_OPTION_NOT_FOUND',action,options:[...el.options].map(o=>o.textContent)};
    el.value=opt.value; fire(el,'input'); fire(el,'change');
    return {ok:true,type:action.type,target:action.target,value:opt.textContent.trim(),raw_value:el.value,name:el.name||null,mechanism:'select'};
  }
  // Choice groups are frequently represented as radio inputs under a
  // fieldset/legend rather than a <select>. Resolve the requested option by
  // its own label/value and click it. The target remains evidence about the
  // semantic group even when HTML does not attach that group name to a label.
  const labels=[...document.querySelectorAll('label')];
  for (const lab of labels) {
    if (!norm(lab.innerText||lab.textContent).includes(wanted)) continue;
    let radio=null;
    if (lab.htmlFor) radio=document.getElementById(lab.htmlFor);
    if (!radio) radio=lab.querySelector('input[type=radio]');
    if (radio && (radio.type||'').toLowerCase()==='radio') {
      if (!radio.checked) radio.click();
      fire(radio,'change');
      return {ok:!!radio.checked,type:action.type,target:action.target,value:(lab.innerText||lab.textContent||action.value).trim(),raw_value:radio.value||null,name:radio.name||null,mechanism:'radio'};
    }
  }
  const radios=[...document.querySelectorAll('input[type=radio]')];
  const radio=radios.find(r=>norm([r.value,r.name,r.id,r.getAttribute('aria-label')].filter(Boolean).join(' ')).includes(wanted));
  if (radio) {
    if (!radio.checked) radio.click();
    fire(radio,'change');
    return {ok:!!radio.checked,type:action.type,target:action.target,value:action.value,raw_value:radio.value||null,name:radio.name||null,mechanism:'radio'};
  }
  return {ok:false,error:'SELECT_TARGET_NOT_FOUND',action};
}
if (action.type==='check') {
  const el=controlFor(action.target,['input']);
  if (!el) return {ok:false,error:'CHECK_TARGET_NOT_FOUND',action};
  if (!['checkbox','radio'].includes((el.type||'').toLowerCase())) return {ok:false,error:'CHECK_TARGET_WRONG_TYPE',action,input_type:el.type};
  if (!el.checked) el.click();
  fire(el,'change');
  return {ok:!!el.checked,type:action.type,target:action.target,checked:!!el.checked,name:el.name||null,value:el.value||null};
}
if (action.type==='click') {
  const wanted=norm(action.target);
  const nodes=[...document.querySelectorAll('button,input[type=submit],input[type=button],a,[role=button]')];
  const el=nodes.find(x=>norm([x.innerText,x.textContent,x.value,x.name,x.id,x.getAttribute('aria-label')].filter(Boolean).join(' ')).includes(wanted));
  if (!el) return {ok:false,error:'CLICK_TARGET_NOT_FOUND',action};
  el.click();
  return {ok:true,type:action.type,target:action.target};
}
if (action.type==='submit') {
  const form=document.querySelector('form');
  const btn=[...document.querySelectorAll('button,input[type=submit]')][0];
  if (btn) { btn.click(); return {ok:true,type:action.type,mechanism:'submit_control'}; }
  if (form) { form.requestSubmit ? form.requestSubmit() : form.submit(); return {ok:true,type:action.type,mechanism:'form'}; }
  return {ok:false,error:'FORM_NOT_FOUND',action};
}
if (action.type==='wait') {
  return {ok:true,type:action.type};
}
return {ok:false,error:'ACTION_TYPE_UNSUPPORTED',action};
"""


def run(args, root):
    url=str(args.get("url") or "").strip()
    if not url.startswith(("https://","http://")):
        raise RuntimeError("BROWSER_URL_INVALID")
    actions=args.get("actions")
    if not isinstance(actions,list) or not actions:
        raise RuntimeError("BROWSER_ACTIONS_REQUIRED")
    screenshot_path=_safe_path(root,args.get("screenshot_path"))
    result_path=_safe_path(root,args.get("result_path"))
    screenshot_path.parent.mkdir(parents=True,exist_ok=True)
    result_path.parent.mkdir(parents=True,exist_ok=True)

    port=_free_port()
    proc=subprocess.Popen(
        ["chromedriver",f"--port={port}","--allowed-ips=127.0.0.1"],
        cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True
    )
    base=f"http://127.0.0.1:{port}"
    sid=None
    try:
        last=None
        for _ in range(80):
            try:
                _json_request("GET",base+"/status",timeout=2)
                break
            except Exception as exc:
                last=exc
                time.sleep(0.1)
        else:
            raise RuntimeError("CHROMEDRIVER_START_FAILED:"+repr(last))

        created=_json_request("POST",base+"/session",{
          "capabilities":{"alwaysMatch":{"browserName":"chrome","goog:chromeOptions":{"args":[
            "--headless=new","--no-sandbox","--disable-dev-shm-usage",
            "--disable-gpu","--window-size=1440,1000"
          ]}}}
        },timeout=30)
        value=created.get("value") or {}
        sid=value.get("sessionId") or created.get("sessionId")
        if not sid:
            raise RuntimeError("WEBDRIVER_SESSION_ID_MISSING:"+json.dumps(created)[:1000])
        sbase=f"{base}/session/{sid}"

        _json_request("POST",sbase+"/url",{"url":url},timeout=45)
        _wait_ready(sbase,20)
        before_url=str((_json_request("GET",sbase+"/url",timeout=15).get("value") or ""))

        trace=[]
        for index,action in enumerate(actions):
            if not isinstance(action,dict):
                raise RuntimeError("BROWSER_ACTION_INVALID:"+str(index))
            typ=str(action.get("type") or "")
            if typ=="wait":
                seconds=max(0.0,min(float(action.get("seconds",0.5)),5.0))
                time.sleep(seconds)
                result={"ok":True,"type":"wait","seconds":seconds}
            else:
                result=_execute(sbase,_ACTION_SCRIPT,[action],timeout=20)
                if not isinstance(result,dict) or result.get("ok") is not True:
                    raise RuntimeError("BROWSER_ACTION_FAILED:"+str(index)+":"+json.dumps(result,sort_keys=True)[:1200])
                if typ in {"submit","click"}:
                    time.sleep(0.5)
                    _wait_ready(sbase,20)
            trace.append({"index":index,"action":action,"result":result})

        final_url=str((_json_request("GET",sbase+"/url",timeout=15).get("value") or ""))
        title=str((_json_request("GET",sbase+"/title",timeout=15).get("value") or ""))
        metrics=_execute(sbase,r"""
          const b=document.body, d=document.documentElement;
          const w=Math.max(b?b.scrollWidth:0,d.scrollWidth,d.clientWidth);
          const h=Math.max(b?b.scrollHeight:0,d.scrollHeight,d.clientHeight);
          return {text:(b?b.innerText:''),width:w,height:h,ready:document.readyState};
        """,[],timeout=20) or {}
        width=max(800,min(int(metrics.get("width") or 1440),1920))
        height=max(800,min(int(metrics.get("height") or 1000),16000))
        _json_request("POST",sbase+"/window/rect",{"x":0,"y":0,"width":width,"height":height},timeout=15)
        shot=_json_request("GET",sbase+"/screenshot",timeout=30).get("value")
        if not isinstance(shot,str) or not shot:
            raise RuntimeError("WEBDRIVER_SCREENSHOT_MISSING")
        png=base64.b64decode(shot)
        if not png.startswith(b"\x89PNG\r\n\x1a\n"):
            raise RuntimeError("WEBDRIVER_SCREENSHOT_NOT_PNG")
        screenshot_path.write_bytes(png)
        text=str(metrics.get("text") or "")
        result={
          "schema":"PROJECT_BRAIN_BROWSER_INTERACTION_RESULT_V1",
          "source_url":url,
          "initial_url":before_url,
          "final_url":final_url,
          "page_title":title,
          "observed_text":text[:200000],
          "document_ready_state":metrics.get("ready"),
          "action_trace":trace,
          "actions_completed":len(trace),
          "screenshot_path":str(screenshot_path.relative_to(root)),
          "screenshot_sha256":hashlib.sha256(png).hexdigest(),
          "screenshot_bytes":len(png)
        }
        result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        return {
          "adapter":"browser_chromedriver_interact",
          "source_url":url,
          "final_url":final_url,
          "page_title":title,
          "text":text,
          "actions_completed":len(trace),
          "result_path":str(result_path.relative_to(root)),
          "screenshot_path":str(screenshot_path.relative_to(root)),
          "screenshot_sha256":hashlib.sha256(png).hexdigest(),
          "screenshot_bytes":len(png),
          "rendered":True,
          "interaction_verified":bool(trace and all(x["result"].get("ok") is True for x in trace)),
          "output_verified":bool(trace and text.strip() and len(png)>100)
        }
    finally:
        if sid:
            try:
                _json_request("DELETE",f"{base}/session/{sid}",timeout=5)
            except Exception:
                pass
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
