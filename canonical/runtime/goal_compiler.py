#!/usr/bin/env python3
"""Deterministic plain-goal compiler for Project Brain.

Purpose: remove hand-authored target_effects/initial_facts for goals that
clearly map to already verified bound capabilities. It intentionally fails
closed on unknown or ambiguous goals so the next missing mechanism remains
observable instead of being guessed.
"""
from __future__ import annotations

import ast

import hashlib
import importlib.util
import json
import math
import pathlib
import re
import sys


class GoalCompilationFailure(RuntimeError):
    def __init__(self, code, detail=None):
        self.code=code
        self.detail=detail
        super().__init__(code if detail is None else f"{code}:{detail}")


def _load_sibling_runtime_module(filename,module_name):
    path=pathlib.Path(__file__).resolve().with_name(filename)
    spec=importlib.util.spec_from_file_location(module_name,path)
    if spec is None or spec.loader is None:
        raise GoalCompilationFailure("RUNTIME_HELPER_LOAD_FAILED",filename)
    module=importlib.util.module_from_spec(spec)
    sys.modules[module_name]=module
    spec.loader.exec_module(module)
    return module


def _uses_effect_result_bindings(entry):
    bindings=(entry or {}).get("proposal_bindings") or {}
    return isinstance(bindings,dict) and any(
        isinstance(spec,dict) and spec.get("type")=="effect_result"
        for spec in bindings.values()
    )


def _planner_capability(planner,cid,entry,action=None):
    return planner.Capability(
        str(cid),
        frozenset(str(x) for x in (entry.get("requires") or [])),
        frozenset(str(x) for x in (entry.get("provides") or [])),
        float(entry.get("cost",1)),
        action or {},
        frozenset(str(x) for x in (entry.get("result_fields") or [])),
    )


STOPWORDS={
    "the","a","an","to","from","of","and","or","with","using","use","do","for",
    "which","is","are","be","this","that","into","on","in","visible"
}

GENERIC_MATCH_TOKENS={
    "generate","image","text","extract","create","save","output","input",
    "file","read","write","convert","process","data"
}



def _current_runtime_platform():
    value=str(sys.platform or "")
    if value.startswith("linux"):
        return "linux"
    if value.startswith("win") or value in {"cygwin","msys"}:
        return "windows"
    if value=="darwin":
        return "darwin"
    raise GoalCompilationFailure("GOAL_COMPILATION_PLATFORM_UNSUPPORTED",value)


def _platform_admissible_registry(registry):
    current=_current_runtime_platform()
    out={}
    for cid,entry in (registry or {}).items():
        if not isinstance(entry,dict):
            continue
        platforms=entry.get("platforms")
        # Legacy verified entries without platform metadata remain visible until
        # separately re-attested. Explicit platform claims are authoritative.
        if platforms is None:
            out[cid]=entry
            continue
        if not isinstance(platforms,list) or not platforms:
            continue
        if current in {str(x) for x in platforms}:
            out[cid]=entry
    return out


def _tokens(value):
    return {
        t.lower() for t in re.findall(r"[A-Za-z0-9]+", str(value or ""))
        if len(t) >= 2 and t.lower() not in STOPWORDS
    }


def _flatten(value):
    if isinstance(value,dict):
        return " ".join(_flatten(v) for v in value.values())
    if isinstance(value,list):
        return " ".join(_flatten(v) for v in value)
    return str(value or "")


def _placeholders(value):
    text=_flatten(value)
    return sorted(set(re.findall(r"\$\{input\.([A-Za-z0-9_]+)\}",text)))


def _repo_paths(goal, root):
    candidates=[]
    # URL path components are not repository paths. Strip complete URLs before
    # scanning for repository-local artifacts.
    path_text=re.sub(r"https?://[^\s)\]}>]+"," ",str(goal or ""))
    for raw in re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+",path_text):
        raw=raw.rstrip(".,;:!?)]}")
        p=(pathlib.Path(root)/raw).resolve()
        rr=pathlib.Path(root).resolve()
        if p==rr or rr in p.parents:
            candidates.append((raw,p))
    return candidates


def _extract_text_argument(goal):
    quoted=re.findall(r'["\']([^"\']+)["\']',goal)
    if len(quoted)==1 and quoted[0].strip():
        return quoted[0].strip()
    patterns=[
        r"\b(?:for|from)\s+the\s+text\s+(.+?)(?=\s+and\s+(?:save|write|store)\b|\s+(?:save|write|store)\b|$)",
        r"\btext\s+(.+?)(?=\s+and\s+(?:save|write|store)\b|\s+(?:save|write|store)\b|$)",
    ]
    for pattern in patterns:
        m=re.search(pattern,goal,flags=re.IGNORECASE)
        if m and m.group(1).strip():
            return m.group(1).strip(" .,:;")
    raise GoalCompilationFailure("GOAL_TEXT_INPUT_BINDING_REQUIRED")


def _context_path_for_key(key, context_paths):
    stem=key[:-5].lower() if key.endswith("_path") else key.lower()
    suffixes={
        "markdown":{".md",".markdown"},
        "json":{".json"},
        "pdf":{".pdf"},
        "text":{".txt",".md",".markdown",".csv",".tsv"},
        "image":{".png",".jpg",".jpeg",".webp"},
        "archive":{".gz",".tgz",".zip",".tar"},
        "manifest":{".json"},
        "yaml":{".yml",".yaml"},
        "workflow":{".yml",".yaml"},
        "xlsx":{".xlsx"},
        "spreadsheet":{".xlsx"},
        "workbook":{".xlsx"},
        "sqlite":{".sqlite",".db",".sqlite3"},
        "database":{".sqlite",".db",".sqlite3"},
        "db":{".sqlite",".db",".sqlite3"},
    }.get(stem,set())
    candidates=[]
    for raw in reversed(list(context_paths or [])):
        p=pathlib.Path(str(raw))
        if suffixes:
            if p.suffix.lower() in suffixes:
                candidates.append(str(raw))
            # Typed inputs must never fall back to lexical substring matching;
            # prose containing "json", "xlsx", etc. is not a file path.
            continue
        if stem in {"input","source"}:
            candidates.append(str(raw))
        elif stem and (stem in p.name.lower() or stem in p.suffix.lower()):
            candidates.append(str(raw))
    seen=[]
    for x in candidates:
        if x not in seen:
            seen.append(x)
    return seen[0] if len(seen)>=1 else None


def _bind_inputs(goal, root, entry, context_paths=None, future_clauses=None):
    template=entry.get("action_template") or {}
    keys=_placeholders(template)
    if not keys:
        return {}
    paths=_repo_paths(goal,root)
    future_text=" ".join(str(x) for x in (future_clauses or []))
    future_paths=_repo_paths(future_text,root) if future_text else []
    result={}
    for key in keys:
        if key=="text":
            result[key]=_extract_text_argument(goal)
            continue
        if key=="goal":
            result[key]=str(goal)
            continue
        if key=="url":
            urls=re.findall(r"https?://[^\s)\]}>]+",goal)
            urls=[u.rstrip(".,;:!?") for u in urls]
            if len(urls)==1:
                result[key]=urls[0]
                continue
            raise GoalCompilationFailure("GOAL_URL_BINDING_REQUIRED",str(len(urls)))
        if key.endswith("_path"):
            stem=key[:-5].lower()
            output_stems={"output","result","report","screenshot","image","artifact","destination","dest"}
            if key.startswith("output_") or stem in output_stems:
                # Future outputs may not exist. Prefer type-compatible paths
                # explicitly named by the goal so multiple outputs can bind
                # without positional guessing.
                suffix_map={
                  "screenshot":{".png",".jpg",".jpeg",".webp"},
                  "image":{".png",".jpg",".jpeg",".webp"},
                  "result":{".json"},
                  "report":{".json",".md",".txt"},
                  "json":{".json"},
                  "archive":{".gz",".tgz",".zip",".tar"},
                  "xlsx":{".xlsx"},
                  "spreadsheet":{".xlsx"},
                  "sqlite":{".sqlite",".db",".sqlite3"},
                  "database":{".sqlite",".db",".sqlite3"},
                }
                wanted=suffix_map.get(stem)
                if wanted is None and stem=="output":
                    declared_formats=sorted(set(
                        str(effect)[len("structured.binary.encode."):]
                        for effect in (entry.get("provides") or [])
                        if str(effect).startswith("structured.binary.encode.")
                        and str(effect)!="structured.binary.encode"
                    ))
                    if len(declared_formats)==1:
                        wanted={"."+declared_formats[0].lower().lstrip(".")}
                    elif len(declared_formats)>1:
                        raise GoalCompilationFailure(
                            "GOAL_OUTPUT_FORMAT_AMBIGUOUS",
                            json.dumps(declared_formats,sort_keys=True)
                        )
                    else:
                        semantic_blob=" ".join(
                            [str(x) for x in entry.get("provides",[])]
                            +[str(x) for x in entry.get("keywords",[])]
                            +[str(entry.get("adapter_module") or "")]
                        ).lower()
                        semantic_suffixes=[
                          (("xlsx","spreadsheet","workbook"),{".xlsx"}),
                          (("docx","word"),{".docx"}),
                          (("pdf",),{".pdf"}),
                          (("sqlite","database"),{".sqlite",".db",".sqlite3"}),
                          (("json",),{".json"}),
                          (("markdown",),{".md",".markdown"}),
                          (("png","qr","barcode","image"),{".png",".jpg",".jpeg",".webp"}),
                        ]
                        for markers,suffix_set in semantic_suffixes:
                            if any(marker in semantic_blob for marker in markers):
                                wanted=suffix_set
                                break
                if wanted:
                    matching=[raw for raw,p in paths if p.suffix.lower() in wanted]
                    future_matching=[raw for raw,p in future_paths if p.suffix.lower() in wanted]
                else:
                    matching=[raw for raw,p in paths if (not stem or stem in raw.lower())]
                    future_matching=[raw for raw,p in future_paths if (not stem or stem in raw.lower())]
                if len(matching)==1:
                    result[key]=matching[0]
                    continue
                if not matching and len(future_matching)==1:
                    result[key]=future_matching[0]
                    continue
                if wanted is None:
                    # Generic output binding: when the clause names exactly one
                    # repository file that does not exist yet, while other named
                    # files already exist as inputs, that unique future artifact
                    # is the only causally admissible output. Do not require its
                    # filename to contain the word "output" or pre-enumerate its
                    # extension.
                    future_artifacts=[
                        raw for raw,p in paths
                        if pathlib.Path(raw).suffix and not p.exists()
                    ]
                    if len(future_artifacts)==1:
                        result[key]=future_artifacts[0]
                        continue
                # Single-path fallback is safe only for an actual typed file,
                # never for URL fragments or extensionless directory-like text.
                if wanted is None and len(paths)==1 and pathlib.Path(paths[0][0]).suffix:
                    result[key]=paths[0][0]
                    continue
            else:
                existing=[(raw,p) for raw,p in paths if p.is_file()]
                matching=[raw for raw,p in existing if (not stem or stem in p.suffix.lower() or stem in raw.lower())]
                if len(matching)==1:
                    result[key]=matching[0]
                    continue
                # Typed inputs such as markdown_path/json_path/pdf_path must
                # prefer causally produced, type-compatible context. A replay
                # may leave a later output artifact on disk; treating that
                # unrelated "only existing file" as the input corrupts the
                # action graph (e.g. binding an existing PDF as markdown_path).
                context_value=_context_path_for_key(key,context_paths)
                if context_value is not None:
                    result[key]=context_value
                    continue
                if stem in {"input","source"} and len(existing)==1:
                    result[key]=existing[0][0]
                    continue
        raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED",key)
    return result


def _execution_surface_constraint_match(goal,entry):
    lower=str(goal or "").lower()
    source=(entry or {}).get("source") or {}
    source_type=str(source.get("type") or "").lower()
    adapter=str((entry or {}).get("adapter_module") or "").lower()
    requires_npm=bool(
        re.search(r"\bnpm\b",lower)
        or re.search(r"\bnode(?:\.js|js)?\b",lower)
        or "javascript library" in lower
    )
    requires_pypi=bool("pypi" in lower or "python library" in lower)
    requires_apt=bool(
        re.search(r"\bapt\b",lower)
        or "ubuntu package" in lower
        or "debian package" in lower
    )
    if requires_npm:
        ok=source_type=="npm" or adapter.startswith("node_") or adapter.startswith("javascript_")
        return ok,{"required_surface":"npm_node","observed_source_type":source_type,"adapter_module":adapter}
    if requires_pypi:
        ok=source_type=="pypi" or adapter.startswith("python_")
        return ok,{"required_surface":"pypi_python","observed_source_type":source_type,"adapter_module":adapter}
    if requires_apt:
        ok=source_type=="apt"
        return ok,{"required_surface":"apt","observed_source_type":source_type,"adapter_module":adapter}
    return True,None


def _structured_binary_format_match(goal,entry):
    provides=[str(x).lower() for x in (entry.get("provides") or [])]
    formats={
        p[len("structured.binary.encode."):]
        for p in provides
        if p.startswith("structured.binary.encode.") and p!="structured.binary.encode"
    }
    if not formats:
        return True,None
    paths=re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+",str(goal or ""))
    output_formats={
        pathlib.Path(raw.rstrip(".,;:!?)]}")).suffix.lower().lstrip(".")
        for raw in paths
    }
    output_formats.discard("")
    nonformat={"json","txt","md","markdown","csv","tsv"}
    requested=output_formats-nonformat
    if not requested:
        return True,None
    matched=requested & formats
    return bool(matched),{
      "requested_formats":sorted(requested),
      "capability_formats":sorted(formats),
      "matched_formats":sorted(matched),
    }


def _score(goal, cid, entry):
    surface_ok,surface_evidence=_execution_surface_constraint_match(goal,entry)
    if not surface_ok:
        return 0,0,{
          "goal_tokens":sorted(_tokens(goal)),
          "matched_provides":[],
          "matched_requires":[],
          "matched_identity":[],
          "matched_keywords":[],
          "execution_surface_rejection":surface_evidence,
        }
    format_ok,format_evidence=_structured_binary_format_match(goal,entry)
    if not format_ok:
        return 0,0,{
          "goal_tokens":sorted(_tokens(goal)),
          "matched_provides":[],
          "matched_requires":[],
          "matched_identity":[],
          "matched_keywords":[],
          "format_rejection":format_evidence,
        }
    gt=_tokens(goal)
    provides=_tokens(entry.get("provides",[]))
    requires=_tokens(entry.get("requires",[]))
    identity=_tokens(cid)
    keywords=_tokens(entry.get("keywords",[]))
    # Requirements are highly informative for environment qualifiers such as
    # image-only/scanned/local/etc. Provides represent the requested effect.
    effect_matches=(gt & provides) | (gt & identity) | (gt & keywords)
    distinctive={x for x in effect_matches if x not in GENERIC_MATCH_TOKENS}
    # Preconditions and generic verbs/nouns may refine a match but may never
    # create one. A barcode-image goal must not become a QR-image action merely
    # because both say "generate" and "image".
    if not effect_matches or not distinctive:
        return 0,0,{
            "goal_tokens":sorted(gt),
            "matched_provides":[],
            "matched_requires":sorted(gt & requires),
            "matched_identity":[],
            "matched_keywords":sorted(gt & keywords),
        }
    score=5*len(gt & provides)+4*len(gt & keywords)+3*len(gt & requires)+2*len(gt & identity)
    # Prefer more-specific matched preconditions when base scores tie.
    specificity=len(gt & requires)
    return score,specificity,{
        "goal_tokens":sorted(gt),
        "matched_provides":sorted(gt & provides),
        "matched_requires":sorted(gt & requires),
        "matched_identity":sorted(gt & identity),
        "matched_keywords":sorted(gt & keywords),
    }


def _render_template(value, inputs):
    if isinstance(value,dict):
        return {k:_render_template(v,inputs) for k,v in value.items()}
    if isinstance(value,list):
        return [_render_template(v,inputs) for v in value]
    if isinstance(value,str):
        exact=re.fullmatch(r"\$\{input\.([A-Za-z0-9_]+)\}",value)
        if exact:
            key=exact.group(1)
            if key not in inputs:
                raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED",key)
            return json.loads(json.dumps(inputs[key]))
        out=value
        for key,val in inputs.items():
            out=out.replace("${input."+str(key)+"}",str(val))
        if "${input." in out:
            raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED","unresolved template input")
        return out
    return value


def decompose_goal(goal):
    """Return ordered action clauses for an explicitly compound plain goal.

    This is intentionally conservative: sentence boundaries, explicit "then",
    and action-bearing "and" connectors only. It does not invent hidden steps.
    """
    text=" ".join(str(goal or "").strip().split())
    if not text:
        return []
    parts=re.split(r"(?<=[.!?])\s+(?=[A-Z])|\b[Tt]hen\b",text)
    clauses=[]
    action_connector=re.compile(
        r"\s+and\s+(?=(?:read|inspect|create|generate|convert|extract|verify|check|render|analy[sz]e)\b)",
        re.IGNORECASE,
    )
    for part in parts:
        part=part.strip(" .")
        if not part:
            continue
        for sub in action_connector.split(part):
            sub=sub.strip(" .")
            if sub:
                clauses.append(sub)

    # "Independently execute/run X and verify/check/assert Y" is one
    # verification operation. Splitting the verification tail into a fresh
    # subgoal causes the compiler to search for a new capability even though
    # the fresh-execution verifier already owns those assertions.
    merged=[]
    i=0
    while i < len(clauses):
        current=clauses[i]
        if (
            i+1 < len(clauses)
            and re.search(r"\bindependently\s+(?:execute|run|reopen|read|reread|inspect|query|decode)\b",current,re.IGNORECASE)
            and re.match(r"^(?:verify|check|assert)\b",clauses[i+1],re.IGNORECASE)
        ):
            merged.append(current+" and "+clauses[i+1])
            i+=2
            continue
        merged.append(current)
        i+=1
    return merged


def _compile_verified_browser_interaction(goal, registry, root):
    """Compile a verified declarative browser-interaction goal.

    This path is activated only after the existing Chromedriver capability has
    explicit interaction verification evidence in the canonical registry.
    It converts conservative natural-language form instructions into a bounded
    action list; unsupported or ambiguous instructions fail closed.
    """
    entry=(registry or {}).get("web.browser.rendered.capture.chromedriver")
    if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    if "web.browser.rendered.interact" not in set(entry.get("provides") or []):
        return None
    verification=entry.get("verification") or {}
    ext=verification.get("interaction_extension") if isinstance(verification,dict) else None
    if not isinstance(ext,dict) or ext.get("mission_id")!="ASTRA-VERIFY-BROWSER-INTERACTION-001":
        return None

    lower=str(goal or "").lower()
    if "browser" not in lower or "submit" not in lower:
        return None
    if not any(w in lower for w in ("enter ","type ","fill ","choose ","select ","check ","click ")):
        return None

    m=re.search(r"https?://[^\s,;]+",str(goal or ""),flags=re.IGNORECASE)
    if not m:
        return None
    url=m.group(0).rstrip(".)]}>")

    paths=[raw for raw,_ in _repo_paths(goal,root)]
    screenshots=[p for p in paths if pathlib.Path(p).suffix.lower()==".png"]
    results=[p for p in paths if pathlib.Path(p).suffix.lower()==".json"]
    if len(screenshots)!=1 or len(results)!=1:
        return None

    actions=[]
    text_match=re.search(
        r"\b(?:enter|type|fill)\s+(.+?)\s+into\s+the\s+(.+?)\s+(?:field|input|box)\b",
        str(goal or ""),flags=re.IGNORECASE
    )
    if text_match:
        value=text_match.group(1).strip(" .,:;")
        target=text_match.group(2).strip(" .,:;")
        if value and target:
            actions.append({"type":"set_text","target":target,"value":value})

    choice_match=re.search(
        r"\b(?:choose|select)\s+([^,.;]+?)\s+(?:pizza\s+)?size\b",
        str(goal or ""),flags=re.IGNORECASE
    )
    if choice_match:
        value=choice_match.group(1).strip(" .,:;")
        if value:
            actions.append({"type":"select_option","target":"size","value":value})
    else:
        generic_choice=re.search(
            r"\b(?:choose|select)\s+(.+?)\s+(?:from|for)\s+the\s+(.+?)(?:\s+(?:field|dropdown|select))?(?=,|\.|;|$)",
            str(goal or ""),flags=re.IGNORECASE
        )
        if generic_choice:
            value=generic_choice.group(1).strip(" .,:;")
            target=generic_choice.group(2).strip(" .,:;")
            if value and target:
                actions.append({"type":"select_option","target":target,"value":value})

    check_match=re.search(
        r"\b(?:check|tick)\s+(?:the\s+)?(.+?)\s+(?:topping|checkbox|option)\b",
        str(goal or ""),flags=re.IGNORECASE
    )
    if check_match:
        target=check_match.group(1).strip(" .,:;")
        if target:
            actions.append({"type":"check","target":target})

    for click_match in re.finditer(
        r"\bclick\s+(?:the\s+)?(.+?)\s+(?:button|link)\b",
        str(goal or ""),flags=re.IGNORECASE
    ):
        target=click_match.group(1).strip(" .,:;")
        if target:
            actions.append({"type":"click","target":target})

    if re.search(r"\bsubmit\b",str(goal or ""),flags=re.IGNORECASE):
        actions.append({"type":"submit"})

    mutating=[a for a in actions if a.get("type") in {"set_text","select_option","check","click","submit"}]
    if len(mutating)<2 or not any(a.get("type")=="submit" for a in actions):
        return None

    invoke={
      "type":"invoke_capability",
      "args":{
        "capability_id":"web.browser.rendered.capture.chromedriver",
        "url":url,
        "actions":actions,
        "screenshot_path":screenshots[0],
        "result_path":results[0],
      },
      "expect":{"type":"field_equals","field":"interaction_verified","value":True},
    }
    return {
      "schema":"PROJECT_BRAIN_COMPILED_COMPOUND_GOAL_V1",
      "compiler_mode":"DETERMINISTIC_COMPOUND_ACTION_PLAN",
      "clauses":[str(goal or "").strip()],
      "compiled_parts":[{
        "index":0,
        "subgoal":str(goal or "").strip(),
        "mode":"VERIFIED_BROWSER_INTERACTION",
        "selected_capability":"web.browser.rendered.capture.chromedriver",
        "url":url,
        "actions":actions,
        "screenshot_path":screenshots[0],
        "result_path":results[0],
        "verification_mission_id":ext.get("mission_id"),
      }],
      "controller_actions":[
        invoke,
        {"type":"finish","args":{"summary":"PLAIN_GOAL_COMPLETE"}},
      ],
      "finish_summary":"PLAIN_GOAL_COMPLETE",
    }


def _compile_single_goal(
    goal, registry, root, context_paths=None, future_clauses=None,
    proposal_binder=None, effect_providers=None
):
    ranked=[]
    for cid,entry in sorted((registry or {}).items()):
        if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
            continue
        if not isinstance(entry.get("action_template"),dict):
            continue
        score,specificity,evidence=_score(goal,cid,entry)
        if score<=0:
            continue
        try:
            if _uses_effect_result_bindings(entry):
                if proposal_binder is None:
                    continue
                instance_id=(
                    "direct-"+hashlib.sha256(
                        (str(cid)+"\n"+str(goal)).encode("utf-8")
                    ).hexdigest()[:16]
                )
                inputs,_=proposal_binder._bind_planned_inputs(
                    goal,root,sys.modules[__name__],instance_id,cid,entry,
                    effect_providers or {}
                )
            else:
                inputs=_bind_inputs(
                    goal,root,entry,
                    context_paths=context_paths,
                    future_clauses=future_clauses
                )
        except Exception:
            continue
        ranked.append((score,specificity,cid,entry,inputs,evidence))
    ranked.sort(key=lambda x:(-x[0],-x[1],x[2]))
    if not ranked:
        raise GoalCompilationFailure("GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH")
    best=ranked[0]
    if len(ranked)>1 and ranked[1][0]==best[0] and ranked[1][1]==best[1]:
        raise GoalCompilationFailure(
            "GOAL_COMPILATION_AMBIGUOUS",
            json.dumps({"candidates":[best[2],ranked[1][2]],"score":best[0]},sort_keys=True)
        )
    score,specificity,cid,entry,inputs,evidence=best
    return {
        "schema":"PROJECT_BRAIN_COMPILED_CAPABILITY_PROBLEM_V1",
        "compiler_mode":"DETERMINISTIC_VERIFIED_CAPABILITY_MATCH",
        "selected_capability":cid,
        "score":score,
        "match_evidence":evidence,
        "inputs":inputs,
        "initial_facts":list(entry.get("requires") or []),
        "target_effects":list(entry.get("provides") or []),
        "capabilities":[],
        "finish_summary":"PLAIN_GOAL_COMPLETE",
    }


