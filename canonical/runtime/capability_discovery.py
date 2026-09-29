#!/usr/bin/env python3
"""Deterministic external capability discovery for Project Brain.

Current source: official public MCP Registry. The registry is an optional
metadata source, never canonical authority. Discovery does not execute or
install third-party code. Binding is a separate verified step.
"""
from __future__ import annotations

import concurrent.futures
import html
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



_EXTERNAL_APT_EXECUTABLE_EVIDENCE_SEARCHER=None
_MANPAGE_TEXT_CACHE={}

def set_external_apt_executable_evidence_searcher(searcher):
    """Inject a provider-neutral executable evidence supplier for verification/tests."""
    global _EXTERNAL_APT_EXECUTABLE_EVIDENCE_SEARCHER
    _EXTERNAL_APT_EXECUTABLE_EVIDENCE_SEARCHER=searcher


def _effect_semantic_terms(effect):
    semantic=_semanticize_paths(effect)
    low_information=set(GENERIC_DISCOVERY_TOKENS) | {
        "those","these","exact","records","record","fields","field",
        "values","value","same","identical","order","count","save",
        "plain","document","file","using","report"
    }
    out=[]
    for token in re.split(r"[^A-Za-z0-9]+",semantic):
        t=token.lower()
        if len(t)<3 or t in STOPWORDS or t in low_information or t.isdigit():
            continue
        if t not in out:
            out.append(t)
    return out[:8]


def _ubuntu_codename():
    try:
        text=pathlib.Path("/etc/os-release").read_text(encoding="utf-8")
        id_match=re.search(r"^ID=([A-Za-z0-9._-]+)$",text,re.MULTILINE)
        codename_match=re.search(r"^VERSION_CODENAME=([A-Za-z0-9._-]+)$",text,re.MULTILINE)
        distro=(id_match.group(1).lower() if id_match else "")
        if distro=="ubuntu" and codename_match:
            return codename_match.group(1).lower()
    except Exception:
        pass
    # The enrichment source is Ubuntu manpages even when the execution host is
    # another Debian-family distribution, so never feed Debian codenames into it.
    return "noble"


def _fetch_ubuntu_manpage_text(command,timeout_s=4,opener=None):
    command=str(command or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.+-]{1,120}",command):
        return ""
    key=(_ubuntu_codename(),command)
    if key in _MANPAGE_TEXT_CACHE:
        return _MANPAGE_TEXT_CACHE[key]
    opener=opener or urllib.request.urlopen
    base=(
        "https://manpages.ubuntu.com/manpages/"
        +urllib.parse.quote(key[0],safe="")
        +"/man1/"+urllib.parse.quote(command,safe="")
    )
    text=""
    # Section 1 covers normal commands; 1p catches packaged Perl CLIs such as
    # exiftool. The two-attempt ceiling keeps enrichment bounded.
    for suffix in (".1.html",".1p.html"):
        url=base+suffix
        req=urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-CapabilityDiscovery/1"})
        try:
            with opener(req,timeout=timeout_s) as resp:
                raw=resp.read(120000)
            page=raw.decode("utf-8","replace")
            page=re.sub(r"<script\b[^>]*>.*?</script>"," ",page,flags=re.I|re.S)
            page=re.sub(r"<style\b[^>]*>.*?</style>"," ",page,flags=re.I|re.S)
            page=re.sub(r"<[^>]+>"," ",page)
            text=html.unescape(re.sub(r"\s+"," ",page)).strip()
            if text:
                break
        except Exception:
            continue
    _MANPAGE_TEXT_CACHE[key]=text
    return text


