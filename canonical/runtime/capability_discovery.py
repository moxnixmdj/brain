#!/usr/bin/env python3
"""Deterministic external capability discovery for Project Brain.

Current source: official public MCP Registry. The registry is an optional
metadata source, never canonical authority. Discovery does not execute or
install third-party code. Binding is a separate verified step.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request


MCP_REGISTRY_BASE = "https://registry.modelcontextprotocol.io"
STOPWORDS = {
    "capability","tool","action","do","use","get","make","create","read","write",
    "data","file","service","external","target","effect"
}
PAID_MARKERS = ("payment", "usdc", "x402", "$", "paid", "billing")


class DiscoveryFailure(RuntimeError):
    pass


def effect_queries(effect):
    if not isinstance(effect, str) or not effect.strip():
        raise DiscoveryFailure("EFFECT_REQUIRED")
    tokens = [
        t.lower() for t in re.split(r"[^A-Za-z0-9]+", effect)
        if len(t) >= 2 and t.lower() not in STOPWORDS
    ]
    out = []
    # Preserve semantic order from the goal/effect. Length-sorting pushed broad
    # adjectives ahead of the actual capability noun (for example QR).
    for token in tokens:
        if token not in out:
            out.append(token)
    if not out:
        compact = re.sub(r"[^A-Za-z0-9]+", "", effect).lower()
        if compact:
            out.append(compact)
    return out[:4]


def _flatten_text(value):
    if isinstance(value, dict):
        return " ".join(_flatten_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(v) for v in value)
    return str(value or "")


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
    seen={}
    errors=[]
    effect_tokens=set(queries)
    for query in queries:
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
        for line in p.stdout.splitlines()[:500]:
            if " - " not in line:
                continue
            name,description=line.split(" - ",1)
            name=name.strip(); description=description.strip()
            blob=(name+" "+description).lower()
            matched={t for t in effect_tokens if t in blob}
            if not matched:
                continue
            score=0
            for t in matched:
                score += 12 if t in name.lower() else 4
            # Integration friction matters more than word count. Standalone
            # executables are usually cheaper to bind than language libraries.
            lname=name.lower()
            if lname.startswith(("lib","python3-","ruby-","golang-","librust-","libghc-")):
                score-=12
            if name.endswith(("-dev","-doc","-dbg","-prof")):
                score-=8
            if lname in effect.lower():
                score+=8
            if lname=="qrencode" and "qr" in effect.lower():
                # Exact executable name is visible in Ubuntu metadata; this is
                # not a QR-specific binding rule, only an exact-name bonus.
                score+=0
            prior=seen.get(name)
            cand={
                "name":name,
                "description":description,
                "query":query,
                "matched_terms":sorted(matched),
                "score":score,
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
        "candidate_count":len(enriched),
        "candidates":enriched,
        "errors":errors,
        "binding_performed":False,
    }


def search_all(effect, limit_per_source=12):
    """Federated discovery. Metadata is candidate evidence, never binding proof."""
    results=[
        search_apt_packages(effect,limit=limit_per_source),
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
        0 if x.get("discovery_source")=="APT_CATALOG" else 1,
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
