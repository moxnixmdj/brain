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
    for raw in re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+",goal):
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


def _bind_inputs(goal, root, entry, context_paths=None):
    template=entry.get("action_template") or {}
    keys=_placeholders(template)
    if not keys:
        return {}
    paths=_repo_paths(goal,root)
    result={}
    for key in keys:
        if key=="text":
            result[key]=_extract_text_argument(goal)
            continue
        if key.endswith("_path"):
            stem=key[:-5].lower()
            if key.startswith("output_"):
                # Output paths are expected not to exist yet. Bind only a
                # repository-safe path explicitly present in the goal.
                matching=[raw for raw,p in paths if (not stem or stem in raw.lower() or p.suffix.lower() in {".png",".jpg",".jpeg",".pdf",".txt",".json",".csv",".md"})]
                if len(matching)==1:
                    result[key]=matching[0]
                    continue
                if len(paths)==1:
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
    return clauses


def _compile_single_goal(goal, registry, root, context_paths=None):
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
            inputs=_bind_inputs(goal,root,entry,context_paths=context_paths)
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
    matches=[p for p in paths if p in set(context_paths or [])]
    if len(matches)!=1:
        return None
    path=matches[0]
    action={
      "type":"assert_file_exists",
      "args":{"path":path},
      "expect":{"type":"field_equals","field":"verified","value":True},
    }
    return {"action":action,"evidence":{"path":path}}


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


def _compile_compound_goal(goal, clauses, registry, root):
    actions=[]
    compiled_parts=[]
    context_paths=[]
    for index,clause in enumerate(clauses):
        lower=clause.lower()
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
            actions.append(existing["action"])
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
        try:
            part=_compile_single_goal(clause,registry,root,context_paths=context_paths)
        except GoalCompilationFailure as exc:
            raise GoalCompilationFailure(
                "GOAL_COMPILATION_SUBGOAL_UNRESOLVED",
                json.dumps({
                    "index":index,
                    "subgoal":clause,
                    "cause":exc.code,
                    "cause_detail":exc.detail,
                    "clauses":clauses,
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
    clauses=decompose_goal(goal)
    if len(clauses)>1:
        return _compile_compound_goal(goal,clauses,registry,root)
    return _compile_single_goal(goal,registry,root)