def _find_status_collection(data, wanted, prefix=()):
    if isinstance(data,dict):
        if data and all(isinstance(v,dict) for v in data.values()):
            for record in data.values():
                if any(v==wanted for v in record.values()):
                    return prefix
        for key,value in data.items():
            found=_find_status_collection(value,wanted,prefix+(str(key),))
            if found is not None:
                return found
    return None


def _jq_path(parts):
    out="."
    for part in parts:
        out+="["+json.dumps(str(part))+"]"
    return out


def _compile_json_markdown_table(subgoal, context_paths, registry, root):
    entry=(registry or {}).get("json.query.jq")
    if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    lower=subgoal.lower()
    if "table" not in lower or "markdown" not in lower and ".md" not in lower:
        return None
    out_paths=[raw for raw,_ in _repo_paths(subgoal,root) if pathlib.Path(raw).suffix.lower() in {".md",".markdown"}]
    if len(out_paths)!=1:
        return None
    json_paths=[p for p in context_paths if pathlib.Path(p).suffix.lower()==".json" and (pathlib.Path(root)/p).is_file()]
    if not json_paths:
        return None

    # Prefer the most recent structured artifact in the causal prefix.
    input_path=json_paths[-1]
    data=json.loads((pathlib.Path(root)/input_path).read_text(encoding="utf-8"))
    semantic=re.sub(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+"," ",subgoal)
    constants=re.findall(r"\b[A-Z][A-Z0-9_]{3,}\b",semantic)
    wanted=None
    collection=None
    for token in constants:
        found=_find_status_collection(data,token)
        if found is not None:
            wanted=token
            collection=found
            break
    if wanted is None or collection is None:
        return None

    base=_jq_path(collection)
    wanted_json=json.dumps(wanted)
    # Generic schema-driven report: all top-level fields of every record whose
    # record contains the requested exact status value. Nested values are
    # serialized, so the report preserves rather than guesses field semantics.
    filt=(
      f'{base} | to_entries '
      f'| map(select(.value | any(. == {wanted_json}))) as $rows '
      '| ($rows | map(.value | keys) | add | unique) as $cols '
      '| (["id"] + $cols) as $headers '
      '| ($headers | "| " + join(" | ") + " |"), '
      '("| " + ($headers | map("---") | join(" | ")) + " |"), '
      '($rows[] | . as $row '
      '| ([ $row.key ] + ($cols | map(($row.value[.] // "") '
      '| if type=="array" then map(tostring) | join(", ") '
      'elif type=="object" then tojson else tostring end))) '
      '| map(gsub("[|]"; "&#124;") | gsub("[\\r\\n]+";" ")) '
      '| "| " + join(" | ") + " |")'
    )
    action={
      "type":"invoke_capability",
      "args":{
        "capability_id":"json.query.jq",
        "input_path":input_path,
        "filter":filt,
        "output_path":out_paths[0],
        "raw_output":True,
        "require_nonempty":True,
        "timeout_s":60,
      },
      "expect":{"type":"field_equals","field":"output_verified","value":True},
    }
    return {
      "action":action,
      "output_path":out_paths[0],
      "evidence":{
        "input_path":input_path,
        "output_path":out_paths[0],
        "status_value":wanted,
        "collection_path":list(collection),
        "capability_id":"json.query.jq",
      }
    }


def _compile_pypi_provenance_audit(subgoal, context_paths, registry, root, future_clauses=None):
    entry=(registry or {}).get("pypi.provenance.audit_live_artifact")
    if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    lower=subgoal.lower()
    if not re.match(r"^verify\b",lower):
        return None
    if "wheel" not in lower or "download" not in lower or ("sha-256" not in lower and "sha256" not in lower):
        return None

    json_paths=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower()==".json"]
    selection_paths=[p for p in json_paths if "STRUCTURED_SELECTION_" in pathlib.Path(p).name]
    metadata_paths=[p for p in json_paths if "LIVE_FETCH_" in pathlib.Path(p).name]
    if not selection_paths or not metadata_paths:
        return None
    selection_path=selection_paths[-1]
    metadata_path=metadata_paths[-1]

    report_path=None
    for clause in future_clauses or []:
        for raw,_ in _repo_paths(clause,root):
            if pathlib.Path(raw).suffix.lower()==".json" and raw not in context_paths:
                report_path=raw
                break
        if report_path:
            break
    if not report_path:
        digest=hashlib.sha256(subgoal.encode("utf-8")).hexdigest()[:12]
        report_path=f"canonical/astra_runtime/tmp/PYPI_PROVENANCE_{digest}.json"

    action={
      "type":"invoke_capability",
      "args":{
        "capability_id":"pypi.provenance.audit_live_artifact",
        "selection_path":selection_path,
        "metadata_path":metadata_path,
        "report_path":report_path,
        "max_bytes":20000000,
        "timeout_s":60,
      },
      "expect":{"type":"field_equals","field":"verified","value":True},
    }
    return {
      "action":action,
      "output_path":report_path,
      "evidence":{
        "selection_path":selection_path,
        "metadata_path":metadata_path,
        "report_path":report_path,
        "capability_id":"pypi.provenance.audit_live_artifact",
      }
    }


def _compile_json_hash_equality_assertion(subgoal, context_paths, root):
    lower=subgoal.lower()
    if not re.match(r"^(?:finally\s+)?(?:independently\s+)?(?:verify|check|assert|read)\b",lower):
        return None
    relevant=(
        "wheel_sha256" in lower
        or ("hash" in lower and any(x in lower for x in ("identical","equal","equals","match")))
        or ("verified is true" in lower)
    )
    if not relevant:
        return None
    json_paths=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower()==".json"]
    if not json_paths:
        return None
    # Prefer a provenance/audit report in the causal prefix.
    report_paths=[p for p in json_paths if any(x in pathlib.Path(p).name.upper() for x in ("PROVENANCE","AUDIT","REPORT"))]
    report_path=(report_paths or json_paths)[-1]
    action={
      "type":"assert_json_fields_equal",
      "args":{
        "path":report_path,
        "fields":["recorded_hash","live_metadata_hash","downloaded_artifact_hash"],
        "true_fields":["verified"],
      },
      "expect":{"type":"field_equals","field":"verified","value":True},
    }
    return {
      "action":action,
      "evidence":{
        "report_path":report_path,
        "equal_fields":["recorded_hash","live_metadata_hash","downloaded_artifact_hash"],
        "true_fields":["verified"],
      }
    }


def _compile_existing_causal_artifact_assertion(subgoal, context_paths, root):
    lower=subgoal.lower()
    if not re.match(r"^(?:create|write|save|store)\b",lower):
        return None
    paths=[raw for raw,_ in _repo_paths(subgoal,root)]
    context=set(context_paths or [])
    matches=[]
    for p in paths:
        if p in context and p not in matches:
            matches.append(p)
    if not matches or len(matches)!=len(dict.fromkeys(paths)):
        return None
    actions=[{
      "type":"assert_file_exists",
      "args":{"path":p},
      "expect":{"type":"field_equals","field":"verified","value":True},
    } for p in matches]
    return {"actions":actions,"evidence":{"paths":matches}}


def _compile_context_url_json_fetch(subgoal, context_paths, registry, root):
    entry=(registry or {}).get("http.json.fetch_from_state")
    if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    lower=subgoal.lower()
    if not re.match(r"^(?:fetch|get|download|retrieve)\b",lower):
        return None
    if "url" not in lower or not any(x in lower for x in ("json","metadata")):
        return None

    # Use the most recent structured artifact in the causal prefix. It may not
    # exist yet during compilation because an earlier action will create it.
    json_paths=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower()==".json"]
    if not json_paths:
        return None
    source_json_path=json_paths[-1]

    # Convert phrases such as "metadata URL" / "artifact URL" into the key
    # expected inside the structured state. Fail closed if the clause does not
    # name the URL role.
    m=re.search(r"\b([a-z][a-z0-9_-]*)\s+url\b",lower)
    if not m:
        return None
    role=m.group(1).replace("-","_")
    if role in {"the","a","an","that","this","live","authoritative","recorded"}:
        # Prefer a semantically meaningful token immediately before that noise.
        tokens=re.findall(r"[a-z][a-z0-9_-]*",lower[:m.end()])
        meaningful=[t for t in tokens if t not in {"the","a","an","that","this","live","authoritative","recorded","from","in","its","project","projects"}]
        role=meaningful[-2] if len(meaningful)>=2 and meaningful[-1]=="url" else (meaningful[-1] if meaningful else "")
    if not role or role=="url":
        return None
    url_key=role+"_url"

    digest=hashlib.sha256(subgoal.encode("utf-8")).hexdigest()[:12]
    output_path=f"canonical/astra_runtime/tmp/LIVE_FETCH_{digest}.json"
    action={
      "type":"invoke_capability",
      "args":{
        "capability_id":"http.json.fetch_from_state",
        "source_json_path":source_json_path,
        "url_key":url_key,
        "output_path":output_path,
        "max_bytes":5000000,
        "timeout_s":30,
      },
      "expect":{"type":"field_equals","field":"output_verified","value":True},
    }
    return {
      "action":action,
      "output_path":output_path,
      "evidence":{
        "source_json_path":source_json_path,
        "url_key":url_key,
        "output_path":output_path,
        "capability_id":"http.json.fetch_from_state",
      }
    }


def _python_test_glob(subgoal, root):
    m=re.search(r"((?:[A-Za-z0-9_.-]+/)+)(test_[A-Za-z0-9_.*?-]*\.py)",subgoal)
    if not m:
        return None
    raw_root=m.group(1).rstrip("/")
    pattern=m.group(2)
    p=(pathlib.Path(root)/raw_root).resolve()
    rr=pathlib.Path(root).resolve()
    if not p.is_dir() or (p!=rr and rr not in p.parents):
        return None
    return {"source_root":raw_root,"pattern":pattern}


def _compile_python_test_audit(subgoal, context_paths, registry, root):
    cap=(registry or {}).get("python.tests.audit.unittest")
    if not isinstance(cap,dict) or cap.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    lower=subgoal.lower()
    if not re.match(r"^(?:create|write|generate)\b",lower):
        return None
    if "record per test file" not in lower or "exit code" not in lower:
        return None
    outputs=[raw for raw,_ in _repo_paths(subgoal,root) if pathlib.Path(raw).suffix.lower()==".json"]
    roots=[str(p) for p in context_paths if str(p).replace("\\","/").endswith("/tests")]
    if len(outputs)!=1 or not roots:
        return None
    source_root=roots[-1]
    action={
      "type":"invoke_capability",
      "args":{
        "capability_id":"python.tests.audit.unittest",
        "source_root":source_root,
        "pattern":"test_*.py",
        "output_path":outputs[0],
        "timeout_s":180,
      },
      "expect":{"type":"field_equals","field":"output_verified","value":True},
    }
    return {
      "action":action,"output_path":outputs[0],
      "evidence":{
        "source_root":source_root,"pattern":"test_*.py",
        "output_path":outputs[0],"capability_id":"python.tests.audit.unittest",
      }
    }


def _compile_python_test_zero_assertion(subgoal, context_paths, root):
    lower=subgoal.lower()
    if "fail if any test file exits nonzero" not in lower:
        return None
    audits=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower()==".json" and "TEST_AUDIT" in pathlib.Path(str(p)).name.upper()]
    if not audits:
        return None
    return {
      "action":{
        "type":"assert_python_test_audit_zero",
        "args":{"audit_path":audits[-1]},
        "expect":{"type":"field_equals","field":"verified","value":True},
      },
      "evidence":{"audit_path":audits[-1]},
    }


def _compile_python_test_fresh_verification(subgoal, context_paths, root):
    lower=subgoal.lower()
    if "independently execute" not in lower or "same complete test corpus" not in lower:
        return None
    audits=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower()==".json" and "TEST_AUDIT" in pathlib.Path(str(p)).name.upper()]
    roots=[str(p) for p in context_paths if str(p).replace("\\","/").endswith("/tests")]
    if not audits or not roots:
        return None
    return {
      "action":{
        "type":"assert_python_test_audit_supported_by_fresh_execution",
        "args":{"audit_path":audits[-1],"source_root":roots[-1],"pattern":"test_*.py"},
        "expect":{"type":"field_equals","field":"verified","value":True},
      },
      "evidence":{
        "audit_path":audits[-1],"source_root":roots[-1],"pattern":"test_*.py",
        "verification_action":"assert_python_test_audit_supported_by_fresh_execution",
      }
    }


def _compile_python_source_audit(subgoal, context_paths, registry, root):
    cap=(registry or {}).get("python.source.audit.ast")
    if not isinstance(cap,dict) or cap.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    lower=subgoal.lower()
    if not re.match(r"^(?:create|write|generate)\b",lower):
        return None
    if "python" not in lower or "one record" not in lower or ".py" not in lower:
        return None
    outputs=[raw for raw,_ in _repo_paths(subgoal,root) if pathlib.Path(raw).suffix.lower()==".json"]
    dirs=[str(p) for p in context_paths if (pathlib.Path(root)/str(p)).is_dir()]
    if len(outputs)!=1 or not dirs:
        return None
    source_root=dirs[-1]
    action={
      "type":"invoke_capability",
      "args":{
        "capability_id":"python.source.audit.ast",
        "source_root":source_root,
        "output_path":outputs[0],
      },
      "expect":{"type":"field_equals","field":"output_verified","value":True},
    }
    return {
      "action":action,
      "output_path":outputs[0],
      "evidence":{
        "source_root":source_root,
        "output_path":outputs[0],
        "capability_id":"python.source.audit.ast",
      }
    }


def _compile_python_audit_totals_assertion(subgoal, context_paths, root):
    lower=subgoal.lower()
    if not lower.startswith("include totals"):
        return None
    audits=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower()==".json" and "PYTHON_RUNTIME_AUDIT" in pathlib.Path(str(p)).name.upper()]
    if not audits:
        return None
    return {
      "action":{
        "type":"assert_file_exists",
        "args":{"path":audits[-1]},
        "expect":{"type":"field_equals","field":"verified","value":True},
      },
      "evidence":{"audit_path":audits[-1],"totals_verified_by_final_source_crosscheck":True},
    }


def _compile_python_source_audit_verification(subgoal, context_paths, root):
    lower=subgoal.lower()
    if "independently verify" not in lower or "raw python source" not in lower:
        return None
    audits=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower()==".json" and "PYTHON_RUNTIME_AUDIT" in pathlib.Path(str(p)).name.upper()]
    dirs=[str(p) for p in context_paths if (pathlib.Path(root)/str(p)).is_dir()]
    if not audits or not dirs:
        return None
    action={
      "type":"assert_python_source_audit_supported_by_source",
      "args":{"audit_path":audits[-1],"source_root":dirs[-1]},
      "expect":{"type":"field_equals","field":"verified","value":True},
    }
    return {
      "action":action,
      "evidence":{
        "audit_path":audits[-1],
        "source_root":dirs[-1],
        "verification_action":"assert_python_source_audit_supported_by_source",
      }
    }


def _compile_github_workflow_audit(subgoal, context_paths, registry, root):
    yq=(registry or {}).get("yaml.to_json.yq")
    jq=(registry or {}).get("json.query.jq")
    if not isinstance(yq,dict) or yq.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    if not isinstance(jq,dict) or jq.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    lower=subgoal.lower()
    if not re.match(r"^(?:create|write|generate)\b",lower):
        return None
    if "workflow" not in lower or "job id" not in lower or "uses action" not in lower:
        return None
    out_paths=[raw for raw,_ in _repo_paths(subgoal,root) if pathlib.Path(raw).suffix.lower()==".json"]
    if len(out_paths)!=1:
        return None
    yaml_paths=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower() in {".yml",".yaml"}]
    if not yaml_paths:
        return None
    yaml_path=yaml_paths[-1]
    digest=hashlib.sha256((yaml_path+"\n"+subgoal).encode("utf-8")).hexdigest()[:12]
    normalized=f"canonical/astra_runtime/tmp/YAML_NORMALIZED_{digest}.json"
    audit_path=out_paths[0]
    yq_action={
      "type":"invoke_capability",
      "args":{
        "capability_id":"yaml.to_json.yq",
        "yaml_path":yaml_path,
        "output_path":normalized,
        "timeout_s":60,
      },
      "expect":{"type":"field_equals","field":"output_verified","value":True},
    }
    filt=(
      '{'
      'schema:"PROJECT_BRAIN_GITHUB_WORKFLOW_AUDIT_V1",'
      'name:(.name // null),'
      'trigger_names:((.["on"] // {}) | if type=="object" then keys else [] end),'
      'push_branches:(.["on"].push.branches // []),'
      'push_paths:(.["on"].push.paths // []),'
      'workflow_dispatch_input_names:((.["on"].workflow_dispatch.inputs // {}) | keys),'
      'permissions:(.permissions // {}),'
      'jobs:((.jobs // {}) | to_entries | map({'
      'id:.key,'
      'runner_label:(.value["runs-on"] // null),'
      'timeout_minutes:(.value["timeout-minutes"] // null),'
      'step_names:[.value.steps[]? | .name // empty],'
      'uses:[.value.steps[]? | .uses // empty]'
      '}))'
      '}'
    )
    jq_action={
      "type":"invoke_capability",
      "args":{
        "capability_id":"json.query.jq",
        "input_path":normalized,
        "filter":filt,
        "output_path":audit_path,
        "raw_output":False,
        "require_nonempty":True,
        "timeout_s":60,
      },
      "expect":{"type":"field_equals","field":"output_verified","value":True},
    }
    return {
      "actions":[yq_action,jq_action],
      "output_path":audit_path,
      "normalized_path":normalized,
      "evidence":{
        "yaml_path":yaml_path,
        "normalized_path":normalized,
        "output_path":audit_path,
        "parser_capability":"yaml.to_json.yq",
        "transform_capability":"json.query.jq",
        "audit_schema":"PROJECT_BRAIN_GITHUB_WORKFLOW_AUDIT_V1",
      }
    }


def _compile_workflow_audit_raw_verification(subgoal, context_paths, root):
    lower=subgoal.lower()
    if "independently verify" not in lower or "raw yaml" not in lower:
        return None
    yaml_paths=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower() in {".yml",".yaml"}]
    json_paths=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower()==".json"]
    audit_paths=[p for p in json_paths if "WORKFLOW_AUDIT" in pathlib.Path(p).name.upper()]
    if not yaml_paths or not audit_paths:
        return None
    action={
      "type":"assert_workflow_audit_supported_by_source",
      "args":{
        "audit_path":audit_paths[-1],
        "yaml_path":yaml_paths[-1],
      },
      "expect":{"type":"field_equals","field":"verified","value":True},
    }
    return {
      "action":action,
      "evidence":{
        "audit_path":audit_paths[-1],
        "yaml_path":yaml_paths[-1],
        "verification_action":"assert_workflow_audit_supported_by_source",
      }
    }


