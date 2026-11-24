"""What can this directory do? Read the room, not the registry.

THE OWNER'S IDEA, AND THE HOLE IT FELL INTO.

    "All he should do is basically go into any new arbitrary environment in the computer and he
     doesn't know anything about anything. So all he should do basically is ask the right question
     and know all of the things that he should know about."

Measured 2026-11-23, that does not happen. A directory was given two honest callables:

    census.py
        profile(path)      -> per-column fill rate and numeric rate for a csv
        as_markdown(report)-> that report as a markdown table

and asked "profile the columns of a csv and write a markdown table". The registry offered five rows
that merely shared vocabulary, chose `document.convert.markdown_pdf.pandoc_weasyprint`, and reported
ACTION_FAILED. `census.profile` was never a candidate, because **nothing in this tree can say "there
is a callable in this directory that I have never met."** Every selector starts from a fixed registry.

The three parts already existed and none of them were connected:

    discover_v1.entrypoints()             reads Makefile / package.json / pyproject -- build commands,
                                          never python functions
    autonomous_capability_inventory_v1    one row per FILE, no functions, no docstrings, no meaning
    capability_forge_v1.forge_and_record  admits a function, but only when handed an `entry` dict that
                                          a human wrote by hand

This module is the missing sentence between them: a directory -> the callables in it, each described
by its own docstring and signature, with the file it came from. It decides nothing. It does not import,
execute, or admit anything. Admission is `capability_forge_v1`'s, selection is the front door's, and
relevance is `objective_relevance_bm25.rank` -- the scorer this tree already owns. Reading a room is
not trusting it.

WHAT IS DELIBERATELY NOT HERE.

  * No relevance scoring. `objective_relevance_bm25` is already the tree's answer to "which of these
    is about my objective", and a second scorer is how this project got two answers that drifted.
  * No import and no execution. A census must be safe on a directory nobody has vouched for, and it
    must be fast: it is the first thing that runs in a place we have never been.
  * No admission. Finding a function is not knowing it works; `forge_function` runs it, mutates it,
    and refuses it if it cannot. A census that admitted would be an inspector certifying itself.
"""
from __future__ import annotations

import ast
import pathlib
from typing import Any

SCHEMA = "PROJECT_BRAIN_ROOM_CENSUS_V1"

# Reading a room has to be the cheap part. These are the bounds, not a policy:
MAX_FILES = 400
MAX_FUNCTIONS = 2500
# Source-shaped files, whether or not this reader can parse them. Membership here is what lets the
# survey say "code is present but unreadable" instead of "nothing is here".
_SOURCE_SUFFIXES = frozenset({".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".rb",
                              ".go", ".rs", ".java", ".c", ".h", ".cpp", ".cc", ".sh", ".bash",
                              ".zsh", ".lua", ".php", ".pl", ".r", ".jl", ".swift", ".kt"})
SKIP_DIRS = frozenset({".git", "__pycache__", "node_modules", ".venv", "venv", ".tox",
                       ".pytest_cache", ".mypy_cache", "build", "dist", ".ruff_cache",
                       "site-packages", ".arena", "out", "target"})
# A callable a person could mean. Leading underscore is private; `__` is machinery.
_PUBLIC = "_"


def _doc_summary(node: ast.AST) -> str:
    """The function's own first paragraph, as meaning.

    A name says what the author typed; the docstring says what it is for. `profile` alone could be a
    profiler, a user profile, or this census's column report -- and it WAS a column report. The
    docstring is the only part of a file that states intent in the author's own words.
    """
    doc = ast.get_docstring(node) or ""
    if not doc:
        return ""
    first = doc.strip().split("\n\n")[0]
    return " ".join(first.split())[:300]


def _signature(node: ast.AST) -> dict[str, Any]:
    """Parameter names, defaults, and annotations -- read from source, never guessed."""
    args = getattr(node, "args", None)
    if args is None:
        return {"params": [], "required": [], "defaults": {}, "annotations": {}}
    positional = list(getattr(args, "posonlyargs", []) or []) + list(args.args)
    names = [a.arg for a in positional]
    # `self`/`cls` belong to a method's receiver, not to a caller
    if names and names[0] in ("self", "cls"):
        names = names[1:]
        positional = positional[1:]
    n_defaults = len(getattr(args, "defaults", []) or [])
    required = names[: len(names) - n_defaults] if n_defaults else list(names)
    defaults: dict[str, str] = {}
    for arg, default in zip(positional[len(positional) - n_defaults:], args.defaults if n_defaults else []):
        try:
            defaults[arg.arg] = ast.unparse(default)[:60]
        except Exception:
            defaults[arg.arg] = ""
    annotations = {}
    for a in positional:
        if a.annotation is not None:
            try:
                annotations[a.arg] = ast.unparse(a.annotation)[:60]
            except Exception:
                annotations[a.arg] = ""
    return {"params": names, "required": required, "defaults": defaults,
            "annotations": annotations}


