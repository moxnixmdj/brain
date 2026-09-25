#!/usr/bin/env python3
from __future__ import annotations
import gzip, importlib.util, json, pathlib, re, sys, urllib.request
from html.parser import HTMLParser

ROOT=pathlib.Path(__file__).resolve().parents[2]

def load_adapter():
    p=ROOT/"canonical/runtime/bound_capabilities/browser_chromedriver.py"
    s=importlib.util.spec_from_file_location("browser_verify_adapter",p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts=[]
    def handle_data(self,data):
        if data and data.strip():
            self.parts.append(data.strip())
    def text(self):
        return " ".join(self.parts)


def html_text(raw_html):
    p=_TextExtractor()
    p.feed(raw_html)
    return p.text()


def stable_release(text):
    patterns=[
      r"Download\s+Python\s+(3\.\d+\.\d+)",
      r"Latest:\s*Python\s+(3\.\d+\.\d+)",
    ]
    for pattern in patterns:
        m=re.search(pattern,text,re.IGNORECASE)
        if m:
            return m.group(1),m
    return None,None


def independent_stable_release(text):
    marker="Python releases by version number"
    i=text.lower().find(marker.lower())
    if i<0:
        return None,None
    tail=text[i:i+12000]
    m=re.search(r"Python\s+(3\.\d+\.\d+)\b",tail,re.IGNORECASE)
    if not m:
        return None,None
    return m.group(1),m


def main():
    evidence_path=ROOT/"canonical/astra_runtime/evidence/ASTRA-BROWSER-PYTHON-RELEASE-VERIFY-001__RESULT.json"
    screenshot="canonical/astra_runtime/tmp/PYTHON_DOWNLOADS.png"
    result="canonical/astra_runtime/tmp/PYTHON_DOWNLOADS_RESULT.json"
    url="https://www.python.org/downloads/"
    browser=load_adapter().run({
      "url":url,"screenshot_path":screenshot,"result_path":result
    },ROOT)
    version,match=stable_release(browser.get("text") or "")
    if not version:
        raise RuntimeError("RENDERED_STABLE_RELEASE_NOT_FOUND")
    req=urllib.request.Request(url,headers={
      "User-Agent":"ProjectBrain-IndependentVerifier/1",
      "Accept-Encoding":"identity"
    })
    with urllib.request.urlopen(req,timeout=30) as r:
        raw=r.read(2_000_000)
        final=r.geturl()
        content_encoding=(r.headers.get("Content-Encoding") or "").lower()
    if content_encoding=="gzip":
        raw=gzip.decompress(raw)
    elif content_encoding not in ("","identity"):
        raise RuntimeError("INDEPENDENT_CONTENT_ENCODING_UNSUPPORTED:"+content_encoding)
    html=raw.decode("utf-8","replace")
    independent_text=html_text(html)
    independent,imatch=independent_stable_release(independent_text)
    if not independent:
        raise RuntimeError("INDEPENDENT_STABLE_RELEASE_NOT_FOUND")
    if independent!=version:
        raise RuntimeError(f"SEMANTIC_RELEASE_MISMATCH:{version}:{independent}")
    p=(ROOT/result).resolve()
    data=json.loads(p.read_text(encoding="utf-8"))
    text=browser.get("text") or ""
    a=max(0,match.start()-180); b=min(len(text),match.end()+220)
    final_result={
      "source_url":url,
      "final_url":browser.get("final_url"),
      "page_title":browser.get("page_title"),
      "latest_stable_python3":version,
      "observed_text_evidence":text[a:b],
      "screenshot_path":browser.get("screenshot_path"),
      "screenshot_sha256":browser.get("screenshot_sha256")
    }
    p.write_text(json.dumps(final_result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    evidence={
      "schema":"PROJECT_BRAIN_RENDERED_BROWSER_VERIFICATION_V1",
      "status":"VERIFIED",
      "verified":True,
      "producer":"chromedriver_rendered_browser",
      "producer_independent_verifier":"urllib_official_python_downloads_page",
      "source_url":url,
      "independent_final_url":final,
      "latest_stable_python3":version,
      "independent_latest_stable_python3":independent,
      "screenshot_path":browser.get("screenshot_path"),
      "screenshot_sha256":browser.get("screenshot_sha256"),
      "screenshot_bytes":browser.get("screenshot_bytes"),
      "result_path":result,
      "page_title":browser.get("page_title"),
      "rendered":browser.get("rendered"),
    }
    evidence_path.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("RENDERED_BROWSER_EFFECT_VERIFIED "+json.dumps(evidence,sort_keys=True))

if __name__=="__main__":
    main()
