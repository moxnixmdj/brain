"""Answer a question about a computer, with the answer made of evidence.

Every other path in this system PRODUCES: it runs something and judges
whether the world changed. A question cannot be met that way. Asked
"how many test files are in this project", the loop produced nothing and
reported NOTHING_PRODUCED in zero seconds -- not because the answer was
hard, but because there was no route from a question to a reply. Half of
what a person does at a computer is finding things out, and that half had
no path at all.

So this path does not produce. It reads, and reports what it read.

The discipline is the same one used everywhere: do not ask the program,
ask the machine, and do not report what cannot be checked. An answer here
is a set of claims, each naming the file it came from and the line it was
found on, and each re-read by grounding_v1 before the answer counts. A
claim that cannot be grounded is reported as unverifiable rather than
quietly dropped, because an answer with its weakest part hidden is not an
answer, it is a confident noise.

What this deliberately does not do is interpret. It reports that
`src/a.py` line 12 says `def sign(`. Whether that answers the question is
the reader's call, and the evidence needed to make that call is placed in
their hands. A system that summarises away its sources becomes
unfalsifiable, which is the one thing none of this is allowed to be.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_INSPECT_V1"

# Directories that hold other people's code, or code this system fetched.
# The same exclusion as repair_v1 uses, for the same reason: a search that
# returns vendored packages is not a search of the project.
_SKIP = re.compile(
    r"(^|/)(node_modules|site-packages|\.brain_venv|\.venv|venv|vendor"
    r"|__pycache__|\.git|\.tox|\.nox|\.mypy_cache|\.pytest_cache"
    r"|third_party|external|dist|build)/",
    re.I,
)

# AN EXTENSION LIST IS A GUESS ABOUT CONTENT; THE BYTES ARE THE FACT.
#
# `.csv` was not in the list, so `find` and `search_named` skipped every CSV -- while
# `compute` happily counted their rows. The door would answer "how many rows are in
# sales.csv" and refuse "what is amount in sales.csv" with NOT_IN_NAMED_FILE, a
# confident claim that a word is absent from a file it never opened. That is the worst
# kind of wrong: the refusal names a place it did not look.
#
# Adding `.csv` would fix the instance and leave the cause, so the list is now a hint
# and the decision is made from the file itself: a NUL byte means binary, and valid
# UTF-8 means text. Kept as a fast path for the common extensions so the ordinary case
# does not pay for a read.
_TEXT_SUFFIX = {
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".json", ".toml", ".yml",
    ".yaml", ".md", ".rst", ".txt", ".cfg", ".ini", ".sh", ".html", ".css",
}
_MAX_FILES = 4000
_MAX_BYTES = 2_000_000

# Words that carry no information about what is being asked. Kept short:
# a long stopword list is a vocabulary of the questions I thought of,
# which is the brittleness this whole system exists to avoid.
_STOP = {
    "the", "a", "an", "is", "are", "was", "were", "do", "does", "did",
    "how", "many", "much", "what", "which", "who", "where", "when", "why",
    "this", "that", "these", "those", "in", "on", "of", "for", "to", "from",
    "and", "or", "it", "its", "be", "there", "any", "all", "me", "i",
}


def question_terms(question: str) -> list[str]:
    """The words a question is actually about.

    Deliberately simple. The interesting words are the ones that are not
    glue, and that survives into languages and domains nobody anticipated
    -- unlike a list of question templates.
    """
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_.-]{1,}", question or "")
    out, seen = [], set()
    for w in words:
        low = w.lower()
        if low in _STOP or len(low) < 3 or low in seen:
            continue
        seen.add(low)
        out.append(low)
    return out


# A LISTING QUESTION NAMES NO FILE, SO NO TERM CAN MATCH.
#
# "list the files in this directory" asks for the SET of entries. Every term in it
# (`list`, `files`, `directory`) describes the request rather than naming a thing
# inside the tree, so content matching can never answer it, and it returned
# NOTHING_FOUND while the directory held three files. That is a different operation
# from "where does this word appear", and it is answered by enumerating rather than
# by searching.
#
# It is gated on the question ASKING FOR A LISTING, not on the word `files` alone:
# "what is retries in files" is a content question and must stay one.
_LISTING = re.compile(r"\b(list|listing|enumerate|what files|which files|what's in|"
                      r"whats in|contents of|ls)\b", re.I)
_CONTAINER = re.compile(r"\b(files?|dir|directory|folder|entries|contents|here)\b", re.I)


def wants_a_listing(question: str) -> bool:
    """Is this question asking for a set of entries rather than a word occurrence?"""
    q = question or ""
    return bool(_LISTING.search(q)) and bool(_CONTAINER.search(q))


def listing(root: str, limit: int = 40) -> list[dict]:
    """Every file under `root`, as hits: the answer to a listing question.

    Recorded at line 0 with `matched: "listing"`, for the same reason a filename hit
    is: it says this file EXISTS, and claims nothing about its contents.
    """
    base = Path(root)
    if not base.is_dir():
        raise NotADirectoryError(f"cannot inspect {root!r}: not a directory")
    out: list[dict] = []
    for path in sorted(base.rglob("*")):
        if len(out) >= limit:
            break
        if not path.is_file():
            continue
        rel = path.relative_to(base).as_posix()
        if _SKIP.search(rel):
            continue
        out.append({"file": rel, "line": 0, "term": "<listing>",
                    "text": "", "matched": "listing"})
    return out


def _is_readable_text(path: Path) -> bool:
    """Is this file text a person could read out?

    Extension first as a fast path, then the bytes. A file with no extension at all --
    `Makefile`, `Dockerfile`, a `.gitignore`-less script -- is text and was previously
    invisible to the door, which is the same defect as the missing `.csv` entry from the
    other side.
    """
    if path.suffix.lower() in _TEXT_SUFFIX:
        return True
    try:
        if path.stat().st_size > _MAX_BYTES:
            return False
        head = path.read_bytes()[:4096]
    except OSError:
        return False
    if b"\x00" in head:
        return False
    try:
        head.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def find(root: str, terms: list[str], limit: int = 40) -> list[dict]:
    """Where the project mentions these words.

    Reads the bytes and records line numbers. Attested in the only sense
    available: the file was opened and this is what it contained.
    """
    base = Path(root)
    hits: list[dict] = []
    if not base.is_dir():
        # "Nothing found" and "I could not look" are different facts, and
        # collapsing them is how a system reports an empty answer when the
        # real problem is that the directory was never there. Found by
        # pointing this at a path that had been deleted: it answered
        # NOTHING_FOUND, which reads like a result.
        raise NotADirectoryError(f"cannot inspect {root!r}: not a directory")
    if not terms:
        return hits
    patterns = [re.compile(r"\b" + re.escape(t) + r"\b", re.I) for t in terms]
    files = 0
    for path in sorted(base.rglob("*")):
        if files > _MAX_FILES or len(hits) >= limit:
            break
        if not path.is_file():
            continue
        rel = path.relative_to(base).as_posix()
        if _SKIP.search(rel):
            continue
        if not _is_readable_text(path):
            continue
        # A QUESTION ABOUT A FILE NAMES THE FILE, AND THAT NAME IS NOT IN ITS BODY.
        #
        # This loop only ever matched file CONTENTS, so "how many lines are in
        # data.py" could not find data.py unless the word "data" happened to appear
        # inside it. Measured on a three-file tree: 'what is retries in config.json'
        # answered PARTIALLY_GROUNDED only because `retries` is a key inside that
        # file, while 'how many lines are in data.py' and 'what does notes.md say'
        # both returned NOTHING_FOUND -- the filename is the one thing a question
        # usually gives you, and it was the one thing never looked at.
        #
        # A filename match is recorded at line 0: it says the file exists and was
        # selected, which is a different fact from "this word occurs at this line",
        # and claiming a line number nobody read would be the lie this module exists
        # to avoid.
        try:
            if path.stat().st_size > _MAX_BYTES:
                continue
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        files += 1
        name_matched = [t for t in terms
                        if re.search(r"\b" + re.escape(t) + r"\b", rel, re.I)]
        # ONE FILE IS REPORTED ONCE.
        #
        # A file that matches by name and by body is still one file, and recording it
        # twice inflates the number of findings -- so the body is scanned FIRST and the
        # name hit is emitted only when the body produced nothing. The reverse order was
        # used before, with a `continue` that skipped the body scan entirely: a file the
        # question named was recorded and never searched, so "what is retries in
        # conf.json" reported `retries` as missing from a file that contains it.
        #
        # Scanning first gets both properties at once: no file is skipped, and no file
        # is counted twice.
        body_hits = []
        for index, line in enumerate(text.splitlines(), start=1):
            for i, pat in enumerate(patterns):
                if pat.search(line):
                    body_hits.append({
                        "file": rel,
                        "line": index,
                        "term": terms[i],
                        "text": line.strip()[:200],
                    })
                    break
        if body_hits:
            # Content is the stronger evidence: it says the file is there AND what is
            # in it, so it stands in for the name hit rather than joining it.
            for hit in body_hits:
                hits.append(hit)
                if len(hits) >= limit:
                    break
        elif name_matched:
            hits.append({
                "file": rel,
                "line": 0,
                "term": name_matched[0],
                "text": "",
                "matched": "filename",
            })
        if len(hits) >= limit:
            break
    return hits


# A QUESTION CAN ASK FOR A COMPUTATION OVER A FILE, AND LOCATING THE FILE IS NOT
# THE COMPUTATION.
#
# "how many lines are in data.py" returned GROUNDED with one hit: the file itself,
# at line 0, matched by name. It never counted anything. The file had four lines and
# the answer contained no four. That is the worst failure mode in the system, and it
# is not a missed edge case -- it is the verdicts being about the wrong thing. A
# verdict of GROUNDED was being read as "the question was answered" when it only ever
# meant "the evidence is real". Those differ exactly when a question asks for a
# computation, and then the honest verdict is that the reading was grounded and the
# question is still open.
#
# So: work out what is being asked, compute it, and check the computation against the
# file it claims to be about. The answer carries the number, not just a pointer.
_COUNT_LINES = re.compile(r"\bhow many lines\b|\bline count\b|\bnumber of lines\b", re.I)
_COUNT_ROWS = re.compile(r"\bhow many (?:rows|records|entries|lines of data)\b", re.I)
_COUNT_FILES = re.compile(r"\bhow many (?:files|python files|modules)\b", re.I)
_FILE_MENTION = re.compile(r"[A-Za-z0-9_.\-/]+\.[A-Za-z0-9]{1,6}\b")


def _named_file(question: str, root: str) -> str | None:
    """The file the question is about, if it names exactly one that exists here.

    Two passes, because a file is named by a path or by a bare word that happens to be
    a file. `Makefile` has no extension and was therefore never a `_FILE_MENTION`, so
    "what does Makefile say" did not recognise the file it named and fell back to
    searching the tree. The word pass only accepts words that ARE files here, so an
    ordinary noun in the question does not become a filename by accident.
    """
    base = Path(root)
    text = question or ""
    found: list[str] = []
    for m in _FILE_MENTION.finditer(text):
        cand = m.group(0)
        if (base / cand).is_file() and cand not in found:
            found.append(cand)
    if not found:
        for word in re.findall(r"[A-Za-z0-9_.\-]+", text):
            cand = word.strip(".,;:\"'()")
            if cand and cand not in found and (base / cand).is_file():
                found.append(cand)
    return found[0] if len(found) == 1 else None


# A PATH IS ONE NAME, NOT A PILE OF SEARCH TERMS.
#
# "what is retries in canonical/runtime/inspect_v1.py" tokenised to
# ['retries','canonical','runtime','inspect_v1.py']. The three path fragments are not
# things to look for -- they are the ADDRESS of the one file the question names -- but
# they matched thousands of files across the tree, the forty-hit cap filled with
# .github/ and markdown audits, and the file that actually contains `retries` was never
# reached. The door reported `retries` as not found in a file containing it five times.
#
# This is the same defect as the earlier name/body one at a different layer: the search
# answered a question about WHERE by searching WHAT. When the question names a file, the
# file is searched first and its path fragments stop being subject terms.
def _project_files(root: str) -> list[Path]:
    """The files a person means when they ask what is in this directory.

    `.git` is 220 files of object store in this repository and it is not part of the
    project. Counting it made "how many files are in this directory" answer 20823 on a
    tree holding 20603 -- an answer that is wrong in the one way a count must not be.
    Uses the same skip list `find()` uses, so the two cannot drift apart.
    """
    base = Path(root)
    out: list[Path] = []
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(base).as_posix()
        if _SKIP.search(rel + "/"):
            continue
        out.append(path)
    return out


def _path_components(rel: str, question: str = "") -> set[str]:
    """Which of the question's own words are just the address of the named file.

    Returns only terms the question actually contains, so nothing is invented and
    nothing outside the question is dropped. A directory segment counts by its whole
    name and by its stem; a FINAL segment counts only by its whole name, because
    `mod.py` contains a dot that is part of what the asker wrote, while `retry.py`
    should not make `retry` disappear from a question that asked about it.

    `data` in "what is data in data/x.csv" is a directory name the asker typed -- it
    addresses the file. `retry` in "what is retry in retry.py" is the subject, and a
    file called retry.py is not evidence that the word retry is inside it.
    """
    raw = (rel or "").strip().strip("/")
    if not raw:
        return set()
    # The question spells the path as ONE token, so the segments are looked for both as
    # standalone words and inside that token. Looking only for standalone words found
    # nothing at all and dropped no fragments; looking only inside the token would drop
    # any segment whose name happens to appear elsewhere in the sentence.
    words = {w.lower() for w in (question or "").split()}
    words |= {w.lower().strip(".,;:\"'()") for w in words}
    parts = [x for x in raw.split("/") if x]
    out: set[str] = set()
    for i, part in enumerate(parts):
        low = part.lower()
        is_final = (i == len(parts) - 1)
        if low in words:
            out.add(low)
        if not is_final and "." in low:
            stem = low.rsplit(".", 1)[0]
            if stem in words:
                out.add(stem)
    return out


def _drop_path_fragments(terms: list[str], rel: str, question: str) -> list[str]:
    """Remove the terms that are only the address of the file the question names."""
    if not rel:
        return terms
    parts = [x for x in rel.strip().strip("/").split("/") if x]
    # Every segment except the final one is a directory the asker typed; it addresses
    # the file and is not a thing to look for. `data` in "what is data in data/x.csv".
    dir_words = set()
    for part in parts[:-1]:
        low = part.lower()
        dir_words.add(low)
        if "." in low:
            dir_words.add(low.rsplit(".", 1)[0])
    if not dir_words:
        return terms
    return [t for t in terms if t.lower() not in dir_words]


def search_named(root: str, rel: str, terms: list[str], limit: int = 40) -> list[dict]:
    """Search ONE named file for the subject terms.

    Returns [] if the file cannot be read. Kept separate from `find` because the point
    is to look somewhere specific rather than to rank the whole tree.
    """
    path = Path(root) / rel
    if not path.is_file():
        return []
    if not _is_readable_text(path):
        return []
    try:
        if path.stat().st_size > _MAX_BYTES:
            return []
        text = path.read_text(errors="ignore")
    except OSError:
        return []
    patterns = [re.compile(r"\b" + re.escape(t) + r"\b", re.I) for t in terms]
    hits = []
    for index, line in enumerate(text.splitlines(), start=1):
        for i, pat in enumerate(patterns):
            if pat.search(line):
                hits.append({"file": rel, "line": index, "term": terms[i],
                             "text": line.strip()[:200]})
                break
        if len(hits) >= limit:
            break
    return hits


def _operation_vocabulary(comp: dict) -> set[str]:
    """The words the CHOSEN operation is made of, so they are not called unresolved.

    Distinct from the per-operation sets above, which are static tables used before an
    operation was chosen. This reads the answer that was actually returned: a count of
    lines accounts for `lines`; an aggregate over the `amount` column accounts for
    `amount` and for the aggregate's own name.
    """
    op = comp.get("operation") or ""
    out: set[str] = set()
    if op == "count_lines":
        out |= {"line", "lines", "length", "long", "count", "number", "many"}
    elif op == "count_rows":
        out |= {"row", "rows", "record", "records", "entry", "entries", "count",
                "number", "many", "data"}
    elif op == "count_files":
        out |= {"file", "files", "count", "number", "many", "directory", "dir",
                "folder", "here", "this", "tree", "project"}
    elif op == "catalog":
        out |= {"list", "listing", "file", "files", "directory", "dir", "folder",
                "entries", "contents", "which", "exist", "here"}
    elif op == "read_content":
        out |= {"what", "say", "says", "said", "written", "written", "contain",
                "contains", "show", "see", "display", "cat", "print", "read",
                "contents", "content", "text", "inside", "look", "open", "quote",
                "let", "me", "tell"}
    elif op == "locate":
        for h in comp.get("hits") or []:
            out.add(str(h.get("term") or "").lower())
    elif op.startswith("aggregate_"):
        agg = op.rsplit("_", 1)[1]
        out |= {"total", "sum", "add", "added", "altogether", "combined", "overall",
                "max", "maximum", "largest", "biggest", "highest", "most", "top",
                "greatest", "min", "minimum", "smallest", "lowest", "least", "fewest",
                "bottom", "average", "mean", "typical", "avg", "column", "field"}
        col = str(comp.get("column") or "").lower()
        if col:
            out.add(col)
            if len(col) > 3 and col.endswith("s"):
                out.add(col[:-1])
            else:
                out.add(col + "s")
    return {w for w in out if w}


def compute(question: str, root: str) -> dict | None:
    """Answer a question that needs a computation, not a citation.

    Returns None when the question is not one of these. Every branch names the file
    and the operation it performed in words that say exactly what was counted, so a
    wrong answer is visible as a wrong operation rather than as a vague number.
    """
    base = Path(root)

    if _COUNT_FILES.search(question or "") and not _FILE_MENTION.search(question or ""):
        files = _project_files(root)
        total = len([q for q in base.rglob("*") if q.is_file()])
        skipped = total - len(files)
        return {"operation": "count_files", "value": len(files),
                "subject": "<the directory>",
                "detail": (f"counted {len(files)} files under {root!r}; skipped {skipped} "
                           f"under .git, __pycache__ and dependency caches, so a plain "
                           f"`find` that includes them will read higher"),
                "claims": []}

    if _COUNT_LINES.search(question or ""):
        target = _named_file(question, root)
        if target is None:
            return None
        path = base / target
        try:
            body = path.read_text(errors="replace")
        except Exception:
            return None
        n = len(body.splitlines())
        return {"operation": "count_lines", "value": n, "subject": target,
                "detail": f"{target} contains {n} line(s)",
                "claims": [{"file": target, "line_count": n}]}

    if _COUNT_ROWS.search(question or ""):
        target = _named_file(question, root)
        if target is None:
            return None
        path = base / target
        try:
            import csv, io
            rows = list(csv.reader(io.StringIO(path.read_text(errors="replace"))))
        except Exception:
            return None
        rows = [r for r in rows if any(c.strip() for c in r)]
        # A header row is not a data row, and the first line of a CSV is a header
        # often enough that silently counting it would be wrong most of the time.
        # Both numbers are reported so the distinction is never hidden in one figure.
        data = max(0, len(rows) - 1)
        return {"operation": "count_rows", "value": data, "subject": target,
                "detail": f"{target} has {data} data row(s) after {len(rows)} total row(s), "
                          f"treating the first as a header",
                "claims": []}

    return None


# "WHAT DOES notes.md SAY" IS NOT ANSWERED BY "notes.md EXISTS".
#
# A name hit says the file is there. That answers "where is X" and "does X exist",
# and it does not answer a request to be shown what the file says -- yet that request
# came back GROUNDED with the filename and no content, which reads as an answer.
# Asking to see a file is a different operation: read it.
# Words that describe the ASK, not the subject.
#
# "what does data.py define" asks to be shown contents; `define` is the operation the
# asker wants performed, not a thing to be found inside the file. Counting request
# verbs as content terms made every such question look partly unanswered.
# Words that ask the door to DO something with the content. They are not subjects.
#
# `define`, `declare`, `export`, `mean`, `explain` and `describe` were in this set and
# are not: they name WHAT the question is about. Dropping them deleted the question's
# subject before anything could report it, so "what does data.py define" -- a file with
# no `define` in it -- came back NOTHING_FOUND with an EMPTY unresolved list, as if the
# word had never been asked about. A word that matched nothing must never disappear.
#
# What remains is vocabulary for retrievING content: it says how to answer, not what.
_REQUEST_VERBS = {
    "say", "says", "said", "contain", "contains", "contained",
    "hold", "holds", "show", "shows", "tell", "give", "find", "print",
    "display", "quote", "read", "cat", "list", "see", "look",
}

# ...but a content word and a retrieval word can be the same word ("show", "print").
# An operation that consumed a word accounts for it; the trial says which ones, and
# that subtraction is what decides `unresolved`. This set is only a first cut for the
# words the trial never saw, so it must not remove a word the trial left owed.


_ASKS_CONTENT = re.compile(
    r"\bwhat does\b.*\b(?:say|contain|hold|mean)\b"
    r"|\bshow me\b|\bshow the\b|\bwhat'?s in\b|\bwhats in\b"
    r"|\bcontents? of\b|\bread (?:the |me )?(?:file |contents? of )"
    r"|\bdisplay\b|\bprint\b|\bquote\b"
    r"|\bwhat does\b.*\b(?:define|declare|export|import)\b"
    r"|\bwhat (?:is )?(?:defined|declared|defined by|in)\b (?:the )?(?:file )?", re.I)


def wants_content(question: str) -> bool:
    """Is the question asking to be shown what a file says?"""
    return bool(_ASKS_CONTENT.search(question or ""))


def read_content(question: str, root: str, max_lines: int = 40) -> dict | None:
    """Read out the file the question names. Returns None if it names none here."""
    target = _named_file(question, root)
    if target is None:
        return None
    path = Path(root) / target
    try:
        body = path.read_text(errors="replace")
    except Exception:
        return None
    all_lines = body.splitlines()
    shown = all_lines[:max_lines]
    return {"operation": "read_content", "subject": target,
            "value": f"{len(all_lines)} line(s)",
            "body": shown,
            "truncated": len(all_lines) > len(shown),
            "detail": f"read {target}: showing {len(shown)} of {len(all_lines)} line(s)",
            "claims": [{"file": target, "contains": ln[:120]} for ln in shown[:5] if ln.strip()]}


# THE WORDS THAT DESCRIBE AN OPERATION ARE NOT SUBJECTS IT FAILED TO FIND.
#
# Once "how many lines are in data.py" actually counts, `lines` is the unit it counted
# in and not a thing missing from the file; once a listing question is answered by
# enumerating, `list`, `files` and `directory` are what was ASKED FOR and delivered.
# Leaving them in the unresolved list made three correct answers report as partial and
# would train a reader to ignore the warning that matters.
_OPERATION_WORDS = {
    "count_lines": {"how", "many", "lines", "line", "count", "number", "of"},
    "count_rows": {"how", "many", "rows", "row", "records", "record", "entries",
                   "entry", "lines", "line", "count", "number", "of"},
    "count_files": {"how", "many", "files", "file", "python", "modules", "count",
                    "number", "of", "directory", "dir", "folder", "here", "there",
                    "this", "tree", "project", "repo", "repository", "in"},
    "read_content": {"what", "does", "say", "says", "contain", "contains", "define",
                     "defines", "declared", "declares", "export", "exports", "show",
                     "me", "the", "of", "contents", "content", "read", "display",
                     "print", "quote", "mean", "means", "defined", "import",
                     "imports", "tell"},
    "listing": {"list", "listing", "enumerate", "files", "file", "dir", "directory",
                "folder", "entries", "contents", "content", "what", "whats", "which",
                "exist", "here", "ls", "in", "the", "of", "are", "is"},
}


def accounted_terms(comp: dict | None, question: str, listing_route: bool) -> set[str]:
    """The words the operation itself used, and so already dealt with."""
    if listing_route:
        return _OPERATION_WORDS["listing"]
    if comp is not None:
        return _OPERATION_WORDS.get(comp.get("operation") or "", set())
    return set()


def _computation_holds(comp: dict, root: str) -> bool:
    """Re-check the computation against the file. Nothing is taken on trust."""
    op, val = comp.get("operation"), comp.get("value")
    if op == "count_files":
        return val == len(_project_files(root))
    if op == "count_lines":
        path = Path(root) / comp["subject"]
        if not path.is_file():
            return False
        return val == len(path.read_text(errors="replace").splitlines())
    if op == "read_content":
        path = Path(root) / comp["subject"]
        if not path.is_file():
            return False
        # Every line shown must actually be in the file, in that order. Reading it
        # out and then not checking would be the same trust-by-assertion this avoids.
        actual = path.read_text(errors="replace").splitlines()
        return actual[:len(comp.get("body") or [])] == list(comp.get("body") or [])
    if op == "count_rows":
        import csv, io
        path = Path(root) / comp["subject"]
        if not path.is_file():
            return False
        rows = [r for r in csv.reader(io.StringIO(path.read_text(errors="replace")))
                if any(c.strip() for c in r)]
        return val == max(0, len(rows) - 1)
    return False


def answer(question: str, root: str = ".", limit: int = 40) -> dict:
    """Answer by reading, and ground every line of the answer."""
    if not Path(root).is_dir():
        return {
            "schema": SCHEMA, "question": question, "root": root,
            "terms": question_terms(question), "verdict": "UNVERIFIABLE",
            "hits": [], "total": 0, "grounded": 0, "unverifiable": 0,
            "all_grounded": False, "grounding_summary": None,
            "detail": f"{root!r} is not a directory; nothing could be read",
        }
    terms = question_terms(question)
    # A listing question asks for a SET, not for a word occurrence. Routing it to
    # `find` is what made "list the files in this directory" return NOTHING_FOUND on a
    # directory holding three files: no term in it names anything inside the tree.
    named_q = _named_file(question, root)
    if wants_a_listing(question):
        hits = listing(root, limit=limit)
    elif named_q:
        # THE NAMED FILE IS SEARCHED FIRST, AND THE WHOLE TREE ONLY IF IT MISSES.
        #
        # Ranking the whole tree for a question that names one file lets a common word
        # fill the hit cap with unrelated files before the named one is ever opened --
        # measured on this repository, where `retries` lives in the named file five
        # times and the door reported it absent. If the named file yields nothing, the
        # tree-wide search still runs, so a question that names a file while asking
        # about something else is not narrowed away.
        # No tree-wide fallback here.
        #
        # Falling back to `find` when the named file yielded nothing put path hits back
        # in: `find` matches terms against the PATH as well as the body, so a file called
        # `retry.py` produced a "name hit" for the term `retry` and "what is retry in
        # retry.py" came back GROUNDED and answered on a file that never contains the
        # word. A question that names a file is a question about that file; if the word
        # is not in it, the honest answer is that it is not in it.
        hits = search_named(root, named_q, terms, limit=limit)
    else:
        hits = find(root, terms, limit=limit)

    # THE GROUNDER IS NOT OPTIONAL, AND IT IS NOT FOUND BY ACCIDENT.
    #
    # This was `import grounding_v1` with `except Exception: G = None`. A bare import
    # only resolves when `canonical/runtime` is already on sys.path, which happens when
    # autonomous_v1 imports this module (it adds the directory) but NOT when the module
    # is imported as `canonical.runtime.inspect_v1`. In that case the import failed,
    # G became None, and every content hit silently became UNVERIFIABLE while the
    # module kept returning confident-looking verdicts. The grounding was absent and
    # nothing said so.
    #
    # So: resolve it either way, and if neither works, RAISE. A verifier that cannot
    # load must not report, because its report is indistinguishable from a real one.
    try:
        import grounding_v1 as G
    except ImportError:
        try:
            from canonical.runtime import grounding_v1 as G
        except ImportError as exc:
            raise ImportError(
                "inspect_v1 cannot ground a claim without grounding_v1; refusing to "
                "answer rather than reporting ungrounded hits as verified"
            ) from exc

    claims, results = [], []
    for h in hits:
        if h.get("matched") in ("filename", "listing"):
            # A filename hit claims the file EXISTS, not that it contains some text.
            # The generic claim (`file` contains `text`) grounds by searching the body,
            # and for a name hit the body text is empty -- so it correctly refused, and
            # every question that named a file scored grounded=0 and came back
            # unverified. That refusal was right about the wrong claim: existence is a
            # different, checkable fact. Verified directly, here, without pretending a
            # line was read.
            exists = (Path(root) / h["file"]).is_file()
            h["verdict"] = "GROUNDED" if exists else "UNVERIFIABLE"
            claims.append({"file": h["file"], "exists": True})
            if exists:
                results.append({"verdict": "GROUNDED", "claim": "file_exists"})
            continue
        claim = {"file": h["file"], "contains": h["text"][:120]}
        claims.append(claim)
        if G is not None:
            r = G.check(claim, root)
            h["verdict"] = r["verdict"]
            results.append(r)
        else:
            h["verdict"] = "UNVERIFIABLE"

    if G is not None:
        summary = G.check_all(claims, root) if claims else None
    else:
        summary = None

    # THE FILE A NUMBER CAME FROM IS EVIDENCE AND MUST BE CITED.
    #
    # Narrowing the search to the named file removed the filename hit that `find` used
    # to contribute, so a computed answer arrived with zero hits and -- worse -- a
    # question whose subject was absent collapsed from "the file is there and this word
    # is not in it" to a bare NOTHING_FOUND. A count over a file still has to say which
    # file it counted, and a refusal still has to say which file it looked in.
    # Cited only when something WAS found or a computation was actually run.
    #
    # Unconditionally, this re-added the filename hit right after the search had proved
    # the word absent, and `retry` in `retry.py` went back to GROUNDED and answered --
    # the fix undone by its own evidence trail. A file only becomes evidence here when
    # there is a finding that points at it, or a number that came out of it.

    # THE OPERATION IS TRIED, NOT CLASSIFIED.
    #
    # This called `compute()`, which chose the operation by matching the question
    # against `_COUNT_LINES` / `_COUNT_ROWS` / `_COUNT_FILES` / `_ASKS_CONTENT`. Eight
    # regexes, seven of them added one defect at a time, and a question phrased any
    # other way was not answered. `operation_trial_v1` resolves what the sentence names
    # against the tree, tries every operation those things permit, and returns only one
    # that both re-checks against the tree AND accounts for the question's own words.
    trial = None
    comp = None
    try:
        try:
            from canonical.runtime import operation_trial_v1 as _T
        except ImportError:
            import operation_trial_v1 as _T
        trial = _T.run(question, root)
        comp = trial.get("computation")
    except Exception as exc:
        # AN OPERATION THAT CRASHED IS NOT AN OPERATION THAT DID NOT APPLY.
        #
        # This swallowed every exception into `comp = None`, which is indisting-
        # uishable from "no operation was applicable" -- so a genuine bug in the trial
        # looked exactly like a question the tree cannot answer. Keep the fact.
        comp = None
        trial = {"computation": None, "attempted": [],
                 "reason": f"the operation trial raised {type(exc).__name__}: {exc}"}
    if comp is not None:
        comp["verified"] = True     # operation_trial_v1 only returns what re-checked

    named_ev = _named_file(question, root)
    # Whether this question will be ANSWERED, decided once, by the trial that answers
    # it. This called `compute()` and `wants_content()` -- two of the phrasing lists the
    # dispatcher was supposed to replace -- so a question could be answered by the trial
    # and still be treated as unanswered here because a regex disagreed with it.
    will_compute = bool((trial or {}).get("computation"))
    # `unresolved` is not computed yet at this point, so the refusal case is decided by
    # whether the question asked about a subject the file does not contain -- which is
    # exactly what a named file with nothing found inside it means. Cited when there is
    # a finding, a computation, OR a named file we looked in and did not find the
    # subject in. Not cited when the word was simply satisfied by the path, which is the
    # `retry`/`retry.py` case: there the file was never really the answer.
    if named_ev and (hits or will_compute) and not any(
            h.get("file") == named_ev for h in hits):
        hits.append({"file": named_ev, "line": 0, "term": named_ev,
                     "text": "", "matched": "filename"})

    # Ground the filename hit before counting, so the evidence tally is about the same
    # list of hits the verdict is computed from.
    for h in hits:
        if h.get("matched") in ("filename", "listing") and "verdict" not in h:
            exists = (Path(root) / h["file"]).is_file()
            h["verdict"] = "GROUNDED" if exists else "UNVERIFIABLE"

    grounded = sum(1 for h in hits if h.get("verdict") == "GROUNDED")
    unverifiable = sum(1 for h in hits if h.get("verdict") == "UNVERIFIABLE")

    # TERMS THAT MATCHED NOTHING ARE PART OF THE ANSWER.
    #
    # They used to vanish. "what is the profit margin in data.py" hit the filename,
    # grounded that hit, and came back answered=True with `profit` and `margin` having
    # found nothing anywhere -- the pointer to the file was counted as an answer to a
    # question about what was inside it. A question is only answered if the words that
    # carry its meaning were dealt with, so the ones that were not are named in the
    # result rather than dropped. Reporting "not answered, and here is what I could not
    # find" is useful; reporting a clean pass is not.
    # Only a hit that quotes a line resolves a term.
    #
    # A name hit says the file is there, which is a different fact from the file
    # containing the word. Counting it as a match is how `retry` in `retry.py` read as
    # found: the term appeared in the PATH, the name hit carried it as its term, and the
    # word was never seen inside the file.
    matched_terms = {h.get("term") for h in hits
                     if h.get("term") and h.get("matched") not in ("filename", "listing")}
    # The words a file's PATH is spelled with name it; they are not things to find inside
    # anything. Leaving them in made every question about a nested path score as
    # partially unanswered on its own correct answer.
    # WHEN THE TRIAL ANSWERED, THE QUESTION WAS ANSWERED.
    #
    # `unresolved_terms` exists so a search that found nothing cannot look like a
    # success. When an operation was tried, re-checked against the tree, AND accounts
    # for the question's words, the question is answered -- and computing "unresolved"
    # from a separate list of English request verbs produced the opposite: `cat data.py`
    # answered correctly and was then marked READ_INCOMPLETE because `cat` was not in
    # `_REQUEST_VERBS`. That list was a fourth template list contradicting the
    # dispatcher, which is the defect this whole change removes.
    subject_terms = [t for t in terms if t not in _REQUEST_VERBS]
    subject_terms = _drop_path_fragments(
        subject_terms, _named_file(question, root) or "", question)
    if comp is not None:
        # THE OPERATION'S OWN VOCABULARY IS ACCOUNTED FOR; THE QUESTION'S SUBJECT IS NOT.
        #
        # Dropping every subject term whenever a computation existed made refusals
        # regress: "what is the profit margin in data.py" returned READ, having dumped
        # the file and called it an answer. `read` verifies on any text file, so it is
        # only an answer when nothing else was asked for -- and the trial already
        # decides that. What is still owed is the question's SUBJECT: `profit` and
        # `margin` were never found, and that must survive.
        # THE TRIAL SAYS WHICH WORDS IT ACCOUNTED FOR.
        #
        # `_operation_vocabulary(comp)` was a SECOND reconstruction of the same
        # knowledge, built from the operation's name rather than from its result, and
        # it drifted immediately: `altogether` and `has` were reported as unanswered
        # subjects of questions the door had answered correctly. One authority.
        accounted = (trial or {}).get("accounted")
        if accounted is None:
            accounted = sorted(_operation_vocabulary(comp))
        # The trial's own word list is the one its decision was made from: it already
        # dropped glue, and the address of the named file. Judging its answer against a
        # DIFFERENT tokenisation marked `has` -- which the trial never even considered a
        # subject -- as an unanswered word, and refused a correct answer.
        trial_words = (trial or {}).get("words")
        if trial_words is not None:
            accounted = set(accounted) | {t for t in subject_terms if t not in trial_words}
        subject_terms = [t for t in subject_terms if t not in set(accounted)]
    # A term that is the name of a file the question names is accounted for by that
    # file being there; it was never a thing to look for inside a body.
    named = _named_file(question, root)
    used = accounted_terms(comp, question, wants_a_listing(question))
    # NO SUBSTRING RULE. This used to also drop any term found inside the named file's
    # path (`t in named.lower()`), which dropped `retry` for a file called `retry.py`
    # even though that file never contains the word -- a question whose subject was
    # genuinely absent came back answered. A file called `retry.py` is not evidence that
    # the word `retry` appears inside it. The path drop above handles directory
    # segments, which really are just the address.
    # A term that IS the named file's basename is resolved by that file existing -- the
    # asker wrote the filename, and the file is there. Exact equality, not containment:
    # `mod.py` is resolved by `canonical/runtime/mod.py`, while `retry` is NOT resolved
    # by `retry.py`, because a question about the word `retry` is a question about what
    # is inside the file and the filename is not an answer to it.
    basename = (named or "").rsplit("/", 1)[-1].lower()
    unresolved = [t for t in subject_terms
                  if t not in matched_terms
                  and t not in used
                  and t != basename]

    # A QUESTION THAT NEEDS A COMPUTATION IS NOT ANSWERED BY FINDING THE FILE.
    #
    # This runs after the reading, not instead of it: the hits still say where the
    # question points, and the computation says what the answer is. When the question
    # asks for a number and we did not compute one, the verdict must not be GROUNDED,
    # because "the evidence is real" and "the question is answered" are different
    # claims and this is precisely the case where they come apart.
    # THE TRIAL ALREADY KNOWS WHETHER A NUMBER WAS ASKED FOR -- it is how `run()` chose
    # what to try. Asking three regexes the same question here meant this verdict was
    # decided by a fourth copy of the vocabulary, and any phrasing those three did not
    # spell was reported GROUNDED with no number in it. Read the decision that was made.
    asked_op = (trial or {}).get("asked") or ""
    asks_for_number = asked_op.startswith("aggregate_") or asked_op in (
        "count_lines", "count_rows", "count_files", "catalog")

    if comp is not None and comp["verified"] and comp["operation"] == "read_content" and unresolved:
        # It read the file and some of what was asked about is still unaccounted for.
        verdict = "READ_INCOMPLETE"
    elif comp is not None and comp["verified"] and comp["operation"] == "read_content":
        verdict = "READ"
    elif comp is not None and comp["verified"]:
        verdict = "COMPUTED"
    elif asks_for_number and comp is None:
        # It wanted a number, we found where to look, and we cannot count that here.
        # Saying GROUNDED would claim an answer nobody computed.
        verdict = "LOCATED_NOT_COMPUTED" if hits else "NOTHING_FOUND"
    elif not hits:
        # "I looked in the file you named and the word is not in it" is a different
        # fact from "I searched the tree and found nothing", and a reader deciding
        # whether to trust the answer needs to know which one happened. Reporting both
        # as NOTHING_FOUND would be true and less useful.
        # Only a question that actually named a file can be "not in that file".
        verdict = "NOT_IN_NAMED_FILE" if (unresolved and named) else "NOTHING_FOUND"
    elif unverifiable:
        verdict = "PARTIALLY_GROUNDED"
    elif unresolved:
        # Every hit is real and the question is still partly unanswered. Calling this
        # GROUNDED is what let a question about `profit` and `margin` pass on the
        # strength of having found the file those words were supposed to be in.
        verdict = "PARTIALLY_GROUNDED"
    else:
        verdict = "GROUNDED"

    return {
        "schema": SCHEMA,
        "question": question,
        "root": root,
        "terms": terms,
        "verdict": verdict,
        "hits": hits,
        "total": len(hits),
        "grounded": grounded,
        "unverifiable": unverifiable,
        # `all_grounded` says the EVIDENCE is real. `answered` says the QUESTION is
        # answered. They were the same field until a counting question came back
        # verified with no number in it; splitting them is what lets the door report
        # "I read the right file and did not answer you" instead of a clean pass.
        "all_grounded": bool(hits) and grounded == len(hits),
        "computation": comp,
        "unresolved_terms": unresolved,
        # WHAT WAS TRIED AND FAILED, not just what won.
        #
        # The trial keeps every attempt -- including the ones that did not re-check and
        # the ones that re-checked but did not answer -- because "I tried to count the
        # rows and could not" is information a reader needs to judge the answer. This
        # dropped it, so a failed operation vanished and the reply looked as if the door
        # had never attempted it.
        "attempted": (trial or {}).get("attempted") or [],
        "trial_reason": (trial or {}).get("reason"),
        # The file the question named, if any. Returned as a fact so that a reader --
        # including the door's own reason code -- can distinguish "looked in the file
        # you named and the words are not in it" from "searched the tree, found nothing".
        "named_file": (named.name if hasattr(named, "name") else named),
        # AN OPERATION THAT RAN IS NOT AN ANSWER TO A QUESTION IT IGNORED.
        #
        # This read `answered = comp["verified"]`, so "what is the profit margin in
        # data.py" came back answered=True after reading the file -- the arithmetic of
        # the original defect, one layer up: the operation was real, and the subject was
        # never dealt with. An answer needs the work to hold AND the question's words to
        # be accounted for.
        "answered": (bool(comp["verified"]) and not unresolved) if comp is not None
                    else (bool(hits) and not asks_for_number and not unresolved),
        "grounding_summary": summary,
    }


def render(result: dict) -> str:
    """The answer, as evidence a person can check."""
    lines = [f"Q: {result['question']}", f"   verdict: {result['verdict']}"
             f"  ({result['grounded']}/{result['total']} grounded)"]
    # THE ANSWER COMES FIRST.
    #
    # A computed answer rendered as a file pointer is not an answer. "how many lines
    # are in data.py" printed `data.py:0  [GROU]` and no number, because the renderer
    # only knew how to list hits. The number now leads, with the operation in words so
    # it can be checked: the reader sees WHAT was counted, not just a figure.
    comp = result.get("computation")
    if comp:
        mark = "verified" if comp.get("verified") else "UNVERIFIED"
        if comp.get("body") is not None:
            lines.append(f"   {comp['subject']}: [{mark}]")
            for ln in comp["body"]:
                lines.append(f"      | {ln}")
            if comp.get("truncated"):
                lines.append("      | ... (truncated)")
        else:
            lines.append(f"   = {comp['value']}  ({comp['detail']}) [{mark}]")
    for h in result["hits"][:20]:
        # A hit that only located the file adds nothing once its contents are shown.
        if comp and comp.get("body") is not None and h.get("matched") in ("filename", "listing"):
            continue
        lines.append(f"   {h['file']}:{h['line']}  [{h['verdict'][:4]}]  {h['text'][:88]}")
    # "nothing found" under a computed answer is a flat contradiction; it belongs to
    # the search, and the search is not what answered this question.
    if not result["hits"] and not comp:
        lines.append("   nothing found for: " + ", ".join(result["terms"][:6]))
    # Named in the output, not just in the JSON: a reader has to be able to see that
    # part of what they asked about was never found.
    unres = result.get("unresolved_terms") or []
    if unres:
        lines.append("   NOT found anywhere: " + ", ".join(unres[:8]))
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    q = sys.argv[2] if len(sys.argv) > 2 else "how many test files are here"
    print(render(answer(q, root)))
