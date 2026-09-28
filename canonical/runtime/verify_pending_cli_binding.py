#!/usr/bin/env python3
"""Fresh verification for an automatically synthesized pending CLI binding."""
from __future__ import annotations
import hashlib,importlib,json,pathlib,re,shutil,subprocess,sys

import apt_cli_probe
import astra_runtime
import capability_discovery
import auto_npm_library_acquisition
import auto_pypi_library_acquisition
import auto_python_source_codec_acquisition
import independent_npm_codec_verifier
from bound_capabilities import (
    cli_command, python_library_codec, node_library_codec, python_source_tree_codec
)

ROOT=pathlib.Path(__file__).resolve().parents[2]

def _inside(raw):
    p=(ROOT/str(raw)).resolve()
    if p!=ROOT.resolve() and ROOT.resolve() not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p

def _resolve_apt_candidate_name(name):
    """Resolve an externally discovered APT package name to pinned local metadata."""
    name=str(name or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9+._-]{0,127}",name):
        return None
    try:
        policy=subprocess.run(
            ["apt-cache","policy",name],text=True,capture_output=True,timeout=10
        )
        version=None
        for line in policy.stdout.splitlines():
            s=line.strip()
            if s.startswith("Candidate:"):
                version=s.split(":",1)[1].strip()
                break
        if not version or version=="(none)":
            return None
        show=subprocess.run(
            ["apt-cache","show",f"{name}={version}"],
            text=True,capture_output=True,timeout=15
        )
        sha=None
        description=""
        for line in show.stdout.splitlines():
            if line.startswith("SHA256:") and sha is None:
                sha=line.split(":",1)[1].strip().lower()
            elif line.startswith("Description:") and not description:
                description=line.split(":",1)[1].strip()
        if not re.fullmatch(r"[0-9a-f]{64}",str(sha or "")):
            return None
        return {
          "name":name,
          "version":version,
          "archive_sha256":sha,
          "description":description,
          "binding_kind":"apt",
          "discovery_source":"EXTERNAL_SEMANTIC_PACKAGE_HINT",
          "zero_cost_eligible":True,
          "integration_friction":0,
          "required_secret_count":0,
          "required_environment_count":0,
          "matched_terms":[],
          "score":1000,
        }
    except Exception:
        return None


def _semantic_verifier_terms(goal, expected_text=""):
    """Return target-effect terms while excluding payload/content tokens."""
    payload_tokens=set(capability_discovery.effect_queries(expected_text or ""))
    raw=[
        t for t in capability_discovery.effect_queries(goal)
        if t not in capability_discovery.GENERIC_DISCOVERY_TOKENS
        and t not in payload_tokens
        and not t.isdigit()
    ]
    producer_words={
        "generate","create","make","render","encode","write","save","output",
        "png","jpg","jpeg","webp","file","image"
    }
    distinctive=[t for t in raw if t not in producer_words]
    if not distinctive:
        distinctive=list(raw)
    return distinctive[:4]


def _semantic_verifier_queries(goal, expected_text=""):
    """Compatibility/evidence view of the bounded verifier search."""
    nouns=_semantic_verifier_terms(goal,expected_text)
    joined=" ".join(nouns)
    out=[]
    for role in ("decode","read","scan","verify"):
        q=(role+" "+joined).strip()
        if q and q not in out:
            out.append(q)
    return out


def _semantic_verifier_query(goal, expected_text=""):
    queries=_semantic_verifier_queries(goal,expected_text)
    return queries[0] if queries else "decode image"


def _package_family_tokens(name):
    """Derive conservative ecosystem-family tokens from a package name.

    This lets a semantic library hit reveal sibling CLI packages without any
    task- or vendor-specific package table.
    """
    value=str(name or "").strip().lower()
    if not value:
        return []
    parts=[p for p in re.split(r"[-_.]+",value) if p]
    noise={
        "lib","libs","library","libraries","dev","devel","doc","docs","dbg",
        "common","utils","tools","tool","cli","bin","java","python","python3",
        "ruby","perl","php","golang","rust","node","js","core","runtime"
    }
    out=[]
    # Strip common glued prefixes such as libFOO and python3FOO.
    glued=re.sub(r"^(?:lib|python3|python|ruby|perl|nodejs?)","",value)
    glued=re.split(r"[-_.0-9]+",glued)[0]
    if len(glued)>=3 and glued not in noise:
        out.append(glued)
    for p in parts:
        p=re.sub(r"\d+$","",p)
        if len(p)>=3 and p not in noise and p not in out:
            out.append(p)
    return out[:3]


def _raw_apt_family_seeds(tokens, per_token_limit=120):
    """Cheaply scan package names/descriptions without pinning/installing candidates.

    This preserves low-friction family evidence that may be buried below the
    enriched/ranked search cutoff. It never executes package code.
    """
    out=[]
    seen=set()
    if not shutil.which("apt-cache"):
        return out
    for token in tokens[:4]:
        try:
            p=subprocess.run(
                ["apt-cache","search",str(token)],
                text=True,capture_output=True,timeout=20
            )
        except Exception:
            continue
        if p.returncode!=0:
            continue
        count=0
        for line in p.stdout.splitlines():
            if " - " not in line:
                continue
            name,description=line.split(" - ",1)
            name=name.strip()
            if not name or name in seen:
                continue
            seen.add(name)
            out.append({"name":name,"description":description.strip(),"seed_token":token})
            count+=1
            if count>=per_token_limit:
                break
    return out


