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
# What this reader can turn into callables today, as opposed to merely list.
_READABLE_SUFFIXES = frozenset({".py"})

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


def _top_level_names(path: pathlib.Path) -> list[str]:
    """The names a file defines at top level and as members of its classes.

    Read from source with ast: no import, no execution. A file's own vocabulary is the best cheap
    description of what it is for -- better than its path, and free to obtain.
    """
    tree = _safe_parse(path)
    if tree is None:
        return []
    out = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name.startswith(_PUBLIC):
                continue
            out.append(node.name)
            if isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not sub.name.startswith(_PUBLIC):
                            out.append(node.name + " " + sub.name)
    return out[:200]


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
    # WALK THE STRUCTURE, NOT A FLATTENED BAG OF NODES.
    #
    # `ast.walk` returns methods and module-level functions alike, with nothing to tell them apart --
    # so a class's methods were listed as if they could be called directly, and the class they belong
    # to was lost. Measured 2026-11-23 on an installed stdlib directory: argparse's entire public
    # surface is `ArgumentParser.add_argument` / `parse_args`, so a room whose answers are all methods
    # presented as nearly empty to anything that could not name the owner.
    #
    # Each callable now carries its `owner` (the class it is defined in, or "" at module level) and a
    # `call` string that a caller can actually use. Nested functions stay unowned: they are closures,
    # not API, and offering them would be advertising something no one outside the file can call.
    entries = []

    def _collect(body, owner, depth):
        for node in body:
            if isinstance(node, ast.ClassDef):
                if node.name.startswith(_PUBLIC):
                    continue
                _collect(node.body, node.name if depth == 0 else owner + "." + node.name, depth + 1)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith(_PUBLIC):
                    continue
                entries.append((node, owner))

    _collect(tree.body, "", 0)

    for node, owner in entries:
        sig = _signature(node)
        doc = _doc_summary(node)
        # MEANING IS NAME + DOCSTRING. A function whose docstring says nothing is still listed --
        # it exists and might be the only thing here -- but it carries the module's own statement
        # so a reader is not handed a bare identifier and told it is an answer.
        # THE OWNER'S NAME IS PART OF WHAT THIS THING IS. `add_argument` alone is generic;
        # `ArgumentParser.add_argument` is the sentence a person would actually say.
        text = " ".join(x for x in (owner.replace("_", " ") if owner else "",
                                    node.name.replace("_", " "), doc) if x)
        out.append({
            "function": node.name,
            "owner": owner,
            "call": (owner + "." + node.name) if owner else node.name,
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


def source_index(root: Any, max_files: int = 4000) -> dict:
    """Every source-shaped file in the room, with NO parsing. The cheap first pass.

    WHY THIS IS SEPARATE FROM `survey`. On a real tree the parse budget runs out long before the
    files do: measured 2026-11-23 on an installed standard-library directory, 667 python files
    against a 400-file budget, and `survey` read whichever 400 sorted first. On a big room that makes
    coverage ARBITRARY -- the function you need is quite likely in a file that was never opened, and
    the survey cannot say so.

    Listing paths costs microseconds each and needs no parse, so the whole room can be indexed even
    when it cannot be read. That is the same split the project already settled on elsewhere: the
    INDEX is task-agnostic, the READING is goal-scoped.
    """
    base = pathlib.Path(root).resolve()
    out, seen, skipped = [], {}, 0
    if not base.is_dir():
        return {"schema": SCHEMA, "root": str(base), "status": "NOT_A_DIRECTORY",
                "files": [], "source_seen": {}, "readable": []}
    for path in sorted(base.rglob("*")):
        if len(out) >= max_files:
            break
        try:
            rel_parts = path.relative_to(base).parts
        except Exception:
            continue
        if any(q in SKIP_DIRS or q.startswith(".") for q in rel_parts[:-1]):
            skipped += 1
            continue
        if not path.is_file():
            continue
        suf = path.suffix.lower()
        if suf not in _SOURCE_SUFFIXES:
            continue
        seen[suf] = seen.get(suf, 0) + 1
        out.append({"rel": str(path.relative_to(base)), "suffix": suf,
                    "readable": suf in _READABLE_SUFFIXES})
    readable = [f["rel"] for f in out if f["readable"]]
    unreadable = {k: v for k, v in seen.items() if k not in _READABLE_SUFFIXES}
    if readable:
        status = "INDEXED"
    elif unreadable:
        status = "NO_READABLE_SOURCE"
    else:
        status = "EMPTY"
    return {"schema": SCHEMA, "root": str(base), "status": status, "files": out,
            "readable": readable, "source_seen": seen, "unreadable_source": unreadable,
            "files_skipped": skipped, "truncated": len(out) >= max_files}


def survey(root: Any, max_files: int = MAX_FILES,
           max_functions: int = MAX_FUNCTIONS, objective: str = "") -> dict:
    """What this directory offers, as callables rather than as files.

    Deterministic and read-only: sorted by path, then by line, so the same room always produces the
    same census and two runs can be compared. Bounded on both axes because this runs first, in places
    nobody has vouched for.
    """
    base = pathlib.Path(root).resolve()
    if not base.is_dir():
        return {"schema": SCHEMA, "root": str(base), "status": "NOT_A_DIRECTORY",
                "functions": [], "files_read": 0, "files_skipped": 0}
    # ONE PASS OVER THE PATHS, THEN THE BUDGET.
    # The loop below used to STOP at max_files, so on a big room every file after the limit was
    # invisible -- there was nothing left for objective-guided selection to choose between, and the
    # reading was simply alphabetical (measured: 665 python files against a 400 budget).
    index = source_index(base)
    if index["status"] == "NOT_A_DIRECTORY":
        return {"schema": SCHEMA, "root": str(base), "status": "NOT_A_DIRECTORY",
                "functions": [], "files_read": 0, "files_skipped": 0}
    skipped = index["files_skipped"]
    seen_suffixes = dict(index["source_seen"])
    files = [base / rel for rel in index["readable"]]

    # WHEN THE ROOM IS BIGGER THAN THE BUDGET, SPEND THE BUDGET ON WHAT THE OBJECTIVE IS ABOUT.
    #
    # Ranking PATHS costs no parsing, and a file's name carries real signal -- a path like
    # `bound_capabilities/objective_relevance_bm25.py` says what it holds. With no objective there is
    # nothing to prefer, so the order is unchanged.
    budget_note = ""
    if objective and len(files) > max_files:
        # one parse per file, no import, no execution -- the same reading the survey would do anyway,
        # just spent on the names rather than on the whole body
        names_by_rel = {}
        for rel in index["readable"]:
            names_by_rel[rel] = _top_level_names(base / rel)
        try:
            from canonical.runtime.bound_capabilities import objective_relevance_bm25 as bm25
            # A FILENAME IS ONE TOKEN; A FILE'S CLASSES AND TOP-LEVEL NAMES ARE MANY.
            #
            # Ranking paths alone lost `argparse.py` for "parse command line arguments": the token
            # `parse` is in it, `argument` is not, and `argparse` is a third token that matches
            # neither. The names a file DEFINES are free to read (ast parse, no import, no exec) and
            # they are exactly the vocabulary a person uses -- `ArgumentParser.parse_args` says what
            # that file is for far better than its path does. So the path index carries each file's
            # top-level names, and the objective is scored against those.
            cands = [{"capability_id": rel,
                      "title": pathlib.PurePosixPath(rel).stem.replace("_", " "),
                      "snippet": (rel.replace("/", " ").replace("_", " ") + " "
                                  + " ".join(names_by_rel.get(rel, ())))}
                     for rel in index["readable"]]
            picked = bm25.rank(objective, cands, limit=max_files)
            chosen = [str((h.get("candidate") or {}).get("capability_id"))
                      for h in (picked.get("ranked_candidates") or [])
                      if (h.get("lexical_relevance_score") or 0) > 0]
            if chosen:
                files = [base / c for c in chosen][:max_files]
                budget_note = ("%d of %d python files read, chosen by objective relevance"
                               % (len(files), len(index["readable"])))
        except Exception:
            budget_note = ""
    # COVERAGE IS REPORTED WHETHER OR NOT IT COULD BE AIMED.
    #
    # `budget` used to be set only on the objective-guided path, so an alphabetically-truncated room
    # returned None -- indistinguishable from having read everything. That is the limit-reported-as-
    # a-fact mistake again, at the level of the survey instead of the reader. Whenever the budget cuts
    # the room, the survey now says so, and says whether anything guided the choice.
    if len(files) > max_files:
        budget_note = budget_note or ("%d of %d read, no objective supplied -- path order"
                                      % (max_files, len(files)))
    files = files[:max_files]

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
        "budget": budget_note or None,
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
        if row["function"].lower() in known or str(row.get("call") or "").lower() in known:
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
                   "title": str(r.get("call") or r["function"]).replace("_", " ").replace(".", " "),
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
        # THE SENTENCE ITSELF, NOT ONLY THE WORDS DERIVED FROM IT.
        # Without this the census read the docstring, used it to build keywords, and then dropped
        # it -- so the admitted capability carried `['summarise']` and nothing said what the function
        # was for. The forge already has a slot for it (`contract["doc"]`); this hands it over.
        "doc": str(row.get("doc") or "")[:400],
        "params": list(row.get("params") or []),
        "required": list(row.get("required") or []),
        "provides": list(provides or []) or ["forged." + stem + "::" + str(row.get("function") or "")],
        "declares": list(declares or []),
        "keywords": sorted(set(words)),
    }
