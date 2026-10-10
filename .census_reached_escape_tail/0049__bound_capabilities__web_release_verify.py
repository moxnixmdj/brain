#!/usr/bin/env python3
from __future__ import annotations
import gzip, json, pathlib, re, urllib.request
from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts=[]
    def handle_data(self,data):
        if data and data.strip():
            self.parts.append(data.strip())
    def text(self):
        return " ".join(self.parts)


def _safe_path(root, raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _visible_text(raw, content_type):
    text=raw.decode("utf-8","replace")
    if "html" not in str(content_type or "").lower():
        return text
    p=_TextExtractor()
    p.feed(text)
    return p.text()


def _extract_release(text, product, major):
    prod=re.escape(product)
    maj=re.escape(str(major))
    semver=maj+r"\.\d+\.\d+"
    patterns=[]
    marker=re.search(r"releases\s+by\s+version\s+number",text,re.IGNORECASE)
    if marker:
        tail=text[marker.end():marker.end()+20000]
        patterns.append((tail,rf"{prod}\s+(?P<version>{semver})"))
    patterns.extend([
        (text,rf"Download\s+{prod}\s+(?P<version>{semver})"),
        (text,rf"Latest:\s*{prod}\s+(?P<version>{semver})"),
        (text,rf"{prod}\s+(?P<version>{semver})"),
    ])
    for haystack,pattern in patterns:
        m=re.search(pattern,haystack,re.IGNORECASE)
        if m:
            return m.group("version"),m.group(0)
    return None,None


def run(args, root):
    result_path=_safe_path(root,args.get("result_path"))
    if not result_path.is_file():
        raise RuntimeError("RELEASE_RESULT_JSON_MISSING")
    data=json.loads(result_path.read_text(encoding="utf-8"))
    version_field=str(args.get("version_field") or "").strip()
    product=str(args.get("product") or "").strip()
    major=str(args.get("major") or "").strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",version_field):
        raise RuntimeError("RELEASE_VERSION_FIELD_INVALID")
    if not product or not re.fullmatch(r"\d+",major):
        raise RuntimeError("RELEASE_PRODUCT_OR_MAJOR_INVALID")
    claimed=str(data.get(version_field) or "").strip()
    if not re.fullmatch(re.escape(major)+r"\.\d+\.\d+",claimed):
        raise RuntimeError("RELEASE_CLAIMED_VERSION_INVALID:"+claimed)
    url=str(data.get("source_url") or data.get("final_url") or "").strip()
    if not url.startswith("https://"):
        raise RuntimeError("RELEASE_SOURCE_URL_REQUIRED")
    req=urllib.request.Request(url,headers={
      "User-Agent":"ProjectBrain-IndependentReleaseVerifier/1",
      "Accept-Encoding":"gzip, identity",
    })
    timeout=max(1,min(int(args.get("timeout_s",30)),90))
    with urllib.request.urlopen(req,timeout=timeout) as r:
        raw=r.read(max(1,min(int(args.get("max_bytes",3000000)),10000000)))
        final_url=r.geturl()
        encoding=(r.headers.get("Content-Encoding") or "").lower()
        content_type=r.headers.get("Content-Type")
    if encoding=="gzip" or raw[:2]==b"\x1f\x8b":
        raw=gzip.decompress(raw)
    elif encoding not in ("","identity"):
        raise RuntimeError("RELEASE_CONTENT_ENCODING_UNSUPPORTED:"+encoding)
    text=_visible_text(raw,content_type)
    observed,evidence=_extract_release(text,product,major)
    if not observed:
        raise RuntimeError("INDEPENDENT_RELEASE_NOT_FOUND")
    verified=(observed==claimed and claimed in text)
    return {
      "adapter":"web_release_verify",
      "verified":verified,
      "producer_independent_verifier":True,
      "transport":"urllib.request",
      "parser":"html.parser",
      "source_url":url,
      "final_url":final_url,
      "product":product,
      "major":major,
      "version_field":version_field,
      "claimed_version":claimed,
      "observed_version":observed,
      "observed_text_evidence":evidence,
      "claimed_string_present":claimed in text,
      "response_bytes":len(raw),
    }
