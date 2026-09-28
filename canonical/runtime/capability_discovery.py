#!/usr/bin/env python3
"""Deterministic external capability discovery for Project Brain.

Current source: official public MCP Registry. The registry is an optional
metadata source, never canonical authority. Discovery does not execute or
install third-party code. Binding is a separate verified step.
"""
from __future__ import annotations

import json
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
OPERATION_TOKENS={
    "create","generate","render","resize","compress","compressed","decompress","decompressed",
    "convert","transform","encode","decode","extract","archive","query","insert","update",
    "delete","parse","scan","verify","validate","compare","calculate","compute","compile",
    "build","export","import","merge","split","transcode","download","upload","search"
}
FORMAT_TOKENS={
    "json","xml","csv","tsv","yaml","yml","html","pdf","png","jpg","jpeg","webp",
    "gif","svg","zip","gzip","gz","tgz","tar","sqlite","sqlite3","db","dot","markdown","md"
}
CONSTRAINT_TOKENS={
    "exact","exactly","primary","key","rows","row","columns","column","pixels","pixel",
    "named","name","same","identical","order","count","utf","utf8","width","height"
}
RELATION_NOISE={
    "at","whose","result","results","containing","contains","every","its","that","final",
    "those","these","with","for","from","into","onto","of","by","using","as","to","and","or"
}
FORMAT_DOMAIN_HINTS={
    "png":["image","graphics"],"jpg":["image","graphics"],"jpeg":["image","graphics"],
    "webp":["image","graphics"],"gif":["image","graphics"],"svg":["image","graphics"],
    "gzip":["compression","archive"],"gz":["compression","archive"],"tgz":["compression","archive"],
    "zip":["compression","archive"],"tar":["archive"],
    "sqlite":["database"],"sqlite3":["database"],"db":["database"],
    "dot":["graph"],"json":["structured","data"],"xml":["structured","data"],
    "csv":["tabular","data"],"tsv":["tabular","data"],"pdf":["document"]
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


def effect_semantic_roles(effect):
    """Extract a minimal role-separated effect representation.

    This is intentionally small: it preserves distinctions that flat lexical
    ranking destroyed without naming any supplier or benchmark.
    """
    if not isinstance(effect,str) or not effect.strip():
        raise DiscoveryFailure("EFFECT_REQUIRED")
    semantic=_semanticize_paths(effect)
    raw=[
        t.lower() for t in re.split(r"[^A-Za-z0-9]+",semantic)
        if len(t)>=2
    ]
    operation=[]
    fmt=[]
    constraints=[]
    domain=[]

    def add(bucket,value):
        value=str(value or "").lower()
        if value and value not in bucket:
            bucket.append(value)

    for token in raw:
        if token in OPERATION_TOKENS:
            add(operation,token)
        if token in FORMAT_TOKENS:
            add(fmt,token)
        if token in CONSTRAINT_TOKENS or token.isdigit():
            add(constraints,token)

    # Preserve domain nouns even when they were historically classed as
    # "generic" (for example image). Exclude syntax, operations, formats and
    # constraint vocabulary.
    for token in raw:
        if (
            token in STOPWORDS or token in RELATION_NOISE
            or token in OPERATION_TOKENS or token in FORMAT_TOKENS
            or token in CONSTRAINT_TOKENS or token.isdigit()
        ):
            continue
        add(domain,token)

    # Format names carry domain knowledge that should not need package-name
    # hints: a PNG is an image, gzip is compression/archive, SQLite is a DB.
    for token in fmt:
        for hint in FORMAT_DOMAIN_HINTS.get(token,[]):
            add(domain,hint)

    return {
      "operation":operation[:4],
      "domain":domain[:6],
      "format":fmt[:4],
      "constraints":constraints[:8],
    }


def effect_queries(effect):
    roles=effect_semantic_roles(effect)
    out=[]
    # Search intent is ordered by causal role. Constraints are retained in the
    # IR but are not allowed to crowd operation/domain/format out of top-K
    # catalog queries.
    for role in ("operation","domain","format"):
        for token in roles[role]:
            if token not in out:
                out.append(token)
            if len(out)>=8:
                return out
    if not out:
        compact=re.sub(r"[^A-Za-z0-9]+","",str(effect)).lower()
        if compact:
            out.append(compact)
    return out[:8]


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


def _apt_supplier_role(name,description):
    name=str(name or "").lower()
    desc=str(description or "").lower()
    blob=name+" "+desc
    evidence=[]

    if name.startswith(("lib","python3-","python-","ruby-","golang-","php-","php")):
        evidence.append("LANGUAGE_LIBRARY_OR_BINDING")
    if name.endswith(("-dev","-doc","-dbg","-prof")) or "documentation" in desc:
        evidence.append("DEV_OR_DOCUMENTATION")
    if any(x in blob for x in (" emacs","emacs "," vim"," editor mode"," major mode")):
        evidence.append("EDITOR_EXTENSION")
    if any(x in desc for x in (" backend","backend "," connectivity module"," plugin"," bindings"," binding ")):
        evidence.append("BACKEND_PLUGIN_OR_BINDING")
    if any(x in desc for x in (" dictionary"," fonts"," icons"," flags"," data files"," examples")):
        evidence.append("DATA_ASSET")

    if evidence:
        return {"role":"AUXILIARY_OR_NON_DIRECT","evidence":sorted(set(evidence))}
    return {"role":"DIRECT_EXECUTABLE_CANDIDATE","evidence":[]}


def _candidate_role_alignment(name,description,roles):
    blob=(str(name or "")+" "+str(description or "")).lower()
    ordered=re.findall(r"[a-z0-9]+",blob)
    tokens=set(ordered) | {
        ordered[i]+ordered[i+1]
        for i in range(len(ordered)-1)
        if len(ordered[i])>=2 and len(ordered[i+1])>=2
    }
    out={}
    for role in ("operation","domain","format"):
        hits=[]
        for term in roles.get(role,[]):
            if any(v in tokens for v in _lexical_variants(term)):
                hits.append(term)
        out[role]=hits
    return out


def _score_apt_candidate(name,description,matched,roles):
    ordered_name_tokens=re.findall(r"[a-z0-9]+",str(name or "").lower())
    name_tokens=set(ordered_name_tokens) | {
        ordered_name_tokens[i]+ordered_name_tokens[i+1]
        for i in range(len(ordered_name_tokens)-1)
    }
    alignment=_candidate_role_alignment(name,description,roles)
    supplier_role=_apt_supplier_role(name,description)

    score=0
    weights={"operation":26,"domain":30,"format":14}
    for role,weight in weights.items():
        for term in alignment[role]:
            score += weight
            if any(v in name_tokens for v in _lexical_variants(term)):
                score += weight//2

    # Keep lexical overlap as subordinate evidence, not the representation.
    for term in matched:
        if not any(term in roles.get(role,[]) for role in ("operation","domain","format")):
            score += 2

    if supplier_role["role"]=="DIRECT_EXECUTABLE_CANDIDATE":
        score += 28
        integration_friction=0
    else:
        score -= 48
        integration_friction=3

    lname=str(name or "").lower()
    if lname.startswith(("python3-","python-","ruby-","golang-","php-","php")):
        integration_friction=max(integration_friction,2)
    if lname.startswith(("lib","librust-","libghc-")):
        integration_friction=max(integration_friction,3)
    if lname.endswith(("-dev","-doc","-dbg","-prof")):
        integration_friction=max(integration_friction,4)

    return score,integration_friction,supplier_role,alignment


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


def _apt_query_variants(queries):
    out=[]
    for query in queries:
        if query not in out:
            out.append(query)
        # Package descriptions frequently spell lexical compounds with a
        # separator while goals use a closed compound, e.g. barcode vs
        # "bar code", qrcode vs "qr-code". apt-cache accepts regex queries,
        # so add a bounded equivalent without introducing domain names.
        if query.endswith("code") and len(query)>4:
            stem=query[:-4]
            for variant in (stem+" code", stem+"-code"):
                if variant not in out:
                    out.append(variant)
    return out


def search_apt_packages(effect, limit=12):
    """Search the local Ubuntu/Debian package catalog without installing anything."""
    if not sys.platform.startswith("linux") or shutil.which("apt-cache") is None:
        return {
            "schema":"PROJECT_BRAIN_CAPABILITY_DISCOVERY_RESULT_V1",
            "effect":effect,"source":"APT_CATALOG","source_url":None,
            "queries":effect_queries(effect),"candidate_count":0,"candidates":[],
            "errors":[{"error":"APT_CACHE_UNAVAILABLE"}],"binding_performed":False,
        }
    roles=effect_semantic_roles(effect)
    queries=effect_queries(effect)
    apt_queries=_apt_query_variants(queries)
    seen={}
    errors=[]
    effect_tokens=set(queries)
    for query in apt_queries:
        try:
            p=subprocess.run(
                ["apt-cache","search",query],
                text=True,capture_output=True,timeout=20
            )
        except Exception as exc:
            errors.append({"query":query,"error":type(exc).__name__+":"+str(exc)})
            continue
        if p.returncode!=0:
            errors.append({"query":query,"error":"APT_SEARCH_FAILED:"+p.stderr[-500:]})
            continue
        for line in p.stdout.splitlines():
            if " - " not in line:
                continue
            name,description=line.split(" - ",1)
            name=name.strip(); description=description.strip()
            blob=(name+" "+description).lower()
            ordered_blob_tokens=re.findall(r"[a-z0-9]+",blob)
            blob_tokens=set(ordered_blob_tokens)
            # Treat common lexical compounds equivalently across package
            # metadata styles: "bar code" -> "barcode", "qr code" ->
            # "qrcode", etc. This stays domain-independent and prevents a
            # spacing convention from hiding the best supplier/verifier.
            compound_tokens={
                ordered_blob_tokens[i]+ordered_blob_tokens[i+1]
                for i in range(len(ordered_blob_tokens)-1)
                if len(ordered_blob_tokens[i])>=2 and len(ordered_blob_tokens[i+1])>=2
            }
            lexical_tokens=blob_tokens | compound_tokens
            matched={
                t for t in effect_tokens
                if any(v in lexical_tokens for v in _lexical_variants(t))
            }
            if not matched:
                continue
            score,integration_friction,supplier_role,semantic_alignment=_score_apt_candidate(
                name,description,matched,roles
            )
            prior=seen.get(name)
            cand={
                "discovery_source":"APT_CATALOG",
                "name":name,
                "description":description,
                "query":query,
                "matched_terms":sorted(matched),
                "score":score,
                "integration_friction":integration_friction,
                "effect_semantic_roles":roles,
                "supplier_role":supplier_role,
                "semantic_role_alignment":semantic_alignment,
                "required_secret_count":0,
                "required_environment_count":0,
                "zero_cost_eligible":True,
                "eligibility_status":"LOCAL_PACKAGE_METADATA_CANDIDATE_UNVERIFIED",
                "binding_kind":"apt",
                "packages":[],
                "remotes":[],
            }
            if prior is None or cand["score"]>prior["score"]:
                seen[name]=cand
    ranked=sorted(seen.values(),key=lambda x:(-x["score"],x["name"]))[:max(1,min(int(limit),50))]
    enriched=[]
    for cand in ranked:
        name=cand["name"]
        try:
            policy=subprocess.run(["apt-cache","policy",name],text=True,capture_output=True,timeout=10)
            version=None
            for line in policy.stdout.splitlines():
                s=line.strip()
                if s.startswith("Candidate:"):
                    version=s.split(":",1)[1].strip()
                    break
            sha=None
            if version and version!="(none)":
                show=subprocess.run(["apt-cache","show",f"{name}={version}"],text=True,capture_output=True,timeout=15)
                for line in show.stdout.splitlines():
                    if line.startswith("SHA256:"):
                        sha=line.split(":",1)[1].strip().lower()
                        break
            cand["version"]=version
            cand["archive_sha256"]=sha
        except Exception as exc:
            cand["metadata_error"]=type(exc).__name__+":"+str(exc)
        enriched.append(cand)
    return {
        "schema":"PROJECT_BRAIN_CAPABILITY_DISCOVERY_RESULT_V1",
        "effect":effect,
        "source":"APT_CATALOG",
        "source_url":None,
        "queries":queries,
        "effect_semantic_roles":roles,
        "candidate_count":len(enriched),
        "candidates":enriched,
        "errors":errors,
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