def _compile_json_record_selection(subgoal, context_paths, registry, root):
    entry=(registry or {}).get("json.query.jq")
    if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    lower=subgoal.lower()
    if not re.match(r"^(?:find|select|identify|locate)\b",lower):
        return None
    json_paths=[p for p in context_paths if pathlib.Path(p).suffix.lower()==".json" and (pathlib.Path(root)/p).is_file()]
    if not json_paths:
        return None
    input_path=json_paths[-1]
    data=json.loads((pathlib.Path(root)/input_path).read_text(encoding="utf-8"))

    # Detect an exact status token if the clause names one.
    semantic=re.sub(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+"," ",subgoal)
    constants=re.findall(r"\b[A-Z][A-Z0-9_]{3,}\b",semantic)
    wanted_status=None
    collection=None
    for token in constants:
        found=_find_status_collection(data,token)
        if found is not None:
            wanted_status=token
            collection=found
            break
    if collection is None:
        collection=_find_record_collection(data)
    if collection is None:
        return None

    # Generic nested-field equality phrasing: "source type is pypi",
    # "source type equals apt", etc. Keep this deliberately narrow and
    # deterministic rather than guessing arbitrary semantics.
    m=re.search(
        r"\b(source)\s+(type|project)\s+(?:is|equals?|=)\s+([A-Za-z0-9_.-]+)\b",
        lower
    )
    nested_field=None
    nested_value=None
    if m:
        nested_field=[m.group(1),m.group(2)]
        nested_value=m.group(3)
    else:
        m=re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\s+type\s+(?:is|equals?|=)\s+([A-Za-z0-9_.-]+)\b",lower)
        if m:
            nested_field=[m.group(1),"type"]
            nested_value=m.group(2)
    if nested_field is None:
        return None

    base=_jq_path(collection)
    predicates=[]
    if wanted_status is not None:
        predicates.append(f'any(. == {json.dumps(wanted_status)})')
    path_expr="".join("["+json.dumps(x)+"]" for x in nested_field)
    predicates.append(f'(.{path_expr} == {json.dumps(nested_value)})')
    # The predicate executes under ".value |", so .["source"]["type"]
    # remains relative to the current record.
    pred=" and ".join(predicates)
    filt=(
      f'{base} | to_entries | map(select(.value | {pred})) '
      '| if length==1 then .[0] | {id:.key, record:.value} '
      'else error("SELECTION_NOT_UNIQUE:"+((length)|tostring)) end'
    )
    digest=hashlib.sha256(subgoal.encode("utf-8")).hexdigest()[:12]
    output_path=f"canonical/astra_runtime/tmp/STRUCTURED_SELECTION_{digest}.json"
    action={
      "type":"invoke_capability",
      "args":{
        "capability_id":"json.query.jq",
        "input_path":input_path,
        "filter":filt,
        "output_path":output_path,
        "raw_output":False,
        "require_nonempty":True,
        "timeout_s":60,
      },
      "expect":{"type":"field_equals","field":"output_verified","value":True},
    }
    return {
      "action":action,
      "output_path":output_path,
      "evidence":{
        "input_path":input_path,
        "output_path":output_path,
        "collection_path":list(collection),
        "status_value":wanted_status,
        "nested_field":nested_field,
        "nested_value":nested_value,
        "capability_id":"json.query.jq",
      }
    }


def _compile_json_status_manifest(subgoal, context_paths, registry, root):
    entry=(registry or {}).get("json.query.jq")
    if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    lower=subgoal.lower()
    if "manifest" not in lower and "one record" not in lower:
        return None
    out_paths=[raw for raw,_ in _repo_paths(subgoal,root) if pathlib.Path(raw).suffix.lower()==".json"]
    if len(out_paths)!=1:
        return None
    json_paths=[p for p in context_paths if pathlib.Path(p).suffix.lower()==".json" and (pathlib.Path(root)/p).is_file()]
    if not json_paths:
        return None

    input_path=json_paths[-1]
    data=json.loads((pathlib.Path(root)/input_path).read_text(encoding="utf-8"))
    semantic=re.sub(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+"," ",subgoal)
    constants=re.findall(r"\b[A-Z][A-Z0-9_]{3,}\b",semantic)
    wanted=None
    collection=None
    for token in constants:
        found=_find_status_collection(data,token)
        if found is not None:
            wanted=token
            collection=found
            break
    if wanted is None or collection is None:
        return None

    base=_jq_path(collection)
    wanted_json=json.dumps(wanted)
    schema_json=json.dumps("PROJECT_BRAIN_STATUS_MANIFEST_V1")
    filt=(
      f'{base} | to_entries '
      f'| map(select(.value | any(. == {wanted_json})) '
      '| {'
      'capability_id:.key, '
      'verification_mission_id:(.value.verification.mission_id // null), '
      'verification_paths:([.value.verification '
      '| paths(strings) as $p '
      '| select(($p[-1] | tostring | test("evidence|receipt|result_path";"i"))) '
      '| getpath($p) '
      '| select(startswith("canonical/"))] | unique), '
      'source:(.value.source // {})'
      '}) '
      f'| {{schema:{schema_json},status_value:{wanted_json},records:.}}'
    )
    action={
      "type":"invoke_capability",
      "args":{
        "capability_id":"json.query.jq",
        "input_path":input_path,
        "filter":filt,
        "output_path":out_paths[0],
        "raw_output":False,
        "require_nonempty":True,
        "timeout_s":60,
      },
      "expect":{"type":"field_equals","field":"output_verified","value":True},
    }
    return {
      "action":action,
      "output_path":out_paths[0],
      "evidence":{
        "input_path":input_path,
        "output_path":out_paths[0],
        "status_value":wanted,
        "collection_path":list(collection),
        "capability_id":"json.query.jq",
        "manifest_schema":"PROJECT_BRAIN_STATUS_MANIFEST_V1",
      }
    }


def _find_record_collection(data, prefix=()):
    if isinstance(data,dict):
        if data and all(isinstance(v,dict) for v in data.values()):
            return prefix
        for key,value in data.items():
            found=_find_record_collection(value,prefix+(str(key),))
            if found is not None:
                return found
    return None


def _compile_pdf_json_key_verification(subgoal, context_paths, registry, root, result_cycle):
    lower=subgoal.lower()
    if not re.match(r"^(?:verify|check)\b",lower):
        return None
    if "pdf" not in lower or "contain" not in lower or (" id" not in lower and " key" not in lower):
        return None
    pdf_paths=[p for p in context_paths if pathlib.Path(p).suffix.lower()==".pdf"]
    json_paths=[p for p in context_paths if pathlib.Path(p).suffix.lower()==".json" and (pathlib.Path(root)/p).is_file()]
    cap=(registry or {}).get("pdf.extract.text.pypdf")
    if not pdf_paths or not json_paths or not isinstance(cap,dict) or cap.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    pdf_path=pdf_paths[-1]
    json_path=json_paths[0]
    data=json.loads((pathlib.Path(root)/json_path).read_text(encoding="utf-8"))
    collection=_find_record_collection(data)
    if collection is None:
        return None
    extract_action={
      "type":"invoke_capability",
      "args":{"capability_id":"pdf.extract.text.pypdf","path":pdf_path,"max_pages":200},
      "expect":{"type":"field_nonempty","field":"text"},
    }
    assert_action={
      "type":"assert_text_contains_json_keys",
      "args":{
        "text":{"$result":{"cycle":result_cycle,"field":"text"}},
        "json_path":json_path,
        "collection_path":list(collection),
        "normalization":"alnum_upper",
      },
      "expect":{"type":"field_equals","field":"verified","value":True},
    }
    return {
      "actions":[extract_action,assert_action],
      "evidence":{
        "pdf_path":pdf_path,
        "json_path":json_path,
        "collection_path":list(collection),
        "extractor_capability":"pdf.extract.text.pypdf",
        "verification_action":"assert_text_contains_json_keys",
      }
    }


def _compile_latest_stable_release_from_capture(subgoal, context_paths, registry, root):
    """Extract an anchored latest-stable semantic version from prior captured page text.

    The producer is intentionally generic: it consumes a structured JSON
    capture containing observed_text/text/content and rewrites that JSON to a
    compact fact record. jq is already independently verified, so this adds no
    new parser/runtime dependency.
    """
    lower=subgoal.lower()
    m=re.search(
        r"^(?:determine|identify|find|extract)\s+the\s+latest\s+stable\s+"
        r"([A-Za-z][A-Za-z0-9_.+-]*)(?:\s+(\d+))?\s+(?:release|version)\b",
        subgoal,re.IGNORECASE
    )
    if not m:
        return None
    entry=(registry or {}).get("json.query.jq")
    if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    json_paths=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower()==".json"]
    if not json_paths:
        return None
    input_path=json_paths[-1]
    product=m.group(1)
    major=m.group(2)
    product_key=re.sub(r"[^a-z0-9]+","",product.lower())
    field="latest_stable_"+product_key+(major or "")
    version_pattern=(re.escape(product)+r"\s+(?<version>"+(re.escape(major)+r"\." if major else r"\d+\.")+r"\d+\.\d+)")
    # Prefer an explicit Download/Latest anchor, but remain page-layout tolerant
    # while keeping the product token adjacent to the captured semantic version.
    anchored=r"(?:Download\s+|Latest:\s*)?"+version_pattern
    jq_regex=json.dumps(anchored)
    field_json=json.dumps(field)
    filt=(
      '(.observed_text // .text // .content // "") as $t '
      f'| ($t | match({jq_regex};"i")) as $m '
      '| ($m.captures | map(select(.name=="version")) | .[0].string) as $v '
      f'| {{source_url:.source_url, final_url:.final_url, page_title:.page_title, '
      f'{field_json}:$v, observed_text_evidence:$m.string}} '
      '| if (.source_url|type)=="string" and (.final_url|type)=="string" '
      'and (.page_title|type)=="string" and ($v|type)=="string" and ($v|length)>0 '
      'then . else error("SEMANTIC_FACT_FIELDS_INCOMPLETE") end'
    )
    action={
      "type":"invoke_capability",
      "args":{
        "capability_id":"json.query.jq",
        "input_path":input_path,
        "filter":filt,
        "output_path":input_path,
        "raw_output":False,
        "require_nonempty":True,
        "timeout_s":60,
      },
      "expect":{"type":"field_equals","field":"output_verified","value":True},
    }
    return {
      "action":action,
      "output_path":input_path,
      "evidence":{
        "input_path":input_path,
        "output_path":input_path,
        "field":field,
        "product":product,
        "major":major,
        "capability_id":"json.query.jq",
        "extraction_mode":"ANCHORED_SEMVER_FROM_CAPTURED_TEXT",
      }
    }


def _compile_independent_web_release_verification(subgoal, context_paths, registry, root):
    """Compile an independent official-page verification of a structured release claim."""
    lower=subgoal.lower()
    if not re.match(r"^(?:finally\s+)?independently\s+(?:verify|check|confirm)\b",lower):
        return None
    if "without trusting" not in lower and "independent" not in lower:
        return None
    entry=(registry or {}).get("web.release.verify.independent_http")
    if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None

    field_match=re.search(r"\bclaimed\s+([A-Za-z_][A-Za-z0-9_]*)\b",subgoal,re.IGNORECASE)
    if not field_match:
        return None
    version_field=field_match.group(1)

    release_match=re.search(
        r"\b(?:current\s+)?stable\s+([A-Za-z][A-Za-z0-9_.+-]*)\s+(\d+)\s+release\b",
        subgoal,re.IGNORECASE
    )
    if not release_match:
        release_match=re.search(
            r"\b([A-Za-z][A-Za-z0-9_.+-]*)\s+(\d+)\s+(?:stable\s+)?release\b",
            subgoal,re.IGNORECASE
        )
    if not release_match:
        return None
    product=release_match.group(1)
    major=release_match.group(2)

    json_paths=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower()==".json"]
    if not json_paths:
        return None
    result_path=json_paths[-1]

    action={
      "type":"invoke_capability",
      "args":{
        "capability_id":"web.release.verify.independent_http",
        "result_path":result_path,
        "version_field":version_field,
        "product":product,
        "major":major,
        "timeout_s":30,
        "max_bytes":3000000,
      },
      "expect":{"type":"field_equals","field":"verified","value":True},
    }
    return {
      "action":action,
      "evidence":{
        "result_path":result_path,
        "version_field":version_field,
        "product":product,
        "major":major,
        "capability_id":"web.release.verify.independent_http",
        "producer_independent_verifier":True,
      }
    }


def _compile_browser_result_record_projection(subgoal, context_paths, root):
    """Compile a deterministic projection from a verified browser result JSON.

    Expected shape: create OUTPUT.json containing a top-level COLLECTION object
    with exactly one record named ID whose status is CONSTANT and whose listed
    fields come from the browser result.
    """
    m=re.match(
        r"^create\s+([^\s]+\.json)\s+containing\s+a\s+top-level\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)\s+object\s+with\s+exactly\s+one\s+record\s+named\s+"
        r"([A-Za-z0-9_.-]+)\s+whose\s+status\s+is\s+([A-Z][A-Z0-9_]{3,})\s+"
        r"and\s+whose\s+(.+?)\s+values\s+come\s+from\s+the\s+browser\s+result$",
        str(subgoal or "").strip(),re.IGNORECASE
    )
    if not m:
        return None
    output_path=m.group(1).strip(" .,:;")
    collection=m.group(2)
    record_id=m.group(3)
    status=m.group(4).upper()
    raw_fields=re.sub(r"\s+and\s+",", ",m.group(5),flags=re.IGNORECASE)
    fields=[x.strip(" .,:;") for x in raw_fields.split(",") if x.strip(" .,:;")]
    if not fields or len(fields)>32 or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",f) for f in fields):
        return None
    json_context=[
        str(p) for p in context_paths
        if pathlib.Path(str(p)).suffix.lower()==".json" and str(p)!=output_path
    ]
    if not json_context:
        return None
    source_path=json_context[-1]
    action={
      "type":"project_browser_result_json",
      "args":{
        "source_path":source_path,
        "output_path":output_path,
        "collection":collection,
        "record_id":record_id,
        "constants":{"status":status},
        "fields":fields,
      },
      "expect":{"type":"field_equals","field":"verified","value":True},
    }
    return {
      "action":action,
      "output_path":output_path,
      "evidence":{
        "source_path":source_path,
        "output_path":output_path,
        "collection":collection,
        "record_id":record_id,
        "constant_status":status,
        "projected_fields":fields,
        "mode":"NATIVE_TYPED_BROWSER_RESULT_PROJECTION",
      }
    }


def _select_text_artifact_capability(fragment, registry):
    ranked=[]
    for cid,entry in sorted((registry or {}).items()):
        if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
            continue
        template=entry.get("action_template")
        if not isinstance(template,dict):
            continue
        placeholders=set(_placeholders(template))
        if not {"text","output_path"}.issubset(placeholders):
            continue
        score,specificity,evidence=_score(fragment,cid,entry)
        if score>0:
            ranked.append((score,specificity,cid,entry,evidence))
    ranked.sort(key=lambda x:(-x[0],-x[1],x[2]))
    if not ranked:
        return None
    best=ranked[0]
    if len(ranked)>1 and ranked[1][0]==best[0] and ranked[1][1]==best[1]:
        return None
    return {
      "capability_id":best[2],
      "entry":best[3],
      "score":best[0],
      "specificity":best[1],
      "match_evidence":best[4],
    }


def _fanout_kind_label(description):
    text=str(description or "").lower()
    if "qr" in text:
        return "QR"
    if "128" in text:
        return "CODE128"
    label=re.sub(r"[^A-Za-z0-9]+","_",str(description or "")).strip("_").upper()
    return label or "ARTIFACT"


def _compile_bounded_loop_goal(goal,clauses,registry,root):
    if len(clauses)!=5:
        return None
    browser=(registry or {}).get("web.browser.rendered.capture.chromedriver")
    if not isinstance(browser,dict) or browser.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    m0=re.match(
      r"^open\s+(https?://[^\s,]+)\s+in\s+a\s+rendered\s+browser\s+repeatedly,\s+no\s+more\s+than\s+(\d+)\s+times$",
      clauses[0],re.IGNORECASE)
    m1=re.match(r"^after\s+each\s+result,\s+inspect\s+the\s+([A-Za-z_][A-Za-z0-9_]*)$",clauses[1],re.IGNORECASE)
    m2=re.match(
      r"^finish\s+when\s+its\s+first\s+hexadecimal\s+character\s+is\s+in\s+([0-9a-fA-F,]+),\s+otherwise\s+continue\s+until\s+attempt\s+(\d+)$",
      clauses[2],re.IGNORECASE)
    m3=re.match(
      r"^save\s+every\s+observed\s+result\s+under\s+([^\s]+)\s+and\s+save\s+([^\s]+\.json)\s+with\s+status,\s*attempts,\s*matched,\s*selected_uuid,\s*and\s*selected_attempt$",
      clauses[3],re.IGNORECASE)
    m4=re.match(r"^independently\s+verify\s+the\s+saved\s+trace\s+and\s+stopping\s+decision$",clauses[4],re.IGNORECASE)
    if not m0 or not m1 or not m2 or not m3 or not m4:
        return None
    max_attempts=int(m0.group(2))
    if max_attempts!=int(m2.group(2)) or max_attempts<1 or max_attempts>64:
        return None
    url=m0.group(1).rstrip(".,;:!?")
    value_key=m1.group(1).lower()
    match_chars="".join(x.strip().lower() for x in m2.group(1).split(",") if x.strip())
    if not re.fullmatch(r"[0-9a-f]+",match_chars):
        return None
    attempts_dir=m3.group(1).strip(" .,:;")
    result_path=m3.group(2).strip(" .,:;")
    repeated=_render_template(
      browser["action_template"],
      {"url":url,"screenshot_path":"__ATTEMPT_SCREENSHOT_PATH__","result_path":"__ATTEMPT_RESULT_PATH__"}
    )
    loop={"type":"invoke_capability_until","args":{
      "action":repeated,"attempts_dir":attempts_dir,"result_path":result_path,
      "max_attempts":max_attempts,"value_key":value_key,"match_chars":match_chars
    },"expect":{"type":"field_equals","field":"output_verified","value":True}}
    verify={"type":"assert_runtime_bounded_loop_trace","args":{
      "attempts_dir":attempts_dir,"result_path":result_path,
      "max_attempts":max_attempts,"value_key":value_key,"match_chars":match_chars
    },"expect":{"type":"field_equals","field":"verified","value":True}}
    return {
      "schema":"PROJECT_BRAIN_COMPILED_COMPOUND_GOAL_V1",
      "compiler_mode":"DETERMINISTIC_BOUNDED_RUNTIME_LOOP_PLAN",
      "clauses":clauses,
      "compiled_parts":[
        {"index":0,"subgoal":clauses[0],"mode":"BOUNDED_REPEATED_VERIFIED_CAPABILITY","selected_capability":"web.browser.rendered.capture.chromedriver","url":url,"max_attempts":max_attempts},
        {"index":1,"subgoal":clauses[1],"mode":"DEFERRED_RUNTIME_VALUE_READ","value_key":value_key},
        {"index":2,"subgoal":clauses[2],"mode":"RUNTIME_LOOP_STOP_CONDITION","match_chars":match_chars,"max_attempts":max_attempts},
        {"index":3,"subgoal":clauses[3],"mode":"RUNTIME_LOOP_TRACE_AND_RESULT_SPEC","attempts_dir":attempts_dir,"result_path":result_path},
        {"index":4,"subgoal":clauses[4],"mode":"INDEPENDENT_RUNTIME_LOOP_TRACE_VERIFICATION","attempts_dir":attempts_dir,"result_path":result_path}
      ],
      "controller_actions":[loop,verify,{"type":"finish","args":{"summary":"COMPOUND_GOAL_COMPLETE"}}],
      "finish_summary":"COMPOUND_GOAL_COMPLETE"
    }