def _merge_verifier_discovery(goal, expected_text="", limit_per_query=40):
    """Search once by semantic roles, then cheaply widen through package families.

    The previous implementation reran a full APT search/enrichment cycle for
    many near-duplicate queries. That is correct but catastrophically slow.
    This implementation performs one aggregated semantic scan, then uses the
    strongest metadata hits to discover sibling packages in the same ecosystem
    family.
    """
    nouns=_semantic_verifier_terms(goal,expected_text)
    seed_effect=" ".join(nouns).strip()
    seed=capability_discovery.search_apt_packages(
        seed_effect,limit=max(24,min(int(limit_per_query),50))
    ) if seed_effect else {"candidate_count":0,"candidates":[],"errors":[]}
    if not (seed.get("candidates") or []):
        fallback_effect=" ".join(["decode","read","scan","verify"]+nouns).strip()
        seed=capability_discovery.search_apt_packages(
            fallback_effect,limit=max(24,min(int(limit_per_query),50))
        )
        seed_effect=fallback_effect
    merged={}
    searches=[{
      "stage":"SEMANTIC_ROLE_SCAN",
      "query":seed_effect,
      "candidate_count":seed.get("candidate_count",0),
      "errors":seed.get("errors",[]),
    }]

    def add(cand, stage, family=None):
        name=str(cand.get("name") or "")
        if not name:
            return
        x=dict(cand)
        x["verifier_discovery_stage"]=stage
        if family:
            x["verifier_package_family"]=family
        prior=merged.get(name)
        if prior is None or float(x.get("score",0))>float(prior.get("score",0)):
            merged[name]=x

    seed_candidates=seed.get("candidates",[]) or []
    for cand in seed_candidates:
        add(cand,"SEMANTIC_ROLE_SCAN")

    # Preserve cheap metadata-only family clues beyond the enriched candidate
    # cutoff. A semantic library/binding hit can reveal a separately packaged
    # CLI sibling even when the library itself is too high-friction to execute.
    raw_family_seeds=_raw_apt_family_seeds(nouns)
    searches.append({
      "stage":"RAW_METADATA_FAMILY_SEED_SCAN",
      "query":" | ".join(nouns),
      "candidate_count":len(raw_family_seeds),
      "errors":[],
    })

    # Expand only a few high-signal families. Libraries and bindings are useful
    # discovery evidence even when they are not themselves executable verifiers.
    families=[]
    family_support={}
    family_sources=list(seed_candidates)+[
        {
          "name":x["name"],
          "description":x.get("description",""),
          "score":12,
          "matched_terms":[x.get("seed_token")],
        }
        for x in raw_family_seeds
    ]
    for cand in sorted(
        family_sources,
        key=lambda x:(-float(x.get("score",0)),str(x.get("name","")))
    )[:120]:
        semantic_support=len(cand.get("matched_terms") or [])
        for token in _package_family_tokens(cand.get("name")):
            prior=family_support.get(token)
            record={
              "parent_package":str(cand.get("name") or ""),
              "semantic_support_terms":semantic_support,
              "parent_matched_terms":list(cand.get("matched_terms") or []),
              "parent_score":float(cand.get("score",0)),
            }
            if prior is None or (
                record["semantic_support_terms"],record["parent_score"]
            ) > (
                prior["semantic_support_terms"],prior["parent_score"]
            ):
                family_support[token]=record
            if token not in families:
                families.append(token)
            if len(families)>=6:
                break
        if len(families)>=6:
            break

    for family in families:
        result=capability_discovery.search_apt_packages(family,limit=16)
        searches.append({
          "stage":"PACKAGE_FAMILY_EXPANSION",
          "query":family,
          "candidate_count":result.get("candidate_count",0),
          "errors":result.get("errors",[]),
        })
        for cand in result.get("candidates",[]) or []:
            enriched=dict(cand)
            support=family_support.get(family) or {}
            enriched["verifier_family_parent_package"]=support.get("parent_package")
            enriched["verifier_family_semantic_support_terms"]=int(
                support.get("semantic_support_terms") or 0
            )
            enriched["verifier_family_parent_matched_terms"]=list(
                support.get("parent_matched_terms") or []
            )
            add(enriched,"PACKAGE_FAMILY_EXPANSION",family)

    candidates=sorted(
        merged.values(),
        key=lambda x:(
            int(x.get("integration_friction",99)),
            -float(x.get("score",0)),
            0 if x.get("verifier_discovery_stage")=="PACKAGE_FAMILY_EXPANSION" else 1,
            str(x.get("name","")),
        )
    )
    return {"queries":searches,"candidates":candidates}


