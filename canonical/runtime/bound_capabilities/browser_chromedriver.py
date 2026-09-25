#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, pathlib, socket, subprocess, time, urllib.error, urllib.request


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
    s=socket.socket(); s.bind(("127.0.0.1",0)); port=s.getsockname()[1]; s.close(); return port


def run(args, root):
    # Backward-compatible extension: passive capture remains the default.
    # When an explicit declarative action list is supplied, delegate to the
    # separately implemented interaction path. This keeps the verified
    # capture behavior stable while letting fresh missions pressure the new
    # effect before it is promoted in the capability registry.
    if isinstance(args.get("actions"),list) and args.get("actions"):
        import importlib.util, sys
        path=pathlib.Path(__file__).resolve().with_name("browser_chromedriver_interact.py")
        spec=importlib.util.spec_from_file_location("project_brain_browser_chromedriver_interact",path)
        if spec is None or spec.loader is None:
            raise RuntimeError("BROWSER_INTERACTION_ADAPTER_LOAD_FAILED")
        module=importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=module
        spec.loader.exec_module(module)
        return module.run(args,root)
    url=str(args.get("url") or "").strip()
    if not url.startswith(("https://","http://")):
        raise RuntimeError("BROWSER_URL_INVALID")
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
                last=exc; time.sleep(0.1)
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
        # Give client-side rendering a bounded settling window.
        time.sleep(1.0)
        final_url=(_json_request("GET",sbase+"/url",timeout=15).get("value") or "")
        title=(_json_request("GET",sbase+"/title",timeout=15).get("value") or "")
        metrics=_json_request("POST",sbase+"/execute/sync",{"script":"""
          const b=document.body, d=document.documentElement;
          const w=Math.max(b?b.scrollWidth:0,d.scrollWidth,d.clientWidth);
          const h=Math.max(b?b.scrollHeight:0,d.scrollHeight,d.clientHeight);
          return {text:(b?b.innerText:''),width:w,height:h,ready:document.readyState};
        ""","args":[]},timeout=20).get("value") or {}
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
          "source_url":url,
          "final_url":str(final_url),
          "page_title":str(title),
          "observed_text":text[:200000],
          "document_ready_state":metrics.get("ready"),
          "viewport":{"width":width,"height":height},
          "screenshot_path":str(screenshot_path.relative_to(root)),
          "screenshot_sha256":hashlib.sha256(png).hexdigest(),
          "screenshot_bytes":len(png)
        }
        result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        return {
          "adapter":"browser_chromedriver",
          "source_url":url,
          "final_url":str(final_url),
          "page_title":str(title),
          "text":text,
          "text_nonempty":bool(text.strip()),
          "result_path":str(result_path.relative_to(root)),
          "screenshot_path":str(screenshot_path.relative_to(root)),
          "screenshot_sha256":hashlib.sha256(png).hexdigest(),
          "screenshot_bytes":len(png),
          "rendered":True,
          "output_verified":bool(text.strip() and len(png)>100)
        }
    finally:
        if sid:
            try: _json_request("DELETE",f"{base}/session/{sid}",timeout=5)
            except Exception: pass
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()
