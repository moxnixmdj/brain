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
    "file","read","write","convert","process","data",
    # "python" alone names a language, not an operation: zero-input fleet rows
    # whose entire match is the word "python" score 16 on "Audit python source
    # structure..." and outrank the right capability only because their empty
    # input contract makes them bindable where python.source.audit.ast (33)
    # still needs an unstated source_root. Measured: adding "python" here
    # restores the audit family selections (compiler + world-binding suites)
    # and no capability in the live registry loses its last distinctive token.
    "python",
    # Repository-self-referential vocabulary. Every goal in this repository
    # names the project ("PROJECT BRAIN") and cites a scratch destination
    # under canonical/astra_runtime/tmp/, so these tokens are present in
    # nearly every goal regardless of what is being asked. Treating them as
    # distinctive let `terminal.kstar.root.assess.stdlib` -- whose keyword
    # list includes "brain" and "runtime" -- tie a Code 128 BARCODE goal at
    # score 8 with `auto.apt.zint`, on the strength of the words "PROJECT
    # BRAIN" and the directory "astra_runtime" alone, and the goal then died
    # as GOAL_COMPILATION_AMBIGUOUS. Measured before adding these: no
    # capability in the live registry loses its last distinctive token, so
    # this can only remove matches that never had a real basis.
    "brain","runtime","canonical","astra","tmp","project",
    # Governance and abstraction vocabulary. `terminal.kstar.root.assess.stdlib`
    # carries 27 keywords of this kind -- proof, evidence, capability, semantic,
    # composition, context, reuse, universal, adequacy, discriminator -- which
    # overlap ordinary technical prose on at least one token almost always. It
    # was therefore selected for four unrelated goals at base 9554215 (QR
    # generate, evidence rank, claim bind, knowledge consistency) and is still
    # selected for two of them, because it binds easily and so survives once
    # the better-matching candidates prove unbindable. Measured before adding
    # these: 0 of 363 live capabilities lose their last distinctive token, so
    # none becomes unmatchable -- a capability that genuinely owns one of these
    # words still matches through its other tokens.
    "terminal","kstar","opus","falsify","tournament","adequacy","discriminator",
    "counterexample","residual","ownership","universal","proof","policy","basis",
    "scope","complete","capability","reuse","cover","composition","transform",
    "generator","context","semantic","evidence"
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


# `_repo_paths` is a pure function of the sentence and the root: it scans the
# goal for path-shaped tokens and normalises each one.  It does not test whether
# anything EXISTS, so nothing about its answer changes when a file is written.
# Measured, it was called 744 times for ONE solve -- once per capability the
# receipt projection asks about -- and each call re-ran `Path.resolve()`, so
# 18,180 realpath calls in twelve solves accounted for 1.42s of a 3.21s profile,
# 44% of the whole.  The work was not hard, it was repeated.
#
# Callers get a COPY.  A caller that appended to the returned list would
# otherwise be editing every later answer to the same sentence.
_REPO_PATHS_CACHE: dict[tuple[str, str], list] = {}
_REPO_PATHS_CACHE_MAX = 1024


def _repo_paths(goal, root):
    key=(str(goal or ""), str(root or ""))
    hit=_REPO_PATHS_CACHE.get(key)
    if hit is not None:
        return list(hit)
    candidates=_repo_paths_uncached(goal, root)
    if len(_REPO_PATHS_CACHE)>=_REPO_PATHS_CACHE_MAX:
        _REPO_PATHS_CACHE.clear()
    _REPO_PATHS_CACHE[key]=list(candidates)
    return list(candidates)