def _compile_multi_source_reduce_goal(goal,clauses,registry,root):
    if len(clauses)!=5:
        return None
    browser=(registry or {}).get("web.browser.rendered.capture.chromedriver")
    xcreate=(registry or {}).get("xlsx.table.create_from_json_records")
    xverify=(registry or {}).get("xlsx.table.verify_against_json_records")
    if any(not isinstance(x,dict) or x.get("status")!="VERIFIED_BOUND_CAPABILITY" for x in (browser,xcreate,xverify)):
        return None

    def source(clause):
        urls=re.findall(r"https?://[^\s,]+",clause)
        paths=[raw for raw,_ in _repo_paths(clause,root)]
        png=[p for p in paths if pathlib.Path(p).suffix.lower()==".png"]
        js=[p for p in paths if pathlib.Path(p).suffix.lower()==".json"]
        if len(urls)!=1 or len(png)!=1 or len(js)!=1:
            return None
        url=urls[0].rstrip(".,;:!?")
        tail=url.split("?",1)[0].rstrip("/").rsplit("/",1)[-1].lower()
        entity=tail[:-1] if tail.endswith("s") and not tail.endswith("ss") else tail
        action=_render_template(browser["action_template"],{"url":url,"screenshot_path":png[0],"result_path":js[0]})
        return {"entity":entity,"url":url,"json":js[0],"action":action}

    s0=source(clauses[0]); s1=source(clauses[1])
    if s0 is None or s1 is None or s0["entity"]==s1["entity"]:
        return None
    by={s0["entity"]:s0,s1["entity"]:s1}

    rm=re.match(
      r"^using\s+both\s+live\s+results,\s+create\s+([^\s]+\.json)\s+containing\s+exactly\s+one\s+record\s+per\s+live\s+(\w+)\s+with\s+(.+?),\s+where\s+(\w+)\s+is\s+the\s+number\s+of\s+live\s+(\w+)\s+whose\s+(\w+)\s+equals\s+that\s+(\w+)'s\s+(\w+)$",
      clauses[2],re.IGNORECASE)

    summary=None
    dim_entity=None
    fields=None
    count_field=None
    fact_entity=None
    fact_key=None
    dim_key=None
    if rm:
        summary=rm.group(1).strip(" .,:;")
        dim_entity=rm.group(2).lower()
        fields=[x.strip(" .,:;").lower() for x in re.sub(r"\s+and\s+",",",rm.group(3),flags=re.I).split(",") if x.strip(" .,:;")]
        count_field=rm.group(4).lower()
        fact_entity=rm.group(5).lower()
        if fact_entity.endswith("s") and not fact_entity.endswith("ss"):
            fact_entity=fact_entity[:-1]
        fact_key=rm.group(6)
        if rm.group(7).lower()!=dim_entity:
            return None
        dim_key=rm.group(8)
    else:
        semantic=str(clauses[2] or "").strip()
        paths=[raw for raw,_ in _repo_paths(semantic,root) if pathlib.Path(raw).suffix.lower()==".json"]
        row=(re.search(r"\bone\s+(?:row|record)\s+(?:for\s+)?(?:each|per)\s+(?:observed|live)?\s*(\w+)\b",semantic,re.I) or re.search(r"\beach\s+(\w+)\s+has\s+a\s+single\s+summary\s+entry\b",semantic,re.I) or re.search(r"\bone\s+summary\s+(?:row|entry|record)\s+per\s+(\w+)\b",semantic,re.I))
        relation=re.search(r"\b(\w+)\.(\w+)\s*(?:=|equals|matching|matches)\s*(\w+)\.(\w+)\b",semantic,re.I)
        count=(re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\s+(?:equal\s+to|equals|is)\s+(?:how\s+many|the\s+number\s+of)\b",semantic,re.I) or re.search(r"\bderive\s+([A-Za-z_][A-Za-z0-9_]*)\s+by\s+counting\b",semantic,re.I))
        field_segment=(re.search(r"\b(?:carrying|with)\s+(.+?)(?:,\s*(?:plus|where)|\s+where\b)",semantic,re.I) or re.search(r"\bcontaining\s+(.+?)(?:;|\.|$)",semantic,re.I))
        if len(paths)!=1 or not row or not relation or not count:
            return None
        summary=paths[0]
        dim_entity=row.group(1).lower()
        if dim_entity.endswith("s") and not dim_entity.endswith("ss"):
            dim_entity=dim_entity[:-1]
        left_entity,left_key,right_entity,right_key=relation.group(1).lower(),relation.group(2),relation.group(3).lower(),relation.group(4)
        if left_entity.endswith("s") and not left_entity.endswith("ss"):
            left_entity=left_entity[:-1]
        if right_entity.endswith("s") and not right_entity.endswith("ss"):
            right_entity=right_entity[:-1]
        if right_entity==dim_entity:
            fact_entity,fact_key,dim_key=left_entity,left_key,right_key
        elif left_entity==dim_entity:
            fact_entity,fact_key,dim_key=right_entity,right_key,left_key
        else:
            return None
        count_field=count.group(1).lower()
        fields=[]
        if field_segment:
            cleaned=re.sub(r"\s+and\s+",",",field_segment.group(1),flags=re.I)
            fields=[x.strip(" .,:;").lower() for x in cleaned.split(",") if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",x.strip(" .,:;"))]
        output_id=dim_entity+"_id"
        for required in (output_id,count_field):
            if required not in fields:
                fields.append(required)

    xm=re.match(
      r"^create\s+([^\s]+\.xlsx)\s+from\s+([^\s]+\.json)\s+with\s+columns\s+(.+)$",
      clauses[3],re.IGNORECASE)
    if not xm:
        alt=(
            re.match(
              r"^turn\s+([^\s]+\.json)\s+into\s+([^\s]+\.xlsx)\s+using\s+(?:the\s+)?columns\s+(.+)$",
              clauses[3],re.IGNORECASE)
            or re.match(
              r"^export\s+([^\s]+\.json)\s+as\s+([^\s]+\.xlsx)\s+with\s+(.+?)\s+as\s+(?:the\s+)?table\s+columns$",
              clauses[3],re.IGNORECASE)
        )
        if alt:
            class _X:
                def __init__(self,m): self.m=m
                def group(self,n):
                    return {1:self.m.group(2),2:self.m.group(1),3:self.m.group(3)}[n]
            xm=_X(alt)
    verify_text=str(clauses[4] or "").lower()
    vm=(
      bool(re.match(r"^independently\s+reread\s+both\s+live\s+source\s+results,\s+the\s+summary\s+json,\s+and\s+the\s+xlsx\s+and\s+verify\b",clauses[4],re.IGNORECASE))
      or (
        ("cross-check" in verify_text or "cross check" in verify_text or "validate" in verify_text)
        and ("json" in verify_text or "summary" in verify_text)
        and ("workbook" in verify_text or "spreadsheet" in verify_text or "xlsx" in verify_text)
        and ("count" in verify_text or "counts" in verify_text or "totals" in verify_text)
        and ("source" in verify_text or "dataset" in verify_text)
      )
    )
    if not xm or not vm:
        return None
    if dim_entity not in by or fact_entity not in by:
        return None
    output_id=dim_entity+"_id"
    if output_id not in fields or count_field not in fields:
        return None
    copy_fields=[f for f in fields if f not in {output_id,count_field}]
    xlsx=xm.group(1).strip(" .,:;")
    cols=[x.strip(" .,:;").lower() for x in re.sub(r"\s+and\s+",",",xm.group(3),flags=re.I).split(",") if x.strip(" .,:;")]
    if xm.group(2).strip(" .,:;")!=summary or cols!=fields:
        return None

    dim=by[dim_entity]; fact=by[fact_entity]
    reduce_action={"type":"aggregate_runtime_json_arrays","args":{
      "dimension_path":dim["json"],"fact_path":fact["json"],
      "dimension_key":dim_key,"fact_key":fact_key,
      "output_path":summary,"output_id_field":output_id,
      "copy_fields":copy_fields,"count_field":count_field
    },"expect":{"type":"field_equals","field":"output_verified","value":True}}
    verify_reduce={"type":"assert_runtime_json_aggregate","args":{
      "dimension_path":dim["json"],"fact_path":fact["json"],
      "summary_path":summary,"dimension_key":dim_key,"fact_key":fact_key,
      "output_id_field":output_id,"copy_fields":copy_fields,"count_field":count_field
    },"expect":{"type":"field_equals","field":"verified","value":True}}
    create=_render_template(xcreate["action_template"],{"goal":clauses[3],"json_path":summary,"output_path":xlsx})
    verify_xlsx=_render_template(xverify["action_template"],{"goal":clauses[4],"json_path":summary,"xlsx_path":xlsx})
    parts=[
      {"index":0,"subgoal":clauses[0],"mode":"VERIFIED_CAPABILITY","selected_capability":"web.browser.rendered.capture.chromedriver"},
      {"index":1,"subgoal":clauses[1],"mode":"VERIFIED_CAPABILITY","selected_capability":"web.browser.rendered.capture.chromedriver"},
      {"index":2,"subgoal":clauses[2],"mode":"NATIVE_RUNTIME_GROUP_REDUCE","dimension_key":dim_key,"fact_key":fact_key,"output_path":summary},
      {"index":3,"subgoal":clauses[3],"mode":"VERIFIED_CAPABILITY","selected_capability":"xlsx.table.create_from_json_records","inputs":{"json_path":summary,"output_path":xlsx}},
      {"index":4,"subgoal":clauses[4],"mode":"INDEPENDENT_MULTI_SOURCE_REDUCE_AND_XLSX_VERIFICATION","summary_path":summary,"xlsx_path":xlsx}
    ]
    return {"schema":"PROJECT_BRAIN_COMPILED_COMPOUND_GOAL_V1","compiler_mode":"DETERMINISTIC_MULTI_SOURCE_REDUCE_PLAN","clauses":clauses,"compiled_parts":parts,"controller_actions":[s0["action"],s1["action"],reduce_action,create,verify_reduce,verify_xlsx,{"type":"finish","args":{"summary":"COMPOUND_GOAL_COMPLETE"}}],"finish_summary":"COMPOUND_GOAL_COMPLETE"}


def _compile_multi_source_join_goal(goal,clauses,registry,root):
    if len(clauses)!=6:
        return None
    browser=(registry or {}).get("web.browser.rendered.capture.chromedriver")
    xcreate=(registry or {}).get("xlsx.table.create_from_json_records")
    xverify=(registry or {}).get("xlsx.table.verify_against_json_records")
    if any(not isinstance(x,dict) or x.get("status")!="VERIFIED_BOUND_CAPABILITY" for x in (browser,xcreate,xverify)):
        return None

    def browser_spec(clause):
        urls=re.findall(r"https?://[^\s,]+",clause)
        paths=[raw for raw,_ in _repo_paths(clause,root)]
        png=[p for p in paths if pathlib.Path(p).suffix.lower()==".png"]
        js=[p for p in paths if pathlib.Path(p).suffix.lower()==".json"]
        if len(urls)!=1 or len(png)!=1 or len(js)!=1:
            return None
        url=urls[0].rstrip(".,;:!?")
        tail=url.split("?",1)[0].rstrip("/").rsplit("/",1)[-1].lower()
        entity=tail[:-1] if tail.endswith("s") and not tail.endswith("ss") else tail
        action=_render_template(browser["action_template"],{"url":url,"screenshot_path":png[0],"result_path":js[0]})
        return {"url":url,"entity":entity,"result_path":js[0],"action":action}

    s0=browser_spec(clauses[0]); s1=browser_spec(clauses[1])
    if s0 is None or s1 is None or s0["entity"]==s1["entity"]:
        return None
    by_entity={s0["entity"]:s0,s1["entity"]:s1}

    jm=re.match(
      r"^using\s+both\s+live\s+results,\s+join\s+every\s+live\s+(\w+)\s+to\s+exactly\s+one\s+live\s+(\w+)\s+where\s+(\w+)\s+(\w+)\s+equals\s+(\w+)\s+(\w+),?$",
      clauses[2],re.IGNORECASE)
    om=re.match(
      r"^create\s+([^\s]+\.json)\s+containing\s+exactly\s+one\s+record\s+per\s+live\s+(\w+)\s+with\s+(.+)$",
      clauses[3],re.IGNORECASE)
    xm=re.match(
      r"^create\s+([^\s]+\.xlsx)\s+from\s+([^\s]+\.json)\s+with\s+columns\s+(.+)$",
      clauses[4],re.IGNORECASE)
    vm=re.match(r"^independently\s+reopen\s+both\s+live\s+source\s+results,\s+the\s+joined\s+json,\s+and\s+the\s+xlsx\s+and\s+verify\b",clauses[5],re.IGNORECASE)
    if not jm or not om or not xm or not vm:
        return None
    right_entity,left_entity=jm.group(1).lower(),jm.group(2).lower()
    if jm.group(3).lower()!=right_entity or jm.group(5).lower()!=left_entity:
        return None
    if left_entity not in by_entity or right_entity not in by_entity or om.group(2).lower()!=right_entity:
        return None
    left,right=by_entity[left_entity],by_entity[right_entity]
    right_key,left_key=jm.group(4),jm.group(6)
    joined=om.group(1).strip(" .,:;")
    fields=[x.strip(" .,:;").lower() for x in re.sub(r"\s+and\s+",",",om.group(3),flags=re.I).split(",") if x.strip(" .,:;")]
    xlsx=xm.group(1).strip(" .,:;")
    cols=[x.strip(" .,:;").lower() for x in re.sub(r"\s+and\s+",",",xm.group(3),flags=re.I).split(",") if x.strip(" .,:;")]
    if xm.group(2).strip(" .,:;")!=joined or cols!=fields or not fields:
        return None

    join={"type":"join_runtime_json_arrays","args":{
      "left_path":left["result_path"],"right_path":right["result_path"],
      "left_key":left_key,"right_key":right_key,
      "left_entity":left_entity,"right_entity":right_entity,
      "output_path":joined,"output_fields":fields
    },"expect":{"type":"field_equals","field":"output_verified","value":True}}
    verify_join={"type":"assert_runtime_json_join","args":{
      "left_path":left["result_path"],"right_path":right["result_path"],
      "joined_path":joined,"left_key":left_key,"right_key":right_key,
      "left_entity":left_entity,"right_entity":right_entity,"output_fields":fields
    },"expect":{"type":"field_equals","field":"verified","value":True}}
    create=_render_template(xcreate["action_template"],{"goal":clauses[4],"json_path":joined,"output_path":xlsx})
    verify_xlsx=_render_template(xverify["action_template"],{"goal":clauses[5],"json_path":joined,"xlsx_path":xlsx})
    parts=[
      {"index":0,"subgoal":clauses[0],"mode":"VERIFIED_CAPABILITY","selected_capability":"web.browser.rendered.capture.chromedriver","inputs":{"url":s0["url"],"result_path":s0["result_path"]}},
      {"index":1,"subgoal":clauses[1],"mode":"VERIFIED_CAPABILITY","selected_capability":"web.browser.rendered.capture.chromedriver","inputs":{"url":s1["url"],"result_path":s1["result_path"]}},
      {"index":2,"subgoal":clauses[2],"mode":"NATIVE_RUNTIME_KEY_JOIN","left_key":left_key,"right_key":right_key},
      {"index":3,"subgoal":clauses[3],"mode":"RUNTIME_JOIN_OUTPUT_SPEC","output_path":joined,"output_fields":fields},
      {"index":4,"subgoal":clauses[4],"mode":"VERIFIED_CAPABILITY","selected_capability":"xlsx.table.create_from_json_records","inputs":{"json_path":joined,"output_path":xlsx}},
      {"index":5,"subgoal":clauses[5],"mode":"INDEPENDENT_MULTI_SOURCE_JOIN_AND_XLSX_VERIFICATION","joined_path":joined,"xlsx_path":xlsx}
    ]
    return {"schema":"PROJECT_BRAIN_COMPILED_COMPOUND_GOAL_V1","compiler_mode":"DETERMINISTIC_MULTI_SOURCE_JOIN_PLAN","clauses":clauses,"compiled_parts":parts,"controller_actions":[s0["action"],s1["action"],join,create,verify_join,verify_xlsx,{"type":"finish","args":{"summary":"COMPOUND_GOAL_COMPLETE"}}],"finish_summary":"COMPOUND_GOAL_COMPLETE"}


def _compile_per_item_fallback_goal(goal, clauses, registry, root):
    if len(clauses)!=6:
        return None
    if not re.match(r"^read\s+the\s+live\s+json\s+array\s+from\s+that\s+result$",str(clauses[1] or ""),re.IGNORECASE):
        return None

    first=_compile_single_goal(
        clauses[0],registry,root,
        context_paths=None,future_clauses=clauses[1:]
    )
    if first.get("selected_capability")!="web.browser.rendered.capture.chromedriver":
        return None
    first_entry=registry[first["selected_capability"]]
    first_action=_render_template(first_entry["action_template"],first["inputs"])
    source_path=str(first["inputs"].get("result_path") or "")
    if not source_path:
        return None

    control=re.match(
        r"^for\s+every\s+user\s+returned\s+at\s+runtime,\s+first\s+generate\s+a\s+"
        r"(.+?)\s+image\s+encoding\s+that\s+user's\s+([A-Za-z_][A-Za-z0-9_]*)\s+"
        r"and\s+validate\s+the\s+decoded\s+.+?\s+against\s+that\s+user's\s+"
        r"([A-Za-z_][A-Za-z0-9_]*);\s*if\s+that\s+validation\s+fails,\s+fall\s+back\s+"
        r"for\s+only\s+that\s+user\s+to\s+a\s+(.+?)\s+image\s+encoding\s+that\s+"
        r"user's\s+([A-Za-z_][A-Za-z0-9_]*)$",
        str(clauses[2] or "").strip(),re.IGNORECASE
    )
    if not control:
        return None
    primary_description=control.group(1).strip()
    primary_field=control.group(2).lower()
    validation_field=control.group(3).lower()
    fallback_description=control.group(4).strip()
    fallback_field=control.group(5).lower()
    if validation_field!=fallback_field:
        return None

    output_match=re.match(
        r"^save\s+the\s+final\s+artifact\s+for\s+each\s+user\s+under\s+([^\s,]+)\s+"
        r"using\s+the\s+user's\s+id\s+as\s+the\s+filename,?$",
        str(clauses[3] or "").strip(),re.IGNORECASE
    )
    manifest_match=re.match(
        r"^create\s+([^\s]+\.json)\s+with\s+exactly\s+one\s+record\s+per\s+live\s+"
        r"user\s+containing\s+(.+)$",
        str(clauses[4] or "").strip(),re.IGNORECASE
    )
    verify_match=re.match(
        r"^finally\s+independently\s+decode\s+every\s+final\s+artifact\s+and\s+verify\s+"
        r"it\s+equals\s+that\s+live\s+user's\s+([A-Za-z_][A-Za-z0-9_]*),\s*every\s+"
        r"live\s+user\s+has\s+exactly\s+one\s+final\s+artifact,\s*every\s+primary\s+"
        r".+?\s+validation\s+failed\s+as\s+expected\s+because\s+([A-Za-z_][A-Za-z0-9_]*)\s+"
        r"differs\s+from\s+([A-Za-z_][A-Za-z0-9_]*),\s*used_fallback\s+is\s+true\s+for\s+"
        r"every\s+record,\s*and\s+no\s+extra\s+manifest\s+records\s+exist$",
        str(clauses[5] or "").strip(),re.IGNORECASE
    )
    if not output_match or not manifest_match or not verify_match:
        return None
    if (
        verify_match.group(1).lower()!=validation_field
        or verify_match.group(2).lower()!=primary_field
        or verify_match.group(3).lower()!=validation_field
    ):
        return None

    output_dir=output_match.group(1).strip(" .,:;")
    manifest_path=manifest_match.group(1).strip(" .,:;")
    raw_fields=re.sub(r"\s+and\s+",",",manifest_match.group(2),flags=re.IGNORECASE)
    fields=[x.strip(" .,:;").lower() for x in raw_fields.split(",") if x.strip(" .,:;")]
    required={"id",primary_field,validation_field,"used_fallback","artifact_kind","artifact_path"}
    if set(fields)!=required:
        return None

    primary=_select_text_artifact_capability("generate a "+primary_description+" image",registry)
    fallback=_select_text_artifact_capability("generate a "+fallback_description+" image",registry)
    decoder=(registry or {}).get("image.code.decode.zbarimg")
    if primary is None or fallback is None:
        return None
    if not isinstance(decoder,dict) or decoder.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None

    primary_action=_render_template(
        primary["entry"]["action_template"],
        {"output_path":"__ITEM_OUTPUT_PATH__","text":"__ITEM_FIELD_"+primary_field+"__"}
    )
    fallback_action=_render_template(
        fallback["entry"]["action_template"],
        {"output_path":"__ITEM_OUTPUT_PATH__","text":"__ITEM_FIELD_"+fallback_field+"__"}
    )
    primary_kind=_fanout_kind_label(primary_description)
    fallback_kind=_fanout_kind_label(fallback_description)
    copy_fields=["id",primary_field]
    if validation_field not in copy_fields:
        copy_fields.append(validation_field)

    fanout_action={
      "type":"invoke_capability_fanout",
      "args":{
        "source_path":source_path,
        "manifest_path":manifest_path,
        "copy_fields":copy_fields,
        "output_dir":output_dir,
        "artifact_field":"artifact_path",
        "used_fallback_field":"used_fallback",
        "artifact_kind_field":"artifact_kind",
        "item_fallback":{
          "primary_action":primary_action,
          "fallback_action":fallback_action,
          "primary_validation":{
            "type":"decoded_equals_source_field",
            "decoder_capability":"image.code.decode.zbarimg",
            "expected_source_field":validation_field,
          },
          "primary_kind":primary_kind,
          "fallback_kind":fallback_kind,
        },
      },
      "expect":{"type":"field_equals","field":"output_verified","value":True},
    }
    verifier={
      "type":"assert_runtime_per_item_fallback_decodes",
      "args":{
        "source_path":source_path,
        "manifest_path":manifest_path,
        "expected_source_field":validation_field,
        "primary_source_field":primary_field,
        "artifact_field":"artifact_path",
        "used_fallback_field":"used_fallback",
        "artifact_kind_field":"artifact_kind",
        "fallback_kind":fallback_kind,
        "decoder_capability":"image.code.decode.zbarimg",
      },
      "expect":{"type":"field_equals","field":"verified","value":True},
    }
    return {
      "schema":"PROJECT_BRAIN_COMPILED_COMPOUND_GOAL_V1",
      "compiler_mode":"DETERMINISTIC_PER_ITEM_FALLBACK_FANOUT_PLAN",
      "clauses":clauses,
      "compiled_parts":[
        {"index":0,"subgoal":clauses[0],"mode":"VERIFIED_CAPABILITY",
         "selected_capability":first["selected_capability"],"inputs":first["inputs"],
         "target_effects":first["target_effects"],"score":first["score"]},
        {"index":1,"subgoal":clauses[1],"mode":"DEFERRED_RUNTIME_COLLECTION_READ",
         "source_path":source_path},
        {"index":2,"subgoal":clauses[2],"mode":"RUNTIME_PER_ITEM_FALLBACK",
         "source_path":source_path,"primary_field":primary_field,
         "validation_field":validation_field,
         "primary_capability":primary["capability_id"],
         "fallback_capability":fallback["capability_id"],
         "primary_kind":primary_kind,"fallback_kind":fallback_kind},
        {"index":3,"subgoal":clauses[3],"mode":"RUNTIME_PER_ITEM_FINAL_ARTIFACT_SPEC",
         "output_dir":output_dir},
        {"index":4,"subgoal":clauses[4],"mode":"RUNTIME_PER_ITEM_FALLBACK_MANIFEST_SPEC",
         "manifest_path":manifest_path,"fields":fields},
        {"index":5,"subgoal":clauses[5],"mode":"INDEPENDENT_PER_ITEM_FALLBACK_VERIFICATION",
         "source_path":source_path,"manifest_path":manifest_path,
         "expected_source_field":validation_field,"primary_source_field":primary_field},
      ],
      "controller_actions":[
        first_action,
        fanout_action,
        verifier,
        {"type":"finish","args":{"summary":"COMPOUND_GOAL_COMPLETE"}},
      ],
      "finish_summary":"COMPOUND_GOAL_COMPLETE",
    }


def _compile_runtime_multi_action_fanout(subgoal, context_paths, registry, future_clauses):
    text=str(subgoal or "").strip()
    m=re.match(r"^for\s+every\s+user\s+returned\s+at\s+runtime,\s+(.+)$",text,re.IGNORECASE)
    if not m or len(future_clauses)<2:
        return None
    action_text=m.group(1).strip()
    action_matches=re.findall(
        r"generate\s+a\s+(.+?)\s+image\s+encoding\s+that\s+user's\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)(?=\s+and\s+also\s+generate|$)",
        action_text,re.IGNORECASE
    )
    if len(action_matches)<2 or len(action_matches)>8:
        return None

    output_clause=str(future_clauses[0] or "").strip()
    output_matches=re.findall(
        r"save\s+each\s+(.+?)\s+image\s+under\s+([^\s,]+)\s+using\s+the\s+"
        r"user's\s+id\s+as\s+the\s+filename",
        output_clause,re.IGNORECASE
    )
    if len(output_matches)!=len(action_matches):
        return None

    manifest_clause=str(future_clauses[1] or "").strip()
    mm=re.match(
        r"^create\s+([^\s]+\.json)\s+with\s+exactly\s+one\s+record\s+per\s+"
        r"live\s+user\s+containing\s+(.+)$",
        manifest_clause,re.IGNORECASE
    )
    if not mm:
        return None
    manifest_path=mm.group(1).strip(" .,:;")
    raw_fields=re.sub(r"\s+and\s+",",",mm.group(2),flags=re.IGNORECASE)
    manifest_fields=[x.strip(" .,:;").lower() for x in raw_fields.split(",") if x.strip(" .,:;")]
    if not manifest_fields or len(manifest_fields)>40 or len(set(manifest_fields))!=len(manifest_fields):
        return None
    if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",x) for x in manifest_fields):
        return None

    json_paths=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower()==".json"]
    if not json_paths:
        return None
    source_path=json_paths[-1]

    item_actions=[]
    checks=[]
    selected=[]
    artifact_fields=[]
    for index,((description,source_field),(output_description,output_dir)) in enumerate(zip(action_matches,output_matches)):
        fragment="generate a "+description+" image"
        chosen=_select_text_artifact_capability(fragment,registry)
        if chosen is None:
            return None
        normalized=re.sub(r"[^a-z0-9]+","",output_description.lower())
        artifact_field=normalized+"_path"
        if artifact_field not in manifest_fields:
            # Prefer a unique manifest *_path field sharing a meaningful token.
            candidates=[
              f for f in manifest_fields if f.endswith("_path")
              and (
                normalized in re.sub(r"[^a-z0-9]+","",f.lower())
                or re.sub(r"[^a-z0-9]+","",f.lower().replace("_path","")) in normalized
              )
            ]
            if len(candidates)!=1:
                return None
            artifact_field=candidates[0]
        if artifact_field in artifact_fields:
            return None
        artifact_fields.append(artifact_field)
        rendered=_render_template(
            chosen["entry"]["action_template"],
            {
              "output_path":"__ITEM_OUTPUT_PATH__",
              "text":"__ITEM_FIELD_"+source_field.lower()+"__",
            }
        )
        item_actions.append({
          "name":re.sub(r"[^A-Za-z0-9_]+","_",output_description).strip("_") or ("action_"+str(index)),
          "source_field":source_field.lower(),
          "artifact_field":artifact_field,
          "output_dir":output_dir.strip(" .,:;"),
          "extension":".png",
          "action":rendered,
        })
        checks.append({
          "source_field":source_field.lower(),
          "artifact_field":artifact_field,
        })
        selected.append({
          "description":description,
          "source_field":source_field.lower(),
          "capability_id":chosen["capability_id"],
          "artifact_field":artifact_field,
          "output_dir":output_dir.strip(" .,:;"),
          "score":chosen["score"],
        })

    copy_fields=[f for f in manifest_fields if f not in artifact_fields]
    if "id" not in copy_fields:
        return None
    source_fields={x["source_field"] for x in item_actions}
    if not source_fields.issubset(set(copy_fields)):
        return None

    return {
      "action":{
        "type":"invoke_capability_fanout",
        "args":{
          "source_path":source_path,
          "manifest_path":manifest_path,
          "copy_fields":copy_fields,
          "item_actions":item_actions,
        },
        "expect":{"type":"field_equals","field":"output_verified","value":True},
      },
      "manifest_path":manifest_path,
      "consume_future":2,
      "evidence":{
        "source_path":source_path,
        "manifest_path":manifest_path,
        "copy_fields":copy_fields,
        "item_actions":[
          {
            "name":x["name"],
            "source_field":x["source_field"],
            "artifact_field":x["artifact_field"],
            "output_dir":x["output_dir"],
          } for x in item_actions
        ],
        "checks":checks,
        "selected_capabilities":selected,
      }
    }


def _compile_runtime_multi_action_fanout_verification(subgoal, compiled_parts):
    text=str(subgoal or "").strip()
    if not re.match(
        r"^finally\s+independently\s+decode\s+every\s+generated\b",
        text,re.IGNORECASE
    ):
        return None
    prior=None
    for part in reversed(compiled_parts or []):
        if isinstance(part,dict) and part.get("mode")=="RUNTIME_MULTI_ACTION_FANOUT":
            prior=part
            break
    if prior is None:
        return None
    return {
      "action":{
        "type":"assert_runtime_fanout_artifacts_decode",
        "args":{
          "source_path":prior["source_path"],
          "manifest_path":prior["manifest_path"],
          "copy_fields":prior["copy_fields"],
          "checks":prior["checks"],
          "decoder_capability":"image.code.decode.zbarimg",
        },
        "expect":{"type":"field_equals","field":"verified","value":True},
      },
      "evidence":{
        "source_path":prior["source_path"],
        "manifest_path":prior["manifest_path"],
        "copy_fields":prior["copy_fields"],
        "checks":prior["checks"],
        "decoder_capability":"image.code.decode.zbarimg",
      }
    }


def _compile_multi_action_fanout_goal(goal, clauses, registry, root):
    if len(clauses)!=6:
        return None
    if not re.match(r"^read\s+the\s+live\s+json\s+array\s+from\s+that\s+result$",clauses[1],re.IGNORECASE):
        return None
    first=_compile_single_goal(
        clauses[0],registry,root,
        context_paths=None,future_clauses=clauses[1:]
    )
    first_entry=registry[first["selected_capability"]]
    first_action=_render_template(first_entry["action_template"],first["inputs"])
    context_paths=[
        str(v) for k,v in first["inputs"].items()
        if isinstance(k,str) and k.endswith("_path")
        and isinstance(v,str) and pathlib.Path(v).suffix
    ]
    fanout=_compile_runtime_multi_action_fanout(
        clauses[2],context_paths,registry,clauses[3:]
    )
    if fanout is None:
        return None
    fanout_part={"mode":"RUNTIME_MULTI_ACTION_FANOUT",**fanout["evidence"]}
    verify=_compile_runtime_multi_action_fanout_verification(
        clauses[-1],[fanout_part]
    )
    if verify is None:
        return None
    return {
      "schema":"PROJECT_BRAIN_COMPILED_COMPOUND_GOAL_V1",
      "compiler_mode":"DETERMINISTIC_MULTI_ACTION_FANOUT_PLAN",
      "clauses":clauses,
      "compiled_parts":[
        {"index":0,"subgoal":clauses[0],"mode":"VERIFIED_CAPABILITY",
         "selected_capability":first["selected_capability"],"inputs":first["inputs"],
         "target_effects":first["target_effects"],"score":first["score"]},
        {"index":1,"subgoal":clauses[1],"mode":"DEFERRED_RUNTIME_COLLECTION_READ",
         "source_path":fanout["evidence"]["source_path"]},
        {"index":2,"subgoal":clauses[2],"mode":"RUNTIME_MULTI_ACTION_FANOUT",
         **fanout["evidence"]},
        {"index":3,"subgoal":clauses[3],"mode":"RUNTIME_MULTI_ACTION_OUTPUT_SPEC",
         "item_actions":fanout["evidence"]["item_actions"]},
        {"index":4,"subgoal":clauses[4],"mode":"RUNTIME_MULTI_ACTION_MANIFEST_SPEC",
         "manifest_path":fanout["manifest_path"],"copy_fields":fanout["evidence"]["copy_fields"]},
        {"index":5,"subgoal":clauses[5],"mode":"INDEPENDENT_RUNTIME_MULTI_ACTION_FANOUT_VERIFICATION",
         **verify["evidence"]},
      ],
      "controller_actions":[
        first_action,
        fanout["action"],
        verify["action"],
        {"type":"finish","args":{"summary":"COMPOUND_GOAL_COMPLETE"}},
      ],
      "finish_summary":"COMPOUND_GOAL_COMPLETE",
    }


def _compile_runtime_dynamic_fanout(subgoal, context_paths, registry, future_clauses):
    text=str(subgoal or "").strip()
    m=re.match(
        r"^for\s+every\s+user\s+returned\s+at\s+runtime,\s+if\s+that\s+user's\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)\s+length\s+is\s+at\s+most\s+(\d+)\s+characters\s+"
        r"generate\s+a\s+qr\s+code\s+image\s+encoding\s+that\s+username;?\s*otherwise\s+"
        r"generate\s+a\s+code\s+128\s+barcode\s+image\s+encoding\s+that\s+username$",
        text,re.IGNORECASE
    )
    if not m or len(future_clauses)<2:
        return None
    out_match=re.match(
        r"^save\s+each\s+selected\s+image\s+under\s+([^\s,]+)\s+using\s+the\s+user's\s+id\s+as\s+the\s+filename,?$",
        str(future_clauses[0] or "").strip(),re.IGNORECASE
    )
    manifest_match=re.match(
        r"^create\s+([^\s]+\.json)\s+with\s+exactly\s+one\s+record\s+per\s+live\s+user\s+"
        r"containing\s+id,\s*username,\s*selected\s+capability\s+kind,\s*and\s+artifact\s+path$",
        str(future_clauses[1] or "").strip(),re.IGNORECASE
    )
    if not out_match or not manifest_match:
        return None
    qr=(registry or {}).get("image.qr.generate.qrencode")
    barcode=(registry or {}).get("auto.apt.zint")
    if not isinstance(qr,dict) or qr.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    if not isinstance(barcode,dict) or barcode.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    json_paths=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower()==".json"]
    if not json_paths:
        return None
    value_field=m.group(1).lower()
    output_dir=out_match.group(1).strip(" .,:;")
    manifest_path=manifest_match.group(1).strip(" .,:;")
    return {
      "action":{
        "type":"invoke_capability_fanout",
        "args":{
          "source_path":json_paths[-1],
          "value_field":value_field,
          "max_length":int(m.group(2)),
          "match_action":_render_template(qr["action_template"],{"output_path":"__ITEM_OUTPUT_PATH__","text":"__ITEM_VALUE__"}),
          "other_action":_render_template(barcode["action_template"],{"output_path":"__ITEM_OUTPUT_PATH__","text":"__ITEM_VALUE__"}),
          "match_kind":"QR",
          "other_kind":"CODE128",
          "output_dir":output_dir,
          "manifest_path":manifest_path,
        },
        "expect":{"type":"field_equals","field":"output_verified","value":True},
      },
      "manifest_path":manifest_path,
      "consume_future":2,
      "evidence":{
        "source_path":json_paths[-1],"value_field":value_field,"max_length":int(m.group(2)),
        "match_kind":"QR","other_kind":"CODE128","output_dir":output_dir,"manifest_path":manifest_path,
      }
    }