def _png_dimensions(path):
    try:
        raw=pathlib.Path(path).read_bytes()[:24]
        if len(raw)<24 or raw[:8]!=b"\x89PNG\r\n\x1a\n":
            return None
        width=int.from_bytes(raw[16:20],"big")
        height=int.from_bytes(raw[20:24],"big")
        if width<1 or height<1 or width>4096 or height>4096:
            return None
        return width,height
    except Exception:
        return None


def _help_symbol_size_candidates(contract, output_path):
    text=str(contract.get("help_excerpt") or "")
    if "symbol-size" not in text.lower():
        return []
    if "row" not in text.lower() or "column" not in text.lower():
        return []
    flag=None
    for line in text.splitlines():
        m=re.match(r"\s*(-[A-Za-z0-9]),\s*--symbol-size",line,re.I)
        if m:
            flag=m.group(1)
            break
    dims=_png_dimensions(output_path)
    if not flag or dims is None:
        return []
    width,height=dims
    return [
      {"flag":flag,"value":f"{height}x{width}"},
      {"flag":flag,"value":f"{width}x{height}"},
    ]


def _semantic_execution_variants(contract, output_path):
    """Build bounded execution variants only from options declared in help."""
    base=[output_path if x=="__OUTPUT_PATH__" else x for x in contract["argv"]]
    out=[{"basis":"PRIMARY_CONTRACT","argv":base}]
    if contract.get("inference_basis")!="POSITIONAL_FILE_TO_STDOUT":
        return out
    help_text=str(contract.get("help_excerpt") or "")
    path=str(contract.get("executable") or "")
    for line in help_text.splitlines():
        m=re.match(
            r"\s*(-[A-Za-z0-9]),\s*--([A-Za-z0-9-]*minimum[A-Za-z0-9-]*)=N\b",
            line,
            re.I,
        )
        if not m:
            continue
        short=m.group(1)
        argv=[path,short,"1",output_path]
        if argv!=base:
            out.append({
              "basis":"HELP_DECLARED_MINIMUM_NUMERIC_RELAXATION",
              "argv":argv,
              "help_line":line.strip()[:500],
            })
        break
    help_text=str(contract.get("help_excerpt") or "")
    path=str(contract.get("executable") or "")
    for line in help_text.splitlines():
        low=line.lower()
        if "pure" not in low and "perfect" not in low:
            continue
        if not any(w in low for w in ("assume","image","code","symbol")):
            continue
        m=re.match(r"\s*(-[^\s,=]+)",line)
        if not m:
            continue
        flag=m.group(1)
        if "=" in flag or flag in {"-h","--help"}:
            continue
        base_argv=list(base)
        insert_at=max(1,len(base_argv)-1)
        variant=base_argv[:insert_at]+[flag]+base_argv[insert_at:]
        if variant!=base and all(v["argv"]!=variant for v in out):
            out.append({
              "basis":"HELP_DECLARED_PURE_INPUT_MODE",
              "argv":variant,
              "help_line":line.strip()[:500],
            })
        break
    prior_variants=list(out)
    for item in _help_symbol_size_candidates(contract,output_path):
        argv=list(base[:-1])+[item["flag"],item["value"],base[-1]]
        if all(v["argv"]!=argv for v in out):
            out.append({
              "basis":"HELP_DECLARED_SYMBOL_SIZE_FROM_RASTER_DIMENSIONS",
              "argv":argv,
              "symbol_size":item["value"],
            })
        for prior in prior_variants:
            if prior.get("basis")!="HELP_DECLARED_MINIMUM_NUMERIC_RELAXATION":
                continue
            prior_argv=list(prior["argv"])
            combo=list(prior_argv[:-1])+[item["flag"],item["value"],prior_argv[-1]]
            if all(v["argv"]!=combo for v in out):
                out.append({
                  "basis":"HELP_DECLARED_MINIMUM_EDGE_PLUS_SYMBOL_SIZE",
                  "argv":combo,
                  "symbol_size":item["value"],
                })
    return out