def _repo_relative(path: pathlib.Path, base: pathlib.Path) -> str:
    """The file's path as a tool runner sees it, when that is knowable; else its room path.

    Never invents a prefix. If the room is not inside the working directory, there is no honest
    repository-relative answer, and the room-relative path is returned unchanged for a caller to
    resolve or refuse.
    """
    try:
        return str(path.resolve().relative_to(pathlib.Path.cwd().resolve()))
    except Exception:
        try:
            return str(path.relative_to(base))
        except Exception:
            return str(path)


def _safe_parse(path: pathlib.Path) -> ast.AST | None:
    """Parse without importing. Anything unreadable is skipped, not guessed at."""
    try:
        if path.stat().st_size > 512_000:
            return None
        return ast.parse(path.read_text(errors="replace"))
    except Exception:
        return None


def functions_in(path: pathlib.Path, root: pathlib.Path) -> list[dict]:
    """Every public function this one file defines, described by its own source."""
    tree = _safe_parse(path)
    if tree is None:
        return []
    try:
        rel = str(path.relative_to(root))
    except Exception:
        rel = str(path)
    # a module-level docstring describes the whole file; functions inherit it as context
    module_doc = " ".join((ast.get_docstring(tree) or "").strip().split("\n\n")[0].split())[:300]
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith(_PUBLIC):
            continue
        sig = _signature(node)
        doc = _doc_summary(node)
        # MEANING IS NAME + DOCSTRING. A function whose docstring says nothing is still listed --
        # it exists and might be the only thing here -- but it carries the module's own statement
        # so a reader is not handed a bare identifier and told it is an answer.
        text = " ".join(x for x in (node.name.replace("_", " "), doc) if x)
        out.append({
            "function": node.name,
            # TWO PATHS, BECAUSE THEY ANSWER TWO DIFFERENT QUESTIONS.
            # `source_rel` is the file's location IN THE ROOM -- what a person standing there would
            # say, and what a gap report should show. `source_path` is the same file relative to the
            # repository, which is what `capability_forge_v1` needs to import it (handed the room-
            # relative name it resolved nothing and refused with RESEARCH_TOOL_PATH_INVALID,
            # measured 2026-11-23). Deriving one from the other is only possible if the room sits
            # under the repository, which is exactly the case a survey cannot assume -- so the
            # survey records what it read rather than leaving a caller to reconstruct it.
            "source_rel": rel,
            "source_path": _repo_relative(path, root),
            "line": getattr(node, "lineno", 0),
            "params": sig["params"],
            "required": sig["required"],
            "defaults": sig["defaults"],
            "annotations": sig["annotations"],
            "doc": doc,
            "module_doc": module_doc,
            "text": text[:600],
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "returns": (ast.unparse(node.returns)[:60] if node.returns is not None else ""),
        })
    return out