def _compile_runtime_dynamic_fanout_verification(subgoal, compiled_parts):
    if not re.match(
        r"^finally\s+independently\s+decode\s+every\s+generated\s+image\s+and\s+verify\s+each\s+decoded\s+value\s+equals\s+that\s+live\s+user's\s+username,\s*every\s+live\s+user\s+has\s+exactly\s+one\s+artifact,\s*and\s+no\s+extra\s+manifest\s+records\s+exist$",
        str(subgoal or "").strip(),re.IGNORECASE
    ):
        return None
    prior=None
    for part in reversed(compiled_parts or []):
        if isinstance(part,dict) and part.get("mode")=="RUNTIME_DYNAMIC_CAPABILITY_FANOUT":
            prior=part
            break
    if prior is None:
        return None
    return {
      "action":{
        "type":"assert_runtime_fanout_decodes",
        "args":{
          "source_path":prior["source_path"],
          "manifest_path":prior["manifest_path"],
          "value_field":prior["value_field"],
          "max_length":prior["max_length"],
          "match_kind":prior["match_kind"],
          "other_kind":prior["other_kind"],
        },
        "expect":{"type":"field_equals","field":"verified","value":True},
      },
      "evidence":{
        "source_path":prior["source_path"],
        "manifest_path":prior["manifest_path"],
        "decoder_capability":"image.code.decode.zbarimg",
      }
    }


def _compile_live_collection_read(subgoal, context_paths):
    if not re.match(r"^read\s+the\s+live\s+json\s+array\s+from\s+that\s+result$",str(subgoal or "").strip(),re.IGNORECASE):
        return None
    json_paths=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower()==".json"]
    if not json_paths:
        return None
    return {"source_path":json_paths[-1]}


def _compile_live_collection_map(subgoal, context_paths, registry):
    text=str(subgoal or "").strip()
    m=re.match(
        r"^for\s+every\s+([A-Za-z_][A-Za-z0-9_-]*)\s+returned\s+at\s+runtime,\s+"
        r"create\s+([^\s]+\.json)\s+containing\s+exactly\s+one\s+record\s+with\s+that\s+"
        r"(?:user|item)'s\s+(.+?),\s+and\s+bucket\s+equal\s+to\s+([A-Za-z_]+)\s+when\s+the\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)\s+length\s+is\s+at\s+most\s+(\d+)\s+characters\s+and\s+"
        r"([A-Za-z_]+)\s+otherwise$",
        text,re.IGNORECASE
    )
    if not m:
        return None
    jq=(registry or {}).get("json.query.jq")
    if not isinstance(jq,dict) or jq.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    json_paths=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower()==".json"]
    if not json_paths:
        return None
    source_path=json_paths[-1]
    output_path=m.group(2).strip(" .,:;")
    raw_fields=re.sub(r"\s+and\s+",",",m.group(3),flags=re.IGNORECASE)
    fields=[x.strip(" .,:;").lower() for x in raw_fields.split(",") if x.strip(" .,:;")]
    measured=m.group(5).lower()
    max_length=int(m.group(6))
    short_label=m.group(4).upper()
    long_label=m.group(7).upper()
    if not fields or measured not in fields or len(fields)>24:
        return None
    if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",f) for f in fields):
        return None
    pairs=",".join(json.dumps(f)+":."+f for f in fields)
    filt=(
      '(.observed_text | fromjson) '
      '| map({'+pairs+','
      '"bucket":(if (.'+measured+' | tostring | length) <= '+str(max_length)+' '
      'then '+json.dumps(short_label)+' else '+json.dumps(long_label)+' end)})'
    )
    return {
      "action":{
        "type":"invoke_capability",
        "args":{
          "capability_id":"json.query.jq",
          "input_path":source_path,
          "filter":filt,
          "output_path":output_path,
          "raw_output":False,
          "require_nonempty":True,
          "timeout_s":60,
        },
        "expect":{"type":"field_equals","field":"output_verified","value":True},
      },
      "output_path":output_path,
      "evidence":{
        "source_path":source_path,
        "output_path":output_path,
        "copy_fields":fields,
        "measured_field":measured,
        "max_length":max_length,
        "short_label":short_label,
        "long_label":long_label,
      }
    }


def _compile_live_collection_verification(subgoal, compiled_parts):
    text=str(subgoal or "").strip()
    if not re.match(
        r"^finally\s+independently\s+reread\s+both\s+files\s+and\s+verify\s+the\s+output\s+contains\s+exactly\s+one\s+record\s+per\s+live\b",
        text,re.IGNORECASE
    ):
        return None
    prior=None
    for part in reversed(compiled_parts or []):
        if isinstance(part,dict) and part.get("mode")=="VERIFIED_RUNTIME_COLLECTION_MAP":
            prior=part
            break
    if prior is None:
        return None
    return {
      "action":{
        "type":"assert_collection_length_bucket",
        "args":{
          "source_path":prior["source_path"],
          "output_path":prior["output_path"],
          "copy_fields":prior["copy_fields"],
          "measured_field":prior["measured_field"],
          "label_field":"bucket",
          "max_length":prior["max_length"],
          "short_label":prior["short_label"],
          "long_label":prior["long_label"],
        },
        "expect":{"type":"field_equals","field":"verified","value":True},
      },
      "evidence":{
        "source_path":prior["source_path"],
        "output_path":prior["output_path"],
        "copy_fields":prior["copy_fields"],
        "measured_field":prior["measured_field"],
        "max_length":prior["max_length"],
        "short_label":prior["short_label"],
        "long_label":prior["long_label"],
      }
    }


def _compile_runtime_capability_choice(subgoal, context_paths, registry):
    text=str(subgoal or "").strip()
    m=re.match(
        r"^if\s+its\s+first\s+hexadecimal\s+character\s+is\s+one\s+of\s+([0-9a-fA-F,]+),?\s+"
        r"generate\s+a\s+qr\s+code\s+image\s+for\s+the\s+observed\s+uuid\s+and\s+save\s+it\s+to\s+"
        r"([^\s;]+\.png);?\s*otherwise\s+generate\s+a\s+code\s+128\s+barcode\s+image\s+for\s+the\s+"
        r"same\s+observed\s+uuid\s+and\s+save\s+it\s+to\s+([^\s]+\.png)$",
        text,re.IGNORECASE
    )
    if not m:
        return None
    qr=(registry or {}).get("image.qr.generate.qrencode")
    barcode=(registry or {}).get("auto.apt.zint")
    if not isinstance(qr,dict) or qr.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    if not isinstance(barcode,dict) or barcode.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    json_paths=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower()==".json"]
    if not json_paths:
        return None
    source_path=json_paths[-1]
    match_chars="".join(x.strip().lower() for x in m.group(1).split(",") if x.strip())
    qr_path=m.group(2).strip(" .,:;")
    barcode_path=m.group(3).strip(" .,:;")
    if not match_chars or not re.fullmatch(r"[0-9a-f]+",match_chars):
        return None
    qr_action=_render_template(qr["action_template"],{
      "output_path":qr_path,
      "text":"__RUNTIME_VALUE__",
    })
    barcode_action=_render_template(barcode["action_template"],{
      "output_path":barcode_path,
      "text":"__RUNTIME_VALUE__",
    })
    return {
      "action":{
        "type":"invoke_capability_by_runtime_value",
        "args":{
          "source_path":source_path,
          "value_key":"uuid",
          "match_chars":match_chars,
          "match_action":qr_action,
          "other_action":barcode_action,
        },
        "expect":{"type":"field_equals","field":"output_verified","value":True},
      },
      "evidence":{
        "source_path":source_path,
        "value_key":"uuid",
        "match_chars":match_chars,
        "match_capability":"image.qr.generate.qrencode",
        "other_capability":"auto.apt.zint",
        "match_path":qr_path,
        "other_path":barcode_path,
      }
    }


def _compile_runtime_capability_choice_verification(subgoal, compiled_parts):
    if not re.match(
        r"^finally\s+independently\s+verify\s+that\s+the\s+artifact\s+selected\s+by\s+the\s+live\s+branch\s+decodes\s+to\s+the\s+observed\s+uuid$",
        str(subgoal or "").strip(),re.IGNORECASE
    ):
        return None
    prior=None
    for part in reversed(compiled_parts or []):
        if isinstance(part,dict) and part.get("mode")=="RUNTIME_SELECTED_VERIFIED_CAPABILITY":
            prior=part
            break
    if prior is None:
        return None
    return {
      "action":{
        "type":"assert_runtime_selected_code_decodes",
        "args":{
          "source_path":prior["source_path"],
          "value_key":prior["value_key"],
          "match_chars":prior["match_chars"],
          "match_path":prior["match_path"],
          "other_path":prior["other_path"],
        },
        "expect":{"type":"field_equals","field":"verified","value":True},
      },
      "evidence":{
        "source_path":prior["source_path"],
        "match_chars":prior["match_chars"],
        "match_path":prior["match_path"],
        "other_path":prior["other_path"],
        "decoder_capability":"image.code.decode.zbarimg",
      }
    }


def _compile_live_uuid_conditional(subgoal, context_paths, registry):
    text=str(subgoal or "").strip()
    m=re.match(
        r"^if\s+its\s+first\s+hexadecimal\s+character\s+is\s+one\s+of\s+([0-9a-fA-F,]+)\s+"
        r"create\s+([^\s]+\.json)\s+with\s+uuid\s+equal\s+to\s+the\s+observed\s+uuid\s+and\s+"
        r"bucket\s+equal\s+to\s+([A-Za-z_]+);?\s*otherwise\s+create\s+it\s+with\s+the\s+same\s+"
        r"observed\s+uuid\s+and\s+bucket\s+equal\s+to\s+([A-Za-z_]+)$",
        text,re.IGNORECASE
    )
    if not m:
        return None
    jq=(registry or {}).get("json.query.jq")
    if not isinstance(jq,dict) or jq.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    json_paths=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower()==".json"]
    if not json_paths:
        return None
    source_path=json_paths[-1]
    output_path=m.group(2).strip(" .,:;")
    low_chars="".join(x.strip().lower() for x in m.group(1).split(",") if x.strip())
    low_bucket=m.group(3).upper()
    high_bucket=m.group(4).upper()
    if not low_chars or not re.fullmatch(r"[0-9a-f]+",low_chars):
        return None
    filt=(
      '(.observed_text | fromjson | .uuid) as $u '
      '| {uuid:$u,'
      'bucket:(if ('+json.dumps(low_chars)+' | contains(($u[0:1]|ascii_downcase))) '
      'then '+json.dumps(low_bucket)+' else '+json.dumps(high_bucket)+' end),'
      '_branch:(if ('+json.dumps(low_chars)+' | contains(($u[0:1]|ascii_downcase))) '
      'then "LOW" else "HIGH" end)}'
    )
    return {
      "action":{
        "type":"invoke_capability",
        "args":{
          "capability_id":"json.query.jq",
          "input_path":source_path,
          "filter":filt,
          "output_path":output_path,
          "raw_output":False,
          "require_nonempty":True,
          "timeout_s":60,
        },
        "expect":{"type":"field_equals","field":"output_verified","value":True},
      },
      "output_path":output_path,
      "evidence":{
        "source_path":source_path,"output_path":output_path,
        "low_chars":low_chars,"low_bucket":low_bucket,"high_bucket":high_bucket,
      }
    }


def _compile_live_uuid_verification(subgoal, context_paths, compiled_parts):
    if not re.match(r"^finally\s+independently\s+reread\s+both\s+files\s+and\s+verify\b",str(subgoal or ""),re.IGNORECASE):
        return None
    json_paths=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower()==".json"]
    if len(json_paths)<2:
        return None
    prior=None
    for part in reversed(compiled_parts or []):
        if isinstance(part,dict) and part.get("mode")=="VERIFIED_RUNTIME_CONDITIONAL":
            prior=part
            break
    if prior is None or not prior.get("low_chars"):
        return None
    return {
      "action":{
        "type":"assert_hex_prefix_bucket",
        "args":{
          "source_path":json_paths[-2],
          "classification_path":json_paths[-1],
          "source_key":"uuid",
          "output_value_field":"uuid",
          "bucket_field":"_branch",
          "low_chars":str(prior.get("low_chars")),
        },
        "expect":{"type":"field_equals","field":"verified","value":True},
      },
      "evidence":{"source_path":json_paths[-2],"classification_path":json_paths[-1]}
    }


def _compile_dynamic_fanout_goal(goal, clauses, registry, root):
    if len(clauses)<6:
        return None
    if not re.match(r"^read\s+the\s+live\s+json\s+array\s+from\s+that\s+result$",clauses[1],re.IGNORECASE):
        return None
    first=_compile_single_goal(
        clauses[0],registry,root,
        context_paths=None,future_clauses=clauses[1:]
    )
    first_entry=registry[first["selected_capability"]]
    first_action=_render_template(first_entry["action_template"],first["inputs"])
    context_paths=[
        str(v) for v in first["inputs"].values()
        if isinstance(v,str) and pathlib.Path(v).suffix
    ]
    fanout=_compile_runtime_dynamic_fanout(
        clauses[2],context_paths,registry,clauses[3:]
    )
    if fanout is None:
        return None
    fanout_part={"mode":"RUNTIME_DYNAMIC_CAPABILITY_FANOUT",**fanout["evidence"]}
    context_paths.append(fanout["manifest_path"])
    actions=[first_action,fanout["action"]]
    compiled_parts=[
      {"index":0,"subgoal":clauses[0],"mode":"VERIFIED_CAPABILITY",
       "selected_capability":first["selected_capability"],"inputs":first["inputs"],
       "target_effects":first["target_effects"],"score":first["score"]},
      {"index":1,"subgoal":clauses[1],"mode":"DEFERRED_RUNTIME_COLLECTION_READ",
       "source_path":context_paths[0]},
      {"index":2,"subgoal":clauses[2],"mode":"RUNTIME_DYNAMIC_CAPABILITY_FANOUT",
       **fanout["evidence"]},
      {"index":3,"subgoal":clauses[3],"mode":"RUNTIME_FANOUT_OUTPUT_SPEC",
       "output_dir":fanout["evidence"]["output_dir"]},
      {"index":4,"subgoal":clauses[4],"mode":"RUNTIME_FANOUT_MANIFEST_SPEC",
       "manifest_path":fanout["evidence"]["manifest_path"]},
    ]

    # Clauses 3 and 4 are consumed by the fanout operator as output-dir and
    # manifest specifications. Any clauses after those and before the final
    # fanout verifier are real downstream work and must be compiled, never
    # silently discarded.
    for index in range(5,len(clauses)-1):
        subgoal=clauses[index]
        part=_compile_single_goal(
            subgoal,registry,root,
            context_paths=context_paths,
            future_clauses=clauses[index+1:]
        )
        entry=registry[part["selected_capability"]]
        action=_render_template(entry["action_template"],part["inputs"])
        actions.append(action)
        for key,value in part["inputs"].items():
            if (
                isinstance(key,str) and key.endswith("_path")
                and isinstance(value,str) and pathlib.Path(value).suffix
                and value not in context_paths
            ):
                context_paths.append(value)
        compiled_parts.append({
          "index":index,"subgoal":subgoal,"mode":"VERIFIED_CAPABILITY",
          "selected_capability":part["selected_capability"],"inputs":part["inputs"],
          "target_effects":part["target_effects"],"score":part["score"],
        })

    verify=_compile_runtime_dynamic_fanout_verification(
        clauses[-1],[fanout_part]
    )
    if verify is None:
        return None
    actions.append(verify["action"])
    compiled_parts.append({
      "index":len(clauses)-1,"subgoal":clauses[-1],
      "mode":"INDEPENDENT_RUNTIME_FANOUT_VERIFICATION",**verify["evidence"],
    })
    actions.append({"type":"finish","args":{"summary":"COMPOUND_GOAL_COMPLETE"}})
    return {
      "schema":"PROJECT_BRAIN_COMPILED_COMPOUND_GOAL_V1",
      "compiler_mode":"DETERMINISTIC_DYNAMIC_FANOUT_PLAN",
      "clauses":clauses,
      "compiled_parts":compiled_parts,
      "controller_actions":actions,
      "finish_summary":"COMPOUND_GOAL_COMPLETE",
    }


def _compile_runtime_fallback_goal(goal, clauses, registry, root):
    if len(clauses)!=4:
        return None
    # Recognize the control shape before compiling any clause. Specialized
    # compilers must be pure probes on unrelated goals, not throw from an
    # attempted partial interpretation.
    if not re.match(
        r"^if\s+the\s+rendered\s+primary\s+result\s+is\s+not\s+a\s+json\s+array\s+"
        r"containing\s+at\s+least\s+one\s+item,\s+fall\s+back\s+to\s+",
        str(clauses[1] or "").strip(),re.IGNORECASE
    ):
        return None

    primary=_compile_single_goal(
        clauses[0],registry,root,
        context_paths=None,future_clauses=clauses[1:]
    )
    if primary.get("selected_capability")!="web.browser.rendered.capture.chromedriver":
        return None
    primary_entry=registry.get(primary["selected_capability"])
    if not isinstance(primary_entry,dict):
        return None
    primary_action=_render_template(primary_entry["action_template"],primary["inputs"])
    primary_url=str(primary["inputs"].get("url") or "")
    primary_result=str(primary["inputs"].get("result_path") or "")
    if not primary_url or not primary_result:
        return None

    fallback_match=re.match(
        r"^if\s+the\s+rendered\s+primary\s+result\s+is\s+not\s+a\s+json\s+array\s+"
        r"containing\s+at\s+least\s+one\s+item,\s+fall\s+back\s+to\s+"
        r"(https?://[^\s,]+),\s+save\s+a\s+screenshot\s+to\s+([^\s,]+),\s+and\s+"
        r"save\s+the\s+rendered\s+result\s+to\s+([^\s]+\.json)$",
        str(clauses[1] or "").strip(),re.IGNORECASE
    )
    if not fallback_match:
        return None
    fallback_url=fallback_match.group(1).rstrip(".,;:!?")
    fallback_screenshot=fallback_match.group(2).strip(" .,:;")
    fallback_result=fallback_match.group(3).strip(" .,:;")

    decision_match=re.match(
        r"^create\s+([^\s]+\.json)\s+containing\s+primary_url,\s*fallback_url,\s*"
        r"used_fallback,\s*final_url,\s*and\s*item_count$",
        str(clauses[2] or "").strip(),re.IGNORECASE
    )
    if not decision_match:
        return None
    decision_path=decision_match.group(1).strip(" .,:;")

    verify_match=re.match(
        r"^finally\s+independently\s+verify\s+the\s+primary\s+result\s+was\s+not\s+a\s+"
        r"nonempty\s+json\s+array,\s*the\s+fallback\s+result\s+was\s+a\s+nonempty\s+"
        r"json\s+array,\s*used_fallback\s+is\s+true,\s*final_url\s+is\s+the\s+fallback\s+"
        r"url,\s*and\s+item_count\s+equals\s+the\s+fallback\s+array\s+length$",
        str(clauses[3] or "").strip(),re.IGNORECASE
    )
    if not verify_match:
        return None

    browser=(registry or {}).get("web.browser.rendered.capture.chromedriver")
    if not isinstance(browser,dict) or browser.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return None
    fallback_action=_render_template(
        browser["action_template"],
        {
          "url":fallback_url,
          "screenshot_path":fallback_screenshot,
          "result_path":fallback_result,
        }
    )

    fallback_control={
      "type":"invoke_capability_fallback",
      "args":{
        "primary_action":primary_action,
        "fallback_action":fallback_action,
        "primary_postcondition":{
          "type":"json_observed_text_nonempty_array",
          "path":primary_result,
        },
        "fallback_postcondition":{
          "type":"json_observed_text_nonempty_array",
          "path":fallback_result,
        },
        "decision_path":decision_path,
      },
      "expect":{"type":"field_equals","field":"output_verified","value":True},
    }
    independent_verify={
      "type":"assert_runtime_fallback_decision",
      "args":{
        "primary_path":primary_result,
        "fallback_path":fallback_result,
        "decision_path":decision_path,
        "primary_url":primary_url,
        "fallback_url":fallback_url,
      },
      "expect":{"type":"field_equals","field":"verified","value":True},
    }
    return {
      "schema":"PROJECT_BRAIN_COMPILED_COMPOUND_GOAL_V1",
      "compiler_mode":"DETERMINISTIC_RUNTIME_FALLBACK_PLAN",
      "clauses":clauses,
      "compiled_parts":[
        {
          "index":0,"subgoal":clauses[0],
          "mode":"VERIFIED_PRIMARY_CAPABILITY",
          "selected_capability":primary["selected_capability"],
          "inputs":primary["inputs"],
          "target_effects":primary["target_effects"],
          "score":primary["score"],
        },
        {
          "index":1,"subgoal":clauses[1],
          "mode":"RUNTIME_POSTCONDITION_FALLBACK",
          "primary_result_path":primary_result,
          "fallback_result_path":fallback_result,
          "primary_url":primary_url,
          "fallback_url":fallback_url,
          "fallback_capability":"web.browser.rendered.capture.chromedriver",
        },
        {
          "index":2,"subgoal":clauses[2],
          "mode":"RUNTIME_FALLBACK_DECISION_SPEC",
          "decision_path":decision_path,
          "fields":["primary_url","fallback_url","used_fallback","final_url","item_count"],
        },
        {
          "index":3,"subgoal":clauses[3],
          "mode":"INDEPENDENT_RUNTIME_FALLBACK_VERIFICATION",
          "primary_path":primary_result,
          "fallback_path":fallback_result,
          "decision_path":decision_path,
        },
      ],
      "controller_actions":[
        fallback_control,
        independent_verify,
        {"type":"finish","args":{"summary":"COMPOUND_GOAL_COMPLETE"}},
      ],
      "finish_summary":"COMPOUND_GOAL_COMPLETE",
    }