def _semantic_help_contract(probe):
    """Infer a bounded image-to-text decoder contract from observed CLI help.

    This deliberately learns transport shape from help instead of naming a
    specific barcode family or verifier implementation.
    """
    candidates=[]
    for exe in probe.get("executables",[]):
        path=str(exe.get("executable") or "")
        for att in exe.get("help_attempts",[]):
            text=str(att.get("text") or "")
            if not text:
                continue
            lower=text.lower()
            normalized=re.sub(r"[^a-z0-9]+","",lower)
            role_score=0
            if any(w in lower for w in ("decode","read","scan")):
                role_score+=4
            if any(w in lower for w in ("image","png","barcode","matrix","code")):
                role_score+=3
            if any(w in lower for w in ("stdout","standard output","print")):
                role_score+=2
            if "encode" in lower or "write barcode" in lower:
                role_score-=4
            if role_score<5:
                continue

            # Explicit raw-output decoder contract, e.g. zbarimg.
            if "--raw" in lower:
                argv=[path]
                if "--quiet" in lower:
                    argv.append("--quiet")
                argv.extend(["--raw","__OUTPUT_PATH__"])
                candidates.append((role_score,2,len(text),path,text,argv,"RAW_FLAG"))
                continue

            # Generic positional input contract. Accept only when observed
            # usage/help declares a file/image positional operand and no
            # separate required output-file option is evident.
            usage_lines=[
                line.strip() for line in text.splitlines()
                if line.strip().lower().startswith(("usage:","usage "))
            ]
            positional_declared=any(
                re.search(r"(?:\[|<)?(?:file|image|filename|input)(?:\]|>)?",line,re.I)
                for line in usage_lines
            )
            writes_stdout=(
                any(w in lower for w in ("stdout","standard output"))
                or any(w in lower for w in ("decode","read","scan"))
            )
            if positional_declared and writes_stdout:
                argv=[path]
                raw_flag=None
                for line in text.splitlines():
                    low=line.lower()
                    if "stdout" not in low:
                        continue
                    if not (
                        ("bytes" in low and "content" in low)
                        or ("raw" in low and "content" in low)
                    ):
                        continue
                    m=re.match(r"\s*(-[^\s,=]+)",line)
                    if m:
                        token=m.group(1)
                        if token not in {"-h","--help"}:
                            raw_flag=token
                            break
                if raw_flag:
                    argv.append(raw_flag)
                argv.append("__OUTPUT_PATH__")
                candidates.append((role_score,1,len(text),path,text,argv,"POSITIONAL_FILE_TO_STDOUT"))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    _,_,_,path,text,argv,basis=candidates[0]
    return {
      "executable":path,
      "help_excerpt":text[:4000],
      "argv":argv,
      "inference_basis":basis
    }


def _acquire_and_run_semantic_verifier(pending, output_path):
    semantic=pending.get("semantic_verification") or {}
    expected=str(semantic.get("expected_text") or "")
    if not expected:
        raise RuntimeError("SEMANTIC_EXPECTED_TEXT_REQUIRED")
    goal=str(semantic.get("goal") or pending.get("goal") or "")
    query=_semantic_verifier_query(goal,expected)
    discovery=_merge_verifier_discovery(goal,expected_text=expected,limit_per_query=24)
    producer=str((pending.get("selected_supplier") or {}).get("name") or "")
    hinted=[]
    for raw in semantic.get("verifier_package_hints") or []:
        name=raw.get("name") if isinstance(raw,dict) else raw
        cand=_resolve_apt_candidate_name(name)
        if cand is not None and cand.get("name")!=producer:
            hinted.append(cand)
    candidates=[]
    seen=set()
    # Autonomous role-conditioned discovery is authoritative. Explicit hints
    # remain only as a final diagnostic fallback and are never required for
    # the normal acceptance path.
    for cand in (discovery.get("candidates",[]) or [])+hinted:
        name=str(cand.get("name") or "")
        if not name or name in seen:
            continue
        seen.add(name)
        candidates.append(cand)
    attempts=[]
    for cand in candidates[:24]:
        name=str(cand.get("name") or "")
        if not name or name==producer:
            continue
        if not cand.get("zero_cost_eligible",False):
            continue
        if int(cand.get("integration_friction",99))!=0:
            continue
        externally_hinted=(cand.get("discovery_source")=="EXTERNAL_SEMANTIC_PACKAGE_HINT")
        family_supported=(
            cand.get("verifier_discovery_stage")=="PACKAGE_FAMILY_EXPANSION"
            and int(cand.get("verifier_family_semantic_support_terms") or 0)>=1
        )
        if (
            not externally_hinted
            and not family_supported
            and len(cand.get("matched_terms") or [])<2
        ):
            continue
        version=str(cand.get("version") or "")
        sha=str(cand.get("archive_sha256") or "").lower()
        if not version or not re.fullmatch(r"[0-9a-f]{64}",sha):
            continue
        attempt={"candidate":cand}
        try:
            probe=apt_cli_probe.probe(name,version,sha,ROOT)
            attempt["probe"]=probe
            contract=_semantic_help_contract(probe)
            if contract is None:
                attempt["status"]="VERIFIER_CONTRACT_REJECTED"
                attempts.append(attempt)
                continue
            attempt["contract"]=contract
            attempt["execution_variants"]=[]
            proc=None
            observed=""
            for variant in _semantic_execution_variants(contract,output_path):
                current=subprocess.run(
                    variant["argv"],text=True,capture_output=True,timeout=60,cwd=ROOT
                )
                record={
                  **variant,
                  "returncode":current.returncode,
                  "stdout":current.stdout[-4000:],
                  "stderr":current.stderr[-4000:],
                }
                attempt["execution_variants"].append(record)
                if current.returncode==0:
                    proc=current
                    observed=current.stdout.strip()
                    attempt["selected_execution_variant"]=record
                    break
            if proc is None:
                last=attempt["execution_variants"][-1] if attempt["execution_variants"] else {}
                attempt["returncode"]=last.get("returncode")
                attempt["stdout"]=last.get("stdout")
                attempt["stderr"]=last.get("stderr")
                attempt["status"]="VERIFIER_EXECUTION_FAILED"
                attempts.append(attempt)
                continue
            attempt["returncode"]=proc.returncode
            attempt["stdout"]=proc.stdout[-4000:]
            attempt["stderr"]=proc.stderr[-4000:]
            verified=observed==expected
            evidence={
              "verified":verified,
              "expected_text":expected,
              "observed_text":observed,
              "verifier_package":name,
              "verifier_version":version,
              "verifier_archive_sha256":sha,
              "verifier_executable":contract["executable"],
              "query":query,
              "autonomous_discovery_queries":discovery.get("queries",[]),
              "producer_package":producer,
              "producer_independent":name!=producer,
              "attempt_count":len(attempts)+1
            }
            attempt["status"]="VERIFIED" if verified else "SEMANTIC_CONTENT_MISMATCH"
            attempts.append(attempt)
            evidence["attempts"]=attempts
            return evidence
        except Exception as exc:
            attempt["status"]="VERIFIER_PROBE_FAILED"
            attempt["error"]=type(exc).__name__+":"+str(exc)
            attempts.append(attempt)
            continue
    raise RuntimeError("SEMANTIC_VERIFIER_ACQUISITION_FAILED:"+json.dumps([
        {
          "name":(a.get("candidate") or {}).get("name"),
          "status":a.get("status"),
          "error":a.get("error"),
          "argv":(a.get("contract") or {}).get("argv"),
          "returncode":a.get("returncode"),
          "stdout":a.get("stdout"),
          "stderr":a.get("stderr"),
          "inference_basis":(a.get("contract") or {}).get("inference_basis"),
          "execution_variants":a.get("execution_variants"),
          "selected_execution_variant":a.get("selected_execution_variant"),
        }
        for a in attempts
    ],sort_keys=True,default=str)[:20000])


