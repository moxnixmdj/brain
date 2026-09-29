#!/usr/bin/env python3
"""Deterministic external capability discovery for Project Brain.

Current source: official public MCP Registry. The registry is an optional
metadata source, never canonical authority. Discovery does not execute or
install third-party code. Binding is a separate verified step.
"""
from __future__ import annotations

import concurrent.futures
import json
import math
import pathlib
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request


MCP_REGISTRY_BASE = "https://registry.modelcontextprotocol.io"
STOPWORDS = {
    "capability","tool","action","do","use","get","make","create","read","write",
    "data","file","service","external","target","effect",
    "containing","contains","every","its","that","final",
    "the","and","or","with","for","from","into","of","by","using","as","to"
}
GENERIC_DISCOVERY_TOKENS={
    "generate","code","image","text","save","output","input","convert",
    "process","program","utility","tool","data"
}
PAID_MARKERS = ("payment", "usdc", "x402", "$", "paid", "billing")


class DiscoveryFailure(RuntimeError):
    pass


def _semanticize_paths(text):
    ext_words={
        "md":"markdown","markdown":"markdown","pdf":"pdf","json":"json",
        "csv":"csv","tsv":"tsv","png":"image","jpg":"image","jpeg":"image",
        "txt":"text","html":"html","htm":"html","xml":"xml"
    }
    pattern=r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+"
    def repl(match):
        raw=match.group(0)
        leaf=raw.rsplit("/",1)[-1]
        ext=leaf.rsplit(".",1)[-1].lower() if "." in leaf else ""
        return " "+ext_words.get(ext,ext)+" "
    return re.sub(pattern,repl,str(text or ""))


def effect_queries(effect):
    if not isinstance(effect, str) or not effect.strip():
        raise DiscoveryFailure("EFFECT_REQUIRED")
    semantic=_semanticize_paths(effect)
    tokens = [
        t.lower() for t in re.split(r"[^A-Za-z0-9]+", semantic)
        if len(t) >= 2 and t.lower() not in STOPWORDS
    ]
    low_information=set(GENERIC_DISCOVERY_TOKENS) | {
        "those","these","exact","records","record","fields","field",
        "values","value","same","identical","order","count","save"
    }
    distinctive=[]
    generic=[]
    for token in tokens:
        target=generic if token in low_information or token.isdigit() else distinctive
        if token not in target:
            target.append(token)
    out=[]
    source=distinctive if distinctive else generic
    for token in source:
        if token not in out:
            out.append(token)
    if not out:
        compact = re.sub(r"[^A-Za-z0-9]+", "", effect).lower()
        if compact:
            out.append(compact)
    return out[:6]


def _flatten_text(value):
    if isinstance(value, dict):
        return " ".join(_flatten_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(v) for v in value)
    return str(value or "")


def _lexical_variants(token):
    token=str(token or "").lower()
    out={token}
    if len(token)>=4:
        out.add(token+"s")
        if token.endswith("e"):
            out.add(token+"r")          # decode -> decoder
            out.add(token[:-1]+"ing")   # decode -> decoding
        else:
            out.add(token+"er")         # scan -> scanner is handled below too
            out.add(token+"ing")
        if token.endswith("n"):
            out.add(token+"ner")        # scan -> scanner
            out.add(token+"ning")       # scan -> scanning
    return out