def _local_apt_executable_evidence(effect,limit=36):
    """Acquire executable-path evidence in one literal multi-pattern apt-file scan.

    This deliberately avoids one regex scan per semantic term. apt-file's
    --from-file path performs one multi-pattern search. Returned rows are then
    filtered to executable paths and scored in-process. Only a small leading
    set receives remote manpage enrichment.
    """
    if shutil.which("apt-file") is None:
        return []
    terms=_effect_semantic_terms(effect)
    if not terms:
        return []
    pattern_blob="\n".join(terms)+"\n"
    try:
        p=subprocess.run(
            ["apt-file","--from-file","--stream-results","search","-"],
            input=pattern_blob,text=True,capture_output=True,timeout=45
        )
    except Exception:
        return []
    if p.returncode not in (0,1):
        return []

    evidence={}
    for line in p.stdout.splitlines():
        if ": " not in line:
            continue
        package,path=line.split(": ",1)
        package=package.strip(); path=path.strip()
        normalized=path.lstrip("/")
        if not package or not normalized.startswith("usr/bin/"):
            continue
        command=normalized.rsplit("/",1)[-1].lower()
        compact=re.sub(r"[^a-z0-9]+","",command)
        hits=[]
        for term in terms:
            tc=re.sub(r"[^a-z0-9]+","",term)
            if term in command or (tc and tc in compact):
                hits.append(term)
        if not hits:
            continue
        ev=evidence.setdefault(package,{"command_paths":set(),"command_terms":set()})
        ev["command_paths"].add("/"+normalized)
        ev["command_terms"].update(hits)

    prelim=[]
    for package,ev in evidence.items():
        paths=sorted(ev["command_paths"])
        hits=sorted(ev["command_terms"])
        score=100*len(hits)+20*len(paths)
        for path in paths:
            cmd=path.rsplit("/",1)[-1].lower()
            for term in hits:
                if cmd==term:
                    score+=80
                elif cmd.startswith(term) or cmd.endswith(term):
                    score+=30
        prelim.append((score,package,paths,hits))
    prelim.sort(key=lambda x:(-x[0],x[1]))
    prelim=prelim[:max(1,min(int(limit),50))]

    # Semantic enrichment is deliberately bounded. Direct executable evidence
    # narrows the field first; remote text is fetched only where it can still
    # change the final ranking.
    enrich_limit=min(12,len(prelim))
    jobs=[]
    for _,package,paths,_ in prelim[:enrich_limit]:
        if paths:
            jobs.append((package,paths[0].rsplit("/",1)[-1]))

    man_by_package={}
    if jobs:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8,len(jobs))) as pool:
            future_map={
                pool.submit(_fetch_ubuntu_manpage_text,command): (package,command)
                for package,command in jobs
            }
            for future in concurrent.futures.as_completed(future_map):
                package,command=future_map[future]
                try:
                    text=future.result()
                except Exception:
                    text=""
                if text:
                    man_by_package[package]={"command":command,"text":text[:16000]}

    out=[]
    for _,package,paths,command_hits in prelim:
        page=man_by_package.get(package)
        combined=" ".join(path.rsplit("/",1)[-1] for path in paths)
        if page:
            combined+=" "+page["text"]
        low=combined.lower()
        compact=re.sub(r"[^a-z0-9]+","",low)
        semantic_hits=[]
        for term in terms:
            tc=re.sub(r"[^a-z0-9]+","",term)
            if term in low or (tc and tc in compact):
                semantic_hits.append(term)
        out.append({
            "name":package,
            "command_paths":paths,
            "command_terms":command_hits,
            "manpage_commands":[page["command"]] if page else [],
            "semantic_terms":terms,
            "semantic_hits":sorted(set(semantic_hits)),
            "semantic_coverage":len(set(semantic_hits))/len(terms) if terms else 0.0,
            "acquisition_mode":"APT_FILE_FROM_FILE_LITERAL_BATCH",
        })
    return out



def _axi_cache_package_candidates(effect,limit=36):
    """Reuse Apt Xapian relevance search as a package-level candidate generator.

    This does not install or execute candidates. It only broadens package
    discovery beyond exact executable-name overlap. axi-cache results are
    already relevance sorted and may use indexed package metadata and Debtags.
    """
    if shutil.which("axi-cache") is None:
        return []
    queries=effect_queries(effect)
    if not queries:
        return []

    def run(query_terms):
        try:
            p=subprocess.run(
                ["axi-cache","--all","search",*query_terms],
                text=True,capture_output=True,timeout=12
            )
        except Exception:
            return []
        if p.returncode!=0:
            return []
        out=[]
        for line in p.stdout.splitlines():
            m=re.match(r"^\s*(\d+)%\s+(\S+)\s+-\s+(.*)$",line)
            if not m:
                continue
            score=int(m.group(1))
            name=m.group(2).strip()
            description=m.group(3).strip()
            if not name:
                continue
            out.append({
                "name":name,
                "description":description,
                "relevance":score,
                "acquisition_mode":"APT_XAPIAN_RELEVANCE",
            })
            if len(out)>=max(1,min(int(limit),100)):
                break
        return out

    # Prefer one relevance query. If it returns nothing, fall back to a few
    # independent terms rather than multiplying calls in the common case.
    found=run(queries)
    if not found:
        merged={}
        for query in queries[:4]:
            for row in run([query]):
                prior=merged.get(row["name"])
                if prior is None or row["relevance"]>prior["relevance"]:
                    merged[row["name"]]=row
        found=sorted(
            merged.values(),
            key=lambda x:(-int(x["relevance"]),str(x["name"]))
        )
    return found[:max(1,min(int(limit),100))]