def survey(root: Any, max_files: int = MAX_FILES,
           max_functions: int = MAX_FUNCTIONS) -> dict:
    """What this directory offers, as callables rather than as files.

    Deterministic and read-only: sorted by path, then by line, so the same room always produces the
    same census and two runs can be compared. Bounded on both axes because this runs first, in places
    nobody has vouched for.
    """
    base = pathlib.Path(root).resolve()
    if not base.is_dir():
        return {"schema": SCHEMA, "root": str(base), "status": "NOT_A_DIRECTORY",
                "functions": [], "files_read": 0, "files_skipped": 0}
    files: list[pathlib.Path] = []
    skipped = 0
    # WHAT KINDS OF SOURCE ARE HERE AT ALL.
    #
    # Reading only `*.py` made this census unable to tell two completely different rooms apart:
    # measured 2026-11-23, a directory holding only `tools.js` reported status SURVEYED with 0
    # functions -- identical to an EMPTY directory. An empty room is a fact; a room of code this
    # reader cannot parse is a LIMIT, and a caller that cannot distinguish them will confidently
    # report "nothing to learn here" about a place full of things to learn.
    #
    # So the survey reports what source kinds it saw and whether it could read them. Python is what
    # this census can turn into callables today; the rest is stated rather than hidden.
    _READABLE_SUFFIXES = {".py"}
    seen_suffixes: dict[str, int] = {}
    for path in sorted(base.rglob("*")):
        if len(files) >= max_files:
            break
        try:
            rel_parts = path.relative_to(base).parts
        except Exception:
            continue
        if any(p in SKIP_DIRS or p.startswith(".") for p in rel_parts[:-1]):
            skipped += 1
            continue
        if not path.is_file():
            continue
        suf = path.suffix.lower()
        if suf in _SOURCE_SUFFIXES:
            seen_suffixes[suf] = seen_suffixes.get(suf, 0) + 1
        if suf not in _READABLE_SUFFIXES:
            continue
        files.append(path)
    found: list[dict] = []
    for path in files:
        if len(found) >= max_functions:
            break
        found.extend(functions_in(path, base))
    # THE STATUS MUST SEPARATE THREE DIFFERENT ROOMS:
    #   SURVEYED                   python was here and was read
    #   NO_READABLE_SOURCE         code is here, in a language this reader cannot parse -- a LIMIT
    #   EMPTY                      nothing source-shaped is here -- a FACT
    # Conflating the last two is how a machine reports "nothing to learn" about a room it simply
    # could not read.
    unreadable = {k: v for k, v in seen_suffixes.items() if k not in _READABLE_SUFFIXES}
    if files:
        status = "SURVEYED"
    elif unreadable:
        status = "NO_READABLE_SOURCE"
    else:
        status = "EMPTY"
    return {
        "schema": SCHEMA,
        "root": str(base),
        "status": status,
        "files_read": len(files),
        "files_skipped": skipped,
        "source_seen": seen_suffixes,
        "unreadable_source": unreadable,
        "readable_source": sorted(_READABLE_SUFFIXES),
        "functions": found[:max_functions],
        "truncated": len(found) > max_functions,
        "note": ("Read from source: no import, no execution, no admission. "
                 "A function found here is a CANDIDATE, not a capability."),
    }


def unknown_functions(census: dict, known_ids) -> list[dict]:
    """The callables in this room that no capability already names.

    THIS is "what I do not know", answered about a place instead of about the registry. A function
    whose source already has a `forged.` row is known; everything else is a gap with a location and
    a signature, which is what makes it closable by one demonstration instead of by training.
    """
    # KNOWN MEANS: SOME CAPABILITY ALREADY NAMES THIS FUNCTION IN THIS FILE.
    #
    # The first version required BOTH the name and the file to match, but a capability id keeps only
    # the file's STEM (`forged.census.profile::profile`), never the directory -- so a fully-qualified
    # `source_rel` could never match it and every function stayed "unknown" forever. A gap that
    # cannot close is worse than no gap: it would ask for the same demonstration on every visit.
    #
    # Matching the FUNCTION NAME is enough, because that is what a capability id carries and what a
    # caller says. If a room holds two functions of one name, both are considered known -- the
    # conservative error, since it can only suppress a redundant demonstration, never a real one.
    known = set()
    for k in (known_ids or ()):
        text = str(k)
        known.add(text.split("::")[-1].lower() if "::" in text else text.split(".")[-1].lower())
    out = []
    for row in census.get("functions") or []:
        if row["function"].lower() in known:
            continue
        out.append(row)
    return out