def normalize_server(entry, query):
    server = entry.get("server", entry) if isinstance(entry, dict) else {}
    meta = entry.get("_meta", {}) if isinstance(entry, dict) else {}
    official = meta.get("io.modelcontextprotocol.registry/official", {}) if isinstance(meta, dict) else {}
    name = str(server.get("name", ""))
    description = str(server.get("description", ""))
    blob = _flatten_text(server).lower()
    packages = server.get("packages") if isinstance(server.get("packages"), list) else []
    remotes = server.get("remotes") if isinstance(server.get("remotes"), list) else []

    required_env = 0
    required_secrets = 0
    package_summaries = []
    for package in packages:
        envs = package.get("environmentVariables") if isinstance(package, dict) else []
        envs = envs if isinstance(envs, list) else []
        required_env += sum(1 for e in envs if isinstance(e, dict) and e.get("isRequired"))
        required_secrets += sum(1 for e in envs if isinstance(e, dict) and e.get("isSecret"))
        package_summaries.append({
            "registry_type": package.get("registryType"),
            "identifier": package.get("identifier"),
            "version": package.get("version"),
            "runtime_hint": package.get("runtimeHint"),
            "transport": package.get("transport"),
            "required_environment": [
                e.get("name") for e in envs if isinstance(e, dict) and e.get("isRequired")
            ],
            "secret_environment": [
                e.get("name") for e in envs if isinstance(e, dict) and e.get("isSecret")
            ],
        })

    remote_summaries = []
    for remote in remotes:
        headers = remote.get("headers") if isinstance(remote, dict) else []
        headers = headers if isinstance(headers, list) else []
        required_secrets += sum(1 for h in headers if isinstance(h, dict) and h.get("isSecret"))
        remote_summaries.append({
            "type": remote.get("type"),
            "url": remote.get("url"),
            "required_headers": [
                h.get("name") for h in headers if isinstance(h, dict)
            ],
        })

    paid = any(marker in blob for marker in PAID_MARKERS)
    status = official.get("status", "unknown")
    is_latest = bool(official.get("isLatest", False))
    q = query.lower()
    lexical = (8 if q and q in name.lower() else 0) + (4 if q and q in description.lower() else 0)
    local_package_bonus = 3 if packages else 0
    active_bonus = 2 if status == "active" else -20
    latest_bonus = 1 if is_latest else 0
    friction = required_env + 3 * required_secrets
    paid_penalty = 100 if paid else 0
    score = lexical + local_package_bonus + active_bonus + latest_bonus - friction - paid_penalty

    return {
        "name": name,
        "description": description,
        "version": server.get("version"),
        "repository": server.get("repository"),
        "status": status,
        "is_latest": is_latest,
        "packages": package_summaries,
        "remotes": remote_summaries,
        "required_environment_count": required_env,
        "required_secret_count": required_secrets,
        "zero_cost_eligible": not paid,
        "score": score,
        "query": query,
    }


def search_mcp_registry(effect, limit=8, timeout_s=12, opener=None):
    queries = effect_queries(effect)
    opener = opener or urllib.request.urlopen
    seen = {}
    errors = []
    for query in queries:
        params = urllib.parse.urlencode({
            "search": query,
            "version": "latest",
            "limit": max(1, min(int(limit), 50)),
        })
        url = f"{MCP_REGISTRY_BASE}/v0.1/servers?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "ProjectBrain-CapabilityDiscovery/1"})
        try:
            with opener(req, timeout=timeout_s) as resp:
                raw = resp.read(300000)
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            errors.append({"query": query, "error": type(exc).__name__ + ":" + str(exc)})
            continue
        for entry in payload.get("servers", []):
            candidate = normalize_server(entry, query)
            if candidate["status"] != "active":
                continue
            prior = seen.get(candidate["name"])
            if prior is None or candidate["score"] > prior["score"]:
                seen[candidate["name"]] = candidate

    candidates = sorted(
        seen.values(),
        key=lambda c: (
            not c["zero_cost_eligible"],
            -c["score"],
            c["required_secret_count"],
            c["required_environment_count"],
            c["name"],
        ),
    )
    return {
        "schema": "PROJECT_BRAIN_CAPABILITY_DISCOVERY_RESULT_V1",
        "effect": effect,
        "source": "OFFICIAL_MCP_REGISTRY",
        "source_url": MCP_REGISTRY_BASE,
        "queries": queries,
        "candidate_count": len(candidates),
        "candidates": candidates[: max(1, min(int(limit), 50))],
        "errors": errors,
        "binding_performed": False,
    }


_APT_PACKAGE_METADATA_CACHE=None
_APT_EXECUTABLE_PATHS_CACHE={}