def _resolve_callable(module,name):
    current=module
    for part in str(name or "").split("."):
        current=getattr(current,part)
    if not callable(current):
        raise RuntimeError("PYPI_CODEC_CALLABLE_INVALID")
    return current



def _pending_codec_format(pending):
    goal=str(pending.get("goal") or "")
    common={
        "json","txt","md","markdown","csv","tsv","html","xml",
        "png","jpg","jpeg","webp","pdf","docx","xlsx",
        "zip","gz","tgz","tar","sqlite","db","sqlite3",
    }
    path_tokens=re.findall(
        r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+",
        re.sub(r"https?://[^\\s)\\]}>]+"," ",goal),
    )
    goal_formats=[]
    for raw in path_tokens:
        suffix=pathlib.PurePosixPath(raw.rstrip(".,;:!?)]}")).suffix.lower().lstrip(".")
        if suffix and suffix not in common and suffix not in goal_formats:
            goal_formats.append(suffix)

    entry=pending.get("registry_entry") or {}
    declared=sorted(set(
        str(effect)[len("structured.binary.encode."):]
        for effect in (entry.get("provides") or [])
        if str(effect).startswith("structured.binary.encode.")
        and str(effect)!="structured.binary.encode"
    ))
    compatible=[fmt for fmt in goal_formats if fmt in declared]
    if len(compatible)==1:
        return compatible[0]
    if not goal_formats and len(declared)==1:
        return declared[0]
    raise RuntimeError(
        "PENDING_CODEC_FORMAT_AMBIGUOUS:"
        +json.dumps({"goal_formats":goal_formats,"declared":declared},sort_keys=True)
    )


def _independent_npm_codec_verifier(pending,fixture_path,output_path):
    producer_source=(pending.get("registry_entry") or {}).get("source") or {}
    producer_project=str(
        producer_source.get("project")
        or producer_source.get("package")
        or producer_source.get("repository")
        or (pending.get("selected_supplier") or {}).get("name")
        or (pending.get("selected_supplier") or {}).get("repository")
        or ""
    )
    evidence=independent_npm_codec_verifier.verify(
        _pending_codec_format(pending),
        str(pathlib.Path(fixture_path).relative_to(ROOT)),
        str(pathlib.Path(output_path).relative_to(ROOT)),
        producer_project,
        ROOT,
    )
    if evidence.get("verified") is not True:
        raise RuntimeError("PENDING_PYPI_INDEPENDENT_VERIFICATION_FAILED")
    return evidence