def _literal_atom(raw):
    text=str(raw or "").strip()
    if re.fullmatch(r"-?\d+",text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+",text):
        return float(text)
    if text.lower()=="true":
        return True
    if text.lower()=="false":
        return False
    if text.lower()=="null":
        return None
    return text.strip("\"'")


def _parse_small_count(raw):
    text=str(raw or "").strip().lower()
    if re.fullmatch(r"\d+",text):
        return int(text)
    words={
      "zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,
      "six":6,"seven":7,"eight":8,"nine":9,"ten":10,
      "eleven":11,"twelve":12,"thirteen":13,"fourteen":14,"fifteen":15,
      "sixteen":16,"seventeen":17,"eighteen":18,"nineteen":19,"twenty":20,
    }
    return words.get(text)


def _compile_literal_json_records(subgoal, root):
    text=str(subgoal or "").strip()
    m=re.match(
        r"^create\s+([^\s]+\.json)\s+containing\s+exactly\s+([A-Za-z0-9]+)\s+records?\s+"
        r"with\s+fields\s+(.+?):\s+(.+)$",
        text,re.IGNORECASE
    )
    if not m:
        return None
    output_path=m.group(1).strip(" .,:;")
    expected_count=_parse_small_count(m.group(2))
    if expected_count is None:
        return None
    raw_fields=re.sub(r"\s+and\s+",",",m.group(3),flags=re.IGNORECASE)
    fields=[x.strip(" .,:;") for x in raw_fields.split(",") if x.strip(" .,:;")]
    if (
        not fields or len(fields)>16 or len(set(fields))!=len(fields)
        or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",x) for x in fields)
        or expected_count<0 or expected_count>1000
    ):
        return None
    chunks=[x.strip() for x in re.split(r"\s*;\s*|\s*,\s*",m.group(4)) if x.strip()]
    if len(chunks)!=expected_count:
        return None
    records=[]
    for chunk in chunks:
        if len(fields)==1:
            values=[chunk]
        else:
            values=chunk.split(None,len(fields)-1)
        if len(values)!=len(fields):
            return None
        records.append({field:_literal_atom(value) for field,value in zip(fields,values)})
    return {
      "action":{
        "type":"write_json_records",
        "args":{"output_path":output_path,"fields":fields,"records":records},
        "expect":{"type":"field_equals","field":"verified","value":True},
      },
      "output_path":output_path,
      "evidence":{"output_path":output_path,"fields":fields,"record_count":expected_count},
    }


def _generic_entity_forms(raw):
    value=str(raw or "").strip().lower()
    forms={value}
    if value.endswith("ies") and len(value)>3:
        forms.add(value[:-3]+"y")
    elif value.endswith("s") and not value.endswith("ss"):
        forms.add(value[:-1])
    else:
        forms.add(value+"s")
    return {x for x in forms if x}


def _context_json_for_entity(context_paths,entity):
    forms=_generic_entity_forms(entity)
    matches=[]
    for raw in context_paths or []:
        p=pathlib.Path(str(raw))
        if p.suffix.lower()!=".json":
            continue
        name=re.sub(r"[^a-z0-9]+","",p.stem.lower())
        if any(re.sub(r"[^a-z0-9]+","",form) in name for form in forms):
            matches.append(str(raw))
    return matches[-1] if matches else None


def _parse_scalar_literal(raw):
    text=str(raw or "").strip().strip(" .,:;")
    lower=text.lower()
    if lower=="true":
        return True
    if lower=="false":
        return False
    if lower in {"null","none"}:
        return None
    if re.fullmatch(r"-?\d+",text):
        return int(text)
    if re.fullmatch(r"-?(?:\d+\.\d*|\d*\.\d+)",text):
        return float(text)
    return text.strip("\"'")


def _compile_generic_group_derive_ir(clause,context_paths,root):
    text=str(clause or "").strip()
    head=re.match(
      r"^using\s+both\s+live\s+results,\s+create\s+([^\s]+\.json)\s+containing\s+"
      r"exactly\s+one\s+record\s+per\s+live\s+([A-Za-z_][A-Za-z0-9_]*)\s+with\s+"
      r"(.+?),\s+where\s+(.+)$",
      text,re.IGNORECASE
    )
    if not head:
        return None
    output_path=head.group(1).strip(" .,:;")
    dimension_entity=head.group(2).lower()
    fields=[
      x.strip(" .,:;")
      for x in re.sub(r"\s+and\s+",",",head.group(3),flags=re.IGNORECASE).split(",")
      if x.strip(" .,:;")
    ]
    field_by_lower={}
    for field in fields:
        key=field.lower()
        if key in field_by_lower:
            return None
        field_by_lower[key]=field
    if not fields:
        return None

    semantic=head.group(4)
    relation=re.search(
      r"\b([A-Za-z_][A-Za-z0-9_]*)\s+is\s+the\s+number\s+of\s+live\s+"
      r"([A-Za-z_][A-Za-z0-9_]*)\s+whose\s+([A-Za-z_][A-Za-z0-9_]*)\s+equals\s+"
      r"that\s+([A-Za-z_][A-Za-z0-9_]*)'s\s+([A-Za-z_][A-Za-z0-9_]*)",
      semantic,re.IGNORECASE
    )
    filtered=re.search(
      r"\b([A-Za-z_][A-Za-z0-9_]*)\s+is\s+the\s+number\s+of\s+those\s+"
      r"([A-Za-z_][A-Za-z0-9_]*)\s+whose\s+([A-Za-z_][A-Za-z0-9_]*)\s+field\s+is\s+"
      r"([^,]+?)(?=,\s+and\s+|,\s*[A-Za-z_][A-Za-z0-9_]*\s+is\s+|$)",
      semantic,re.IGNORECASE
    )
    summed=re.search(
      r"\b([A-Za-z_][A-Za-z0-9_]*)\s+is\s+the\s+sum\s+of\s+those\s+"
      r"([A-Za-z_][A-Za-z0-9_]*)['’]\s+([A-Za-z_][A-Za-z0-9_]*)\s+field\b",
      semantic,re.IGNORECASE
    )
    ratio=re.search(
      r"\b([A-Za-z_][A-Za-z0-9_]*)\s+is\s+([A-Za-z_][A-Za-z0-9_]*)\s+divided\s+by\s+"
      r"([A-Za-z_][A-Za-z0-9_]*)\b",
      semantic,re.IGNORECASE
    )
    if not relation or not ratio:
        return None

    count_all_key=relation.group(1).lower()
    fact_entity=relation.group(2).lower()
    fact_key=relation.group(3)
    relation_dim=relation.group(4).lower()
    dimension_key=relation.group(5)
    if not (_generic_entity_forms(relation_dim)&_generic_entity_forms(dimension_entity)):
        return None
    if count_all_key not in field_by_lower:
        return None

    metric_keys={count_all_key}
    metrics=[{"name":field_by_lower[count_all_key],"op":"count"}]

    if filtered:
        filtered_key=filtered.group(1).lower()
        filtered_entity=filtered.group(2).lower()
        if filtered_key not in field_by_lower:
            return None
        if not (_generic_entity_forms(filtered_entity)&_generic_entity_forms(fact_entity)):
            return None
        metrics.append({
          "name":field_by_lower[filtered_key],
          "op":"count_where",
          "where":{filtered.group(3):_parse_scalar_literal(filtered.group(4))},
        })
        metric_keys.add(filtered_key)

    if summed:
        sum_key=summed.group(1).lower()
        sum_entity=summed.group(2).lower()
        if sum_key not in field_by_lower:
            return None
        if not (_generic_entity_forms(sum_entity)&_generic_entity_forms(fact_entity)):
            return None
        metrics.append({
          "name":field_by_lower[sum_key],
          "op":"sum",
          "field":summed.group(3),
        })
        metric_keys.add(sum_key)

    ratio_key=ratio.group(1).lower()
    ratio_num_key=ratio.group(2).lower()
    ratio_den_key=ratio.group(3).lower()
    if ratio_key not in field_by_lower:
        return None
    if ratio_num_key not in metric_keys or ratio_den_key not in metric_keys:
        return None

    output_id_candidates=[
      f for f in fields
      if re.sub(r"[^a-z0-9]+","",f.lower())==re.sub(r"[^a-z0-9]+","",dimension_entity+"id")
    ]
    if len(output_id_candidates)!=1:
        return None
    output_id_field=output_id_candidates[0]
    dimension_path=_context_json_for_entity(context_paths,dimension_entity)
    fact_path=_context_json_for_entity(context_paths,fact_entity)
    if not dimension_path or not fact_path or dimension_path==fact_path:
        return None

    semantic_output_keys=metric_keys|{ratio_key,output_id_field.lower()}
    copy_fields=[f for f in fields if f.lower() not in semantic_output_keys]
    derived=[{
      "name":field_by_lower[ratio_key],
      "op":"divide",
      "numerator":field_by_lower[ratio_num_key],
      "denominator":field_by_lower[ratio_den_key],
    }]
    return {
      "action":{
        "type":"derive_grouped_records",
        "args":{
          "dimension_path":dimension_path,
          "fact_path":fact_path,
          "dimension_key":dimension_key,
          "fact_key":fact_key,
          "output_path":output_path,
          "output_id_field":output_id_field,
          "copy_fields":copy_fields,
          "metrics":metrics,
          "derived":derived,
        },
        "expect":{"type":"field_equals","field":"output_verified","value":True},
      },
      "output_path":output_path,
      "evidence":{
        "dimension_path":dimension_path,"fact_path":fact_path,
        "dimension_key":dimension_key,"fact_key":fact_key,
        "output_path":output_path,"output_id_field":output_id_field,
        "copy_fields":copy_fields,"metrics":metrics,"derived":derived,
        "fields":fields,
      }
    }


def _parse_rank_limit(raw):
    text=str(raw or "").strip().lower()
    words={
      "one":1,"two":2,"three":3,"four":4,"five":5,
      "six":6,"seven":7,"eight":8,"nine":9,"ten":10,
    }
    if text in words:
        return words[text]
    if re.fullmatch(r"\d+",text):
        value=int(text)
        return value if 1<=value<=1000 else None
    return None


def _compile_generic_rank_select_ir(clause,context_paths,root):
    text=str(clause or "").strip()
    m=re.match(
      r"^from\s+([^\s]+\.json)\s+select\s+exactly\s+"
      r"(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
      r"([A-Za-z_][A-Za-z0-9_]*)\s+with\s+the\s+greatest\s+"
      r"([A-Za-z_][A-Za-z0-9_]*),\s+breaking\s+ties\s+by\s+the\s+lowest\s+"
      r"([A-Za-z_][A-Za-z0-9_]*),\s+and\s+save\s+([^\s]+\.json)\s+containing\s+(.+)$",
      text,re.IGNORECASE
    )
    if not m:
        return None
    source_path=m.group(1).strip(" .,:;")
    limit=_parse_rank_limit(m.group(2))
    primary_key=m.group(4).lower()
    tie_key=m.group(5).lower()
    output_path=m.group(6).strip(" .,:;")
    field_text=re.sub(r"\s+in\s+ranked\s+order\s*$","",m.group(7),flags=re.IGNORECASE)
    fields=[
      x.strip(" .,:;")
      for x in re.sub(r"\s+and\s+",",",field_text,flags=re.IGNORECASE).split(",")
      if x.strip(" .,:;")
    ]
    field_by_lower={}
    for field in fields:
        key=field.lower()
        if key in field_by_lower:
            return None
        field_by_lower[key]=field
    if (
        limit is None or source_path not in context_paths or not fields
        or primary_key not in field_by_lower or tie_key not in field_by_lower
    ):
        return None
    order_by=[
      {"field":field_by_lower[primary_key],"direction":"desc"},
      {"field":field_by_lower[tie_key],"direction":"asc"},
    ]
    return {
      "action":{
        "type":"select_ranked_record",
        "args":{
          "source_path":source_path,
          "output_path":output_path,
          "order_by":order_by,
          "output_fields":fields,
          "limit":limit,
        },
        "expect":{"type":"field_equals","field":"output_verified","value":True},
      },
      "output_path":output_path,
      "evidence":{
        "source_path":source_path,"output_path":output_path,
        "order_by":order_by,"output_fields":fields,"limit":limit,
      }
    }


def _compile_generic_dataflow_verification_ir(clause,compiled_parts):
    lower=str(clause or "").strip().lower()
    if not re.match(r"^finally\s+independently\s+(?:reopen|reread|verify|check)\b",lower):
        return None
    grouped=[]
    ranked=None
    for part in compiled_parts or []:
        if not isinstance(part,dict):
            continue
        if part.get("mode")=="GENERIC_GROUP_DERIVE_IR":
            path=str(part.get("output_path") or "")
            if path and path.lower() in lower:
                grouped.append(part)
        elif part.get("mode")=="GENERIC_RANK_SELECT_IR":
            ranked=part
    if not grouped or ranked is None:
        return None
    if str(ranked.get("output_path") or "").lower() not in lower:
        return None

    actions=[]
    for part in grouped:
        actions.append({
          "type":"assert_grouped_derived_records",
          "args":{
            "dimension_path":part["dimension_path"],
            "fact_path":part["fact_path"],
            "summary_path":part["output_path"],
            "dimension_key":part["dimension_key"],
            "fact_key":part["fact_key"],
            "output_id_field":part["output_id_field"],
            "copy_fields":part["copy_fields"],
            "metrics":part["metrics"],
            "derived":part["derived"],
          },
          "expect":{"type":"field_equals","field":"verified","value":True},
        })
    actions.append({
      "type":"assert_ranked_record",
      "args":{
        "source_path":ranked["source_path"],
        "selected_path":ranked["output_path"],
        "order_by":ranked["order_by"],
        "output_fields":ranked["output_fields"],
        "limit":ranked.get("limit",1),
      },
      "expect":{"type":"field_equals","field":"verified","value":True},
    })
    return {
      "actions":actions,
      "evidence":{
        "summary_paths":[part["output_path"] for part in grouped],
        "selected_path":ranked["output_path"],
        "verification_mode":"INDEPENDENT_RECOMPUTATION_OF_EVERY_REFERENCED_DERIVED_STAGE",
      }
    }


def _parse_json_path_spec(raw_path):
    path_spec=[]
    for part in str(raw_path or "").strip().split("."):
        if not part:
            return None
        if re.fullmatch(r"\d+",part):
            path_spec.append(int(part))
        elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",part):
            path_spec.append(part)
        else:
            return None
    return path_spec


def _compile_external_json_knowledge_fetch(clause,action_cycle):
    text=str(clause or "").strip()
    m=re.match(
        r"^using\s+(?:an?\s+)?external\s+json\s+source\s+(https?://[^\s,]+),\s*"
        r"extract\s+json\s+path\s+([^\s]+)\s+and\s+save\s+(?:the\s+)?knowledge\s+evidence\s+to\s+"
        r"([^\s]+\.json)$",
        text,re.IGNORECASE
    )
    if not m:
        return None
    url=m.group(1).rstrip(".,;:!?")
    path_spec=_parse_json_path_spec(m.group(2))
    if path_spec is None:
        return None
    output_path=m.group(3).strip(" .,:;")
    return {
      "action":{
        "type":"fetch_json_knowledge",
        "args":{
          "url":url,
          "json_path":path_spec,
          "output_path":output_path,
          "authoritative":False,
          "timeout_s":20,
          "max_bytes":1000000,
        },
        "expect":{"type":"field_equals","field":"verified","value":True},
      },
      "output_path":output_path,
      "result_cycle":int(action_cycle),
      "evidence":{
        "source_url":url,
        "json_path":path_spec,
        "evidence_path":output_path,
        "result_cycle":int(action_cycle),
        "authoritative":False,
      }
    }


def _compile_knowledge_consistency_assessment(clause,context_paths):
    text=str(clause or "").strip()
    m=re.match(
        r"^assess\s+(?:the\s+)?knowledge\s+evidence\s+(.+?)\s+and\s+save\s+(?:the\s+)?assessment\s+to\s+"
        r"([^\s]+\.json)(?:\s+with\s+freshness\s+budget\s+(\d+)\s+seconds?)?$",
        text,re.IGNORECASE
    )
    if not m:
        return None
    blob=m.group(1)
    output_path=m.group(2).strip(" .,:;")
    max_age=int(m.group(3)) if m.group(3) is not None else None
    paths=re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.json",blob)
    if len(paths)<2:
        return None
    known={str(x) for x in context_paths or []}
    if any(p not in known for p in paths):
        return None
    args={"evidence_paths":paths,"output_path":output_path}
    if max_age is not None:
        args["max_age_s"]=max_age
    return {
      "action":{
        "type":"assess_knowledge_consistency",
        "args":args,
        "expect":{"type":"field_nonempty","field":"status"},
      },
      "output_path":output_path,
      "evidence":{"evidence_paths":paths,"output_path":output_path,"max_age_s":max_age}
    }


def _compile_knowledge_status_assertion(clause,context_paths):
    text=str(clause or "").strip()
    m=re.match(
        r"^(?:finally\s+)?verify\s+(?:that\s+)?(?:the\s+)?knowledge\s+status\s+is\s+"
        r"(SUPPORTED|CONFLICTED|INSUFFICIENT|STALE)$",
        text,re.IGNORECASE
    )
    if not m:
        return None
    status=m.group(1).upper()
    json_paths=[str(x) for x in context_paths or [] if str(x).lower().endswith(".json")]
    if not json_paths:
        return None
    assessment_path=json_paths[-1]
    return {
      "action":{
        "type":"assert_knowledge_status",
        "args":{"assessment_path":assessment_path,"expected_status":status},
        "expect":{"type":"field_equals","field":"verified","value":True},
      },
      "evidence":{"assessment_path":assessment_path,"expected_status":status}
    }


def _compile_authoritative_json_knowledge_fetch(clause,action_cycle):
    text=str(clause or "").strip()
    m=re.match(
        r"^using\s+the\s+authoritative\s+json\s+source\s+(https?://[^\s,]+),\s*"
        r"extract\s+json\s+path\s+([^\s]+)\s+and\s+save\s+the\s+knowledge\s+evidence\s+to\s+"
        r"([^\s]+\.json)$",
        text,re.IGNORECASE
    )
    if not m:
        return None
    url=m.group(1).rstrip(".,;:!?")
    raw_path=m.group(2).strip(" .,:;")
    output_path=m.group(3).strip(" .,:;")
    path_spec=_parse_json_path_spec(raw_path)
    if path_spec is None:
        return None
    return {
      "action":{
        "type":"fetch_json_knowledge",
        "args":{
          "url":url,
          "json_path":path_spec,
          "output_path":output_path,
          "authoritative":True,
          "timeout_s":20,
          "max_bytes":1000000,
        },
        "expect":{"type":"field_equals","field":"verified","value":True},
      },
      "output_path":output_path,
      "result_cycle":int(action_cycle),
      "evidence":{
        "source_url":url,
        "json_path":path_spec,
        "evidence_path":output_path,
        "result_cycle":int(action_cycle),
      }
    }


def _restricted_numeric_expression_names(expression):
    """Validate the compiler-visible arithmetic grammar and return names in first-use order."""
    try:
        tree=ast.parse(str(expression or "").strip(),mode="eval")
    except SyntaxError as exc:
        raise GoalCompilationFailure("NUMERIC_EXPRESSION_SYNTAX_INVALID") from exc
    nodes=list(ast.walk(tree))
    if len(nodes)>64:
        raise GoalCompilationFailure("NUMERIC_EXPRESSION_NODE_LIMIT")
    names=[]
    def visit(node,depth=0):
        if depth>16:
            raise GoalCompilationFailure("NUMERIC_EXPRESSION_DEPTH_LIMIT")
        if isinstance(node,ast.Expression):
            return visit(node.body,depth+1)
        if isinstance(node,ast.Constant):
            if isinstance(node.value,bool) or not isinstance(node.value,(int,float)):
                raise GoalCompilationFailure("NUMERIC_EXPRESSION_LITERAL_TYPE_REJECTED")
            if not math.isfinite(float(node.value)) or abs(float(node.value))>1e100:
                raise GoalCompilationFailure("NUMERIC_EXPRESSION_LITERAL_INVALID")
            return
        if isinstance(node,ast.Name):
            if node.id not in names:
                names.append(node.id)
            return
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            return visit(node.operand,depth+1)
        if isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Add,ast.Sub,ast.Mult,ast.Div,ast.Pow)):
            visit(node.left,depth+1); visit(node.right,depth+1)
            if isinstance(node.op,ast.Pow) and isinstance(node.right,ast.Constant):
                if isinstance(node.right.value,bool) or not isinstance(node.right.value,(int,float)):
                    raise GoalCompilationFailure("NUMERIC_EXPRESSION_EXPONENT_INVALID")
                if abs(float(node.right.value))>32:
                    raise GoalCompilationFailure("NUMERIC_EXPRESSION_EXPONENT_LIMIT")
            return
        raise GoalCompilationFailure("NUMERIC_EXPRESSION_AST_NODE_REJECTED",type(node).__name__)
    visit(tree)
    return names


_NUMERIC_BINDING_GENERIC_TOKENS={
    "canonical","astra","runtime","tmp","parent","knowledge","evidence","json",
    "value","result","source","input","output","numeric","expression","data",
}

def _numeric_binding_tokens(value):
    return [
        token.lower()
        for token in re.findall(r"[A-Za-z0-9]+",str(value or ""))
        if token and token.lower() not in _NUMERIC_BINDING_GENERIC_TOKENS
    ]

def _numeric_producer_tokens(part):
    tokens=[]
    evidence_path=str((part or {}).get("evidence_path") or "")
    if evidence_path:
        tokens.extend(_numeric_binding_tokens(pathlib.Path(evidence_path).stem))
    for item in (part or {}).get("json_path") or []:
        tokens.extend(_numeric_binding_tokens(item))
    # Preserve order only for diagnostics; matching itself is set-based.
    return list(dict.fromkeys(tokens))

def _numeric_binding_score(name,part):
    name_tokens=_numeric_binding_tokens(name)
    producer_tokens=_numeric_producer_tokens(part)
    score=0
    matched=[]
    for left in name_tokens:
        best=0
        best_token=None
        for right in producer_tokens:
            if left==right:
                candidate=6 if len(left)>1 else 3
            elif len(left)>=3 and len(right)>=3 and (left.startswith(right) or right.startswith(left)):
                candidate=2
            else:
                candidate=0
            if candidate>best:
                best=candidate
                best_token=right
        if best:
            score+=best
            matched.append([left,best_token])
    return score,matched

def _bind_numeric_expression_producers(names,producers):
    if len(producers)<len(names):
        raise GoalCompilationFailure("NUMERIC_EXPRESSION_INSUFFICIENT_PRIOR_SCALARS")
    if len(names)==1 and len(producers)==1:
        return [(names[0],producers[0],{"mode":"ONLY_PRIOR_SCALAR"})]

    selected=[]
    used_cycles=set()
    for name in names:
        scored=[]
        for part in producers:
            cycle=int(part["result_cycle"])
            if cycle in used_cycles:
                continue
            score,matched=_numeric_binding_score(name,part)
            scored.append((score,cycle,part,matched))
        if not scored:
            raise GoalCompilationFailure("NUMERIC_EXPRESSION_PRODUCER_BINDING_REQUIRED",name)
        best_score=max(x[0] for x in scored)
        if best_score<=0:
            # Elimination is safe only when exactly one producer and one name
            # remain after prior semantic bindings.
            remaining_names=len(names)-len(selected)
            remaining_parts=[x for x in scored if x[1] not in used_cycles]
            if remaining_names==1 and len(remaining_parts)==1:
                _,cycle,part,matched=remaining_parts[0]
                selected.append((name,part,{"mode":"UNIQUE_REMAINDER","matched":matched}))
                used_cycles.add(cycle)
                continue
            raise GoalCompilationFailure("NUMERIC_EXPRESSION_PRODUCER_BINDING_REQUIRED",name)
        winners=[x for x in scored if x[0]==best_score]
        if len(winners)!=1:
            raise GoalCompilationFailure(
                "NUMERIC_EXPRESSION_PRODUCER_BINDING_AMBIGUOUS",
                name+":"+",".join(str(x[1]) for x in winners),
            )
        score,cycle,part,matched=winners[0]
        selected.append((name,part,{"mode":"SEMANTIC_TOKEN_MATCH","score":score,"matched":matched}))
        used_cycles.add(cycle)

    if len(selected)!=len(names):
        raise GoalCompilationFailure("NUMERIC_EXPRESSION_PRODUCER_BINDING_INCOMPLETE")
    return selected