def _apt_package_records():
    """Load the local APT package metadata once per process.

    Package semantics are the discovery surface. Contents/apt-file is used
    later only to prove that a semantically relevant package actually ships a
    normal executable.
    """
    global _APT_PACKAGE_METADATA_CACHE
    if _APT_PACKAGE_METADATA_CACHE is not None:
        return _APT_PACKAGE_METADATA_CACHE
    try:
        p=subprocess.run(
            ["apt-cache","dumpavail"],
            text=True,capture_output=True,timeout=35
        )
    except Exception:
        _APT_PACKAGE_METADATA_CACHE=[]
        return _APT_PACKAGE_METADATA_CACHE
    if p.returncode!=0:
        _APT_PACKAGE_METADATA_CACHE=[]
        return _APT_PACKAGE_METADATA_CACHE

    records={}
    current={}
    last=None

    def flush():
        if not current:
            return
        name=str(current.get("Package") or "").strip()
        if not name:
            return
        description=str(current.get("Description") or "").strip()
        prior=records.get(name)
        value={"name":name,"description":description}
        if prior is None or len(description)>len(str(prior.get("description") or "")):
            records[name]=value

    for raw in p.stdout.splitlines()+[""]:
        if not raw.strip():
            flush()
            current={}
            last=None
            continue
        if raw[:1].isspace() and last:
            current[last]=str(current.get(last) or "")+" "+raw.strip()
            continue
        if ":" not in raw:
            continue
        key,value=raw.split(":",1)
        last=key.strip()
        current[last]=value.strip()

    _APT_PACKAGE_METADATA_CACHE=list(records.values())
    return _APT_PACKAGE_METADATA_CACHE


def _semantic_term_variants(term):
    term=str(term or "").lower()
    out=set(_lexical_variants(term))
    if term.endswith("e") and len(term)>=4:
        out.add(term+"d")
    if term.endswith("y") and len(term)>=4:
        out.add(term[:-1]+"ies")
    return {x for x in out if x}


def _package_lexical_tokens(name,description):
    ordered=re.findall(r"[a-z0-9]+",(str(name)+" "+str(description)).lower())
    tokens=set(ordered)
    tokens.update(
        ordered[i]+ordered[i+1]
        for i in range(len(ordered)-1)
        if len(ordered[i])>=2 and len(ordered[i+1])>=2
    )
    return tokens


def _package_name_tokens(name):
    ordered=re.findall(r"[a-z0-9]+",str(name or "").lower())
    out=set(ordered)
    out.update(
        ordered[i]+ordered[i+1]
        for i in range(len(ordered)-1)
        if len(ordered[i])>=2 and len(ordered[i+1])>=2
    )
    return out


def _apt_semantic_candidates(effect,limit=40):
    records=_apt_package_records()
    terms=effect_queries(effect)
    if not records or not terms:
        return []

    term_variants={t:_semantic_term_variants(t) for t in terms}
    document_tokens=[]
    df={t:0 for t in terms}
    for rec in records:
        tokens=_package_lexical_tokens(rec.get("name"),rec.get("description"))
        document_tokens.append(tokens)
        for term,variants in term_variants.items():
            if any(v in tokens for v in variants):
                df[term]+=1

    n=max(1,len(records))
    out=[]
    for rec,tokens in zip(records,document_tokens):
        matched=[
            term for term,variants in term_variants.items()
            if any(v in tokens for v in variants)
        ]
        if not matched:
            continue
        name=str(rec.get("name") or "")
        lname=name.lower()
        name_tokens=_package_name_tokens(name)
        score=0.0
        for term in matched:
            idf=math.log((n+1)/(df.get(term,0)+1))+1.0
            in_name=any(v in name_tokens for v in term_variants[term])
            score+=idf*(1.35 if in_name else 1.0)

        # Joint semantic coverage is evidence. It is intentionally stronger
        # than package/executable naming coincidence.
        score+=0.55*max(0,len(matched)-1)

        friction=0
        if lname.startswith(("python3-","ruby-","golang-","php-","php")):
            friction=2
        if lname.startswith(("lib","librust-","libghc-")):
            friction=max(friction,3)
        if lname.endswith(("-dev","-doc","-dbg","-prof")):
            friction=max(friction,4)
        score-=0.35*friction

        out.append({
            "discovery_source":"APT_CATALOG",
            "name":name,
            "description":str(rec.get("description") or ""),
            "query":"SEMANTIC_APT_METADATA_INDEX",
            "matched_terms":sorted(matched),
            "score":round(score,8),
            "integration_friction":friction,
            "required_secret_count":0,
            "required_environment_count":0,
            "zero_cost_eligible":True,
            "eligibility_status":"LOCAL_PACKAGE_METADATA_CANDIDATE_UNVERIFIED",
            "binding_kind":"apt",
            "packages":[],
            "remotes":[],
        })

    out.sort(key=lambda x:(
        -float(x.get("score",0)),
        int(x.get("integration_friction",0)),
        str(x.get("name","")),
    ))
    return out[:max(1,min(int(limit),50))]


