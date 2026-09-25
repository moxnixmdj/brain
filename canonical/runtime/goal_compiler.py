#!/usr/bin/env python3
"""Deterministic plain-goal compiler for Project Brain.

Purpose: remove hand-authored target_effects/initial_facts for goals that
clearly map to already verified bound capabilities. It intentionally fails
closed on unknown or ambiguous goals so the next missing mechanism remains
observable instead of being guessed.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re


class GoalCompilationFailure(RuntimeError):
    def __init__(self, code, detail=None):
        self.code=code
        self.detail=detail
        super().__init__(code if detail is None else f"{code}:{detail}")


STOPWORDS={
    "the","a","an","to","from","of","and","or","with","using","use","do","for",
    "which","is","are","be","this","that","into","on","in","visible"
}

GENERIC_MATCH_TOKENS={
    "generate","image","text","extract","create","save","output","input",
    "file","read","write","convert","process","data"
}


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
        if suffixes and p.suffix.lower() in suffixes:
            candidates.append(str(raw))
        elif stem in {"input","source"}:
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
                # Single-path fallback is safe only for an actual typed file,
                # never for URL fragments or extensionless directory-like text.
                if len(paths)==1 and pathlib.Path(paths[0][0]).suffix:
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


def _score(goal, cid, entry):
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


def _compile_single_goal(goal, registry, root, context_paths=None, future_clauses=None):
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
            inputs=_bind_inputs(goal,root,entry,context_paths=context_paths,future_clauses=future_clauses)
        except GoalCompilationFailure:
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
    m=re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\s+type\s+(?:is|equals?|=)\s+([A-Za-z0-9_.-]+)\b",lower)
    nested_field=None
    nested_value=None
    if m:
        nested_field=[m.group(1),"type"]
        nested_value=m.group(2)
    else:
        m=re.search(r"\bsource\s+type\s+(?:is|equals?|=)\s+([A-Za-z0-9_.-]+)\b",lower)
        if m:
            nested_field=["source","type"]
            nested_value=m.group(1)
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
        for value in part["inputs"].values():
            if isinstance(value,str) and pathlib.Path(value).suffix and value not in context_paths:
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


def _compile_compound_goal(goal, clauses, registry, root):
    actions=[]
    compiled_parts=[]
    context_paths=[]
    consumed_indices=set()
    for index,clause in enumerate(clauses):
        if index in consumed_indices:
            continue
        lower=clause.lower()

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

        try:
            part=_compile_single_goal(
                clause,registry,root,
                context_paths=context_paths,
                future_clauses=clauses[index+1:]
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
        action=_render_template(entry["action_template"],part["inputs"])
        actions.append(action)
        for value in part["inputs"].values():
            if isinstance(value,str) and pathlib.Path(value).suffix:
                context_paths.append(value)
        compiled_parts.append({
            "index":index,
            "subgoal":clause,
            "mode":"VERIFIED_CAPABILITY",
            "selected_capability":cid,
            "inputs":part["inputs"],
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


def compile_goal(goal, registry, root):
    goal=str(goal or "").strip()
    if not goal:
        raise GoalCompilationFailure("GOAL_REQUIRED")
    browser_interaction=_compile_verified_browser_interaction(goal,registry,root)
    if browser_interaction is not None:
        return browser_interaction
    clauses=decompose_goal(goal)
    dynamic_fanout=_compile_dynamic_fanout_goal(goal,clauses,registry,root)
    if dynamic_fanout is not None:
        return dynamic_fanout
    if len(clauses)>1:
        return _compile_compound_goal(goal,clauses,registry,root)
    return _compile_single_goal(goal,registry,root)