def _independent_pypi_codec_verifier(pending,fixture_path,output_path):
    goal=str(pending.get("goal") or "")
    producer_source=(pending.get("registry_entry") or {}).get("source") or {}
    attempts=[]
    try:
        candidates=auto_pypi_library_acquisition._candidate_pool(goal,discovery=None)
    except Exception as exc:
        raise RuntimeError(
            "INDEPENDENT_PYPI_VERIFIER_DISCOVERY_FAILED:"
            +type(exc).__name__+":"+str(exc)
        ) from exc
    for candidate in candidates[:16]:
        attempt={"candidate":candidate}
        try:
            closure=auto_pypi_library_acquisition._download_compatible_wheel_closure(candidate,ROOT)
            contract=auto_pypi_library_acquisition._infer_codec_contract(candidate,closure,ROOT)
            root_wheel=closure["root"]
            source={
              "type":"pypi",
              "project":str(candidate.get("project") or candidate.get("name")),
              "version":str(candidate.get("version")),
              "metadata_url":str(candidate.get("metadata_url")),
              "wheel_filename":root_wheel["filename"],
              "wheel_sha256":root_wheel["sha256"],
              "dependency_closure":closure["lock"],
              "license":candidate.get("license"),
            }
            dependency=astra_runtime._ensure_pypi_dependency(source)
            importlib.invalidate_caches()
            module=importlib.import_module(contract["module"])
            decoder=_resolve_callable(module,contract["decode_callable"])
            observed=decoder(
                output_path.read_bytes(),
                **(contract.get("decode_kwargs") or {})
            )
            envelope_key=contract.get("envelope_key")
            if envelope_key is not None:
                key=str(envelope_key)
                if not isinstance(observed,dict) or key not in observed:
                    raise RuntimeError("INDEPENDENT_PYPI_VERIFIER_ENVELOPE_MISSING:"+key)
                observed=observed[key]
            expected=json.loads(fixture_path.read_text(encoding="utf-8"))
            verified=observed==expected
            attempt["project"]=source["project"]
            attempt["version"]=source["version"]
            attempt["verified"]=verified
            if verified:
                return {
                  "verified":True,
                  "implementation_independent":True,
                  "supplier_class_independent":producer_source.get("type")!="pypi",
                  "producer_source_type":producer_source.get("type"),
                  "verifier_source_type":"pypi",
                  "verifier_project":source["project"],
                  "verifier_version":source["version"],
                  "verifier_wheel_sha256":root_wheel["sha256"],
                  "verifier_contract":{
                    "module":contract["module"],
                    "decode_callable":contract["decode_callable"],
                  },
                  "attempts":attempts+[attempt],
                }
        except Exception as exc:
            attempt["error"]=type(exc).__name__+":"+str(exc)
        attempts.append(attempt)
    raise RuntimeError(
        "NO_INDEPENDENT_PYPI_CODEC_VERIFIER:"
        +json.dumps(attempts,sort_keys=True)[:4000]
    )