def _apt_file_list_executables(package,timeout_s=8):
    package=str(package or "").strip()
    if not package:
        return []
    if package in _APT_EXECUTABLE_PATHS_CACHE:
        return list(_APT_EXECUTABLE_PATHS_CACHE[package])
    if shutil.which("apt-file") is None:
        return []
    try:
        p=subprocess.run(
            ["apt-file","list",package],
            text=True,capture_output=True,timeout=timeout_s
        )
    except Exception:
        _APT_EXECUTABLE_PATHS_CACHE[package]=[]
        return []
    if p.returncode not in (0,1):
        _APT_EXECUTABLE_PATHS_CACHE[package]=[]
        return []
    paths=[]
    prefix=package+": "
    for line in p.stdout.splitlines():
        if not line.startswith(prefix):
            continue
        value=line[len(prefix):]
        normalized=str(value or "").strip().lstrip("/")
        if normalized.startswith("usr/bin/"):
            path="/"+normalized
            if path not in paths:
                paths.append(path)
    _APT_EXECUTABLE_PATHS_CACHE[package]=paths
    return list(paths)


def _attach_executable_ownership(candidates):
    if not candidates or shutil.which("apt-file") is None:
        return candidates
    workers=min(8,len(candidates))
    results={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        future_map={
            pool.submit(_apt_file_list_executables,c["name"]):c["name"]
            for c in candidates
        }
        for future in concurrent.futures.as_completed(future_map):
            name=future_map[future]
            try:
                results[name]=future.result()
            except Exception:
                results[name]=[]
    out=[]
    for cand in candidates:
        item=dict(cand)
        paths=results.get(cand["name"],[])
        if paths:
            item["executable_semantic_evidence"]={
                "command_paths":paths,
                "command_terms":[],
                "semantic_terms":effect_queries(item.get("description") or item.get("name") or ""),
                "semantic_hits":item.get("matched_terms") or [],
                "semantic_coverage":1.0,
                "acquisition_mode":"SEMANTIC_PACKAGE_METADATA_PLUS_APT_FILE_OWNERSHIP",
            }
            item["evidence_tier"]="SEMANTIC_PACKAGE_EXECUTABLE_OWNERSHIP"
            item["eligibility_status"]="LOCAL_EXECUTABLE_OWNERSHIP_VERIFIED"
        out.append(item)
    return out


def search_apt_packages(effect, limit=12):
    """Discover executable APT packages from semantics, then prove ownership.

    Package/executable names are never an admission requirement. The local APT
    metadata corpus generates semantically relevant candidates; apt-file only
    verifies executable ownership for the leading candidates.
    """
    if not sys.platform.startswith("linux") or shutil.which("apt-cache") is None:
        return {
            "schema":"PROJECT_BRAIN_CAPABILITY_DISCOVERY_RESULT_V1",
            "effect":effect,"source":"APT_CATALOG","source_url":None,
            "queries":effect_queries(effect),"candidate_count":0,"candidates":[],
            "errors":[{"error":"APT_CACHE_UNAVAILABLE"}],"binding_performed":False,
        }

    pool_limit=max(24,min(50,max(1,int(limit))*2))
    candidates=_apt_semantic_candidates(effect,limit=pool_limit)
    candidates=_attach_executable_ownership(candidates)

    # Verified executable ownership is the binding-confidence discriminator;
    # semantic relevance remains the ranking signal inside each tier.
    candidates.sort(key=lambda x:(
        0 if x.get("evidence_tier")=="SEMANTIC_PACKAGE_EXECUTABLE_OWNERSHIP" else 1,
        -float(x.get("score",0)),
        int(x.get("integration_friction",0)),
        str(x.get("name","")),
    ))
    candidates=candidates[:max(1,min(int(limit),50))]

    for cand in candidates:
        name=cand["name"]
        try:
            policy=subprocess.run(
                ["apt-cache","policy",name],
                text=True,capture_output=True,timeout=8
            )
            version=None
            for line in policy.stdout.splitlines():
                s=line.strip()
                if s.startswith("Candidate:"):
                    version=s.split(":",1)[1].strip()
                    break
            cand["version"]=version
        except Exception as exc:
            cand["metadata_error"]=type(exc).__name__+":"+str(exc)

    return {
        "schema":"PROJECT_BRAIN_CAPABILITY_DISCOVERY_RESULT_V1",
        "effect":effect,
        "source":"APT_CATALOG",
        "source_url":None,
        "queries":effect_queries(effect),
        "candidate_count":len(candidates),
        "candidates":candidates,
        "errors":[],
        "binding_performed":False,
    }


def _requested_output_format_tokens(effect):
    text=re.sub(r"https?://[^\s)\]}>]+"," ",str(effect or ""))
    paths=re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+",text)
    out=[]
    common={"json","txt","md","markdown","csv","tsv","html","xml","png","jpg","jpeg","webp","pdf","docx","xlsx","zip","gz","tgz","tar","sqlite","db","sqlite3"}
    for raw in paths:
        suffix=pathlib.PurePosixPath(raw.rstrip(".,;:!?)]}")).suffix.lower().lstrip(".")
        if suffix and suffix not in common and suffix not in out:
            out.append(suffix)
    return out


def _pypi_candidate_names(effect):
    names=[]
    for token in effect_queries(effect):
        variants=[
            token,
            token.replace("_","-"),
            token.replace("-",""),
        ]
        for value in variants:
            value=value.strip("-_.").lower()
            if re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,80}",value) and value not in names:
                names.append(value)
    return names[:12]