def rank(census: dict, objective: str, limit: int = 8) -> dict:
    """Which of these callables is about this objective, scored by the tree's own BM25.

    Reused, not reimplemented. `objective_relevance_bm25.rank` is the answer this repository already
    settled on for "does this candidate bear on my objective", including its honest
    `semantic_entailment_status: UNVERIFIED`. Writing a second scorer here would be the mistake the
    tree records twice over.
    """
    from canonical.runtime.bound_capabilities import objective_relevance_bm25 as bm25
    rows = census.get("functions") or []
    if not rows:
        return {"schema": SCHEMA, "status": "NOTHING_TO_RANK", "ranked": []}
    # THE SCORER READS title / snippet, AND WEIGHTS THE TITLE TWICE.
    # Handing it a key it does not read (`text`) produced a room where every candidate scored 0.0
    # and the ranking said nothing -- measured 2026-11-23, on the very first room this surveyed.
    # The function's NAME is its title; its docstring is its snippet. Using the scorer's own fields,
    # rather than making it read mine, is the difference between reusing it and replacing it.
    candidates = [{"capability_id": "%s::%s" % (r["source_rel"], r["function"]),
                   "title": r["function"].replace("_", " "),
                   "snippet": r.get("doc") or "",
                   "row": r} for r in rows]
    report = bm25.rank(objective, candidates, limit=limit)
    ranked = []
    # A ZERO IS NOT A MATCH. `rank` returns every candidate it scored, including the ones with no
    # shared term, so passing them through would present "nothing here is about this" as a ranked
    # shortlist. Only positive-evidence rows are offered, and an all-zero room reports UNRESOLVED.
    for hit in (report.get("ranked_candidates") or [])[:limit]:
        if not (hit.get("lexical_relevance_score") or 0) > 0:
            continue
        cand = hit.get("candidate") or {}
        row = cand.get("row") if isinstance(cand, dict) else None
        if row is None:
            continue
        # the field is the scorer's own name for its own number; copying it under a different
        # name would let a reader think a second measurement had been taken
        ranked.append({**row, "score": hit.get("lexical_relevance_score"),
                       "matched_terms": hit.get("matched_terms")})
    return {"schema": SCHEMA, "status": report.get("status"), "objective": objective,
            "ranked": ranked,
            "relevance_scope": report.get("relevance_claim_scope"),
            "semantic_entailment_status": report.get("semantic_entailment_status")}


def closing_plan(census: dict, objective: str, known_ids=(), limit: int = 4) -> dict:
    """The room, the gaps in it, and which gaps this objective needs closed.

    One answer in the shape the owner asked for: here is what is here, here is what I did not
    know, and here is the short list worth a demonstration.
    """
    gaps = unknown_functions(census, known_ids)
    short = {"schema": SCHEMA, "root": census.get("root"), "functions_seen": len(census.get("functions") or []),
             "unknown": len(gaps), "objective": objective}
    if not gaps:
        return {**short, "status": "ROOM_ALREADY_KNOWN", "need": []}
    ranked = rank({**census, "functions": gaps}, objective, limit=limit)
    need = [{"source_rel": r["source_rel"], "function": r["function"],
             "params": r["params"], "doc": r["doc"][:160], "score": r["score"]}
            for r in ranked.get("ranked") or []]
    return {**short, "status": ranked.get("status"),
            "relevance_scope": ranked.get("relevance_scope"),
            "semantic_entailment_status": ranked.get("semantic_entailment_status"),
            "need": need}


def forge_entry(row: dict, keywords=None, provides=None, declares=None) -> dict:
    """Turn a census row into the `entry` dict `capability_forge_v1` consumes.

    WHY THIS EXISTS: THE TWO FIELDS ARE EASY TO GET WRONG, AND GETTING THEM WRONG LOOKS LIKE A BAD TOOL.

    Measured 2026-11-23: `forge_and_record` wants `module` to be the bare stem (`census`) and
    `source_rel` to be the repository path (`.../census.py`). Passing a dotted module name in `module`
    -- the obvious thing to write -- produced `RESEARCH_TOOL_PATH_INVALID` and `ran: 0/3`, which reads
    like the function being broken. It was not: the same row admitted at 2/3, 8/8 mutations killed,
    once spelled correctly.

    The census already knows both values, so it should not make every caller rediscover which one
    goes where. This is a spelling of a dict, not a decision: admission is still the forge's, and it
    still runs the function, twice, and tries to corrupt it.
    """
    rel = str(row.get("source_path") or row.get("source_rel") or "")
    stem = pathlib.PurePosixPath(rel).stem if rel else str(row.get("function") or "")
    words = [w for w in (keywords or []) if w]
    if not words:
        # the function's own name and docstring are what it says it is for; nothing is invented
        words = [w.lower() for w in str(row.get("function") or "").replace("_", " ").split()]
        words += [w.lower() for w in (row.get("doc") or "").split() if len(w) > 3][:12]
    return {
        "module": stem,
        "function": str(row.get("function") or ""),
        "source_rel": rel,
        "params": list(row.get("params") or []),
        "required": list(row.get("required") or []),
        "provides": list(provides or []) or ["forged." + stem + "::" + str(row.get("function") or "")],
        "declares": list(declares or []),
        "keywords": sorted(set(words)),
    }