def _verify_pending_pypi(pending,result_path):
    entry=pending["registry_entry"]
    source=entry.get("source") or {}
    dependency=astra_runtime._ensure_pypi_dependency(source)
    contract=pending.get("contract") or {}
    fixture=pending.get("verification_fixture")
    if not isinstance(fixture,(list,dict)):
        raise RuntimeError("PYPI_VERIFICATION_FIXTURE_INVALID")
    fixture_path=ROOT/"canonical"/"astra_runtime"/"tmp"/(pending["verification_mission_id"]+"_SOURCE.json")
    output_path=ROOT/"canonical"/"astra_runtime"/"tmp"/(pending["verification_mission_id"]+"_OUTPUT.bin")
    fixture_path.parent.mkdir(parents=True,exist_ok=True)
    fixture_path.write_text(json.dumps(fixture,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    observed=python_library_codec.run({
      "module":contract["module"],
      "encode_callable":contract["encode_callable"],
      "encode_kwargs":contract.get("encode_kwargs") or {},
      "envelope_key":contract.get("envelope_key"),
      "json_path":str(fixture_path.relative_to(ROOT)),
      "output_path":str(output_path.relative_to(ROOT)),
    },ROOT)
    if observed.get("output_verified") is not True:
        raise RuntimeError("PENDING_PYPI_PRODUCER_EFFECT_FAILED")
    import importlib
    importlib.invalidate_caches()
    module=importlib.import_module(contract["module"])
    decoder=_resolve_callable(module,contract["decode_callable"])
    decoded=decoder(output_path.read_bytes(),**(contract.get("decode_kwargs") or {}))
    envelope_key=contract.get("envelope_key")
    if envelope_key is not None:
        key=str(envelope_key)
        if not isinstance(decoded,dict) or key not in decoded:
            raise RuntimeError("PENDING_PYPI_ENVELOPE_MISSING:"+key)
        decoded=decoded[key]
    expected=json.loads(fixture_path.read_text(encoding="utf-8"))
    if decoded!=expected:
        raise RuntimeError("PENDING_PYPI_SEMANTIC_ROUNDTRIP_MISMATCH")
    independent=_independent_npm_codec_verifier(
        pending,fixture_path,output_path
    )
    if independent.get("verified") is not True:
        raise RuntimeError("PENDING_PYPI_INDEPENDENT_VERIFICATION_FAILED")
    raw=output_path.read_bytes()
    result={
      "schema":"PROJECT_BRAIN_AUTO_BINDING_VERIFICATION_V1",
      "capability_id":pending["capability_id"],
      "verification_mission_id":pending["verification_mission_id"],
      "dependency":dependency,
      "adapter_result":observed,
      "semantic_roundtrip":{
        "verified":True,
        "separate_decode_invocation":True,
        "producer_roundtrip_verified":True,
        "implementation_independent":True,
        "module":contract["module"],
        "decode_callable":contract["decode_callable"],
        "independent_verifier":independent,
      },
      "independent_output_sha256":hashlib.sha256(raw).hexdigest(),
      "independent_output_bytes":len(raw),
      "independent_verified":True,
      "status":"VERIFIED",
    }
    result_path.parent.mkdir(parents=True,exist_ok=True)
    result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("PENDING_PYPI_BINDING_EFFECT_VERIFIED",json.dumps(result,sort_keys=True))


def _verify_pending_source_tree(pending,result_path):
    entry=pending["registry_entry"]
    source=entry.get("source") or {}
    supplied=source.get("tree")
    expected_tree_sha=str(source.get("tree_sha256") or "")
    contract=pending.get("contract") or {}
    fixture=pending.get("verification_fixture")
    if not isinstance(fixture,(list,dict)):
        raise RuntimeError("SOURCE_TREE_VERIFICATION_FIXTURE_INVALID")
    fixture_path=ROOT/"canonical"/"astra_runtime"/"tmp"/(pending["verification_mission_id"]+"_SOURCE.json")
    output_path=ROOT/"canonical"/"astra_runtime"/"tmp"/(pending["verification_mission_id"]+"_OUTPUT.bin")
    fixture_path.parent.mkdir(parents=True,exist_ok=True)
    fixture_path.write_text(json.dumps(fixture,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    import tempfile
    with tempfile.TemporaryDirectory(prefix="brain-source-tree-verify-") as td:
        source_root=pathlib.Path(td)/"site"
        manifest=auto_python_source_codec_acquisition._materialize(supplied,source_root)
        if manifest.get("tree_sha256")!=expected_tree_sha:
            raise RuntimeError("SOURCE_TREE_VERIFICATION_TREE_HASH_MISMATCH")
        common={
          "_source_root":str(source_root),
          "module":contract["module"],
          "encode_callable":contract["encode_callable"],
          "decode_callable":contract["decode_callable"],
          "encode_kwargs":contract.get("encode_kwargs") or {},
          "decode_kwargs":contract.get("decode_kwargs") or {},
          "envelope_key":contract.get("envelope_key"),
          "json_path":str(fixture_path.relative_to(ROOT)),
        }
        observed=python_source_tree_codec.run({
          **common,
          "output_path":str(output_path.relative_to(ROOT)),
        },ROOT)
        if observed.get("output_verified") is not True:
            raise RuntimeError("PENDING_SOURCE_TREE_PRODUCER_EFFECT_FAILED")
        decoded=python_source_tree_codec.run({
          **common,
          "mode":"decode_verify",
          "binary_path":str(output_path.relative_to(ROOT)),
        },ROOT)
        if decoded.get("verified") is not True:
            raise RuntimeError("PENDING_SOURCE_TREE_SEMANTIC_ROUNDTRIP_MISMATCH")
        independent=_independent_npm_codec_verifier(
            pending,fixture_path,output_path
        )
        if (
            independent.get("verified") is not True
            or independent.get("implementation_independent") is not True
            or independent.get("supplier_class_independent") is not True
        ):
            raise RuntimeError("PENDING_SOURCE_TREE_INDEPENDENT_VERIFICATION_FAILED")
    raw=output_path.read_bytes()
    result={
      "schema":"PROJECT_BRAIN_AUTO_BINDING_VERIFICATION_V1",
      "capability_id":pending["capability_id"],
      "verification_mission_id":pending["verification_mission_id"],
      "source_tree_manifest":manifest,
      "adapter_result":observed,
      "semantic_roundtrip":{
        "verified":True,
        "producer_roundtrip_verified":True,
        "implementation_independent":True,
        "module":contract["module"],
        "decode_callable":contract["decode_callable"],
        "independent_verifier":independent,
      },
      "independent_output_sha256":hashlib.sha256(raw).hexdigest(),
      "independent_output_bytes":len(raw),
      "independent_verified":True,
      "status":"VERIFIED",
    }
    result_path.parent.mkdir(parents=True,exist_ok=True)
    result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("PENDING_SOURCE_BINDING_EFFECT_VERIFIED",json.dumps(result,sort_keys=True))


def _verify_pending_npm(pending,result_path):
    entry=pending["registry_entry"]
    source=entry.get("source") or {}
    dependency=astra_runtime._ensure_npm_dependency(source)
    package_root=str(dependency.get("package_root") or "")
    if not package_root:
        raise RuntimeError("NPM_VERIFICATION_PACKAGE_ROOT_MISSING")
    contract=pending.get("contract") or {}
    fixture=pending.get("verification_fixture")
    if not isinstance(fixture,(list,dict)):
        raise RuntimeError("NPM_VERIFICATION_FIXTURE_INVALID")
    fixture_path=ROOT/"canonical"/"astra_runtime"/"tmp"/(pending["verification_mission_id"]+"_SOURCE.json")
    output_path=ROOT/"canonical"/"astra_runtime"/"tmp"/(pending["verification_mission_id"]+"_OUTPUT.bin")
    fixture_path.parent.mkdir(parents=True,exist_ok=True)
    fixture_path.write_text(json.dumps(fixture,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    common={
      "_package_root":package_root,
      "package":contract["package"],
      "root_selector":contract["root_selector"],
      "encode_export":contract["encode_export"],
      "decode_export":contract["decode_export"],
      "json_path":str(fixture_path.relative_to(ROOT)),
    }
    observed=node_library_codec.run({
      **common,
      "output_path":str(output_path.relative_to(ROOT)),
    },ROOT)
    if observed.get("output_verified") is not True:
        raise RuntimeError("PENDING_NPM_PRODUCER_EFFECT_FAILED")
    # Fresh decode verification is a separate Node process.
    decoded=node_library_codec.run({
      **common,
      "mode":"decode_verify",
      "binary_path":str(output_path.relative_to(ROOT)),
    },ROOT)
    if decoded.get("verified") is not True:
        raise RuntimeError("PENDING_NPM_SEMANTIC_ROUNDTRIP_MISMATCH")
    independent=_independent_pypi_codec_verifier(
        pending,fixture_path,output_path
    )
    if independent.get("verified") is not True:
        raise RuntimeError("PENDING_NPM_INDEPENDENT_VERIFICATION_FAILED")
    raw=output_path.read_bytes()
    result={
      "schema":"PROJECT_BRAIN_AUTO_BINDING_VERIFICATION_V1",
      "capability_id":pending["capability_id"],
      "verification_mission_id":pending["verification_mission_id"],
      "dependency":dependency,
      "adapter_result":observed,
      "semantic_roundtrip":{
        "verified":True,
        "fresh_node_decode_invocation":True,
        "producer_roundtrip_verified":True,
        "implementation_independent":True,
        "package":contract["package"],
        "decode_export":contract["decode_export"],
        "independent_verifier":independent,
      },
      "independent_output_sha256":hashlib.sha256(raw).hexdigest(),
      "independent_output_bytes":len(raw),
      "independent_verified":True,
      "status":"VERIFIED",
    }
    result_path.parent.mkdir(parents=True,exist_ok=True)
    result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("PENDING_NPM_BINDING_EFFECT_VERIFIED",json.dumps(result,sort_keys=True))


def main():
    if len(sys.argv)!=3:
        raise SystemExit("usage: verify_pending_cli_binding.py PENDING_JSON RESULT_JSON")
    pending_path=_inside(sys.argv[1])
    result_path=_inside(sys.argv[2])
    pending=json.loads(pending_path.read_text(encoding="utf-8"))
    if pending.get("schema")!="PROJECT_BRAIN_PENDING_AUTO_BINDING_V1":
        raise RuntimeError("PENDING_BINDING_SCHEMA_INVALID")
    entry=pending["registry_entry"]
    source=entry.get("source") or {}
    if source.get("type")=="pypi":
        _verify_pending_pypi(pending,result_path)
        return
    if source.get("type")=="npm":
        _verify_pending_npm(pending,result_path)
        return
    if source.get("type")=="git_source_tree":
        _verify_pending_source_tree(pending,result_path)
        return
    if source.get("type")!="apt":
        raise RuntimeError("PENDING_BINDING_SOURCE_UNSUPPORTED")
    dependency=astra_runtime._ensure_apt_dependencies(source)
    args=dict(pending["verification_args"])
    observed=cli_command.run(args,ROOT)
    out=_inside(observed["output_path"])
    raw=out.read_bytes()
    expected_prefix=bytes.fromhex(str(args.get("output_prefix_hex") or ""))
    independent_ok=(
        observed.get("output_verified") is True
        and observed.get("returncode")==0
        and bool(raw)
        and (not expected_prefix or raw.startswith(expected_prefix))
        and hashlib.sha256(raw).hexdigest()==observed.get("output_sha256")
    )
    if not independent_ok:
        raise RuntimeError("PENDING_BINDING_INDEPENDENT_EFFECT_CHECK_FAILED")
    semantic=pending.get("semantic_verification") or {}
    if semantic.get("required") is True:
        evidence=semantic.get("evidence")
        if not isinstance(evidence,dict) or evidence.get("verified") is not True:
            evidence=_acquire_and_run_semantic_verifier(pending,str(out))
            semantic["evidence"]=evidence
            semantic["status"]="VERIFIED" if evidence.get("verified") is True else "FAILED"
            pending["semantic_verification"]=semantic
            pending_path.write_text(json.dumps(pending,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        if evidence.get("expected_text")!=semantic.get("expected_text"):
            raise RuntimeError("SEMANTIC_VERIFICATION_EXPECTED_TEXT_MISMATCH")
        if evidence.get("observed_text")!=semantic.get("expected_text"):
            raise RuntimeError("SEMANTIC_VERIFICATION_CONTENT_MISMATCH")
    result={
      "schema":"PROJECT_BRAIN_AUTO_BINDING_VERIFICATION_V1",
      "capability_id":pending["capability_id"],
      "verification_mission_id":pending["verification_mission_id"],
      "dependency":dependency,
      "adapter_result":observed,
      "independent_output_sha256":hashlib.sha256(raw).hexdigest(),
      "independent_output_bytes":len(raw),
      "independent_verified":True,
      "status":"VERIFIED"
    }
    result_path.parent.mkdir(parents=True,exist_ok=True)
    result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("PENDING_CLI_BINDING_EFFECT_VERIFIED",json.dumps(result,sort_keys=True))
if __name__=="__main__":
    main()