_EXTERNAL_PACKAGE_NAME_SEARCHER=None

def set_external_package_name_searcher(searcher):
    global _EXTERNAL_PACKAGE_NAME_SEARCHER
    _EXTERNAL_PACKAGE_NAME_SEARCHER=searcher

def _pypi_simple_related_names(effect,timeout_s=12,opener=None,limit=24):
    """Discover related PyPI project names from the official Simple index.

    PyPI does not expose a supported full-text search API. The Simple index is
    authoritative project-name metadata, so use it only to widen exact-name
    probes after those probes produce no viable candidate. No package code is
    downloaded or executed here.
    """
    opener=opener or urllib.request.urlopen
    format_tokens=_requested_output_format_tokens(effect)
    distinctive=format_tokens or [
        t for t in effect_queries(effect)
        if t not in GENERIC_DISCOVERY_TOKENS
        and t not in {"those","these","exact","records","record","fields","field","values","value","same","identical","order","count","save"}
        and not t.isdigit()
        and len(t)>=3
    ]
    if not distinctive:
        return []
    if callable(_EXTERNAL_PACKAGE_NAME_SEARCHER):
        try:
            names=_EXTERNAL_PACKAGE_NAME_SEARCHER(
                effect=effect, ecosystem="pypi", tokens=distinctive,
                limit=max(1,min(int(limit),50)), timeout_s=timeout_s
            )
            if isinstance(names,list):
                out=[]
                for raw in names:
                    project=str(raw or "").strip()
                    if re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,120}",project) and project.lower() not in [x.lower() for x in out]:
                        out.append(project)
                if out:
                    return out[:max(1,min(int(limit),50))]
        except Exception:
            pass
    req=urllib.request.Request(
        "https://pypi.org/simple/",
        headers={"User-Agent":"ProjectBrain-CapabilityDiscovery/1"}
    )
    found=[]
    try:
        with opener(req,timeout=timeout_s) as resp:
            carry=""
            total=0
            while True:
                raw=resp.read(262144)
                if not raw:
                    break
                total+=len(raw)
                # Bound metadata work. The current Simple index is large, but
                # 64 MiB is enough to inspect a substantial authoritative name
                # surface without turning discovery into an unbounded crawl.
                if total>64*1024*1024:
                    break
                text=carry+raw.decode("utf-8","replace")
                # Keep a small tail because an anchor may straddle chunks.
                carry=text[-1024:]
                body=text[:-1024] if len(text)>1024 else ""
                for name in re.findall(r">\s*([^<>\s][^<>]{0,120}?)\s*</a>",body,re.IGNORECASE):
                    project=name.strip()
                    normalized=re.sub(r"[-_.]+","",project.lower())
                    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,120}",project.lower()):
                        continue
                    if not any(re.sub(r"[-_.]+","",token.lower()) in normalized for token in distinctive):
                        continue
                    if project.lower() not in [x.lower() for x in found]:
                        found.append(project)
                    if len(found)>=max(1,min(int(limit),50)):
                        return found
            if carry:
                for name in re.findall(r">\s*([^<>\s][^<>]{0,120}?)\s*</a>",carry,re.IGNORECASE):
                    project=name.strip()
                    normalized=re.sub(r"[-_.]+","",project.lower())
                    if any(re.sub(r"[-_.]+","",token.lower()) in normalized for token in distinctive):
                        if re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,120}",project.lower()) and project.lower() not in [x.lower() for x in found]:
                            found.append(project)
                            if len(found)>=max(1,min(int(limit),50)):
                                break
    except Exception:
        return []
    return found