def _preferred_package_command(package,paths,terms):
    package_compact=re.sub(r"[^a-z0-9]+","",str(package or "").lower())
    def key(path):
        command=path.rsplit("/",1)[-1].lower()
        compact=re.sub(r"[^a-z0-9]+","",command)
        exact_pkg=(compact==package_compact)
        term_hits=sum(
            1 for term in terms
            if re.sub(r"[^a-z0-9]+","",term) in compact
        )
        return (not exact_pkg,-term_hits,len(command),command)
    return min(paths,key=key).rsplit("/",1)[-1] if paths else None


def _batched_package_executable_evidence(effect,package_names,limit=36):
    """Enumerate executables for relevant packages in one apt-file list batch.

    Unlike the older name-first path, admission here is package relevance.
    Executable names do not need to contain literal task tokens.
    """
    if shutil.which("apt-file") is None:
        return []
    terms=_effect_semantic_terms(effect)
    ordered=[]
    for raw in package_names:
        name=str(raw or "").strip()
        if name and name not in ordered:
            ordered.append(name)
    ordered=ordered[:max(1,min(int(limit),50))]
    if not ordered:
        return []

    try:
        p=subprocess.run(
            ["apt-file","--from-file","--stream-results","list","-"],
            input="\n".join(ordered)+"\n",
            text=True,capture_output=True,timeout=45
        )
    except Exception:
        return []
    if p.returncode not in (0,1):
        return []

    allowed=set(ordered)
    paths_by_package={name:set() for name in ordered}
    for line in p.stdout.splitlines():
        if ": " not in line:
            continue
        package,path=line.split(": ",1)
        package=package.strip(); path=path.strip()
        normalized=path.lstrip("/")
        if package not in allowed or not normalized.startswith("usr/bin/"):
            continue
        paths_by_package[package].add("/"+normalized)

    selected=[]
    for package in ordered:
        paths=sorted(paths_by_package.get(package) or [])
        if not paths:
            continue
        command=_preferred_package_command(package,paths,terms)
        selected.append((package,paths,command))

    # Preserve the existing bounded semantic-enrichment budget.
    jobs=[]
    for package,paths,command in selected[:12]:
        if command:
            jobs.append((package,command))
    man_by_package={}
    if jobs:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8,len(jobs))) as pool:
            future_map={
                pool.submit(_fetch_ubuntu_manpage_text,command):(package,command)
                for package,command in jobs
            }
            for future in concurrent.futures.as_completed(future_map):
                package,command=future_map[future]
                try:
                    text=future.result()
                except Exception:
                    text=""
                if text:
                    man_by_package[package]={"command":command,"text":text[:16000]}

    out=[]
    for package,paths,command in selected:
        page=man_by_package.get(package)
        combined=" ".join(path.rsplit("/",1)[-1] for path in paths)
        if page:
            combined+=" "+page["text"]
        low=combined.lower()
        compact=re.sub(r"[^a-z0-9]+","",low)
        semantic_hits=[]
        for term in terms:
            tc=re.sub(r"[^a-z0-9]+","",term)
            if term in low or (tc and tc in compact):
                semantic_hits.append(term)
        out.append({
            "name":package,
            "command_paths":paths,
            "command_terms":[],
            "manpage_commands":[page["command"]] if page else [],
            "semantic_terms":terms,
            "semantic_hits":sorted(set(semantic_hits)),
            "semantic_coverage":len(set(semantic_hits))/len(terms) if terms else 0.0,
            "acquisition_mode":"APT_XAPIAN_RELEVANCE_PLUS_BATCH_PACKAGE_ENUMERATION",
        })
    return out


