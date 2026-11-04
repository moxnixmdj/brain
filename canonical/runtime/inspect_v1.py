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
        if path.suffix.lower() not in _TEXT_SUFFIX:
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
    """The file the question is about, if it names exactly one that exists here."""
    base = Path(root)
    found = []
    for m in _FILE_MENTION.finditer(question or ""):
        cand = m.group(0)
        if (base / cand).is_file():
            found.append(cand)
    return found[0] if len(found) == 1 else None


def compute(question: str, root: str) -> dict | None:
    """Answer a question that needs a computation, not a citation.

    Returns None when the question is not one of these. Every branch names the file
    and the operation it performed in words that say exactly what was counted, so a
    wrong answer is visible as a wrong operation rather than as a vague number.
    """
    base = Path(root)

    if _COUNT_FILES.search(question or "") and not _FILE_MENTION.search(question or ""):
        files = [p for p in base.rglob("*") if p.is_file()]
        return {"operation": "count_files", "value": len(files),
                "subject": "<the directory>",
                "detail": f"counted {len(files)} files under {root!r}",
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
_REQUEST_VERBS = {
    "define", "defines", "defined", "declare", "declares", "declared", "export",
    "exports", "exported", "say", "says", "said", "contain", "contains", "contained",
    "hold", "holds", "mean", "means", "show", "shows", "explain", "explains",
    "describe", "describes", "tell", "give", "find", "print", "display", "quote",
}


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
                    "number", "of"},
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
        return val == len([p for p in Path(root).rglob("*") if p.is_file()])
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
    hits = listing(root, limit=limit) if wants_a_listing(question) else find(root, terms, limit=limit)

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

    grounded = sum(1 for h in hits if h.get("verdict") == "GROUNDED")
    unverifiable = sum(1 for h in hits if h.get("verdict") == "UNVERIFIABLE")

    comp = None
    try:
        comp = compute(question, root)
        # A listing question about a directory is not a request to read one file,
        # so this runs only when no listing already answered it.
        if comp is None and not wants_a_listing(question) and wants_content(question):
            comp = read_content(question, root)
    except Exception:
        comp = None
    if comp is not None:
        comp["verified"] = _computation_holds(comp, root)

    # TERMS THAT MATCHED NOTHING ARE PART OF THE ANSWER.
    #
    # They used to vanish. "what is the profit margin in data.py" hit the filename,
    # grounded that hit, and came back answered=True with `profit` and `margin` having
    # found nothing anywhere -- the pointer to the file was counted as an answer to a
    # question about what was inside it. A question is only answered if the words that
    # carry its meaning were dealt with, so the ones that were not are named in the
    # result rather than dropped. Reporting "not answered, and here is what I could not
    # find" is useful; reporting a clean pass is not.
    matched_terms = {h.get("term") for h in hits if h.get("term")}
    subject_terms = [t for t in terms if t not in _REQUEST_VERBS]
    # A term that is the name of a file the question names is accounted for by that
    # file being there; it was never a thing to look for inside a body.
    named = _named_file(question, root)
    used = accounted_terms(comp, question, wants_a_listing(question))
    unresolved = [t for t in subject_terms
                  if t not in matched_terms
                  and t not in used
                  and t != (named or "").lower()
                  and not (named and t in named.lower())]
    if named:
        # The file named in the question is evidence in its own right, so its name
        # stops being an unresolved term once the file is known to exist.
        unresolved = [t for t in unresolved if t not in named.lower()]

    # A QUESTION THAT NEEDS A COMPUTATION IS NOT ANSWERED BY FINDING THE FILE.
    #
    # This runs after the reading, not instead of it: the hits still say where the
    # question points, and the computation says what the answer is. When the question
    # asks for a number and we did not compute one, the verdict must not be GROUNDED,
    # because "the evidence is real" and "the question is answered" are different
    # claims and this is precisely the case where they come apart.
    asks_for_number = bool(_COUNT_LINES.search(question or "")
                           or _COUNT_ROWS.search(question or "")
                           or _COUNT_FILES.search(question or ""))

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
        verdict = "NOTHING_FOUND"
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
        "answered": bool(comp["verified"]) if comp is not None
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