def search_pypi_packages(effect, limit=12, timeout_s=12, opener=None):
    """Probe exact PyPI project candidates derived from the effect contract.

    PyPI has no supported full-text search API, so this stays conservative:
    semantic/effect tokens and output extensions become exact project probes.
    Metadata discovery never installs code.
    """
    opener=opener or urllib.request.urlopen
    exact_queries=_pypi_candidate_names(effect)
    queries=list(exact_queries)
    candidates=[]
    errors=[]
    effect_tokens=set(effect_queries(effect))

    def probe_queries(query_values):
        local=[]
        local_errors=[]
        for query in query_values:
            url="https://pypi.org/pypi/"+urllib.parse.quote(query,safe="")+"/json"
            req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-CapabilityDiscovery/1"})
            try:
                with opener(req,timeout=timeout_s) as resp:
                    raw=resp.read(3000000)
                payload=json.loads(raw.decode("utf-8"))
            except Exception as exc:
                local_errors.append({"query":query,"error":type(exc).__name__+":"+str(exc)})
                continue
            info=payload.get("info") or {}
            name=str(info.get("name") or query)
            version=str(info.get("version") or "")
            if not version:
                continue
            urls=payload.get("urls") or []
            wheels=[]
            for item in urls:
                filename=str(item.get("filename") or "")
                digest=str((item.get("digests") or {}).get("sha256") or "").lower()
                artifact_url=str(item.get("url") or "")
                if filename.endswith(".whl") and re.fullmatch(r"[0-9a-f]{64}",digest) and artifact_url.startswith("https://"):
                    wheels.append({
                      "filename":filename,
                      "sha256":digest,
                      "url":artifact_url,
                      "size":item.get("size"),
                      "python_version":item.get("python_version"),
                    })
            if not wheels:
                continue
            blob=(name+" "+str(info.get("summary") or "")+" "+str(info.get("keywords") or "")).lower()
            matched=sorted(t for t in effect_tokens if t in blob or t==re.sub(r"[-_.]+","",name.lower()))
            normalized_name=re.sub(r"[-_.]+","",name.lower())
            normalized_query=re.sub(r"[-_.]+","",query.lower())
            score=(50 if normalized_name==normalized_query else 0)+12*len(matched)
            format_tokens=_requested_output_format_tokens(effect)
            normalized_blob=re.sub(r"[-_.]+","",blob)
            raw_name=str(name or "").lower()
            name_segments=[x for x in re.split(r"[-_.]+",raw_name) if x]
            for fmt in format_tokens:
                nfmt=re.sub(r"[-_.]+","",fmt.lower())
                if not nfmt:
                    continue
                if normalized_name==nfmt:
                    score+=180
                elif raw_name.startswith(fmt.lower()+"-") or raw_name.startswith(fmt.lower()+"_") or raw_name.startswith(fmt.lower()+"."):
                    score+=150
                elif fmt.lower() in name_segments:
                    score+=130
                elif normalized_name.startswith(nfmt):
                    score+=110
                elif nfmt in normalized_name:
                    score+=45
                elif nfmt in normalized_blob:
                    score+=25
            requires_dist=info.get("requires_dist") or []
            dependency_count=len(requires_dist) if isinstance(requires_dist,list) else 0
            score-=4*dependency_count
            local.append({
              "discovery_source":"PYPI",
              "name":name,
              "project":name,
              "description":str(info.get("summary") or ""),
              "version":version,
              "metadata_url":"https://pypi.org/pypi/"+urllib.parse.quote(name,safe="")+"/"+urllib.parse.quote(version,safe="")+"/json",
              "query":query,
              "matched_terms":matched,
              "score":score,
              "integration_friction":1+dependency_count,
              "required_secret_count":0,
              "required_environment_count":0,
              "dependency_count":dependency_count,
              "zero_cost_eligible":True,
              "eligibility_status":"PYPI_METADATA_CANDIDATE_UNVERIFIED",
              "binding_kind":"pypi",
              "wheels":wheels,
              "requires_python":info.get("requires_python"),
              "license":info.get("license"),
            })
        return local,local_errors

    exact_candidates,exact_errors=probe_queries(exact_queries)
    candidates.extend(exact_candidates)
    errors.extend(exact_errors)

    # Exact-name probing misses common relationships such as a format token
    # being embedded in a longer project name. Widen unless an exact probe
    # produced a candidate that actually matches the requested binary format.
    format_tokens=_requested_output_format_tokens(effect)
    def matches_requested_format(cand):
        if not format_tokens:
            return True
        blob=(
            str(cand.get("name") or "")+" "
            +str(cand.get("description") or "")+" "
            +" ".join(str(x) for x in cand.get("matched_terms") or [])
        ).lower()
        normalized=re.sub(r"[-_.]+","",blob)
        return any(re.sub(r"[-_.]+","",fmt.lower()) in normalized for fmt in format_tokens)

    if not any(matches_requested_format(x) for x in candidates):
        related=_pypi_simple_related_names(effect,timeout_s=timeout_s,opener=opener,limit=max(12,int(limit)*2))
        related=[x for x in related if x.lower() not in {q.lower() for q in queries}]
        queries.extend(related)
        widened,widened_errors=probe_queries(related)
        candidates.extend(widened)
        errors.extend(widened_errors)

    # Deduplicate projects while preserving the best-scoring metadata record.
    by_project={}
    for cand in candidates:
        key=re.sub(r"[-_.]+","",str(cand.get("project") or cand.get("name") or "").lower())
        prior=by_project.get(key)
        if prior is None or float(cand.get("score",0))>float(prior.get("score",0)):
            by_project[key]=cand
    candidates=list(by_project.values())

    candidates.sort(key=lambda x:(-float(x.get("score",0)),int(x.get("dependency_count",0)),str(x.get("name",""))))
    return {
      "schema":"PROJECT_BRAIN_CAPABILITY_DISCOVERY_RESULT_V1",
      "effect":effect,
      "source":"PYPI",
      "source_url":"https://pypi.org/",
      "queries":queries,
      "candidate_count":len(candidates),
      "candidates":candidates[:max(1,min(int(limit),50))],
      "errors":errors,
      "binding_performed":False,
    }