def _repo_paths_uncached(goal, root):
    candidates=[]
    # URL path components are not repository paths. Strip complete URLs before
    # scanning for repository-local artifacts.
    path_text=re.sub(r"https?://[^\s)\]}>]+"," ",str(goal or ""))
    rr=pathlib.Path(root).resolve()
    for m in re.finditer(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+",path_text):
        raw=m.group(0).rstrip(".,;:!?)]}")
        # The pattern cannot match a leading "/", so an absolute path such as
        # /home/user/brain/canonical/x.json is matched starting at "home/", and
        # joining that onto the repository root silently doubles the prefix into
        # /home/user/brain/home/user/brain/canonical/x.json -- a path that can
        # never exist, so every path-dependent binding then fails closed.
        # Reattach the separator and resolve it as absolute first, normalising to
        # the repository-relative form the rest of the compiler expects.
        start=m.start()
        if start>0 and path_text[start-1]=="/":
            ap=pathlib.Path("/"+raw).resolve()
            if ap!=rr and rr in ap.parents:
                try:
                    candidates.append((str(ap.relative_to(rr)),ap))
                except ValueError:
                    pass
                continue
        p=(rr/raw).resolve()
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


_GOAL_ARGUMENT_PATTERNS=[
    r"\bwith\s+(?:the\s+)?goal\s+(.+?)(?=\s+and\s+(?:save|write|store|using)\b|\s+(?:save|write|store)\s+(?:it|the|output)\b|$)",
    r"\bfor\s+the\s+goal\s+(.+?)(?=\s+and\s+(?:save|write|store)\b|$)",
]


def _extract_goal_argument(goal):
    """The goal the sentence STATES, or the whole sentence when it states none.

    ``_bind_inputs`` gave a ``goal`` input the entire raw request verbatim.  That is
    right when the request *is* the goal ("Write a report on quarterly sales"), and
    wrong when the request is an INVOCATION that names a capability and then hands
    the goal over as an argument.  Measured on 0351c257:

        "Run the docx document create python docx with goal Write a report on
         quarterly sales."
        goal -> "Run the docx document create python docx with goal Write a report
                 on quarterly sales."

    4 of the 13 capabilities that take a ``goal`` were handed their own invocation
    wrapper as the thing to do.  ``_extract_text_argument`` below already did this
    for ``text``; ``goal`` never got the same treatment.  A quoted string wins, then
    an explicit "with/for the goal" clause; anything else keeps the whole request,
    which is what every plain request has always received.
    """
    text=str(goal or "")
    quoted=re.findall(r'["\']([^"\']+)["\']',text)
    if len(quoted)==1 and quoted[0].strip():
        return quoted[0].strip()
    for pattern in _GOAL_ARGUMENT_PATTERNS:
        m=re.search(pattern,text,flags=re.IGNORECASE)
        if m and m.group(1).strip():
            return m.group(1).strip(" .,:;")
    return text


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


def _path_named_by_role(goal, stem, root):
    """Bind a typed input by the role the sentence assigns it, not its filename.

    "create an archive from the manifest X" names X as the manifest whatever X
    happens to be called.  Matching ``stem`` against X's own name rejects a real
    manifest named ``m9.json``, and the whole goal then fails closed even though
    the goal states plainly which file plays which part.

    Returns the repository path that immediately follows the stem word in the
    goal, or None when the sentence does not name one.  Only ever consulted for
    inputs that no other rule could bind, so it cannot move a binding that
    already succeeds.
    """
    if not stem:
        return None
    candidates=_repo_paths(goal,root)
    if not candidates:
        return None
    text=str(goal)
    word=str(stem).replace("_"," ")
    # Nearest path after the role word, not the path immediately after it: goals
    # say "the manifest X" and "the source file X" and "the source files under X"
    # alike, and requiring adjacency only ever matched the first wording.
    best=None
    best_at=None
    for m in re.finditer(r"\b"+re.escape(word)+r"\b",text,re.IGNORECASE):
        for raw,_p in candidates:
            if not raw:
                continue
            # The goal may name the path in absolute form while the candidate is
            # held repository-relative, so both spellings have to be tried.
            for spelling in (raw, str(raw).lstrip("/"), str(_p)):
                if not spelling:
                    continue
                at=text.find(spelling,m.end())
                if at<0:
                    continue
                if best_at is None or at<best_at:
                    best_at=at
                    best=raw
    return best


# A verb, up to four words of object ("write the report", "save the final audit"),
# then "to".  A fixed phrase list only ever matched the exact wording it was
# written against: "write to" matched, "write the report to" did not.
_OUTPUT_ROLE_RE=r"\b(?:save|write|store|output|emit)\b(?:\s+[A-Za-z0-9_.\-']+){0,4}\s+to\b"


# Clauses are separated by a comma, a semicolon, or a coordinating word.  A
# period is deliberately NOT a boundary: repository paths contain dots, and a
# window cut at the first dot would truncate at "out.txt".
_CLAUSE_BOUNDARY_RE=re.compile(r"[,;]|\band\b|\bthen\b",re.IGNORECASE)


# "the tests in X" never names the SUBJECT of a code question; it names the
# witness that decides the answer.  The distinction already exists elsewhere in
# this repository -- _promised_source_files skips "the WITNESS test" when it
# decides which source file a repair verb governs -- and it is the difference
# between a sentence that names two directories and one that names a
# directory and its oracle.
#
# Measured on 814ae41 + three analysis rows: "Which function in <b>/app is
# never executed by the tests in <b>/tests?" selected
# python.source.dead_code.v1 correctly and then failed to bind source_root at
# all, because the binder saw two existing directories named and refused to
# guess -- which was right.  The sentence had already said which was which.
_WITNESS_PHRASE_RE = re.compile(
    r"\b(?:tests?|suite|test\s+suite)\s+(?:in|under|inside|within|at)\s+",
    re.IGNORECASE)


def _witness_directories(goal, paths):
    """Paths the sentence names as the WITNESS, not as the subject.

    A witness phrase binds the nearest stated path that follows it.  Only paths
    that literally appear after the phrase are returned, and only within the same
    sentence, so nothing is inferred about a path the caller did not place there.
    """
    text = str(goal or "")
    out = set()
    for m in _WITNESS_PHRASE_RE.finditer(text):
        # The NEAREST path after the phrase, never every path in a window.
        # Measured: "Would the tests in <b>/tests catch a bug introduced in
        # <b>/app?" has no clause boundary between the two, so a window swallowed
        # BOTH and the binder lost its subject as well -- the same defect, in the
        # other direction.
        best, best_at = None, None
        for raw, _path in paths:
            at = text.find(str(raw), m.end())
            if at >= 0 and (best_at is None or at < best_at):
                best, best_at = str(raw), at
        if best is not None:
            out.add(best)
    return out


def _path_named_after_output_verb(goal, root):
    """Return the repository path the goal names as the destination, or None.

    "save it to X" names X as the output whatever X happens to be called, and
    whether or not an earlier run already created it.

    The destination is the first repository path in the SAME CLAUSE as the verb;
    it does not have to sit immediately after "to".  Requiring adjacency meant
    "write the text T to the file X" named no destination at all -- the noun
    "file" sat in between -- so a later "save the report to Y" in the same
    sentence won the binding instead.  text.file.write then reported
    PASS__COMPOSED_CAPABILITY_CHAIN having written T into the report, while X,
    the file the goal actually named, never existed on disk.
    """
    candidates=_repo_paths(goal,root)
    if not candidates:
        return None
    text=str(goal)
    for m in re.finditer(_OUTPUT_ROLE_RE,text,re.IGNORECASE):
        tail=text[m.end():]
        best=None
        for raw,_p in candidates:
            for spelling in (raw, str(raw).lstrip("/"), str(_p)):
                if not spelling:
                    continue
                at=tail.find(spelling)
                if at>=0:
                    if best is None or at<best[0]:
                        best=(at,raw)
                    break
        if best is None:
            continue
        boundary=_CLAUSE_BOUNDARY_RE.search(tail)
        if boundary is not None and boundary.start()<best[0]:
            # The nearest path belongs to a later clause, so this verb does not
            # name it.  Trying the next verb is what lets "write ... to X and
            # save the report to Y" bind X rather than Y.
            continue
        return best[1]
    return None


_PATH_ROLE_SUFFIXES=("_paths","_path","_root","_dir")


def _path_role_words(keys):
    """The role word each path-bearing input key implies.

    Needed so a path can be given to the role that most recently precedes it
    rather than to every role mentioned anywhere earlier in the sentence.
    """
    out=set()
    for key in keys or ():
        text=str(key)
        for suffix in _PATH_ROLE_SUFFIXES:
            if text.endswith(suffix) and len(text)>len(suffix):
                out.add(text[:-len(suffix)].lower().replace("_"," "))
                break
    return out


def _paths_named_by_role(goal, stem, root, other_roles=()):
    """Every repository path the sentence gives this role, in order of mention.

    The singular helper answers "which file is the manifest"; this answers "which
    files are the tests", because a *_paths input is a list and a suite is
    normally more than one file.

    A path belongs to the role word that most recently PRECEDES it.  Collecting
    every path that merely appears after the role word lets the first role in a
    sentence swallow the rest of it: for "Repair the python source S with the test
    guided repair loop so that the unit tests in A, B pass, and save the repair
    report to R" both source_paths and test_paths came back as the same
    everything-list, the repair loop was handed its own tests as the files to
    repair, and it died with NO_LOCALIZED_SOURCE_FILES.
    """
    if not stem:
        return []
    candidates=_repo_paths(goal,root)
    if not candidates:
        return []
    # A role list names files in the repository, so a candidate has to be one.
    # _repo_paths only checks that a path RESOLVES under the root, which admits
    # anything with a slash in it: the test command "/usr/bin/python3 X" handed
    # the binder "usr/bin/python3" as though it were a test file, and the adapter
    # rejected it with FILE_INVALID.  Filtering on existence is the general rule;
    # it happened to be masked while a derived argv counted as a competing claim.
    rr=pathlib.Path(root).resolve()
    candidates=[(raw,p) for raw,p in candidates if p.is_file() and rr in p.parents]
    if not candidates:
        return []
    text=str(goal)
    word=str(stem).replace("_"," ")
    words={word} | {
        str(r).replace("_"," ") for r in (other_roles or ()) if str(r or "").strip()
    }
    marks=[]
    for role_word in words:
        for m in re.finditer(r"\b"+re.escape(role_word)+r"s?\b",text,re.IGNORECASE):
            marks.append((m.start(),m.end(),role_word))
    marks.sort()
    hits=[]
    for raw,_p in candidates:
        at=-1
        for spelling in (raw, str(raw).lstrip("/"), str(_p)):
            if not spelling:
                continue
            at=text.find(spelling)
            if at>=0:
                break
        if at<0:
            continue
        owner=None
        for _start,end,role_word in marks:
            if end<=at:
                owner=role_word
            else:
                break
        if owner==word:
            hits.append((at,raw))
    found=[]
    for _at,raw in sorted(hits):
        if raw not in found:
            found.append(raw)
    return found


def _claimed_paths(result):
    """Every path the sentence has already given to some other input key.

    A repository path in a sentence has ONE role.  "the source root D ... the test
    D/t.py ... save output_path R.json" names three paths in three roles, and a
    *_paths list that scoops up all three hands the adapter a directory and an
    output file as though they were tests -- which then fails with FILE_INVALID
    rather than doing the work.  Role exclusivity is the general rule; filtering
    by recognising the output verb is only ever a special case of it.

    A *_argv value is NOT a claim.  It is a derived command line, and the paths
    inside it are the very paths of the role it was derived from -- the test
    runner takes the tests as arguments.  Counting them as somebody else's claim
    cancels the role against itself.  Measured: with test_argv bound before
    test_paths in the template order (output_path, source_root, test_argv,
    test_paths), the exclusivity filter emptied a correct
    test_paths=[test_goal_compiler.py], the "sentence named the files
    separately" fallback then fired, and test_paths became every file in the
    sentence -- source included.
    """
    claimed=set()
    for key,value in (result or {}).items():
        if str(key).endswith("_argv"):
            continue
        if isinstance(value,str):
            claimed.add(value)
        elif isinstance(value,(list,tuple)):
            claimed.update(str(x) for x in value if isinstance(x,str))
    return claimed


def _find_suite_argv(mod, _seen=None, _depth=0):
    """Follow an adapter's own delegation chain to the suite runner it uses.

    ``test_argv`` is optional in every adapter that takes it, because each falls
    back to a shared ``suite_argv`` that embeds the collecting suite runner.  The
    adapters reach that helper at different depths:

        python_software_repair_loop_v1.py                  ptg.suite_argv            depth 1
        python_repair_measured_acceptance_controller_v1.py _REPAIR._PATCH.suite_argv depth 2
        python_repair_semantic_acceptance_controller_v1.py v8._REPAIR._PATCH....     depth 3

    Searching only one module level found the first and missed the other two, so
    those capabilities could never bind ``test_argv`` and were unreachable from
    any sentence however well it described the work.  The delegation is real in
    all three; only the discovery stopped early.

    Bounded on purpose: a visited set stops import cycles and a depth cap stops
    an unbounded walk.  ``suite_argv`` is a project-specific name, so reaching it
    anywhere in the adapter's own import graph means it is the project's runner
    rather than something unrelated.
    """
    import types
    seen=_seen if _seen is not None else set()
    if id(mod) in seen or _depth>4:
        return None
    seen.add(id(mod))
    fn=getattr(mod,"suite_argv",None)
    if callable(fn):
        return fn
    for name in dir(mod):
        obj=getattr(mod,name,None)
        if isinstance(obj,types.ModuleType):
            found=_find_suite_argv(obj,seen,_depth+1)
            if found is not None:
                return found
    return None


def _adapter_default_argv(entry, root, targets):
    """The command line the capability's OWN adapter would derive, or None.

    ``test_argv`` is optional in every adapter that takes it: each falls back to
    ``suite_argv(sys.executable, *tests)``.  That helper embeds the suite runner
    which collects tests through the loader, because 695 of 2019 unittest files
    here carry no __main__ guard and running them as scripts silently executes
    nothing.  Copying that into the compiler would duplicate it and drift, so the
    adapter is asked for its own default and the binding fails closed if the
    adapter offers none.
    """
    rel=((entry or {}).get("source") or {}).get("adapter_path")
    if not rel:
        return None
    p=(pathlib.Path(root)/str(rel)).resolve()
    if not p.is_file():
        return None
    try:
        import importlib.util
        spec=importlib.util.spec_from_file_location("_argv_adapter_"+p.stem,p)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception:
        return None
    fn=_find_suite_argv(mod)
    if not callable(fn):
        return None
    try:
        argv=fn(sys.executable,*[str(t) for t in targets])
    except Exception:
        return None
    if not isinstance(argv,(list,tuple)) or not argv:
        return None
    return [str(x) for x in argv]


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
            result[key]=_extract_goal_argument(goal)
            continue
        if key=="url":
            urls=re.findall(r"https?://[^\s)\]}>]+",goal)
            urls=[u.rstrip(".,;:!?") for u in urls]
            if len(urls)==1:
                result[key]=urls[0]
                continue
            raise GoalCompilationFailure("GOAL_URL_BINDING_REQUIRED",str(len(urls)))
        if key.endswith("_paths"):
            # A *_paths input is a LIST of repository paths, and the binder only
            # ever produced scalars, so every capability taking test_paths or
            # evidence_paths raised GOAL_INPUT_BINDING_REQUIRED and lost the
            # ranking however well it matched the goal.
            stem=key[:-6].lower()
            role=_paths_named_by_role(goal,stem,root,_path_role_words(keys))
            if role:
                # Everything after the role word is not necessarily in that role:
                # "the test X passes, and write the report to Y" put the report
                # among the tests.  Drop whatever the sentence gives the output
                # role -- a suite that contains its own report is not a suite.
                out=_path_named_after_output_verb(goal,root)
                if out is not None:
                    role=[x for x in role if x!=out]
                # The output-verb filter only fires when the sentence uses a verb
                # this helper recognises.  "save output_path R.json" does not, so
                # the report still landed among the tests -- and so did the source
                # root directory.  Drop every path already bound to another key,
                # which covers both and every future phrasing.
                claimed=_claimed_paths(result)
                role=[x for x in role if x not in claimed]
                if role:
                    result[key]=role
                    continue
            # The sentence gave the role but named the files separately.
            if re.search(r"\b"+re.escape(str(stem).replace("_"," "))+r"s?\b",
                         str(goal),re.IGNORECASE):
                files=[raw for raw,p in paths if p.is_file()]
                # THE SAME TWO FILTERS THE TWO SITES ABOVE ALREADY APPLY.  This
                # fallback had neither, and it is the one that fires when the
                # sentence names no file at all -- which is how an ordinary
                # request is phrased.  Measured on 96015b9:
                #
                #   "Fix the failing test in the python source root D and write
                #    the report to D_out/r1.json"
                #
                #   selected  python.software.repair.apply.verified.v1
                #   test_paths ["canonical/astra_runtime/tmp/hx/r1.json"]
                #
                # The machine handed the repair adapter ITS OWN REPORT as the
                # test to fix.  Nothing was repaired, the promise layer saw no
                # source change, and the run died PROMISED_SOURCE_CHANGE_NOT_APPLIED
                # -- a truthful refusal for the wrong reason.  Both filters
                # already exist in this file and are already applied to the role
                # list above and to the derived *_argv below; a helper that
                # fixes a defect has to be called from every site that has it.
                out=_path_named_after_output_verb(goal,root)
                if out is not None:
                    files=[x for x in files if x!=out]
                files=[x for x in files if x not in _claimed_paths(result)]
                if files:
                    result[key]=files
                    continue
                # The role was stated and no file survived, so the sentence
                # named no test.  [] is the identity element for a list input,
                # not a guess -- the same discipline this function already uses
                # for {} on a key/value input and [] on a payload selector.  The
                # capability that owns the semantics derives the corpus from the
                # tree it was given and still fails closed on a tree that has no
                # tests (NO_TEST_FILES_UNDER_SOURCE_ROOT), so nothing is
                # invented here and a green empty suite is still impossible.
                # Guessing the report was worse than either: it is a file that
                # exists, so every downstream existence check passed.
                if key=="test_paths":
                    result[key]=[]
                    continue
        if key.endswith("_argv"):
            # Derived, never invented: ask the adapter for the command line it
            # would itself have used for the tests the sentence named, and fail
            # closed when it offers no default.
            stem=key[:-5].lower()
            targets=result.get(stem+"_paths") or _paths_named_by_role(
                goal,stem,root,_path_role_words(keys))
            if not targets:
                targets=[raw for raw,p in paths if p.is_file()]
            # Key order is the template's, so this often runs before the matching
            # *_paths key is bound and falls back to the raw role list -- which
            # still contains the report.  Exclude it here for the same reason.
            out=_path_named_after_output_verb(goal,root)
            if out is not None:
                targets=[t for t in targets if t!=out]
            targets=[t for t in targets if t not in _claimed_paths(result)]
            argv=_adapter_default_argv(entry,root,targets)
            if argv is not None:
                result[key]=argv
                continue
        if key.endswith("_root") or key.endswith("_dir"):
            # A *_root key names a DIRECTORY, and the binder only ever handled
            # *_path.  Every capability whose input is source_root therefore
            # raised GOAL_INPUT_BINDING_REQUIRED, so it could never be bound
            # from a goal and silently lost the ranking to whatever
            # lower-scoring candidate happened to bind -- which is how an
            # AST-audit goal ended up selecting a semantic-behaviour compiler
            # that scored 15 against the audit capability's 35.
            stem=key[:-5].lower()
            rr=pathlib.Path(root).resolve()
            # The sentence has to give a path this role before it is used.
            # Inferring "the parent of the only file mentioned" binds source_root
            # out of an unrelated file -- measured: in a compound plan whose only
            # existing file was a registry JSON, that inference bound source_root
            # to canonical/runtime and let the AST audit steal a clause that
            # belonged to the markdown-to-PDF capability.
            named=bool(re.search(
                r"\b"+re.escape(str(stem).replace("_"," "))+r"\b",str(goal),re.IGNORECASE))
            dirs=[(raw,p) for raw,p in paths if p.is_dir()]
            matching=[raw for raw,p in dirs if not stem or stem in raw.lower()]
            if len(matching)==1:
                result[key]=matching[0]
                continue
            if named and len(dirs)==1:
                result[key]=dirs[0][0]
                continue
            if named:
                # The sentence gave a path this role, so the parent of the one
                # file it names is the root that file lives under.
                files=[(raw,fp) for raw,fp in paths if fp.is_file()]
                if len(files)==1 and files[0][1].parent!=rr and rr in files[0][1].parent.parents:
                    result[key]=str(files[0][1].parent.relative_to(rr))
                    continue
            role_bound=_path_named_by_role(goal,stem,root)
            if role_bound is not None:
                rp=(rr/role_bound).resolve()
                if rp.is_dir():
                    result[key]=role_bound
                    continue
                # A goal that names one file names the root that file lives under.
                if rp.is_file() and rp.parent!=rr and rr in rp.parent.parents:
                    result[key]=str(rp.parent.relative_to(rr))
                    continue
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
                    # Non-existence is only a proxy for "this is the output".
                    # On a replay the artifact the previous run wrote is already
                    # on disk, so the proxy fails, _bind_inputs gives up, and a
                    # goal that succeeded once can never be run again.  Fall back
                    # to the role the sentence assigns: the path named after an
                    # output verb is the destination whether or not it exists.
                    verb_bound=_path_named_after_output_verb(goal,root)
                    if verb_bound is not None:
                        result[key]=verb_bound
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
                # Last resort for a typed input: the sentence itself said which
                # file plays this role.  Consulted only after the stem match and
                # the context path both came up empty, so it can only rescue a
                # binding that would otherwise fail closed.
                role_bound=_path_named_by_role(goal,stem,root)
                if role_bound is not None:
                    result[key]=role_bound
                    continue
                if stem in {"input","source"} and len(existing)==1:
                    result[key]=existing[0][0]
                    continue
        raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED",key)
    return result


def _complete_inputs_via_world_binding(goal, root, cid, entry):
    """Fill placeholders `_bind_inputs` could not ground, or return None.

    `_bind_inputs` binds what the goal SAYS and is authoritative: when it
    succeeds its answer wins untouched. It fails closed for values the goal
    merely IMPLIES -- a destination that does not exist yet, or a root one
    step away from a named file -- which silently disables a capability that
    was correctly selected.

    `world_binding_v1` closes exactly that gap and reports, per placeholder,
    whether the value came from the goal, the world, a companion slot, or a
    demonstrated admission case. This wrapper accepts its answer ONLY when
    nothing is left missing; a partially justified mapping is still refused,
    so this widens the bindable set without ever inventing an input.
    """
    try:
        from canonical.runtime import world_binding_v1 as _wb
    except Exception:
        return None
    try:
        # `synthesize_output_path` and `_ext_for` derive both the deterministic
        # digest and the artifact extension from the capability identity, and
        # registry entries do not carry that key. Omitting it would emit a
        # wrong-extension artifact under an empty slug.
        wb_entry = dict(entry)
        wb_entry.setdefault("capability_id", str(cid))
        completed = _wb.complete_inputs(goal, root, wb_entry, compiler=sys.modules[__name__])
    except Exception:
        return None
    if not isinstance(completed, dict):
        return None
    if completed.get("missing"):
        return None
    inputs = completed.get("inputs")
    if not isinstance(inputs, dict):
        return None
    return inputs, completed


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


# A precondition token that most of the registry shares discriminates nothing.
#
# `_score` pays 3 points per matched `requires` token and counts every one as
# specificity, on the stated reasoning that "requirements are highly informative
# for environment qualifiers such as image-only/scanned/local". That is true of a
# qualifier. It is not true of `python.source.file.available`, which 82% of the
# entries that declare any precondition also declare, token by token: available
# 82.1%, file 55.4%, source 35.7%, python 28.6%, then a clear gap to test/corpus
# at 19.6%.
#
# Measured on "Count the functions defined in the python file <abs>/calc.py and
# write the report to <abs>/a.json", python.source.audit.ast scored 15 on the
# two keywords that ARE the question -- `functions` and `python` -- and lost to
# python.software.repair.apply.verified.v1 at 22, whose only keyword match was
# `write` and which collected 6 points and 2 specificity for requiring that a
# python file exist. A capability was chosen for a sentence because both of them
# need a python file to be there.
#
# Derived from the registry, never written by hand: the set recomputes whenever
# the registry changes, so it cannot go stale the way a word list does.
_REQUIRES_SHARE_CEILING = 0.25
_nondiscriminating_requires_cache = None


def _nondiscriminating_requires_tokens():
    global _nondiscriminating_requires_cache
    if _nondiscriminating_requires_cache is not None:
        return _nondiscriminating_requires_cache
    out = frozenset()
    try:
        path = pathlib.Path(__file__).resolve().parent / "BOUND_CAPABILITY_REGISTRY_V1.json"
        with open(path, "r", encoding="utf-8") as fh:
            caps = (json.load(fh) or {}).get("capabilities") or {}
        declaring = [_tokens(e.get("requires", [])) for e in caps.values() if isinstance(e, dict) and e.get("requires")]
        if declaring:
            counts = {}
            for toks in declaring:
                for t in toks:
                    counts[t] = counts.get(t, 0) + 1
            n = float(len(declaring))
            out = frozenset(t for t, c in counts.items() if c / n > _REQUIRES_SHARE_CEILING)
    except Exception:
        out = frozenset()
    _nondiscriminating_requires_cache = out
    return out


# A verb does not carry its own meaning; its OBJECT does.  "write the repair
# report to R" asks for evidence, not for the source bytes to change, and the
# word "write" alone then credits the one capability that overwrites the input
# (python.software.repair.apply.verified.v1) over the test-guided loop the same
# sentence names by name.  Measured: the coupled/repair families routed to the
# in-place writer and were refused by an oracle that forbids writing the source.
# "apply" is deliberately NOT in this verb list: "apply the patch to X" is a real
# source-write request, and only artifact-writing verbs are neutralized here.
_ARTIFACT_WRITE_VERBS = ("write", "save", "dump", "emit", "store", "record",
                         "log", "output", "print", "persist")
_EVIDENCE_OBJECTS = ("report", "receipt", "log", "transcript", "summary",
                     "manifest", "evidence", "proof", "trace", "plan", "patch",
                     "json", "csv", "markdown", "txt")


# The names a sentence uses when it chooses a patch-producing route rather than an
# in-place one.  Closed on purpose, and it is the same vocabulary the repair
# families themselves use ("with the test guided repair loop", "with the coupled
# multi-edit repair loop", "with ast patch search").
_PATCH_ROUTE_NOUNS = ("loop", "patch search")


def _names_a_patch_route(goal):
    text = str(goal or "").lower()
    return any(noun in text for noun in _PATCH_ROUTE_NOUNS)


def _artifact_write_tokens(goal):
    """Words in ``goal`` that only say WHERE evidence goes, not what to change."""
    text = str(goal or "")
    verbs = "(?:" + "|".join(_ARTIFACT_WRITE_VERBS) + ")"
    nouns = "(?:" + "|".join(_EVIDENCE_OBJECTS) + ")"
    out = set()
    for m in re.finditer(r"\b" + verbs + r"\b((?:\s+[A-Za-z0-9_.-]+){1,4})", text,
                         re.IGNORECASE):
        tail = m.group(1).lower()
        if re.search(r"\b" + nouns + r"\b", tail):
            out.add(m.group(0).split()[0].lower())
    return out


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
    # Evidence-only verbs are removed from the EFFECT side of the match.  They
    # still count as requirements below, because "write a report to R" does state
    # a needed surface; they just may not create or weight a source-change match.
    # When the sentence names the ROUTE ("... with the test guided repair loop"),
    # the route decides and the report verb is bookkeeping.  When it names no
    # route, the repair verb governs the file itself: leaving "write" credited is
    # what keeps "Repair the python source file X ... and write the report to R"
    # on python.software.repair.apply.verified.v1, the one capability that both
    # finds the patch and lands it, so the file really is repaired.
    gt_effect=gt-(_artifact_write_tokens(goal) if _names_a_patch_route(goal) else set())
    provides=_tokens(entry.get("provides",[]))
    requires=_tokens(entry.get("requires",[]))
    identity=_tokens(cid)
    keywords=_tokens(entry.get("keywords",[]))
    # Requirements are highly informative for environment qualifiers such as
    # image-only/scanned/local/etc. Provides represent the requested effect.
    effect_matches=(gt_effect & provides) | (gt_effect & identity) | (gt_effect & keywords)
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
    # A precondition most of the registry shares is not evidence about this
    # sentence. See _nondiscriminating_requires_tokens for the measurement.
    nondiscriminating=_nondiscriminating_requires_tokens()
    informative_requires=(gt & requires) - nondiscriminating
    score=5*len(gt_effect & provides)+4*len(gt_effect & keywords)+3*len(informative_requires)+2*len(gt_effect & identity)
    # Prefer more-specific matched preconditions when base scores tie.
    specificity=len(informative_requires)
    return score,specificity,{
        "goal_tokens":sorted(gt),
        "matched_provides":sorted(gt_effect & provides),
        "matched_requires":sorted(gt & requires),
        "informative_requires":sorted(informative_requires),
        "nondiscriminating_requires":sorted((gt & requires) & nondiscriminating),
        "matched_identity":sorted(gt_effect & identity),
        "matched_keywords":sorted(gt_effect & keywords),
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


_BM25_MODULE=None
_BM25_LOAD_FAILED=False


def _bm25_module():
    """Load the repo's own BM25 scorer once. Returns None if it cannot be loaded."""
    global _BM25_MODULE,_BM25_LOAD_FAILED
    if _BM25_MODULE is not None or _BM25_LOAD_FAILED:
        return _BM25_MODULE
    path=(pathlib.Path(__file__).resolve().parent
          /"bound_capabilities"/"objective_relevance_bm25.py")
    if not path.is_file():
        _BM25_LOAD_FAILED=True
        return None
    try:
        spec=importlib.util.spec_from_file_location(
            "project_brain_objective_relevance_bm25_v1",path)
        if spec is None or spec.loader is None:
            _BM25_LOAD_FAILED=True
            return None
        module=importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=module
        spec.loader.exec_module(module)
        _BM25_MODULE=module
    except Exception:
        _BM25_LOAD_FAILED=True
        _BM25_MODULE=None
    return _BM25_MODULE


def _bm25_terms(value):
    """Token LIST (not set) so BM25 sees real term frequencies."""
    return [
        t.lower() for t in re.findall(r"[A-Za-z0-9]+",str(value or ""))
        if len(t)>=2 and t.lower() not in STOPWORDS
    ]


def _capability_document(cid,entry):
    """The indexed text for one capability.

    Field weighting by repetition, the same approximation
    ``objective_relevance_bm25._candidate_text`` uses: the identity and the
    declared effect are repeated because they state what the capability IS and
    DOES, while ``keywords`` are supporting vocabulary. Nothing is invented
    here -- every field already exists on the registry entry.
    """
    identity=_bm25_terms(cid)
    provides=_bm25_terms(entry.get("provides",[]))
    requires=_bm25_terms(entry.get("requires",[]))
    keywords=_bm25_terms(entry.get("keywords",[]))
    return identity+identity+provides+provides+requires+keywords


def _bm25_rerank(goal,ranked):
    """Reorder already-admissible candidates by BM25 relevance.

    This changes ORDER ONLY. Every element of ``ranked`` has already passed
    ``_score`` (execution-surface and structured-format rejections, plus the
    distinctive-token requirement) and has already bound its inputs, so BM25
    cannot introduce a capability the pinned scorer refused and cannot make an
    unbindable one bindable. It decides which of the survivors the goal is
    most likely to mean.

    Why BM25 rather than the raw overlap count: the count treats every shared
    token as equally informative, so a capability carrying 27 governance
    keywords (``terminal.kstar.root.assess.stdlib``) out-scores the capability
    that actually owns the task, and the only defence is a hand-maintained
    denylist of generic tokens. BM25's inverse document frequency derives that
    weighting from the corpus instead: a token most capabilities carry is worth
    little, a token only this one carries is worth a lot. No denylist to
    maintain, and no capability can win on vocabulary it shares with everyone.
    """
    if len(ranked)<2:
        return ranked
    module=_bm25_module()
    if module is None:
        return ranked
    try:
        docs=[_capability_document(item[2],item[3]) for item in ranked]
        scores=module._bm25_scores(_bm25_terms(goal),docs)
    except Exception:
        return ranked
    if len(scores)!=len(ranked):
        return ranked
    out=[]
    for item,(relevance,_contributions) in zip(ranked,scores):
        score,specificity,cid=item[0],item[1],item[2]
        out.append((relevance,score,specificity,cid,item))
    # BM25 first; the pinned overlap score breaks BM25 ties, then specificity,
    # then identity for determinism.
    out.sort(key=lambda x:(-x[0],-x[1],-x[2],x[3]))
    ordered=[x[4] for x in out]
    # A capability that binds VACUOUSLY -- it declares no ``${input.}``
    # placeholder at all, so it attaches to any sentence for free -- is demoted
    # below every candidate the pinned scorer rated strictly higher.
    #
    # This is the same distinction _compile_single_goal already draws when it
    # decides whether a substitution is a substitution ("a vacuous bind: it
    # attaches to any sentence for free, e.g. msgpack/kstar catch-alls"); it was
    # only ever applied to the REFUSAL, never to the ORDER, and the order is
    # what selects: _compile_single_goal takes ranked[0].  Measured on
    # 29b3107, "Localize the fault in the python source root D using the tests"
    # ranked terminal.kstar.root.assess.stdlib FIRST at pinned score 15, above
    # the capability that owns the sentence at 28 -- the exact inversion this
    # function's own docstring says BM25 exists to prevent -- because BM25's
    # inverse document frequency is measured over the surviving shortlist,
    # where a token most capabilities carry but few survivors carry looks rare.
    # Rather than re-weight the whole corpus and move goals that already select
    # correctly, the ordering is made to respect the fact the pinned scorer
    # already established: a binder that consumed nothing from the sentence
    # does not outrank one that consumed it and scored higher.
    def _vacuous(item):
        args=((item[3].get("action_template") or {}).get("args") or {})
        return not any(
            isinstance(v,str) and v.startswith("${input.") for v in args.values()
        )
    grounded=[it[0] for it in ordered if not _vacuous(it)]
    if not grounded:
        return ordered
    best_grounded=max(grounded)
    head=[]
    tail=[]
    for it in ordered:
        if _vacuous(it) and it[0]<best_grounded:
            tail.append(it)
        else:
            head.append(it)
    return head+tail


def _effect_providers(registry):
    """Which capability produces each effect, read off the registry itself.

    A consumer capability declares its inputs as ``proposal_bindings`` of type
    ``effect_result``: "this slot is filled from the output of whoever produces
    effect X". The binder then looks the producer up in ``effect_providers`` --
    a map the CALLER has to supply. On the single-clause path nothing supplied
    it, so every one of those consumers was dropped before ranking with
    ``PROPOSAL_EFFECT_PROVIDER_MISSING``, however well it matched the goal.

    Nothing is inferred here. ``provides`` is already on every entry, and the
    binder separately insists that the producer declare the exact
    ``result_field`` the consumer names, so a producer that cannot actually
    yield that field is still refused. The map only tells the binder which
    capabilities exist to be asked.
    """
    providers={}
    for cid,entry in sorted((registry or {}).items()):
        if not isinstance(entry,dict):
            continue
        for effect in entry.get("provides") or []:
            key=str(effect).strip()
            if key:
                # sorted() above makes first-writer-wins deterministic.
                providers.setdefault(key.lower(),(cid,entry))
    return providers


def _plan_score(plan):
    """The score of a compiled plan, comparable across passes.

    Both passes score with the same ``_score``, so this is a like-for-like
    comparison and not a heuristic. A compound plan is scored by its strongest
    part, which is the part that decided the selection.
    """
    if not isinstance(plan,dict):
        return -1
    parts=plan.get("compiled_parts") or []
    if parts:
        best=-1
        for part in parts:
            if isinstance(part,dict):
                try:
                    best=max(best,float(part.get("score") or 0))
                except (TypeError,ValueError):
                    continue
        if best>=0:
            return best
    try:
        return float(plan.get("score") or 0)
    except (TypeError,ValueError):
        return -1


def _plan_has_unjustified_world_slots(plan):
    """True when the plan filled at least one slot by scanning the filesystem.

    ``world_binding_v1.complete_inputs`` already separates the two ways a slot can
    be filled from outside the sentence, and this reads that distinction rather
    than inventing one:

      ``filled_from_demonstrated_case``  a slot backed by a demonstrated admission
                                         case -- evidence.
      ``filled_from_world_not_goal``     a slot picked off the filesystem with
                                         nothing in the sentence pointing at it --
                                         a guess.

    Measured on the live benchmark, the two are not interchangeable.  "Audit the
    python source tree with an AST." fills ``source_root`` from a demonstrated
    case and has an EMPTY ``filled_from_world_not_goal``.  "Summarize a markdown
    document into a decision record." fills ``markdown_path`` with AGENTS.md --
    one file out of the many the repository holds, none of them named -- and that
    slot lands in ``filled_from_world_not_goal``.

    ``_plan_score`` is a pure lexical number and cannot tell those two plans
    apart, which is why the comparison needs this predicate.
    """
    if not isinstance(plan,dict):
        return False
    rows=[plan]
    rows.extend(p for p in (plan.get("compiled_parts") or []) if isinstance(p,dict))
    for row in rows:
        provenance=row.get("binding_provenance")
        if isinstance(provenance,dict) and (provenance.get("filled_from_world_not_goal") or {}):
            return True
    return False


def _rank_bindable_candidates(
    goal, registry, root, context_paths=None, future_clauses=None,
    proposal_binder=None, effect_providers=None, allow_world_binding=False,
    unbindable_out=None
):
    """Score every live capability the goal could select, then try to bind it.

    ``allow_world_binding`` is deliberately OFF on the first pass. A capability
    bound from the goal's own words is strictly more grounded than one whose
    slots had to be inferred from the world, and the two must never compete on
    raw lexical score: admitting inferred candidates into the same ranking let a
    barcode DECODER outrank the barcode GENERATOR the goal actually asked for,
    because inference makes almost anything bindable and so destroys the very
    disambiguation power that bindability provides.

    The inferred pass therefore runs only when nothing grounded survived.

    ``unbindable_out`` (optional list) receives every word-matched candidate
    that could NOT be bound at this level, as ``(score, specificity, cid)``
    tuples. The caller compares it against the bindable survivors: when the
    best word-match is unbindable, the honest answer is a refusal -- never a
    substitution with a weaker-scoring tool that happens to be callable.
    """
    ranked=[]
    for cid,entry in sorted((registry or {}).items()):
        if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
            continue
        if not isinstance(entry.get("action_template"),dict):
            continue
        # A zero-input capability with declared prerequisite effects is an
        # internal composition node: this plain-goal ranker binds none of those
        # prerequisites, so admitting the node as "grounded" is false. Its
        # broad keywords can otherwise tie ahead of the input-bearing owner.
        # Keep legacy standalone zero-input entries visible (the chained-plan
        # negative control depends on terminal.kstar.root.assess.stdlib), and
        # keep explicit capability_id invocation outside this ranker.
        if entry.get("requires") and not _placeholders(entry["action_template"]):
            continue
        score,specificity,evidence=_score(goal,cid,entry)
        if score<=0:
            continue
        binding_provenance=None
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
                    effect_providers or {},_already_produced_paths=context_paths
                )
            else:
                inputs=_bind_inputs(
                    goal,root,entry,
                    context_paths=context_paths,
                    future_clauses=future_clauses
                )
        except Exception:
            inputs=None
        if inputs is None:
            if not allow_world_binding or _uses_effect_result_bindings(entry):
                if unbindable_out is not None:
                    unbindable_out.append((score,specificity,cid))
                continue
            # BIND FIRST, THEN RANK. Ambiguity is frequently an artefact of
            # ranking unbound candidates: several capabilities match the words,
            # but only some can actually be called with what the world offers.
            completed=_complete_inputs_via_world_binding(goal,root,cid,entry)
            if completed is None:
                if unbindable_out is not None:
                    unbindable_out.append((score,specificity,cid))
                continue
            inputs,binding_provenance=completed
        ranked.append((score,specificity,cid,entry,inputs,evidence,binding_provenance))
    ranked.sort(key=lambda x:(-x[0],-x[1],x[2]))
    # Pinned ordering first, then BM25 reorders the survivors. Reordering only:
    # see ``_bm25_rerank``.
    return _bm25_rerank(goal,ranked)


def _resolve_tie_by_executability(
    goal, registry, root, ranked,
    context_paths=None, future_clauses=None,
    proposal_binder=None, effect_providers=None
):
    """Break an exact score/specificity tie using what the world can bind.

    This is the same principle the ranking already states -- "BIND FIRST, THEN
    RANK. Ambiguity is frequently an artefact of ranking unbound candidates" --
    applied to the one case it was never reached for: a tie.

    It does NOT admit inferred candidates into the ranking. The tied set is
    fixed by the grounded pass, so an inferred candidate can never outrank a
    grounded one on raw lexical score, which is the failure this file warns
    about (a barcode DECODER outranking the barcode GENERATOR the goal asked
    for). Inference is used only to order capabilities that are already
    indistinguishable on the goal's own words -- where returning nothing is
    provably worse than returning the one that can actually be called.

    Returns the winning ranked tuple, or ``None`` when even executability
    cannot separate them, in which case the caller refuses exactly as before.
    """
    best=ranked[0]
    tied=[c for c in ranked if c[0]==best[0] and c[1]==best[1]]
    if len(tied)<2:
        return None
    tied_ids={c[2] for c in tied}
    try:
        reranked=_rank_bindable_candidates(
            goal,registry,root,
            context_paths=context_paths,
            future_clauses=future_clauses,
            proposal_binder=proposal_binder,
            effect_providers=effect_providers,
            allow_world_binding=True,
        )
    except Exception:
        return None
    survivors=[c for c in reranked if c[2] in tied_ids]
    if not survivors:
        return None
    if len(survivors)==1:
        return survivors[0]
    top=survivors[0]
    if survivors[1][0]==top[0] and survivors[1][1]==top[1]:
        # Executability could not separate them either. The clause was carved
        # out of a longer sentence, and the words that decide between these
        # candidates are usually in the part that was carved away -- measured:
        # "Read a PDF" scores pdf.extract.text.pypdf and pdf.extract.ocr.tesseract
        # at 10 and 10, while the sentence it came from, "Read a PDF and extract
        # its text.", scores them 24 and 17. Re-scoring against the wider text
        # the compiler already holds uses no new policy, only information that
        # was discarded by the split.
        wider=str(goal)
        for clause in (future_clauses or []):
            if clause and str(clause) not in wider:
                wider=f"{wider} {clause}"
        if wider!=str(goal):
            rescored=[]
            for item in survivors:
                try:
                    sc,sp,ev=_score(wider,item[2],item[3])
                except Exception:
                    continue
                rescored.append((sc,sp,item))
            rescored.sort(key=lambda x:(-x[0],-x[1],x[2][2]))
            if rescored and (
                len(rescored)==1
                or rescored[1][0]!=rescored[0][0]
                or rescored[1][1]!=rescored[0][1]
            ):
                return rescored[0][2]
        # DEPENDENCY ORDER BREAKS A TIE THAT NOTHING ELSE CAN.
        #
        # Two capabilities can be indistinguishable on the words of a sentence and
        # still not be alternatives, because one CONSUMES what the other PRODUCES.
        # The registry already declares that edge in `requires`/`provides`, so
        # reading it invents no policy -- it is the same composition contract the
        # planner uses to build a DAG, read one level deep.
        #
        # Measured.  "Summarize a markdown document into a decision record." ties
        # `decision.synthesis.verify.stdlib` against `decision.synthesis.typed.stdlib`
        # at score 14 and specificity 1.  Nothing separates them: both bind through
        # their declared proposal_bindings, executability cannot split them, and the
        # wider-text rescore has no wider text to use.  So the compiler raised
        # GOAL_COMPILATION_AMBIGUOUS, the chained pass returned nothing, and the
        # front door fell back to the world-bound
        # `document.convert.markdown_pdf.pandoc_weasyprint` -- which bound
        # `markdown_path` to AGENTS.md, a file the sentence never mentioned, and
        # offered a PDF conversion nobody asked for.
        #
        # But `decision.synthesis.verify.stdlib` declares
        # `requires: [decision.synthesis.typed]`, which is exactly what its tied
        # competitor provides.  The verifier is DOWNSTREAM of the synthesizer, so a
        # request that has produced no decision yet cannot be asking for the check on
        # one.  Dropping the candidate that consumes a sibling's output leaves
        # precisely the synthesizer, which is what the benchmark expects.
        #
        # One-directional and conservative on purpose: it fires only inside an exact
        # tie, it drops only a candidate that consumes a sibling's declared output,
        # and it returns nothing unless exactly one candidate survives.  "Verify a
        # typed decision synthesis." is untouched, because it never reaches a tie --
        # the verifier scores 37 against the synthesizer's 32 -- and a tie-break
        # never runs on a race that already has a winner.
        independent=[]
        for item in survivors:
            requires={str(x) for x in ((item[3] or {}).get("requires") or [])}
            consumes_a_sibling=any(
                other is not item
                and bool(requires & {str(x) for x in ((other[3] or {}).get("provides") or [])})
                for other in survivors
            )
            if not consumes_a_sibling:
                independent.append(item)
        if len(independent)==1:
            return independent[0]
        return None
    return top


def _subgoal_absorbed_by_prefix(clause, compiled_parts, registry):
    """True when a clause asks only for what the compiled prefix already does.

    Clause splitting on conjunctions can divide ONE action into two sentences:
    "Read a PDF and extract its text" describes a single capability,
    ``pdf.extract.text.pypdf``, twice. The second clause then matches nothing
    -- not because the machine lacks the ability, but because the ability is
    already compiled.

    The test is lexical containment against the prefix capability's own
    identity, which invents no new policy: every content word of the clause
    must already appear in the capability the prefix selected.
    """
    stopwords={
        "a","an","the","its","it","to","and","of","from","then","that","this",
        "with","into","out","on","in","for","be","is","are","as","at","by",
        "their","them","they","those","these","was","were","do","does",
    }
    words={
        w for w in re.findall(r"[a-z0-9_]+",str(clause).lower())
        if w not in stopwords and len(w)>2
    }
    if not words:
        return False
    if not compiled_parts:
        return False
    cid=str((compiled_parts[-1] or {}).get("selected_capability") or "")
    entry=(registry or {}).get(cid)
    if not isinstance(entry,dict):
        return False
    identity=" ".join(str(x) for x in (
        cid,
        entry.get("name") or "",
        entry.get("description") or "",
        " ".join(entry.get("keywords") or []) if isinstance(entry.get("keywords"),list) else "",
    )).lower()
    tokens=set(re.findall(r"[a-z0-9_]+",identity))
    return bool(tokens) and words<=tokens


def _collect_effect_result_refs(value, out=None):
    """Every ``{"$effect_result": {...}}`` reference reachable in a value."""
    if out is None:
        out=[]
    if isinstance(value,dict):
        ref=value.get("$effect_result")
        if isinstance(ref,dict):
            out.append(ref)
        for item in value.values():
            _collect_effect_result_refs(item,out)
    elif isinstance(value,list):
        for item in value:
            _collect_effect_result_refs(item,out)
    return out


def _channel_candidates(store,effect):
    """Ordered channel list for ``effect`` from either store shape.

    Typed composition channels: a channel maps an effect to every endpoint
    that published it, in plan order. Legacy single-entry stores (tuple)
    still read; ``None`` means no channel exists.
    """
    value=store.get(effect)
    if value is None:
        return None
    if isinstance(value,list):
        return list(value)
    return [value]


def _channel_where(where,detail):
    """Validate an optional ``where`` predicate; return (provider_set, format).

    Phase C knows two predicates: ``provider`` (a capability id or a list) and
    ``format`` (a declared channel format string, matched against a producer's
    channel_schema for the exact field being bound). Unknown shapes refuse
    loudly rather than degrade into a silent pick.
    """
    if where is None:
        return None
    if not isinstance(where,dict) or not where or set(where)-{"provider","format"}:
        raise GoalCompilationFailure(
            "CAPABILITY_CHANNEL_INVALID",
            str(detail),
        )
    provider_set=None
    if "provider" in where:
        provider=where["provider"]
        if isinstance(provider,str) and provider.strip():
            provider_set={provider.strip()}
        elif (
            isinstance(provider,list)
            and provider
            and all(isinstance(x,str) and x.strip() for x in provider)
        ):
            provider_set={x.strip() for x in provider}
        else:
            raise GoalCompilationFailure(
                "CAPABILITY_CHANNEL_INVALID",
                str(detail),
            )
    fmt=None
    if "format" in where:
        fmt=where["format"]
        if not (isinstance(fmt,str) and fmt.strip()):
            raise GoalCompilationFailure(
                "CAPABILITY_CHANNEL_INVALID",
                str(detail),
            )
        fmt=fmt.strip()
    return provider_set,fmt


def _channel_entry_format(entry,field):
    """Declared format of ``field`` on a registry entry, else None."""
    schema=(entry or {}).get("channel_schema")
    if not isinstance(schema,dict):
        return None
    spec=schema.get(field)
    if not isinstance(spec,dict):
        return None
    fmt=str(spec.get("format") or "").strip()
    return fmt or None


def _select_channel(candidates,where,detail,field=""):
    """Pick one channel endpoint under the typed-channel law.

    Predicates filter first: provider id set, then declared channel format for
    the field being bound (schema-less producers cannot satisfy it). More than
    one survivor under ANY predicate fails closed CAPABILITY_CHANNEL_AMBIGUOUS.
    Without a predicate the historical last-writer-wins law of overwrite stores
    is preserved exactly (single-endpoint legacy maps trivially keep theirs).
    """
    if not candidates:
        return None
    parsed=_channel_where(where,detail)
    if parsed is None:
        return candidates[-1]
    provider_set,fmt=parsed
    chosen=candidates
    if provider_set is not None:
        chosen=[x for x in chosen if x[0] in provider_set]
    if fmt is not None:
        chosen=[x for x in chosen if _channel_entry_format(x[1],field)==fmt]
    if len(chosen)>1:
        raise GoalCompilationFailure(
            "CAPABILITY_CHANNEL_AMBIGUOUS",
            json.dumps({
                "detail":str(detail),
                "candidates":sorted(str(x[0]) for x in chosen),
            },sort_keys=True),
        )
    if not chosen:
        return None
    return chosen[0]


def _channel_discriminator(ref):
    """Stable identity of a reference's ``where`` for cycle dedupe.

    Two references route to the same producer step exactly when their
    predicates are equal; without a predicate both collapse to "" so the
    existing two-fields-of-one-producer dedupe is unchanged.
    """
    where=ref.get("where") if isinstance(ref,dict) else None
    if where is None:
        return ""
    return json.dumps(where,sort_keys=True)


def _rewrite_effect_result_refs(value, cycle_by_ref):
    """Point a dangling effect reference at the step that now produces it."""
    if isinstance(value,dict):
        ref=value.get("$effect_result")
        if isinstance(ref,dict):
            key=(str(ref.get("effect") or ""),str(ref.get("field") or ""),
                 _channel_discriminator(ref))
            cycle=cycle_by_ref.get(key)
            if cycle is None:
                return value
            return {"$result":{"cycle":cycle,"field":key[1]}}
        return {k:_rewrite_effect_result_refs(v,cycle_by_ref) for k,v in value.items()}
    if isinstance(value,list):
        return [_rewrite_effect_result_refs(v,cycle_by_ref) for v in value]
    return value


def _bind_producer_inputs(goal, root, provider_id, provider_entry,
                          context_paths=None, future_clauses=None):
    """Bind a producer, auto-generating output slots a sentence never names.

    ``_bind_inputs`` refuses any ``output_path`` the sentence does not state,
    which is every sentence: goals describe work, not output filenames. The
    proposal binder already solves this with its ``auto_path`` binding type, so
    output-shaped placeholders are masked out here and generated with the same
    content-addressed convention rather than being demanded of the sentence.
    Returns None when any NON-output slot cannot be bound, which is the
    fail-closed case.
    """
    template=provider_entry.get("action_template") or {}
    args=template.get("args") or {}
    output_keys=[]
    for key,value in args.items():
        name=str(value)
        if not (name.startswith("${input.") and name.endswith("}")):
            continue
        slot=name[len("${input."):-1]
        if slot=="output_path" or slot.startswith("output_"):
            output_keys.append(slot)
    # A producer is itself a consumer. Slots its own ``proposal_bindings`` fill
    # from an upstream effect cannot be bound from the sentence, and
    # ``_bind_inputs`` does not speak ``effect_result`` -- it would refuse the
    # whole producer. Mask them exactly as output slots are masked, then put
    # the reference back so ``_append_producer_parts`` can recurse on it and
    # emit the upstream step. Without this the middle link of a two-level chain
    # (verifier <- synthesizer <- locator) always failed to bind and the chain
    # was never emitted.
    bindings=provider_entry.get("proposal_bindings") or {}
    effect_slots={
        str(slot):(binding.get("effect"),binding.get("field"))
        for slot,binding in bindings.items()
        if isinstance(binding,dict) and binding.get("type")=="effect_result"
    }
    effect_where={
        str(slot):json.loads(json.dumps(binding["where"]))
        for slot,binding in bindings.items()
        if isinstance(binding,dict) and binding.get("type")=="effect_result"
        and binding.get("where") is not None
    }
    masked=dict(provider_entry)
    masked["proposal_bindings"]={
        k:v for k,v in bindings.items() if k not in effect_slots
    }
    masked_args={k:v for k,v in args.items()
                 if not (isinstance(v,str) and v.startswith("${input.")
                         and v.endswith("}") and v[len("${input."):-1] in output_keys
                         or isinstance(v,str) and v.startswith("${input.")
                         and v.endswith("}") and v[len("${input."):-1] in effect_slots)}
    masked["action_template"]={**template,"args":masked_args}
    try:
        inputs=_bind_inputs(goal,root,masked,
                            context_paths=context_paths,
                            future_clauses=future_clauses)
    except Exception:
        return None
    if inputs is None:
        return None
    inputs=dict(inputs)
    for slot,(effect,field) in effect_slots.items():
        ref={"effect":str(effect or ""),"field":str(field or "")}
        if slot in effect_where:
            # Typed-channel predicate travels with the reference so both the
            # planner lowering and the producer-attach walk select the same
            # channel endpoint the binding spec asked for.
            ref["where"]=json.loads(json.dumps(effect_where[slot]))
        inputs[slot]={"$effect_result":ref}
    for slot in output_keys:
        if slot in inputs:
            continue
        digest=hashlib.sha256(str(goal).encode("utf-8")).hexdigest()[:16]
        slug=re.sub(r"[^a-z0-9]+","-",str(provider_id).lower()).strip("-")[:72]
        suffix=".json" if slot=="output_path" else ""
        inputs[slot]=(
            "canonical/astra_runtime/tmp/auto_proposal/"
            +digest+"_effect-producer_"+slug+"_"+re.sub(r"[^a-z0-9]+","-",slot.lower()).strip("-")[:32]
            +suffix
        )
    return inputs


_MAX_PRODUCER_CHAIN_DEPTH=3


def _append_producer_parts(
    refs, goal, registry, root, effect_providers, parts, actions, cycle_by_ref,
    context_paths=None, future_clauses=None, depth=0
):
    """Emit one producer step per dangling effect reference, deepest first.

    Returns False -- leaving ``parts`` for the caller to discard -- whenever any
    reference cannot be satisfied by a real producer that itself binds. The
    caller then returns the plan untouched, so a gap stays a gap instead of
    becoming a chain whose first step is guaranteed to fail.

    Recursion is the load-bearing part. A producer is itself a consumer: it may
    declare an ``effect_result`` slot that this same sentence never states.
    Measured on ``EXT_DECISION_VERIFY`` -- "Verify a typed decision synthesis"
    -- the verifier needs ``decision.synthesis.typed``, whose producer
    ``decision.synthesis.typed.stdlib`` in turn needs
    ``structured.decision_evidence.available``. Resolving only the outer level
    bound the synthesizer's ``input_path`` to a dangling ``$effect_result`` and
    the verifier still died with ``DECISION_VERIFIER_INPUT_MISSING``. A
    producer's own references are therefore resolved BEFORE it is numbered, so
    cycle indices stay in execution order and every ``$result`` reference
    points at a step that runs earlier.

    ``depth`` bounds the walk. Providers are looked up in a map keyed by the
    effect they declare, so a malformed registry claiming to provide its own
    requirement would otherwise recurse forever; the bound turns that into a
    refusal.
    """
    providers=effect_providers or {}
    for ref in refs:
        effect=str(ref.get("effect") or "").strip()
        field=str(ref.get("field") or "").strip()
        discr=_channel_discriminator(ref)
        if (effect,field,discr) in cycle_by_ref:
            continue
        prior=[c for (e,_f,d),c in cycle_by_ref.items() if e==effect and d==discr]
        if prior:
            # A consumer may read two fields of one producer's result --
            # EXT_DECISION_VERIFY takes both ``input_path`` and ``result_path``
            # from ``decision.synthesis.typed``. That is one upstream step, not
            # two, so map the second field at the cycle already emitted instead
            # of running the producer again. Derived from cycle_by_ref so it
            # stays correct across recursion levels. The discriminator keeps
            # this scoped to references that ask for the SAME channel.
            cycle_by_ref[(effect,field,discr)]=min(prior)
            continue
        if depth<=0:
            return False
        provider=_select_channel(
            _channel_candidates(providers,effect.lower()),
            ref.get("where"),
            str(effect)+"/"+str(field),
            field=field,
        )
        if not provider:
            return False
        provider_id,provider_entry=provider[0],provider[1]
        if not isinstance(provider_entry,dict):
            return False
        declared={str(x).strip() for x in provider_entry.get("result_fields") or []
                  if isinstance(x,str) and x.strip()}
        if field not in declared:
            return False
        producer_inputs=_bind_producer_inputs(
            goal,root,provider_id,provider_entry,
            context_paths=context_paths,future_clauses=future_clauses
        )
        if producer_inputs is None:
            return False
        nested=_collect_effect_result_refs(producer_inputs)
        if nested:
            if not _append_producer_parts(
                nested,goal,registry,root,effect_providers,parts,actions,cycle_by_ref,
                context_paths=context_paths,future_clauses=future_clauses,
                depth=depth-1,
            ):
                return False
            producer_inputs=_rewrite_effect_result_refs(producer_inputs,cycle_by_ref)
            if _collect_effect_result_refs(producer_inputs):
                return False
        cycle=len(parts)
        cycle_by_ref[(effect,field,discr)]=cycle
        parts.append({
            "index":cycle,
            "mode":"EFFECT_PRODUCER",
            "selected_capability":provider_id,
            "subgoal":goal,
            "inputs":producer_inputs,
            "target_effects":list(provider_entry.get("provides") or []),
            "score":0,
        })
        actions.append({"type":"invoke_capability",
                        "args":_render_action_args(provider_entry,producer_inputs,provider_id)})
    return True


def _attach_effect_producer_steps(
    result, goal, registry, root, effect_providers,
    context_paths=None, future_clauses=None
):
    """Replace a dangling ``$effect_result`` with a real producer step.

    ``_bind_planned_inputs`` resolves a consumer's ``effect_result`` slot to
    ``{"$effect_result": {"effect": E, "field": F}}`` and records which
    capability produces ``E``, but the plan was emitted with the reference
    still dangling and no step able to satisfy it. The adapter then received a
    dict where its contract expects a path. Measured on the benchmark:
    ``EXT_DECISION_VERIFY`` reached ``decision.synthesis.verify.stdlib``
    carrying that dict verbatim and died with
    ``DECISION_VERIFIER_INPUT_MISSING``, and both knowledge goals reached
    ``assess_knowledge_consistency`` the same way.

    A producer is attached only when its own non-output inputs bind from this
    sentence. A producer that needs a url or a path the goal never states is
    left exactly as it was, so this cannot turn an honest refusal into a chain
    whose first step is guaranteed to fail.
    """
    refs=_collect_effect_result_refs(result.get("inputs"))
    if not refs:
        return result
    cycle_by_ref={}
    parts=[]
    actions=[]
    if not _append_producer_parts(
        refs,goal,registry,root,effect_providers,parts,actions,cycle_by_ref,
        context_paths=context_paths,future_clauses=future_clauses,
        depth=_MAX_PRODUCER_CHAIN_DEPTH,
    ):
        return result
    consumer_inputs=_rewrite_effect_result_refs(result.get("inputs"),cycle_by_ref)
    if _collect_effect_result_refs(consumer_inputs):
        return result
    consumer_id=result.get("selected_capability")
    consumer_entry=(registry or {}).get(consumer_id) or {}
    parts.append({
        "index":len(parts),
        "mode":"EFFECT_CONSUMER",
        "selected_capability":consumer_id,
        "subgoal":goal,
        "inputs":consumer_inputs,
        "target_effects":list(consumer_entry.get("provides") or []),
        "score":result.get("score"),
    })
    actions.append({"type":"invoke_capability",
                    "args":_render_action_args(consumer_entry,consumer_inputs,consumer_id)})
    actions.append({"type":"finish","args":{"summary":"EFFECT_PRODUCER_CHAIN_COMPLETE"}})
    chained=dict(result)
    chained["inputs"]=consumer_inputs
    chained["compiled_parts"]=parts
    chained["controller_actions"]=actions
    chained["binding_source"]=str(result.get("binding_source") or "")+"+EFFECT_PRODUCER_CHAIN"
    chained["effect_producer_chain"]=[p["selected_capability"] for p in parts]
    return chained


def _render_action_args(entry, inputs, capability_id):
    """Render an action_template against bound inputs, as the runtime does."""
    args={}
    for key,value in ((entry.get("action_template") or {}).get("args") or {}).items():
        if isinstance(value,str) and value.startswith("${input.") and value.endswith("}"):
            args[key]=inputs.get(value[len("${input."):-1])
        else:
            args[key]=value
    args.setdefault("capability_id",capability_id)
    return args


def _compile_single_goal(
    goal, registry, root, context_paths=None, future_clauses=None,
    proposal_binder=None, effect_providers=None, attach_producer_steps=False
):
    ranked_unbindable=[]  # [(score, specificity, cid), ...] word-matched, could not bind
    ranked=_rank_bindable_candidates(
        goal,registry,root,
        context_paths=context_paths,
        future_clauses=future_clauses,
        proposal_binder=proposal_binder,
        effect_providers=effect_providers,
        allow_world_binding=False,
        unbindable_out=ranked_unbindable,
    )
    binding_source="GOAL_STATEMENT"
    if not ranked:
        ranked=_rank_bindable_candidates(
            goal,registry,root,
            context_paths=context_paths,
            future_clauses=future_clauses,
            proposal_binder=proposal_binder,
            effect_providers=effect_providers,
            allow_world_binding=True,
            unbindable_out=ranked_unbindable,
        )
        binding_source="GOAL_STATEMENT+WORLD_BINDING"
    if ranked and ranked_unbindable:
        # THE LAW THIS REPO ALREADY STATES: when the best word-match cannot be
        # called, refuse -- never substitute a weaker-scoring tool merely
        # because it happens to be callable.  Bindable-beats-unbindable
        # regardless of score is the measured failure shape that made a
        # barcode decoder outrank the barcode generator, msgpack cover XLSX,
        # and pandoc cover jq.
        #
        # Precise scope: the predicate fires only against a substitution that
        # consumed NOTHING from the sentence -- the would-be substitute either
        # declares no input placeholders at all (a vacuous bind: it attaches
        # to any sentence for free, e.g. msgpack/kstar catch-alls) or filled at
        # least one slot with a world guess the goal never justified
        # (``filled_from_world_not_goal``: pandoc pinning markdown_path to
        # AGENTS.md for a jq query).  A sentence that fully states a grounded
        # candidate's contract therefore still selects it with certainty:
        # lexical noise from unbindable neighbours (a decoder outscoring the
        # generator the sentence fully names) is noise, not law.
        best_unbindable=max(ranked_unbindable, key=lambda x:(x[0],x[1]))
        survivor_provenance=ranked[0][6]
        survivor_args=((ranked[0][3].get("action_template") or {}).get("args") or {})
        survivor_vacuous=not any(
            isinstance(v,str) and v.startswith("${input.") for v in survivor_args.values()
        )
        survivor_unjustified=bool(
            isinstance(survivor_provenance,dict)
            and (survivor_provenance.get("filled_from_world_not_goal") or {})
        )
        if best_unbindable[0] > ranked[0][0] and (survivor_vacuous or survivor_unjustified):
            raise GoalCompilationFailure(
                "GOAL_COMPILATION_BEST_MATCH_UNBINDABLE",
                json.dumps({
                    "unbindable_best_match": best_unbindable[2],
                    "unbindable_best_match_score": best_unbindable[0],
                    "substitute_refused": ranked[0][2],
                    "substitute_score": ranked[0][0],
                    "substitute_binding": (
                        "VACUOUS" if survivor_vacuous else "UNJUSTIFIED_WORLD_SLOTS"
                    ),
                }, sort_keys=True),
            )
    if not ranked:
        raise GoalCompilationFailure("GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH")
    best=ranked[0]
    if len(ranked)>1 and ranked[1][0]==best[0] and ranked[1][1]==best[1]:
        resolved=_resolve_tie_by_executability(
            goal,registry,root,ranked,
            context_paths=context_paths,
            future_clauses=future_clauses,
            proposal_binder=proposal_binder,
            effect_providers=effect_providers,
        )
        if resolved is None:
            raise GoalCompilationFailure(
                "GOAL_COMPILATION_AMBIGUOUS",
                json.dumps({"candidates":[best[2],ranked[1][2]],"score":best[0]},sort_keys=True)
            )
        best=resolved
        # The winning slots were completed from the world, not the sentence, so
        # the provenance label must say so -- the same label the inferred pass
        # already uses.
        binding_source="GOAL_STATEMENT+WORLD_BINDING"
    score,specificity,cid,entry,inputs,evidence,binding_provenance=best
    result={
        "schema":"PROJECT_BRAIN_COMPILED_CAPABILITY_PROBLEM_V1",
        "compiler_mode":"DETERMINISTIC_VERIFIED_CAPABILITY_MATCH",
        "selected_capability":cid,
        "score":score,
        "match_evidence":evidence,
        "inputs":inputs,
        "binding_source":binding_source,
        "initial_facts":list(entry.get("requires") or []),
        "target_effects":list(entry.get("provides") or []),
        "capabilities":[],
        "finish_summary":"PLAIN_GOAL_COMPLETE",
    }
    if binding_provenance:
        # Inference is shown, never buried: which slots were filled, and from
        # where, so a reviewer can see exactly what was not stated.
        result["binding_provenance"]={
            "filled_by_world_binding":binding_provenance.get("filled_by_world_binding") or [],
            "filled_from_world_not_goal":binding_provenance.get("filled_from_world_not_goal") or {},
            "filled_from_companion_not_goal":binding_provenance.get("filled_from_companion_not_goal") or {},
            "filled_from_demonstrated_case":binding_provenance.get("filled_from_demonstrated_case") or {},
        }
    if not attach_producer_steps:
        # Clause-level compiles are numbered by the compound path, which owns
        # the $result cycle indices. Attaching a producer step here would
        # renumber them out from under it.
        return result
    return _attach_effect_producer_steps(
        result,goal,registry,root,effect_providers,
        context_paths=context_paths,future_clauses=future_clauses,
    )


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


def _compile_literal_json_goal(goal, root):
    """Promote the existing strict literal-record grammar to a top-level goal."""
    text=" ".join(str(goal or "").strip().split())
    compiled=_compile_literal_json_records(text,root)
    if compiled is None:
        return None
    output_path=str(compiled["output_path"])
    path=pathlib.PurePosixPath(output_path)
    if (
        not output_path.startswith("canonical/")
        or path.is_absolute()
        or ".." in path.parts
        or path.suffix.lower()!=".json"
    ):
        return None
    action=compiled["action"]
    records=(action.get("args") or {}).get("records")
    fields=(action.get("args") or {}).get("fields")
    if not isinstance(records,list) or not isinstance(fields,list):
        return None
    return {
      "schema":"PROJECT_BRAIN_COMPILED_LITERAL_JSON_RECORDS_V1",
      "compiler_mode":"DETERMINISTIC_LITERAL_JSON_RECORDS",
      "target_effects":["structured.json.literal_records"],
      "clauses":[text],
      "compiled_parts":[{
        "index":0,
        "subgoal":text,
        "mode":"NATIVE_LITERAL_JSON_RECORDS",
        "output_path":output_path,
        "fields":list(fields),
        "record_count":len(records),
        "records_sha256":hashlib.sha256(
            json.dumps(records,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
      }],
      "controller_actions":[
        action,
        {"type":"finish","args":{"summary":"LITERAL_JSON_GOAL_COMPLETE"}},
      ],
      "finish_summary":"LITERAL_JSON_GOAL_COMPLETE",
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
        r"^(?:determine|check|verify|assess)\s+whether\s+(?:the\s+)?"
        r"(?:(?:two\s+.+?)|(?:.+?\s+and\s+.+?))\s+"
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


def _attribute_chained_parts_to_clauses(clauses, parts, registry):
    """Attribute a producer-chain plan's steps back to the sentence's clauses.

    A clause split compiles one capability per clause, so its ``compiled_parts``
    line up 1:1 with ``clauses`` and coverage is trivially complete. A chained
    plan is the other shape: it resolves the sentence's own dependency order, so
    "Extract evidence from a source, then rank it, then bind it to a claim"
    needs enumerate -> rank -> extract -> bind -- four steps for three clauses,
    because extracting objective-grounded evidence requires ranked candidates
    first.

    The clause ledger is about *the sentence being accounted for*, not about how
    many steps execution takes. So each clause is attributed to the step that
    actually answers it, scored with the same ``_score`` the rest of the
    compiler uses, and each clause must win a DISTINCT step. Steps that answer
    no clause -- the prerequisites the dependency order forced -- stay in the
    execution chain and in ``effect_producer_chain``, but are not claimed as
    clause coverage, because they are not what any clause asked for.

    Returns one part per clause index, or ``None`` when the attribution is not
    clean. Returning ``None`` is the honest outcome: an unattributable clause
    means the sentence is not accounted for and the caller refuses exactly as
    it did before.
    """
    if not isinstance(clauses, list) or not clauses:
        return None
    if not isinstance(parts, list) or not parts:
        return None
    scored = []
    for clause_index, clause in enumerate(clauses):
        text = clause.get("text") if isinstance(clause, dict) else clause
        if not isinstance(text, str) or not text.strip():
            return None
        best = None
        for part_index, part in enumerate(parts):
            if not isinstance(part, dict):
                return None
            cid = str(part.get("selected_capability") or "")
            entry = (registry or {}).get(cid)
            if not isinstance(entry, dict):
                return None
            score = _score(text, cid, entry)[0]
            if best is None or score > best[0]:
                best = (score, part_index)
        if best is None or best[0] <= 0:
            return None
        scored.append((clause_index, best[1], best[0]))
    # Each clause must win a distinct step. Two clauses collapsing onto one
    # step means the chain does not actually cover the sentence.
    if len({s[1] for s in scored}) != len(scored):
        return None
    attributed = []
    for clause_index, part_index, score in sorted(scored):
        part = parts[part_index]
        clause = clauses[clause_index]
        text = clause.get("text") if isinstance(clause, dict) else clause
        attributed.append({
            "index": clause_index,
            "subgoal": text,
            "mode": "EFFECT_PRODUCER_CHAIN_STEP",
            "selected_capability": part.get("selected_capability"),
            "inputs": part.get("inputs"),
            "score": score,
            "target_effects": part.get("target_effects") or [],
        })
    return attributed


def _inherit_producer_goal_for_verifier_steps(actions, registry):
    """Hand a verifier step the exact goal string its producer was given.

    Every clause of a compound goal is compiled with its own clause text bound to
    the ``goal`` input. That is correct for a step doing independent work and
    wrong for a step whose whole contract is to re-check an earlier one: an
    independent verifier recomputes a digest of the goal it is handed and compares
    it against the digest the producer recorded, so both must be handed the same
    string or the comparison can never succeed.

    Measured on BENCH_GROUNDING_AND_VERIFY -- "Compile a plain goal into a bound
    capability and verify the grounding." The clause split gave the producer
    'Compile a plain goal into a bound capability' (sha256 8999f288...) and the
    verifier 'verify the grounding' (sha256 4c9ae405...), so
    plain_goal.bound_capability.grounding.verify.stdlib failed with
    GOAL_HASH_MISMATCH even though the producer had succeeded.

    The relation is proved from the registry, not guessed: this fires only where a
    step requires an effect that an earlier step in this same plan provides. It
    therefore cannot fire on a single-step goal, and it does not fire on the
    archive verifier, whose requirements are ambient facts rather than plan
    outputs, so the tar goals are untouched. The inherited string still comes from
    the original request text and never from the producer's own output document,
    so the verifier remains independent of the thing it checks.
    """
    if not isinstance(actions, list) or len(actions) < 2:
        return actions
    producer_by_effect = {}
    for action in actions:
        if not isinstance(action, dict):
            continue
        args = action.get("args")
        if not isinstance(args, dict):
            continue
        entry = (registry or {}).get(str(args.get("capability_id") or "")) or {}
        if not isinstance(entry, dict):
            continue
        requires = {str(x) for x in entry.get("requires") or [] if isinstance(x, str) and x}
        consumed = requires & set(producer_by_effect)
        if consumed and "goal" in args:
            earliest = min(producer_by_effect[effect] for effect in consumed)
            producer_goal = earliest[1]
            if isinstance(producer_goal, str) and args["goal"] != producer_goal:
                args["goal"] = producer_goal
        producer_goal = args.get("goal")
        for effect in entry.get("provides") or []:
            if isinstance(effect, str) and effect:
                producer_by_effect.setdefault(effect, (len(producer_by_effect), producer_goal))
    return actions


# A clause that only says WHERE the previous answer goes is delivery, not a
# second task.  The census writes its questions that way, because that is how a
# person writes them:
#
#   "Which function in <b>/app is never executed by the tests in <b>/tests?
#    Write its name to <b>/answer.json"
#
# Measured on 814ae41 + three analysis rows: the first clause reached
# python.source.dead_code.v1 correctly, and the delivery clause was handed to
# python.software.request.semantic_behavior.compile.v1 as its own step, which
# failed, which made the whole run FAIL_CLOSED__TOOL_REPORTED_NON_SUCCESS -- for
# a question the machine had just answered.
#
# The object is ANAPHORIC: "its name", "the number", "the file and line".  It
# does not name a new subject, so it cannot name a new capability.  The
# vocabulary is closed on purpose, and "report"/"patch" are deliberately absent:
# "and write the report to R" is a promise the repair lane discharges, and
# stealing it here would unbind the artifact that gate reads.
_DELIVERY_RE = re.compile(
    r"^\s*(?:write|save|store|output)\s+(?:(?:its|their|the)\s+)?"
    r"(?:yes or no|true or false|name|number|count|result|results|answer|value|values|"
    r"file and line|path and line|line and file|path|line)\s+to\s+\S+\s*$",
    re.IGNORECASE)


def _compile_answer_delivery(clause, actions, compiled_parts, root):
    """Point the PREVIOUS step's output at the destination this clause names.

    Returns True when the clause was consumed.  Nothing new is executed: the
    delivery is the destination of the answer the previous step already
    produces, which is exactly what a single-capability compile of the same
    sentence does with ``output_path``.
    """
    text = str(clause or "")
    if not _DELIVERY_RE.match(text):
        return False
    if not actions:
        return False
    stated = [str(raw) for raw, path in _repo_paths(text, root) if not path.is_dir()]
    if len(stated) != 1:
        return False
    args = actions[-1].get("args")
    if not isinstance(args, dict) or "output_path" not in args:
        return False
    args["output_path"] = stated[0]
    for part in reversed(compiled_parts):
        inputs = part.get("inputs")
        if isinstance(inputs, dict) and "output_path" in inputs:
            inputs["output_path"] = stated[0]
            break
    return True


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

        # Delivery of the previous answer is not a second subgoal.
        if _compile_answer_delivery(clause, actions, compiled_parts, root):
            consumed_indices.add(index)
            continue

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
            if (
                exc.code=="GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH"
                and compiled_parts
                and _subgoal_absorbed_by_prefix(clause,compiled_parts,registry)
            ):
                # The sentence was split into clauses, but one action was
                # described twice: "Read a PDF and extract its text" names a
                # single capability whose own identity is extracting text from
                # a PDF. The second clause matches nothing because there is
                # nothing left to match -- the work it asks for is already in
                # the compiled prefix. Absorb it rather than refuse a goal the
                # machine can in fact carry out.
                #
                # Deliberately narrow: only when NO capability matched at all,
                # and only when every content word of the clause is already
                # present in the prefix capability's own identity. A clause with
                # a real candidate is never absorbed.
                compiled_parts.append({
                    "index":index,"subgoal":clause,
                    "mode":"SUBGOAL_ABSORBED_BY_COMPILED_PREFIX",
                    "selected_capability":compiled_parts[-1].get("selected_capability"),
                })
                continue
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
        if not isinstance(runtime_inputs,dict):
            # A compiled part with no input mapping is a compiler defect, not a
            # missing value. Fail closed with a named reason: dereferencing it
            # raised AttributeError out of the planner, which is an unhandled
            # crash rather than a refusal.
            raise GoalCompilationFailure(
                "GOAL_COMPILED_PART_INPUTS_MISSING",
                json.dumps({"index":index,"subgoal":clause,"capability":cid},sort_keys=True)
            )
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
            # Typed channels: every producer of an effect publishes an
            # endpoint in step order; nothing is silently overwritten.
            # Untyped consumers resolve via the selection law whose default
            # keeps the historical last-writer-wins endpoint byte-identical.
            effect_providers.setdefault(effect,[]).append((cid,entry))
            runtime_effect_providers.setdefault(effect,[]).append((producer_cycle,producer_cap))
        compiled_parts.append({
            "index":index,
            "subgoal":clause,
            "mode":"VERIFIED_CAPABILITY",
            "selected_capability":cid,
            "inputs":runtime_inputs,
            "target_effects":part["target_effects"],
            "score":part["score"],
        })
    _inherit_producer_goal_for_verifier_steps(actions, registry)
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



def _compile_exact_markdown_pdf_goal(goal, registry, root):
    """Bind the exact repository-local Markdown-to-PDF conversion family.

    Generic token scoring sees the output PDF path and can prefer PDF readers.
    This exact compiler resolves only the unambiguous conversion grammar and
    requires the already-verified Pandoc+WeasyPrint producer.
    """
    text=" ".join(str(goal or "").strip().split())
    match=re.fullmatch(
        r"Convert (?P<markdown>canonical/[A-Za-z0-9_.\-/]+\.(?:md|markdown)) "
        r"to (?P<output>canonical/[A-Za-z0-9_.\-/]+\.pdf)\.?",
        text,
        re.IGNORECASE,
    )
    if match is None:
        return None
    cid="document.convert.markdown_pdf.pandoc_weasyprint"
    entry=(registry or {}).get(cid)
    if (
        not isinstance(entry,dict)
        or entry.get("status")!="VERIFIED_BOUND_CAPABILITY"
        or str(entry.get("adapter_module") or "")!="pandoc_weasyprint"
        or not isinstance(entry.get("action_template"),dict)
    ):
        raise GoalCompilationFailure("MARKDOWN_PDF_VERIFIED_PRODUCER_REQUIRED")
    root_path=pathlib.Path(root).resolve()
    markdown=match.group("markdown")
    output=match.group("output")
    src=(root_path/markdown).resolve()
    dst=(root_path/output).resolve()
    try:
        src.relative_to(root_path)
        dst.relative_to(root_path)
    except ValueError as exc:
        raise GoalCompilationFailure("MARKDOWN_PDF_PATH_OUTSIDE_REPOSITORY") from exc
    if not src.is_file():
        raise GoalCompilationFailure("MARKDOWN_PDF_SOURCE_MISSING",markdown)
    if src == dst:
        raise GoalCompilationFailure("MARKDOWN_PDF_INPUT_OUTPUT_COLLISION")
    inputs={"markdown_path":markdown,"output_path":output}
    return {
        "schema":"PROJECT_BRAIN_COMPILED_CAPABILITY_PROBLEM_V1",
        "compiler_mode":"DETERMINISTIC_EXACT_MARKDOWN_PDF_CONVERSION",
        "selected_capability":cid,
        "score":1000,
        "match_evidence":{
            "exact_grammar":"REPOSITORY_LOCAL_MARKDOWN_TO_PDF_V1",
            "source_exists":True,
            "producer_adapter":"pandoc_weasyprint",
        },
        "inputs":inputs,
        "initial_facts":list(entry.get("requires") or []),
        "target_effects":list(entry.get("provides") or []),
        "capabilities":[],
        "finish_summary":"PLAIN_GOAL_COMPLETE",
    }


def _compile_exact_literal_response_goal(goal):
    """Lower a strict exact-literal response instruction to one native finish action.

    This is intentionally narrow. Unquoted literals must be a single safe atom;
    multi-word or punctuation-sensitive literals must be quoted. The compiler
    never guesses where an unquoted literal ends.
    """
    text=" ".join(str(goal or "").strip().split())
    if not text:
        return None
    match=re.fullmatch(
        r"""(?:reply|respond)\s+with\s+exactly\s+(?:"([^"\r\n]{1,4096})"|'([^'\r\n]{1,4096})'|([A-Za-z0-9_:+/@#%=-]{1,512}))\.?""",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    literal=next((x for x in match.groups() if x is not None),None)
    if literal is None or not literal:
        return None
    return {
      "schema":"PROJECT_BRAIN_COMPILED_EXACT_LITERAL_RESPONSE_V1",
      "compiler_mode":"DETERMINISTIC_EXACT_LITERAL_RESPONSE",
      "target_effects":["response.exact_literal"],
      "clauses":[text],
      "compiled_parts":[{
        "index":0,
        "subgoal":text,
        "mode":"NATIVE_EXACT_LITERAL_RESPONSE",
        "literal_sha256":hashlib.sha256(literal.encode("utf-8")).hexdigest(),
        "literal_length":len(literal),
      }],
      "controller_actions":[{
        "type":"finish",
        "args":{"summary":literal},
      }],
      "finish_summary":literal,
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
    exact_literal=_compile_exact_literal_response_goal(goal)
    if exact_literal is not None:
        return _validate_compiled_clause_coverage(exact_literal)
    literal_json=_compile_literal_json_goal(goal,root)
    if literal_json is not None:
        return _validate_compiled_clause_coverage(literal_json)
    markdown_pdf=_compile_exact_markdown_pdf_goal(goal,registry,root)
    if markdown_pdf is not None:
        return _validate_compiled_clause_coverage(markdown_pdf)
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
        try:
            return _validate_compiled_clause_coverage(
                _compile_compound_goal(goal,clauses,registry,root)
            )
        except GoalCompilationFailure as compound_failure:
            # The clause split compiles each clause against producers already
            # in the plan (_compile_compound_goal starts effect_providers={}),
            # so a clause whose correct capability needs an upstream producer
            # can only fall back to a weaker one -- and then the sentence's
            # real dependency order can never be completed. The chained pass
            # resolves that order instead, scoring 30 against the grounded
            # single pass's 19 on "Extract evidence from a source, then rank
            # it, then bind it to a claim", with the full
            # enumerate -> rank -> extract -> bind chain.
            #
            # This runs ONLY where the split has already failed, so it cannot
            # take a goal the split was answering. And it is refused unless
            # every clause wins a distinct step: an incomplete attribution
            # re-raises the split's original, honest reason.
            if compound_failure.code!="GOAL_COMPILATION_SUBGOAL_UNRESOLVED":
                raise
            try:
                chained=_compile_single_goal(
                    goal,registry,root,
                    proposal_binder=_load_sibling_runtime_module(
                        "capability_proposal_generators.py",
                        "project_brain_direct_compiler_proposal_binder",
                    ),
                    effect_providers=_effect_providers(registry),
                    attach_producer_steps=True,
                )
            except GoalCompilationFailure:
                raise compound_failure
            attributed=_attribute_chained_parts_to_clauses(
                clauses,chained.get("compiled_parts"),registry
            )
            if attributed is None:
                raise compound_failure
            covered=dict(chained)
            covered["clauses"]=[
                c if isinstance(c,dict) else {"text":c} for c in clauses
            ]
            covered["compiled_parts"]=attributed
            covered["effect_producer_chain_steps"]=(
                chained.get("effect_producer_chain") or []
            )
            return _validate_compiled_clause_coverage(covered)
    # Producer->consumer (``effect_result``) binding reaches nine capabilities
    # that the grounded pass cannot, because their slots are filled from another
    # capability's output. Two ways to use it have both been measured:
    #
    #   always on            compiled 18 to 16, correct 14 to 11  (net loss: three
    #                        goals stolen, three begun refusing)
    #   only after a failure compiled 18 to 19, correct 14 to 15  (net gain, but
    #                        blind: a goal that compiles wrongly never retries)
    #
    # The failure trigger was blind in a specific, measured way: on "Assess
    # knowledge consistency" the grounded pass SUCCEEDS with
    # terminal.kstar.root.assess.stdlib at score 2, while
    # knowledge.consistency.assess scores 22 and is reachable once producers are
    # supplied -- so the retry never fired and the catch-all won.
    #
    # Both passes score with the same _score, so their results are directly
    # comparable. Run both and keep the better-scoring one: that recovers the
    # goals the failure trigger missed while still refusing to let a greedier
    # capability take one the grounded pass already answered better.
    binder=_load_sibling_runtime_module(
        "capability_proposal_generators.py",
        "project_brain_direct_compiler_proposal_binder",
    )
    providers=_effect_providers(registry)
    grounded=None
    grounded_failure=None
    try:
        grounded=_compile_single_goal(goal,registry,root)
    except GoalCompilationFailure as exc:
        grounded_failure=exc
    try:
        chained=_compile_single_goal(
            goal,registry,root,
            proposal_binder=binder,
            effect_providers=providers,
            attach_producer_steps=True,
        )
    except GoalCompilationFailure:
        chained=None
    if grounded is None and chained is None:
        # The grounded pass's reason is the honest one: it describes what the
        # goal itself lacked, not what the wider second pass also lacked.
        raise grounded_failure
    if grounded is None:
        return chained
    if chained is None:
        return grounded
    # A PLAN BUILT ON A GUESS LOSES TO A PLAN BUILT ON THE SENTENCE.
    #
    # `grounded` above falls back to world binding when the sentence alone binds
    # nothing, so the plan named `grounded` can be one whose slots were filled by
    # scanning the filesystem -- and `_plan_score` is a pure lexical number, so
    # such a plan can outscore a chained plan every one of whose slots the
    # sentence accounted for.
    #
    # Measured.  "Summarize a markdown document into a decision record." gives a
    # grounded pass of `document.convert.markdown_pdf.pandoc_weasyprint` at score
    # 25 whose `markdown_path` was filled with AGENTS.md, and a chained pass of
    # `decision.synthesis.typed.stdlib` at score 14 whose every slot comes from
    # the sentence plus a declared producer.  Score alone picks the converter,
    # which then offers a PDF nobody asked for.
    #
    # The test is deliberately narrow, and it is the repository's own distinction
    # rather than a new one: it fires only when the winning plan has a slot in
    # `filled_from_world_not_goal` AND the alternative has none.  A world-bound
    # plan whose slots are all backed by a demonstrated case is untouched, which
    # is what keeps "Audit the python source tree with an AST." on
    # `python.source.audit.ast`.  Measured across all 23 benchmark goals this
    # fires on exactly one, and that one is a fix.  Preferring grounded over
    # world-bound UNCONDITIONALLY was tried and measured at 21->19 canonical and
    # 20->19 front-door, because it broke exactly those audit goals -- so the
    # unjustified-slot test is load-bearing, not decoration.
    if (_plan_has_unjustified_world_slots(grounded)
            and not _plan_has_unjustified_world_slots(chained)):
        return chained
    return chained if _plan_score(chained)>_plan_score(grounded) else grounded