def _compile_typed_scalar_numeric_expression(clause,compiled_parts,registry,action_cycle):
    text=str(clause or "").strip()
    m=re.match(
        r"^(?:calculate|compute|derive|evaluate)\s+.+?\s+using\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$",
        text,re.IGNORECASE,
    )
    if not m:
        return None
    result_name=m.group(1)
    expression=m.group(2).strip()
    if len(expression)>512:
        raise GoalCompilationFailure("NUMERIC_EXPRESSION_TOO_LONG")
    names=_restricted_numeric_expression_names(expression)
    if not names:
        raise GoalCompilationFailure("NUMERIC_EXPRESSION_VARIABLE_REQUIRED")
    entry=(registry or {}).get("math.numeric_expression.sympy")
    if not isinstance(entry,dict) or entry.get("status") not in {"VERIFIED_BOUND_CAPABILITY","CANDIDATE_BOUND_CAPABILITY"}:
        raise GoalCompilationFailure("NUMERIC_EXPRESSION_VERIFIED_SYMPY_REQUIRED")
    producers=[
        part for part in (compiled_parts or [])
        if isinstance(part,dict)
        and part.get("mode") in {"AUTHORITATIVE_JSON_KNOWLEDGE_FETCH","EXTERNAL_JSON_KNOWLEDGE_FETCH"}
        and isinstance(part.get("result_cycle"),int)
    ]
    selected_bindings=_bind_numeric_expression_producers(names,producers)
    variables={
        name:{"$result":{"cycle":int(part["result_cycle"]),"field":"value"}}
        for name,part,_evidence in selected_bindings
    }
    digest=hashlib.sha256((text+"\n"+json.dumps(
        [(name,int(part["result_cycle"])) for name,part,_evidence in selected_bindings],
        separators=(",",":")
    )).encode("utf-8")).hexdigest()[:12].upper()
    output_path=f"canonical/astra_runtime/tmp/NUMERIC_EXPRESSION_{digest}_RESULT.json"
    action={
      "type":"invoke_capability",
      "args":{
        "capability_id":"math.numeric_expression.sympy",
        "expression":expression,
        "variables":variables,
        "output_path":output_path,
      },
      "expect":{"type":"field_equals","field":"output_verified","value":True},
    }
    return {
      "action":action,
      "output_path":output_path,
      "evidence":{
        "selected_capability":"math.numeric_expression.sympy",
        "result_name":result_name,
        "expression":expression,
        "variable_names":names,
        "variable_bindings":{
          name:{
            "cycle":int(part["result_cycle"]),
            "field":"value",
            "binding_evidence":binding_evidence,
          }
          for name,part,binding_evidence in selected_bindings
        },
        "producer_result_cycles":[
          int(part["result_cycle"]) for _name,part,_evidence in selected_bindings
        ],
        "result_cycle":int(action_cycle),
        "result_field":"value",
        "output_path":output_path,
        "model_dependency_count":0,
      },
    }


def _compile_two_scalar_absolute_difference_relation(clause,compiled_parts,registry):
    """Lower one bounded numeric relation onto existing native JSON + jq machinery.

    Supported semantic form is intentionally generic and narrow: determine/check/
    verify/assess whether two causally prior scalar results differ by at most a
    literal finite numeric threshold. The compiler never binds domain names or
    source-specific literals. Runtime jq type checks fail closed on non-numbers.
    """
    text=str(clause or "").strip()
    m=re.match(
        r"^(?:determine|check|verify|assess)\s+whether\s+(?:the\s+)?two\s+.+?\s+"
        r"differ\s+by\s+(?:at\s+most|no\s+more\s+than|less\s+than\s+or\s+equal\s+to)\s+"
        r"([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)$",
        text,re.IGNORECASE,
    )
    if not m:
        return None
    threshold=float(m.group(1))
    if not math.isfinite(threshold) or threshold < 0:
        raise GoalCompilationFailure("NUMERIC_RELATION_THRESHOLD_INVALID")

    jq_entry=(registry or {}).get("json.query.jq")
    if not isinstance(jq_entry,dict) or jq_entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
        raise GoalCompilationFailure("NUMERIC_RELATION_VERIFIED_JQ_REQUIRED")

    source_producers=[
        part for part in (compiled_parts or [])
        if isinstance(part,dict)
        and part.get("mode") in {"AUTHORITATIVE_JSON_KNOWLEDGE_FETCH","EXTERNAL_JSON_KNOWLEDGE_FETCH"}
        and isinstance(part.get("result_cycle"),int)
    ]
    expression_producers=[
        part for part in (compiled_parts or [])
        if isinstance(part,dict)
        and part.get("mode")=="VERIFIED_BOUND_NUMERIC_EXPRESSION"
        and isinstance(part.get("result_cycle"),int)
    ]
    producer_specs=[]
    if expression_producers:
        derived=expression_producers[-1]
        used=set(int(x) for x in (derived.get("producer_result_cycles") or []))
        unused=[p for p in source_producers if int(p["result_cycle"]) not in used]
        if len(unused)!=1:
            raise GoalCompilationFailure(
                "NUMERIC_RELATION_DERIVED_REQUIRES_ONE_UNUSED_PRIOR_SCALAR",
                str(len(unused)),
            )
        producer_specs=[
            {"cycle":int(derived["result_cycle"]),"field":str(derived.get("result_field") or "value")},
            {"cycle":int(unused[0]["result_cycle"]),"field":"value"},
        ]
    else:
        if len(source_producers)!=2:
            raise GoalCompilationFailure(
                "NUMERIC_RELATION_REQUIRES_EXACTLY_TWO_PRIOR_SCALARS",
                str(len(source_producers)),
            )
        producer_specs=[
            {"cycle":int(source_producers[0]["result_cycle"]),"field":"value"},
            {"cycle":int(source_producers[1]["result_cycle"]),"field":"value"},
        ]

    digest=hashlib.sha256(
        (text+"\\n"+str(producer_specs[0]["cycle"])+"\\n"+str(producer_specs[1]["cycle"])).encode("utf-8")
    ).hexdigest()[:12].upper()
    input_path=f"canonical/astra_runtime/tmp/NUMERIC_RELATION_{digest}_INPUT.json"
    output_path=f"canonical/astra_runtime/tmp/NUMERIC_RELATION_{digest}_RESULT.json"
    materialize={
      "type":"write_json_records",
      "args":{
        "output_path":input_path,
        "fields":["left","right","threshold"],
        "records":[{
          "left":{"$result":{"cycle":producer_specs[0]["cycle"],"field":producer_specs[0]["field"]}},
          "right":{"$result":{"cycle":producer_specs[1]["cycle"],"field":producer_specs[1]["field"]}},
          "threshold":threshold,
        }],
      },
      "expect":{"type":"field_equals","field":"verified","value":True},
    }
    filt=(
      '.[0] as $r '
      '| if (($r.left|type)!="number" or ($r.right|type)!="number" or ($r.threshold|type)!="number") '
      'then error("NUMERIC_RELATION_INPUT_NOT_NUMBER") '
      'else (($r.left-$r.right)|fabs) as $d '
      '| {left:$r.left,right:$r.right,threshold:$r.threshold,'
      'absolute_difference:$d,relation:"ABS_DIFF_LTE",predicate:($d <= $r.threshold)} end'
    )
    compute={
      "type":"invoke_capability",
      "args":{
        "capability_id":"json.query.jq",
        "input_path":input_path,
        "filter":filt,
        "output_path":output_path,
        "raw_output":False,
        "require_nonempty":True,
        "timeout_s":60,
      },
      "expect":{"type":"field_equals","field":"output_verified","value":True},
    }
    return {
      "actions":[materialize,compute],
      "output_path":output_path,
      "evidence":{
        "selected_capability":"json.query.jq",
        "relation":"ABS_DIFF_LTE",
        "threshold":threshold,
        "input_path":input_path,
        "output_path":output_path,
        "producer_result_cycles":[producer_specs[0]["cycle"],producer_specs[1]["cycle"]],
        "model_dependency_count":0,
      },
    }


def _compile_learned_value_record(clause,compiled_parts):
    text=str(clause or "").strip()
    m=re.match(
        r"^create\s+([^\s]+\.json)\s+with\s+one\s+record\s+containing\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)\s+([^\s,]+)\s+and\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)\s+equal\s+to\s+the\s+learned\s+value$",
        text,re.IGNORECASE
    )
    if not m:
        return None
    prior=None
    for part in reversed(compiled_parts or []):
        if isinstance(part,dict) and part.get("mode")=="AUTHORITATIVE_JSON_KNOWLEDGE_FETCH":
            prior=part
            break
    if prior is None:
        return None
    output_path=m.group(1).strip(" .,:;")
    literal_field=m.group(2)
    literal_value=m.group(3).strip(" .,:;")
    learned_field=m.group(4)
    return {
      "action":{
        "type":"write_json_records",
        "args":{
          "output_path":output_path,
          "fields":[literal_field,learned_field],
          "records":[{
            literal_field:literal_value,
            learned_field:{"$result":{"cycle":int(prior["result_cycle"]),"field":"value"}},
          }],
        },
        "expect":{"type":"field_equals","field":"verified","value":True},
      },
      "output_path":output_path,
      "evidence":{
        "output_path":output_path,
        "literal_field":literal_field,
        "learned_field":learned_field,
        "knowledge_evidence_path":prior["evidence_path"],
      }
    }


def _compile_knowledge_revalidation(clause,compiled_parts,future_clauses=None):
    text=str(clause or "").strip()
    consume_future=0
    whole=re.match(
        r"^finally\s+independently\s+re-fetch\s+the\s+authoritative\s+source\s+and\s+"
        r"verify\s+the\s+learned\s+value\s+is\s+unchanged$",
        text,re.IGNORECASE
    )
    if not whole:
        first=re.match(
            r"^finally\s+independently\s+re-fetch\s+the\s+authoritative\s+source$",
            text,re.IGNORECASE
        )
        next_clause=str((future_clauses or [""])[0] or "").strip() if (future_clauses or []) else ""
        second=re.match(
            r"^verify\s+the\s+learned\s+value\s+is\s+unchanged$",
            next_clause,re.IGNORECASE
        )
        if not first or not second:
            return None
        consume_future=1
    prior=None
    for part in reversed(compiled_parts or []):
        if isinstance(part,dict) and part.get("mode")=="AUTHORITATIVE_JSON_KNOWLEDGE_FETCH":
            prior=part
            break
    if prior is None:
        return None
    return {
      "action":{
        "type":"assert_json_knowledge",
        "args":{
          "evidence_path":prior["evidence_path"],
          "timeout_s":20,
          "max_bytes":1000000,
        },
        "expect":{"type":"field_equals","field":"verified","value":True},
      },
      "consume_future":consume_future,
      "evidence":{
        "evidence_path":prior["evidence_path"],
        "source_url":prior["source_url"],
        "json_path":prior["json_path"],
      }
    }


def _compile_compound_goal(goal, clauses, registry, root):
    actions=[]
    compiled_parts=[]
    context_paths=[]
    consumed_indices=set()
    proposal_binder=_load_sibling_runtime_module(
        "capability_proposal_generators.py",
        "project_brain_direct_compiler_proposal_binder",
    )
    planner=_load_sibling_runtime_module(
        "capability_planner.py",
        "project_brain_direct_compiler_capability_planner",
    )
    effect_providers={}
    runtime_effect_providers={}
    for index,clause in enumerate(clauses):
        if index in consumed_indices:
            continue
        lower=clause.lower()

        external_knowledge_fetch=_compile_external_json_knowledge_fetch(clause,len(actions))
        if external_knowledge_fetch is not None:
            actions.append(external_knowledge_fetch["action"])
            context_paths.append(external_knowledge_fetch["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"EXTERNAL_JSON_KNOWLEDGE_FETCH",
                **external_knowledge_fetch["evidence"],
            })
            continue

        knowledge_assessment=_compile_knowledge_consistency_assessment(clause,context_paths)
        if knowledge_assessment is not None:
            actions.append(knowledge_assessment["action"])
            context_paths.append(knowledge_assessment["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"KNOWLEDGE_CONSISTENCY_ASSESSMENT",
                **knowledge_assessment["evidence"],
            })
            continue

        knowledge_status=_compile_knowledge_status_assertion(clause,context_paths)
        if knowledge_status is not None:
            actions.append(knowledge_status["action"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"KNOWLEDGE_STATUS_ASSERTION",
                **knowledge_status["evidence"],
            })
            continue

        knowledge_fetch=_compile_authoritative_json_knowledge_fetch(clause,len(actions))
        if knowledge_fetch is not None:
            actions.append(knowledge_fetch["action"])
            context_paths.append(knowledge_fetch["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"AUTHORITATIVE_JSON_KNOWLEDGE_FETCH",
                **knowledge_fetch["evidence"],
            })
            continue

        numeric_expression=_compile_typed_scalar_numeric_expression(
            clause,compiled_parts,registry,len(actions)
        )
        if numeric_expression is not None:
            actions.append(numeric_expression["action"])
            context_paths.append(numeric_expression["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"VERIFIED_BOUND_NUMERIC_EXPRESSION",
                **numeric_expression["evidence"],
            })
            continue

        numeric_relation=_compile_two_scalar_absolute_difference_relation(
            clause,compiled_parts,registry
        )
        if numeric_relation is not None:
            actions.extend(numeric_relation["actions"])
            context_paths.append(numeric_relation["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"VERIFIED_BOUND_NUMERIC_RELATION",
                **numeric_relation["evidence"],
            })
            continue

        learned_record=_compile_learned_value_record(clause,compiled_parts)
        if learned_record is not None:
            actions.append(learned_record["action"])
            context_paths.append(learned_record["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"KNOWLEDGE_VALUE_DOWNSTREAM_MATERIALIZATION",
                **learned_record["evidence"],
            })
            continue

        knowledge_revalidation=_compile_knowledge_revalidation(
            clause,compiled_parts,clauses[index+1:]
        )
        if knowledge_revalidation is not None:
            actions.append(knowledge_revalidation["action"])
            consume=int(knowledge_revalidation.get("consume_future") or 0)
            for offset in range(1,consume+1):
                consumed_indices.add(index+offset)
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"INDEPENDENT_KNOWLEDGE_REVALIDATION",
                **knowledge_revalidation["evidence"],
            })
            for offset in range(1,consume+1):
                compiled_parts.append({
                    "index":index+offset,
                    "subgoal":clauses[index+offset],
                    "mode":"KNOWLEDGE_REVALIDATION_CONTINUATION",
                    **knowledge_revalidation["evidence"],
                })
            continue

        literal_json=_compile_literal_json_records(clause,root)
        if literal_json is not None:
            actions.append(literal_json["action"])
            context_paths.append(literal_json["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"NATIVE_LITERAL_JSON_RECORDS",
                **literal_json["evidence"],
            })
            continue

        live_collection_read=_compile_live_collection_read(clause,context_paths)
        if live_collection_read is not None:
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"DEFERRED_RUNTIME_COLLECTION_READ",
                "source_path":live_collection_read["source_path"],
            })
            continue

        live_collection_map=_compile_live_collection_map(clause,context_paths,registry)
        if live_collection_map is not None:
            actions.append(live_collection_map["action"])
            context_paths.append(live_collection_map["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"VERIFIED_RUNTIME_COLLECTION_MAP",
                **live_collection_map["evidence"],
            })
            continue

        live_collection_verify=_compile_live_collection_verification(clause,compiled_parts)
        if live_collection_verify is not None:
            actions.append(live_collection_verify["action"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"INDEPENDENT_RUNTIME_COLLECTION_VERIFICATION",
                **live_collection_verify["evidence"],
            })
            continue

        if re.match(r"^read\s+the\s+uuid\s+from\s+that\s+live\s+result$",str(clause or ""),re.IGNORECASE):
            json_paths=[str(p) for p in context_paths if pathlib.Path(str(p)).suffix.lower()==".json"]
            if not json_paths:
                raise GoalCompilationFailure("LIVE_UUID_SOURCE_REQUIRED")
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"DEFERRED_RUNTIME_VALUE_READ",
                "source_path":json_paths[-1],
            })
            continue

        runtime_choice=_compile_runtime_capability_choice(clause,context_paths,registry)
        if runtime_choice is not None:
            actions.append(runtime_choice["action"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"RUNTIME_SELECTED_VERIFIED_CAPABILITY",
                **runtime_choice["evidence"],
            })
            continue

        runtime_choice_verify=_compile_runtime_capability_choice_verification(clause,compiled_parts)
        if runtime_choice_verify is not None:
            actions.append(runtime_choice_verify["action"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"INDEPENDENT_RUNTIME_CAPABILITY_CHOICE_VERIFICATION",
                **runtime_choice_verify["evidence"],
            })
            continue

        live_conditional=_compile_live_uuid_conditional(clause,context_paths,registry)
        if live_conditional is not None:
            actions.append(live_conditional["action"])
            context_paths.append(live_conditional["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"VERIFIED_RUNTIME_CONDITIONAL",
                **live_conditional["evidence"],
            })
            continue

        live_verify=_compile_live_uuid_verification(clause,context_paths,compiled_parts)
        if live_verify is not None:
            actions.append(live_verify["action"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"INDEPENDENT_RUNTIME_CONDITIONAL_VERIFICATION",
                **live_verify["evidence"],
            })
            continue

        grouped_ir=_compile_generic_group_derive_ir(clause,context_paths,root)
        if grouped_ir is not None:
            actions.append(grouped_ir["action"])
            context_paths.append(grouped_ir["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"GENERIC_GROUP_DERIVE_IR",
                **grouped_ir["evidence"],
            })
            continue

        rank_ir=_compile_generic_rank_select_ir(clause,context_paths,root)
        if rank_ir is not None:
            actions.append(rank_ir["action"])
            context_paths.append(rank_ir["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"GENERIC_RANK_SELECT_IR",
                **rank_ir["evidence"],
            })
            continue

        generic_verify=_compile_generic_dataflow_verification_ir(clause,compiled_parts)
        if generic_verify is not None:
            actions.extend(generic_verify["actions"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"INDEPENDENT_GENERIC_DATAFLOW_VERIFICATION",
                **generic_verify["evidence"],
            })
            continue

        browser_interaction=_compile_verified_browser_interaction(clause,registry,root)
        if browser_interaction is not None:
            first_action=(browser_interaction.get("controller_actions") or [None])[0]
            part=(browser_interaction.get("compiled_parts") or [None])[0]
            if not isinstance(first_action,dict) or not isinstance(part,dict):
                raise GoalCompilationFailure("BROWSER_INTERACTION_COMPILED_PLAN_INVALID")
            actions.append(first_action)
            for p in (part.get("screenshot_path"),part.get("result_path")):
                if isinstance(p,str) and p not in context_paths:
                    context_paths.append(p)
            compiled_parts.append({
                "index":index,
                "subgoal":clause,
                **{k:v for k,v in part.items() if k not in {"index","subgoal"}},
            })
            continue

        projection=_compile_browser_result_record_projection(clause,context_paths,root)
        if projection is not None:
            actions.append(projection["action"])
            context_paths.append(projection["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"NATIVE_TYPED_BROWSER_RESULT_PROJECTION",
                **projection["evidence"],
            })
            continue
        test_glob=_python_test_glob(clause,root)
        if test_glob is not None and re.match(r"^(?:execute|run)\b",lower):
            action={
                "type":"list_tree",
                "args":{"prefix":test_glob["source_root"]},
                "expect":{"type":"field_nonempty","field":"items"},
            }
            actions.append(action)
            context_paths.append(test_glob["source_root"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"NATIVE_TEST_CORPUS_DISCOVERY",
                **test_glob,
            })
            continue

        # Evidence-only repository reads are native runtime actions and should
        # not require a separately acquired capability.
        if re.match(r"^(?:read|inspect|open)\b",lower):
            paths=_repo_paths(clause,root)
            existing=[(raw,p) for raw,p in paths if p.is_file()]
            directories=[(raw,p) for raw,p in paths if p.is_dir()]
            if len(existing)==1:
                action={
                    "type":"read_file",
                    "args":{"path":existing[0][0]},
                    "expect":{"type":"field_nonempty","field":"content"},
                }
                actions.append(action)
                context_paths.append(existing[0][0])
                compiled_parts.append({
                    "index":index,"subgoal":clause,"mode":"NATIVE_READ",
                    "path":existing[0][0],
                })
                continue
            if len(directories)==1:
                action={
                    "type":"list_tree",
                    "args":{"prefix":directories[0][0]},
                    "expect":{"type":"field_nonempty","field":"items"},
                }
                actions.append(action)
                context_paths.append(directories[0][0])
                compiled_parts.append({
                    "index":index,"subgoal":clause,"mode":"NATIVE_TREE_INSPECTION",
                    "path":directories[0][0],
                })
                continue

        test_fresh=_compile_python_test_fresh_verification(clause,context_paths,root)
        if test_fresh is not None:
            actions.append(test_fresh["action"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"INDEPENDENT_PYTHON_TEST_CORPUS_VERIFICATION",
                **test_fresh["evidence"],
            })
            continue

        test_zero=_compile_python_test_zero_assertion(clause,context_paths,root)
        if test_zero is not None:
            actions.append(test_zero["action"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"PYTHON_TEST_ZERO_FAILURE_ASSERTION",
                **test_zero["evidence"],
            })
            continue

        test_audit=_compile_python_test_audit(clause,context_paths,registry,root)
        if test_audit is not None:
            actions.append(test_audit["action"])
            context_paths.append(test_audit["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"VERIFIED_PYTHON_TEST_AUDIT",
                **test_audit["evidence"],
            })
            continue

        python_verify=_compile_python_source_audit_verification(clause,context_paths,root)
        if python_verify is not None:
            actions.append(python_verify["action"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"INDEPENDENT_PYTHON_SOURCE_VERIFICATION",
                **python_verify["evidence"],
            })
            continue

        python_totals=_compile_python_audit_totals_assertion(clause,context_paths,root)
        if python_totals is not None:
            actions.append(python_totals["action"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"PYTHON_AUDIT_TOTALS_INCLUDED",
                **python_totals["evidence"],
            })
            continue

        python_audit=_compile_python_source_audit(clause,context_paths,registry,root)
        if python_audit is not None:
            actions.append(python_audit["action"])
            context_paths.append(python_audit["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"VERIFIED_PYTHON_SOURCE_AUDIT",
                **python_audit["evidence"],
            })
            continue

        workflow_verify=_compile_workflow_audit_raw_verification(clause,context_paths,root)
        if workflow_verify is not None:
            actions.append(workflow_verify["action"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"INDEPENDENT_WORKFLOW_SOURCE_VERIFICATION",
                **workflow_verify["evidence"],
            })
            continue

        workflow_audit=_compile_github_workflow_audit(clause,context_paths,registry,root)
        if workflow_audit is not None:
            actions.extend(workflow_audit["actions"])
            context_paths.append(workflow_audit["normalized_path"])
            context_paths.append(workflow_audit["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"VERIFIED_YAML_WORKFLOW_AUDIT",
                **workflow_audit["evidence"],
            })
            continue

        verification=_compile_pdf_json_key_verification(
            clause,context_paths,registry,root,len(actions)
        )
        if verification is not None:
            actions.extend(verification["actions"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"INDEPENDENT_CONTENT_VERIFICATION",
                **verification["evidence"],
            })
            continue

        provenance=_compile_pypi_provenance_audit(
            clause,context_paths,registry,root,future_clauses=clauses[index+1:]
        )
        if provenance is not None:
            actions.append(provenance["action"])
            context_paths.append(provenance["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"VERIFIED_PYPI_PROVENANCE",
                **provenance["evidence"],
            })
            continue

        hash_assert=_compile_json_hash_equality_assertion(clause,context_paths,root)
        if hash_assert is not None:
            actions.append(hash_assert["action"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"INDEPENDENT_JSON_INTEGRITY_ASSERTION",
                **hash_assert["evidence"],
            })
            continue

        existing=_compile_existing_causal_artifact_assertion(clause,context_paths,root)
        if existing is not None:
            actions.extend(existing["actions"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"CAUSAL_ARTIFACT_ALREADY_PRODUCED",
                **existing["evidence"],
            })
            continue

        live_fetch=_compile_context_url_json_fetch(clause,context_paths,registry,root)
        if live_fetch is not None:
            actions.append(live_fetch["action"])
            context_paths.append(live_fetch["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"VERIFIED_LIVE_JSON_FETCH",
                **live_fetch["evidence"],
            })
            continue

        selection=_compile_json_record_selection(clause,context_paths,registry,root)
        if selection is not None:
            actions.append(selection["action"])
            context_paths.append(selection["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"VERIFIED_STRUCTURED_SELECTION",
                **selection["evidence"],
            })
            continue

        structured=_compile_json_markdown_table(clause,context_paths,registry,root)
        if structured is not None:
            actions.append(structured["action"])
            context_paths.append(structured["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"VERIFIED_STRUCTURED_TRANSFORM",
                **structured["evidence"],
            })
            continue

        manifest=_compile_json_status_manifest(clause,context_paths,registry,root)
        if manifest is not None:
            actions.append(manifest["action"])
            context_paths.append(manifest["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"VERIFIED_STRUCTURED_MANIFEST",
                **manifest["evidence"],
            })
            continue
        release_verify=_compile_independent_web_release_verification(
            clause,context_paths,registry,root
        )
        if release_verify is not None:
            actions.append(release_verify["action"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"INDEPENDENT_WEB_RELEASE_VERIFICATION",
                **release_verify["evidence"],
            })
            continue

        semantic_fact=_compile_latest_stable_release_from_capture(
            clause,context_paths,registry,root
        )
        if semantic_fact is not None:
            actions.append(semantic_fact["action"])
            if semantic_fact["output_path"] not in context_paths:
                context_paths.append(semantic_fact["output_path"])
            compiled_parts.append({
                "index":index,"subgoal":clause,
                "mode":"VERIFIED_STRUCTURED_SEMANTIC_EXTRACTION",
                **semantic_fact["evidence"],
            })
            continue

        if re.match(r"^(?:finally\s+)?independently\s+decode\b",lower):
            prior=None
            for item in reversed(compiled_parts):
                cid=item.get("selected_capability") if isinstance(item,dict) else None
                entry=(registry or {}).get(cid) if cid else None
                if isinstance(entry,dict) and entry.get("adapter_module") in {"python_library_codec","python_source_tree_codec","node_library_codec"}:
                    if _execution_surface_constraint_match(clause,entry)[0]:
                        prior=(item,entry)
                        break
            if prior is not None:
                item,entry=prior
                inputs=item.get("inputs") or {}
                template_args=((entry.get("action_template") or {}).get("args") or {})
                json_path=inputs.get("json_path")
                binary_path=inputs.get("output_path")
                adapter=str(entry.get("adapter_module") or "")
                requires_distinct_implementation=bool(re.search(
                    r"(?:implementation\s+that\s+is\s+not\s+provided\s+by|different\s+implementation|not\s+provided\s+by\s+the\s+.+?producer|producer-independent)",
                    lower,re.IGNORECASE
                ))
                if adapter in {"python_library_codec","python_source_tree_codec"}:
                    module=template_args.get("module")
                    decode_callable=template_args.get("decode_callable")
                    decode_kwargs=template_args.get("decode_kwargs") or {}
                    envelope_key=template_args.get("envelope_key")
                    if all(isinstance(x,str) and x for x in (json_path,binary_path,module,decode_callable)):
                        if requires_distinct_implementation:
                            source=entry.get("source") or {}
                            producer_project=str(source.get("project") or source.get("repository") or "")
                            fmt=pathlib.Path(str(binary_path)).suffix.lower().lstrip(".")
                            if not producer_project or not fmt:
                                raise GoalCompilationFailure(
                                    "INDEPENDENT_CODEC_VERIFIER_BINDING_REQUIRED",
                                    json.dumps({
                                      "capability_id":item["selected_capability"],
                                      "producer_project":producer_project,
                                      "binary_path":binary_path,
                                    },sort_keys=True)
                                )
                            actions.append({
                              "type":"verify_with_independent_npm_codec",
                              "args":{
                                "format":fmt,
                                "json_path":json_path,
                                "binary_path":binary_path,
                                "producer_project":producer_project,
                                "producer_capability_id":item["selected_capability"],
                              },
                              "expect":{"type":"field_equals","field":"verified","value":True},
                            })
                            compiled_parts.append({
                              "index":index,"subgoal":clause,
                              "mode":"CROSS_SUPPLIER_PRODUCER_INDEPENDENT_CODEC_VERIFICATION",
                              "producer_capability":item["selected_capability"],
                              "producer_project":producer_project,
                              "verifier_supplier_class":"npm_javascript_library",
                              "format":fmt,
                              "json_path":json_path,
                              "binary_path":binary_path,
                            })
                        elif adapter=="python_library_codec":
                            actions.append({
                              "type":"invoke_capability",
                              "args":{
                                "capability_id":item["selected_capability"],
                                "mode":"decode_verify",
                                "module":module,
                                "decode_callable":decode_callable,
                                "decode_kwargs":decode_kwargs,
                                "envelope_key":envelope_key,
                                "json_path":json_path,
                                "binary_path":binary_path,
                              },
                              "expect":{"type":"field_equals","field":"verified","value":True},
                            })
                            compiled_parts.append({
                              "index":index,"subgoal":clause,
                              "mode":"INDEPENDENT_PYTHON_CODEC_ROUNDTRIP_VERIFICATION",
                              "selected_capability":item["selected_capability"],
                              "json_path":json_path,
                              "binary_path":binary_path,
                              "decode_callable":decode_callable,
                              "envelope_key":envelope_key,
                            })
                        continue
                elif adapter=="node_library_codec":
                    package=template_args.get("package")
                    root_selector=template_args.get("root_selector")
                    encode_export=template_args.get("encode_export")
                    decode_export=template_args.get("decode_export")
                    if all(isinstance(x,str) and x for x in (
                        json_path,binary_path,package,root_selector,encode_export,decode_export
                    )):
                        if requires_distinct_implementation:
                            source=entry.get("source") or {}
                            producer_project=str(source.get("package") or package or "")
                            fmt=pathlib.Path(str(binary_path)).suffix.lower().lstrip(".")
                            if not producer_project or not fmt:
                                raise GoalCompilationFailure(
                                    "INDEPENDENT_NODE_CODEC_VERIFIER_BINDING_REQUIRED",
                                    json.dumps({
                                      "capability_id":item["selected_capability"],
                                      "package":package,
                                      "binary_path":binary_path,
                                    },sort_keys=True)
                                )
                            actions.append({
                              "type":"verify_with_independent_pypi_codec",
                              "args":{
                                "format":fmt,
                                "json_path":json_path,
                                "binary_path":binary_path,
                                "producer_project":producer_project,
                                "producer_capability_id":item["selected_capability"],
                              },
                              "expect":{"type":"field_equals","field":"verified","value":True},
                            })
                            compiled_parts.append({
                              "index":index,"subgoal":clause,
                              "mode":"CROSS_SUPPLIER_PRODUCER_INDEPENDENT_CODEC_VERIFICATION",
                              "producer_capability":item["selected_capability"],
                              "producer_project":producer_project,
                              "verifier_supplier_class":"pypi_python_library",
                              "format":fmt,
                              "json_path":json_path,
                              "binary_path":binary_path,
                            })
                            continue
                        actions.append({
                          "type":"invoke_capability",
                          "args":{
                            "capability_id":item["selected_capability"],
                            "mode":"decode_verify",
                            "package":package,
                            "root_selector":root_selector,
                            "encode_export":encode_export,
                            "decode_export":decode_export,
                            "json_path":json_path,
                            "binary_path":binary_path,
                          },
                          "expect":{"type":"field_equals","field":"verified","value":True},
                        })
                        compiled_parts.append({
                          "index":index,"subgoal":clause,
                          "mode":"FRESH_NODE_CODEC_ROUNDTRIP_VERIFICATION",
                          "selected_capability":item["selected_capability"],
                          "package":package,
                          "json_path":json_path,
                          "binary_path":binary_path,
                          "decode_export":decode_export,
                        })
                        continue

        if re.match(r"^(?:if|otherwise|for\s+every|for\s+each)\b",lower):
            raise GoalCompilationFailure(
                "GOAL_CONTROL_FLOW_UNSUPPORTED",
                json.dumps({"index":index,"subgoal":clause},sort_keys=True)
            )
        if (
            re.match(r"^using\s+both\s+live\s+results\b",lower)
            or re.match(r"^from\s+(?:these\s+two|both)\s+live\s+datasets\b",lower)
            or re.match(r"^take\s+(?:those\s+two|both)\s+observed\s+datasets\b",lower)
        ):
            raise GoalCompilationFailure(
                "GOAL_CAUSAL_COMPOSITION_UNSUPPORTED",
                json.dumps({"index":index,"subgoal":clause},sort_keys=True)
            )

        try:
            part=_compile_single_goal(
                clause,registry,root,
                context_paths=context_paths,
                future_clauses=clauses[index+1:],
                proposal_binder=proposal_binder,
                effect_providers=effect_providers,
            )
        except GoalCompilationFailure as exc:
            raise GoalCompilationFailure(
                "GOAL_COMPILATION_SUBGOAL_UNRESOLVED",
                json.dumps({
                    "index":index,
                    "subgoal":clause,
                    "cause":exc.code,
                    "cause_detail":exc.detail,
                    "clauses":clauses,
                    "compiled_prefix":compiled_parts,
                    "context_paths":context_paths,
                },sort_keys=True)
            ) from exc
        cid=part["selected_capability"]
        entry=registry[cid]
        if re.match(r"^(?:finally\s+)?(?:independently\s+)?(?:verify|check|assert|decode|reopen|reread)\b",lower):
            semantic=" ".join(
                [str(x) for x in entry.get("provides",[])]
                +[str(x) for x in entry.get("keywords",[])]
                +[str(cid)]
            ).lower()
            if not any(token in semantic for token in ("verify","decode","audit","check","assert","validate")):
                raise GoalCompilationFailure(
                    "GOAL_VERIFICATION_CAPABILITY_REQUIRED",
                    json.dumps({"index":index,"subgoal":clause,"rejected_capability":cid},sort_keys=True)
                )
        runtime_inputs=part["inputs"]
        if _uses_effect_result_bindings(entry):
            consumer=_planner_capability(planner,cid,entry)
            try:
                runtime_inputs=planner._resolve_effect_bindings(
                    part["inputs"],consumer,runtime_effect_providers
                )
            except Exception as exc:
                raise GoalCompilationFailure(
                    "GOAL_CAUSAL_BINDING_LOWERING_FAILED",
                    str(cid)+":"+type(exc).__name__+":"+str(exc),
                ) from exc
        action=_render_template(entry["action_template"],runtime_inputs)
        actions.append(action)
        for key,value in runtime_inputs.items():
            if (
                isinstance(key,str) and key.endswith("_path")
                and isinstance(value,str) and pathlib.Path(value).suffix
                and value not in context_paths
            ):
                context_paths.append(value)
        producer_cap=_planner_capability(planner,cid,entry,action)
        producer_cycle=len(actions)-1
        for effect in entry.get("provides") or []:
            effect=str(effect)
            effect_providers[effect]=(cid,entry)
            runtime_effect_providers[effect]=(producer_cycle,producer_cap)
        compiled_parts.append({
            "index":index,
            "subgoal":clause,
            "mode":"VERIFIED_CAPABILITY",
            "selected_capability":cid,
            "inputs":runtime_inputs,
            "target_effects":part["target_effects"],
            "score":part["score"],
        })
    actions.append({
        "type":"finish",
        "args":{"summary":"COMPOUND_GOAL_COMPLETE"},
    })
    return {
        "schema":"PROJECT_BRAIN_COMPILED_COMPOUND_GOAL_V1",
        "compiler_mode":"DETERMINISTIC_COMPOUND_ACTION_PLAN",
        "clauses":clauses,
        "compiled_parts":compiled_parts,
        "controller_actions":actions,
        "finish_summary":"COMPOUND_GOAL_COMPLETE",
    }