def search_all(effect, limit_per_source=12):
    """Federated discovery. Metadata is candidate evidence, never binding proof."""
    results=[
        search_apt_packages(effect,limit=limit_per_source),
        search_pypi_packages(effect,limit=limit_per_source,timeout_s=12),
        search_mcp_registry(effect,limit=limit_per_source,timeout_s=12),
    ]
    merged=[]
    for result in results:
        source=result.get("source")
        for cand in result.get("candidates",[]):
            x=dict(cand)
            x["discovery_source"]=source
            if source=="OFFICIAL_MCP_REGISTRY":
                x["eligibility_status"]="REMOTE_REGISTRY_METADATA_CANDIDATE_UNVERIFIED"
                x["live_probe_required"]=True
            merged.append(x)
    # Prefer local zero-secret supply when capability relevance is comparable.
    merged.sort(key=lambda x:(
        not bool(x.get("zero_cost_eligible")),
        x.get("required_secret_count",0)>0,
        0 if x.get("discovery_source") in {"APT_CATALOG","PYPI"} else 1,
        int(x.get("integration_friction",1 if x.get("discovery_source")=="OFFICIAL_MCP_REGISTRY" else 0)),
        -float(x.get("score",0)),
        str(x.get("name","")),
    ))
    return {
        "schema":"PROJECT_BRAIN_FEDERATED_CAPABILITY_DISCOVERY_V1",
        "effect":effect,
        "sources":[r.get("source") for r in results],
        "results":results,
        "candidates":merged[:max(1,min(int(limit_per_source)*2,50))],
        "binding_performed":False,
    }