def _apt_executable_evidence(effect,limit=36):
    if callable(_EXTERNAL_APT_EXECUTABLE_EVIDENCE_SEARCHER):
        try:
            value=_EXTERNAL_APT_EXECUTABLE_EVIDENCE_SEARCHER(
                effect=effect,
                semantic_terms=_effect_semantic_terms(effect),
                limit=max(1,min(int(limit),50)),
            )
            if isinstance(value,list):
                return value
        except Exception:
            pass
    return _local_apt_executable_evidence(effect,limit=limit)


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
    queries=effect_queries(effect)

    # Fast discovery path: package relevance is enough to choose candidates.
    # Executable enumeration, remote manpages, and archive hashing belong to
    # binding/verification after a package has been selected, not discovery.
    xapian_fast=_axi_cache_package_candidates(
        effect,limit=max(24,min(50,max(1,int(limit))*3))
    )
    if xapian_fast:
        candidates=[]
        for ax in xapian_fast[:max(1,min(int(limit),50))]:
            name=str(ax.get("name") or "").strip()
            if not name:
                continue
            candidates.append({
                "discovery_source":"APT_CATALOG",
                "name":name,
                "description":str(ax.get("description") or ""),
                "query":"APT_XAPIAN_RELEVANCE",
                "matched_terms":[],
                "score":60+float(ax.get("relevance") or 0),
                "integration_friction":0,
                "required_secret_count":0,
                "required_environment_count":0,
                "zero_cost_eligible":True,
                "eligibility_status":"LOCAL_PACKAGE_METADATA_CANDIDATE_UNVERIFIED",
                "binding_kind":"apt",
                "packages":[],
                "remotes":[],
                "package_relevance_source":"APT_XAPIAN_RELEVANCE",
            })
        return {
            "schema":"PROJECT_BRAIN_CAPABILITY_DISCOVERY_RESULT_V1",
            "effect":effect,
            "source":"APT_CATALOG",
            "source_url":None,
            "queries":queries,
            "candidate_count":len(candidates),
            "candidates":candidates,
            "errors":[],
            "binding_performed":False,
        }

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
            score=0
            ordered_name_tokens=re.findall(r"[a-z0-9]+",name.lower())
            name_tokens=set(ordered_name_tokens) | {
                ordered_name_tokens[i]+ordered_name_tokens[i+1]
                for i in range(len(ordered_name_tokens)-1)
            }
            for t in matched:
                distinctive=t not in GENERIC_DISCOVERY_TOKENS
                if t in name_tokens:
                    score += 24 if distinctive else 6
                else:
                    score += 10 if distinctive else 2
            # Integration friction matters more than word count. Standalone
            # executables are usually cheaper to bind than language libraries.
            lname=name.lower()
            integration_friction=0
            if lname.startswith(("python3-","ruby-","golang-","php-","php")):
                integration_friction=2
                score-=10
            if lname.startswith(("lib","librust-","libghc-")):
                integration_friction=3
                score-=12
            if name.endswith(("-dev","-doc","-dbg","-prof")):
                integration_friction=max(integration_friction,4)
                score-=8
            if integration_friction==0:
                score+=8
            # Reward candidates that jointly cover multiple distinct pieces
            # of the requested effect. A package matching both "decode" and
            # "barcode" is more useful than one that merely mentions barcode.
            if len(matched)>1:
                score += 20*(len(matched)-1)
            if lname in effect.lower():
                score+=8
            prior=seen.get(name)
            cand={
                "discovery_source":"APT_CATALOG",
                "name":name,
                "description":description,
                "query":query,
                "matched_terms":sorted(matched),
                "score":score,
                "integration_friction":integration_friction,
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
    literal_evidence=_apt_executable_evidence(
        effect,limit=max(24,min(50,max(1,int(limit))*3))
    )
    relevance_seed_names=[
        x["name"] for x in sorted(
            seen.values(),
            key=lambda x:(-float(x.get("score",0)),int(x.get("integration_friction",0)),str(x.get("name","")))
        )[:max(24,min(50,max(1,int(limit))*3))]
    ]
    relevance_evidence=_batched_package_executable_evidence(
        effect,relevance_seed_names,
        limit=max(24,min(50,max(1,int(limit))*3))
    )

    evidence_by_name={}
    for ev in list(literal_evidence)+list(relevance_evidence):
        name=str(ev.get("name") or "").strip()
        if not name:
            continue
        prior=evidence_by_name.get(name)
        if prior is None:
            evidence_by_name[name]=dict(ev)
            continue
        merged=dict(prior)
        merged["command_paths"]=sorted(set(prior.get("command_paths") or [])|set(ev.get("command_paths") or []))
        merged["command_terms"]=sorted(set(prior.get("command_terms") or [])|set(ev.get("command_terms") or []))
        merged["manpage_commands"]=sorted(set(prior.get("manpage_commands") or [])|set(ev.get("manpage_commands") or []))
        merged["semantic_terms"]=sorted(set(prior.get("semantic_terms") or [])|set(ev.get("semantic_terms") or []))
        merged["semantic_hits"]=sorted(set(prior.get("semantic_hits") or [])|set(ev.get("semantic_hits") or []))
        terms=merged.get("semantic_terms") or []
        merged["semantic_coverage"]=len(merged["semantic_hits"])/len(terms) if terms else 0.0
        modes={str(prior.get("acquisition_mode") or ""),str(ev.get("acquisition_mode") or "")}
        merged["acquisition_mode"]="+".join(sorted(x for x in modes if x))
        evidence_by_name[name]=merged
    executable_evidence=list(evidence_by_name.values())
    for ev in executable_evidence:
        name=str(ev.get("name") or "").strip()
        if not name:
            continue
        command_paths=sorted(set(ev.get("command_paths") or []))
        command_terms=sorted(set(str(x).lower() for x in ev.get("command_terms") or []))
        semantic_hits=sorted(set(str(x).lower() for x in ev.get("semantic_hits") or []))
        coverage=float(ev.get("semantic_coverage") or 0.0)
        if not command_paths or not command_terms:
            continue
        prior=seen.get(name)
        if prior is None:
            lname=name.lower()
            integration_friction=0
            if lname.startswith(("python3-","ruby-","golang-","php-","php")):
                integration_friction=2
            if lname.startswith(("lib","librust-","libghc-")):
                integration_friction=3
            if name.endswith(("-dev","-doc","-dbg","-prof")):
                integration_friction=max(integration_friction,4)
            prior={
                "discovery_source":"APT_CATALOG",
                "name":name,
                "description":"",
                "query":"BATCHED_EXECUTABLE_EVIDENCE",
                "matched_terms":[],
                "score":0,
                "integration_friction":integration_friction,
                "required_secret_count":0,
                "required_environment_count":0,
                "zero_cost_eligible":True,
                "eligibility_status":"LOCAL_EXECUTABLE_METADATA_CANDIDATE_UNVERIFIED",
                "binding_kind":"apt",
                "packages":[],
                "remotes":[],
            }
        cand=dict(prior)
        cand["matched_terms"]=sorted(
            set(cand.get("matched_terms") or [])|set(command_terms)|set(semantic_hits)
        )
        # Direct executable evidence matters, but literal filename overlap is
        # no longer an absolute semantic proxy. Package relevance and manpage
        # evidence can now compete in the same score space.
        evidence_bonus=20+35*len(command_terms)+100*coverage+16*len(semantic_hits)
        cand["score"]=float(cand.get("score",0))+evidence_bonus
        cand["executable_semantic_evidence"]={
            "command_paths":command_paths,
            "command_terms":command_terms,
            "manpage_commands":ev.get("manpage_commands") or [],
            "semantic_terms":ev.get("semantic_terms") or [],
            "semantic_hits":semantic_hits,
            "semantic_coverage":coverage,
            "acquisition_mode":ev.get("acquisition_mode"),
        }
        cand["evidence_tier"]=(
            "DIRECT_EXECUTABLE_SEMANTIC"
            if semantic_hits else "DIRECT_EXECUTABLE_PATH"
        )
        seen[name]=cand

    def _apt_rank_key(x):
        ev=x.get("executable_semantic_evidence") or {}
        semantic=ev.get("semantic_hits") or []
        return (
            -float(x.get("score",0)),
            -float(ev.get("semantic_coverage") or 0.0),
            -len(semantic),
            int(x.get("integration_friction",0)),
            str(x.get("name","")),
        )

    ranked=sorted(seen.values(),key=_apt_rank_key)[:max(1,min(int(limit),50))]
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