def _compile_domain_free_authority_source_goal(goal,clauses,registry,root):
    text=" ".join(str(goal or "").strip().split())
    m=re.search(
        r"\bfind\s+the\s+authoritative\s+(.+?)\s+source\s+for\s+"
        r"(?:indicator|series|code|item|subject)\s+([A-Za-z0-9][A-Za-z0-9._:-]{2,})\b",
        text,re.IGNORECASE
    )
    if not m:
        return None
    lower=text.lower()
    if "authority domain" not in lower or "source url" not in lower:
        return None
    if not any(x in lower for x in ("verify the official authority site","verify the authority site")):
        return None
    if "semantically relevant" not in lower:
        return None

    entity_name=m.group(1).strip(" ,.;:")
    subject_id=m.group(2).strip(" ,.;:")
    if not entity_name or not subject_id:
        return None
    entry=(registry or {}).get("web.browser.rendered.capture.chromedriver")
    if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
        raise GoalCompilationFailure("AUTHORITY_SOURCE_BROWSER_CAPABILITY_REQUIRED")

    digest=hashlib.sha256(text.encode("utf-8")).hexdigest()[:12].upper()
    prefix="canonical/astra_runtime/tmp/AUTHORITY_SOURCE_"+digest
    identity_path=prefix+"_IDENTITY.json"
    home_screen=prefix+"_HOME.png"
    home_result=prefix+"_HOME_RENDER.json"
    discovery_path=prefix+"_DISCOVERY.json"
    source_screen=prefix+"_SOURCE.png"
    source_result=prefix+"_SOURCE_RENDER.json"
    query=f"{entity_name} {subject_id} official source"

    extraction_spec=None
    extraction_index=None
    extraction_verify_index=None
    recognized_clause_modes={}
    for index,clause in enumerate(clauses):
        cl=str(clause or "").strip()
        low=cl.lower()
        if index==0 and "find the authoritative" in low:
            recognized_clause_modes[index]="DOMAIN_FREE_AUTHORITY_SOURCE_RESOLUTION"
            continue
        if "semantically relevant" in low and subject_id.lower() in low:
            recognized_clause_modes[index]="DOMAIN_FREE_AUTHORITY_SOURCE_SEMANTIC_VERIFICATION"
            continue
        em=re.match(
            r"^extract\s+the\s+source\s+fields\s+(.+?)\s+and\s+save\s+"
            r"([^\s]+\.json)\s+containing\s+exactly\s+one\s+record\s+with\s+fields\s+(.+)$",
            cl,re.IGNORECASE
        )
        if em:
            raw_labels=re.sub(r"\s+and\s+",",",em.group(1),flags=re.IGNORECASE)
            raw_outputs=re.sub(r"\s+and\s+",",",em.group(3),flags=re.IGNORECASE)
            labels=[x.strip(" .,:;") for x in raw_labels.split(",") if x.strip(" .,:;")]
            outputs=[x.strip(" .,:;") for x in raw_outputs.split(",") if x.strip(" .,:;")]
            if (
                not labels or len(labels)!=len(outputs)
                or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",x) for x in outputs)
            ):
                raise GoalCompilationFailure(
                    "SEMANTIC_EXTRACTION_FIELD_MAPPING_INVALID",
                    json.dumps({"labels":labels,"outputs":outputs},sort_keys=True)
                )
            extraction_spec={
              "output_path":em.group(2).strip(" .,:;"),
              "fields":[
                {"label":label,"output_field":output}
                for label,output in zip(labels,outputs)
              ],
            }
            extraction_index=index
            recognized_clause_modes[index]="SEMANTIC_LABELED_FIELD_EXTRACTION"
            continue
        if re.match(
            r"^finally\s+independently\s+verify\s+the\s+saved\s+values\s+against\s+"
            r"a\s+fresh\s+retrieval\s+of\s+the\s+discovered\s+authoritative\s+source$",
            cl,re.IGNORECASE
        ):
            extraction_verify_index=index
            recognized_clause_modes[index]="INDEPENDENT_FRESH_SOURCE_FIELD_VERIFICATION"
            continue

    if extraction_spec is not None and extraction_verify_index is None:
        raise GoalCompilationFailure("SEMANTIC_EXTRACTION_INDEPENDENT_VERIFICATION_REQUIRED")
    if extraction_verify_index is not None and extraction_spec is None:
        raise GoalCompilationFailure("SEMANTIC_EXTRACTION_SPEC_REQUIRED")
    unrecognized=[i for i in range(len(clauses)) if i not in recognized_clause_modes]
    if unrecognized:
        raise GoalCompilationFailure(
            "DOMAIN_FREE_AUTHORITY_SOURCE_UNCONSUMED_CLAUSE",
            json.dumps({"indices":unrecognized,"clauses":[clauses[i] for i in unrecognized]},sort_keys=True)
        )

    actions=[
      {
        "type":"resolve_authority_identity",
        "args":{
          "entity_name":entity_name,
          "output_path":identity_path,
          "timeout_s":20,
        },
        "expect":{"type":"field_equals","field":"verified","value":True},
      },
      {
        "type":"invoke_capability",
        "args":{
          "capability_id":"web.browser.rendered.capture.chromedriver",
          "url":{"$result":{"cycle":0,"field":"official_url"}},
          "screenshot_path":home_screen,
          "result_path":home_result,
        },
        "expect":{"type":"field_equals","field":"output_verified","value":True},
      },
      {
        "type":"assert_authority_identity",
        "args":{
          "evidence_path":identity_path,
          "browser_result_path":home_result,
        },
        "expect":{"type":"field_equals","field":"verified","value":True},
      },
      {
        "type":"discover_authoritative_web_source",
        "args":{
          "query":query,
          "authority_domains":[{"$result":{"cycle":0,"field":"authority_domain"}}],
          "output_path":discovery_path,
          "timeout_s":20,
          "max_bytes":1500000,
        },
        "expect":{"type":"field_equals","field":"verified","value":True},
      },
      {
        "type":"invoke_capability",
        "args":{
          "capability_id":"web.browser.rendered.capture.chromedriver",
          "url":{"$result":{"cycle":3,"field":"chosen_url"}},
          "screenshot_path":source_screen,
          "result_path":source_result,
        },
        "expect":{"type":"field_equals","field":"output_verified","value":True},
      },
      {
        "type":"assert_authoritative_source_discovery",
        "args":{
          "evidence_path":discovery_path,
          "browser_result_path":source_result,
        },
        "expect":{"type":"field_equals","field":"verified","value":True},
      },
    ]
    if extraction_spec is not None:
        actions.append({
          "type":"extract_labeled_fields_from_rendered_source",
          "args":{
            "browser_result_path":source_result,
            "output_path":extraction_spec["output_path"],
            "fields":extraction_spec["fields"],
          },
          "expect":{"type":"field_equals","field":"verified","value":True},
        })
        actions.append({
          "type":"assert_labeled_fields_against_fresh_source",
          "args":{
            "browser_result_path":source_result,
            "extracted_path":extraction_spec["output_path"],
            "fields":extraction_spec["fields"],
            "timeout_s":20,
            "max_bytes":2000000,
          },
          "expect":{"type":"field_equals","field":"verified","value":True},
        })
    actions.append({"type":"finish","args":{"summary":"COMPOUND_GOAL_COMPLETE"}})
    frame_evidence={
      "entity_name":entity_name,
      "subject_id":subject_id,
      "query":query,
      "identity_evidence_path":identity_path,
      "authority_home_result_path":home_result,
      "source_discovery_path":discovery_path,
      "source_result_path":source_result,
      "authority_domain_from_runtime":True,
      "source_url_from_runtime":True,
      "semantic_relevance_required":True,
    }
    parts=[]
    for index,clause in enumerate(clauses):
        mode=recognized_clause_modes[index]
        part={
          "index":index,
          "subgoal":clause,
          "mode":mode,
          **frame_evidence,
        }
        if mode=="SEMANTIC_LABELED_FIELD_EXTRACTION":
            part["output_path"]=extraction_spec["output_path"]
            part["fields"]=extraction_spec["fields"]
        elif mode=="INDEPENDENT_FRESH_SOURCE_FIELD_VERIFICATION":
            part["extracted_path"]=extraction_spec["output_path"]
            part["fields"]=extraction_spec["fields"]
        parts.append(part)
    return {
      "schema":"PROJECT_BRAIN_COMPILED_COMPOUND_GOAL_V1",
      "compiler_mode":"DETERMINISTIC_DOMAIN_FREE_AUTHORITY_SOURCE_PLAN",
      "clauses":clauses,
      "compiled_parts":parts,
      "controller_actions":actions,
      "finish_summary":"COMPOUND_GOAL_COMPLETE",
    }


def _validate_compiled_clause_coverage(compiled):
    if not isinstance(compiled,dict):
        raise GoalCompilationFailure("COMPILED_PLAN_INVALID")
    clauses=compiled.get("clauses")
    parts=compiled.get("compiled_parts")
    if clauses is None and parts is None:
        return compiled
    if not isinstance(clauses,list) or not isinstance(parts,list):
        raise GoalCompilationFailure("COMPILED_CLAUSE_COVERAGE_METADATA_INVALID")
    indexes=[]
    for part in parts:
        if not isinstance(part,dict) or not isinstance(part.get("index"),int):
            raise GoalCompilationFailure("COMPILED_CLAUSE_INDEX_INVALID")
        indexes.append(part["index"])
    expected=list(range(len(clauses)))
    if sorted(indexes)!=expected:
        missing=sorted(set(expected)-set(indexes))
        duplicate=sorted({x for x in indexes if indexes.count(x)>1})
        extra=sorted(set(indexes)-set(expected))
        raise GoalCompilationFailure(
            "COMPILED_CLAUSE_COVERAGE_INCOMPLETE",
            json.dumps({
              "missing":missing,
              "duplicate":duplicate,
              "extra":extra,
              "clause_count":len(clauses),
              "compiler_mode":compiled.get("compiler_mode"),
            },sort_keys=True)
        )
    compiled=dict(compiled)
    compiled["clause_coverage_verified"]=True
    return compiled


def compile_goal(goal, registry, root):
    goal=str(goal or "").strip()
    if not goal:
        raise GoalCompilationFailure("GOAL_REQUIRED")
    browser_interaction=_compile_verified_browser_interaction(goal,registry,root)
    if browser_interaction is not None:
        return _validate_compiled_clause_coverage(browser_interaction)
    clauses=decompose_goal(goal)
    authority_source=_compile_domain_free_authority_source_goal(goal,clauses,registry,root)
    if authority_source is not None:
        return _validate_compiled_clause_coverage(authority_source)
    bounded_loop=_compile_bounded_loop_goal(goal,clauses,registry,root)
    if bounded_loop is not None:
        return _validate_compiled_clause_coverage(bounded_loop)
    multi_source_reduce=_compile_multi_source_reduce_goal(goal,clauses,registry,root)
    if multi_source_reduce is not None:
        return _validate_compiled_clause_coverage(multi_source_reduce)
    multi_source_join=_compile_multi_source_join_goal(goal,clauses,registry,root)
    if multi_source_join is not None:
        return _validate_compiled_clause_coverage(multi_source_join)
    per_item_fallback=_compile_per_item_fallback_goal(goal,clauses,registry,root)
    if per_item_fallback is not None:
        return _validate_compiled_clause_coverage(per_item_fallback)
    multi_action_fanout=_compile_multi_action_fanout_goal(goal,clauses,registry,root)
    if multi_action_fanout is not None:
        return _validate_compiled_clause_coverage(multi_action_fanout)
    dynamic_fanout=_compile_dynamic_fanout_goal(goal,clauses,registry,root)
    if dynamic_fanout is not None:
        return _validate_compiled_clause_coverage(dynamic_fanout)
    runtime_fallback=_compile_runtime_fallback_goal(goal,clauses,registry,root)
    if runtime_fallback is not None:
        return _validate_compiled_clause_coverage(runtime_fallback)
    if len(clauses)>1:
        return _validate_compiled_clause_coverage(
            _compile_compound_goal(goal,clauses,registry,root)
        )
    return _compile_single_goal(goal,registry,root)
