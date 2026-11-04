"""A question is an attempt, not a classification.

THE DEFECT THIS REPLACES
------------------------
Every prior version of the inspect door decided what to do with a question by
matching its WORDS against a list: `_COUNT_LINES`, `_ASKS_CONTENT`, `_QUESTION`,
`_LISTING`, `_REQUEST_VERBS`. Three separate lists, in two modules, none of which
knew about the others. Measured on ten phrasings of two questions: three were
answered. `display data.py` failed even though `display` was in the content list,
because a DIFFERENT list had already refused to route it as a question.

Adding a ninth regex fixes the instance and leaves the shape, and the shape is the
problem. A template list can only recognise a question somebody already thought of,
which is precisely the brittleness the project says it exists to avoid. What made it
hard to see is that a fired template and an understanding produce the SAME confident
answer, so the door could not tell them apart -- the same category error as a verdict
that meant both "the evidence is real" and "the question is answered".

WHAT REPLACES IT
----------------
In a question the phrasing is open-ended and the REFERENTS ARE FINITE. "how many
lines", "line count", "how long", "count the lines" are four phrasings of one
referent (`data.py`) and one operation (count its lines). So the sentence is not
classified; the things it names are RESOLVED AGAINST THE TREE, and then every
operation those things permit is TRIED, and what comes back is only what VERIFIES.

That moves the dispatch from a list of English phrasings to the tree itself. A new
operation extends every phrasing at once, which is the property a table of regexes
does not have. And because each attempt reports whether it verified, the door can
still say "I tried these five things and none of them held" -- a claim about work
actually done, rather than a template that quietly missed.

The result is the same shape `compute()` returned, so everything downstream --
verdicts, `answered`, `unresolved_terms` -- is unchanged.
"""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_OPERATION_TRIAL_V1"

# Files the tree already treats as not-the-project.
_SKIP = re.compile(
    r"(^|/)(node_modules|site-packages|\.brain_venv|\.venv|venv|vendor|__pycache__|"
    r"\.git|\.tox|\.nox|\.mypy_cache|\.pytest_cache|third_party|external|dist|build)/"
)

# Extensions that are text. Kept only as a FAST PATH -- the decision is made from the
# bytes, because a list is a guess about content and was wrong in the direction that
# produced confident refusals about files nobody had read.
_TEXT_SUFFIX = {
    ".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".csv", ".tsv", ".rst", ".sh", ".js", ".mjs", ".cjs", ".ts", ".tsx",
    ".html", ".css", ".xml", ".sql",
}

_MAX_BYTES = 2_000_000

# Words that carry no referent. Deliberately small: this is not the noun-detection
# mechanism, and it must not be, because that is the template list again.
_GLUE = {
    "a", "an", "the", "this", "that", "these", "those", "to", "from", "into", "in",
    "on", "at", "by", "for", "of", "with", "and", "or", "but", "is", "are", "was",
    "were", "be", "been", "it", "its", "as", "if", "then", "than", "which", "what",
    "when", "where", "how", "who", "why", "do", "does", "did", "can", "could",
    "should", "would", "please", "me", "my", "i", "you", "we", "there", "here",
    "tell", "give", "show", "let", "us", "get", "got", "have", "has", "had",
}


def _is_text(path: Path) -> bool:
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


def _read(path: Path) -> str | None:
    try:
        if path.stat().st_size > _MAX_BYTES:
            return None
        return path.read_text(errors="replace")
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Referents: what the sentence names that actually exists here.
# ---------------------------------------------------------------------------

class Entity:
    """Something the sentence names and the tree actually has."""

    def __init__(self, rel: str, kind: str, path: Path):
        self.rel = rel          # how a person would write it
        self.kind = kind        # "file" | "dir"
        self.path = path

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Entity({self.rel!r}, {self.kind})"


def _candidate_spellings(question: str) -> list[str]:
    """Everything in the sentence that could be the name of something.

    Paths first (they can contain separators and dots), then bare words. This is not
    noun detection -- it is a list of strings that will each be CHECKED against the
    filesystem, and the filesystem is what decides.
    """
    text = question or ""
    out: list[str] = []
    for m in re.finditer(r"[A-Za-z0-9_.\-/\\]{2,}", text):
        cand = m.group(0).strip(".,;:'\"()")
        cand = cand.replace("\\", "/")
        if cand and cand not in out:
            out.append(cand)
    return out


_HERE_WORDS = {"this", "here", "these"}


def entities(question: str, root: str) -> list[Entity]:
    """The files and directories the question names, longest match first.

    A bare word counts only if it IS a path here, so an ordinary noun in a question
    cannot become a filename by accident.
    """
    text_words = {w.lower() for w in re.findall(r"[A-Za-z]+", question or "")}
    base = Path(root)
    if not base.is_dir():
        return []
    found: list[Entity] = []
    seen: set[str] = set()
    # THE ROOT IS A THING THE QUESTION CAN NAME.
    #
    # "how many files are in this directory" names no path, so nothing resolved and the
    # question fell through with no subject at all. A demonstrative that points at the
    # place we are standing is a referent; it is resolved the same way as any other, by
    # the tree, not by a list of synonyms for "here".
    if any(w in text_words for w in _HERE_WORDS):
        found.append(Entity(".", "dir", base))
    for cand in sorted(_candidate_spellings(question), key=len, reverse=True):
        if cand in seen:
            continue
        target = base / cand
        try:
            if target.is_file():
                found.append(Entity(cand, "file", target))
                seen.add(cand)
            elif target.is_dir() and not _SKIP.search(cand.rstrip("/") + "/"):
                found.append(Entity(cand, "dir", target))
                seen.add(cand)
        except OSError:
            continue
    # A directory named by a path also contains the file named by the same path;
    # the file is more specific, so the directory is dropped when the file exists.
    return found


def _subject_words(question: str, ents: list[Entity]) -> list[str]:
    """The words in the question that are not just the address of a named entity.

    "how many lines are in data.py" -> ['lines'] with the file `data.py` taken out.
    These are what an operation will look for INSIDE the entity. Not a template list:
    the same routine serves counting, reading, locating and aggregation.
    """
    # The ADDRESS of a named entity, as whole segments -- never by substring.
    #
    # This was `if low in named` against the joined paths, so the word `retry` was
    # dropped from "what is retry in retry.py" because it is spelled inside the
    # filename. The subject then vanished, the question had no words left to be
    # unaccounted for, and the door answered it with a dump of the file. The project
    # already forbade this rule for exactly this reason; it had grown back.
    address = {seg.lower() for e in ents for seg in e.rel.replace("\\", "/").split("/")}
    address |= {e.rel.lower() for e in ents}
    out: list[str] = []
    for w in re.findall(r"[A-Za-z_][A-Za-z0-9_.\-]{1,}", question or ""):
        low = w.lower()
        if low in _GLUE or len(low) < 2:
            continue
        if low in address:
            continue
        # directory segments of a named path are its address, not its contents
        if any(low == seg.lower() for e in ents for seg in e.rel.split("/")):
            continue
        if low not in out:
            out.append(low)
    return out


# ---------------------------------------------------------------------------
# Operations. Each is total and each VERIFIES against the tree.
# ---------------------------------------------------------------------------

def _lines_of(text: str) -> list[str]:
    return text.splitlines()


def _table(path: Path) -> tuple[list[str], list[list[str]]] | None:
    """A header row and its data rows, if this is a delimited table."""
    text = _read(path)
    if text is None or not text.strip():
        return None
    try:
        rows = [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]
    except Exception:
        return None
    if len(rows) < 2:
        return None
    return rows[0], rows[1:]


def _numeric(values: list[str]) -> list[float] | None:
    out = []
    for v in values:
        v = v.strip().replace(",", "").replace("$", "").replace("%", "")
        if v == "":
            continue
        try:
            out.append(float(v))
        except ValueError:
            return None
    return out or None


def _match_column(header: list[str], words: list[str]) -> str | None:
    """Which column the question is about, decided by the file's own header.

    Singular/plural and case are normalised here because they are spelling, not
    meaning: "the amounts" and a column called `amount` are the same column.
    """
    def norm(s: str) -> str:
        s = s.strip().lower()
        if len(s) > 3 and s.endswith("s") and not s.endswith("ss"):
            s = s[:-1]
        return s

    norms = {norm(h): h for h in header}
    for w in words:
        if norm(w) in norms:
            return norms[norm(w)]
    # a column whose name appears inside a word of the question ("amounts" -> "amount")
    for w in words:
        nw = norm(w)
        for key, original in norms.items():
            if key and (key in nw or nw in key) and len(key) > 2:
                return original
    return None


def _op_read(ent: Entity) -> dict:
    if ent.kind != "file":
        return {"ok": False, "why": "not a file"}
    text = _read(ent.path)
    if text is None:
        return {"ok": False, "why": "unreadable"}
    lines = _lines_of(text)
    shown = lines[:40]
    return {"ok": True, "operation": "read_content", "subject": ent.rel,
            "value": f"{len(lines)} line(s)", "body": shown,
            "truncated": len(lines) > len(shown),
            "detail": f"read {ent.rel}: showing {len(shown)} of {len(lines)} line(s)",
            "claims": [{"file": ent.rel, "contains": ln[:120]} for ln in shown[:5] if ln.strip()]}


def _op_count_lines(ent: Entity) -> dict:
    if ent.kind != "file":
        return {"ok": False, "why": "not a file"}
    text = _read(ent.path)
    if text is None:
        return {"ok": False, "why": "unreadable"}
    n = len(_lines_of(text))
    return {"ok": True, "operation": "count_lines", "value": n, "subject": ent.rel,
            "detail": f"{ent.rel} contains {n} line(s)",
            "claims": [{"file": ent.rel, "line_count": n}]}


def _op_count_rows(ent: Entity) -> dict:
    if ent.kind != "file":
        return {"ok": False, "why": "not a file"}
    table = _table(ent.path)
    if table is None:
        return {"ok": False, "why": "not a table"}
    header, rows = table
    return {"ok": True, "operation": "count_rows", "value": len(rows), "subject": ent.rel,
            "detail": (f"{ent.rel} has {len(rows)} data row(s) after "
                       f"{len(rows) + 1} total row(s), treating the first as a header"),
            "claims": []}


def _op_count_files(ent: Entity) -> dict:
    if ent.kind != "dir":
        return {"ok": False, "why": "not a directory"}
    files = []
    total = 0
    for p in ent.path.rglob("*"):
        if not p.is_file():
            continue
        total += 1
        rel = p.relative_to(ent.path).as_posix()
        if _SKIP.search(rel + "/"):
            continue
        files.append(p)
    return {"ok": True, "operation": "count_files", "value": len(files),
            "subject": "<the directory>",
            "detail": (f"counted {len(files)} files under {str(ent.path)!r}; skipped "
                       f"{total - len(files)} under .git, __pycache__ and dependency "
                       f"caches, so a plain `find` that includes them will read higher"),
            "claims": []}


def _op_catalog(ent: Entity) -> dict:
    if ent.kind != "dir":
        return {"ok": False, "why": "not a directory"}
    entries = []
    for p in sorted(ent.path.rglob("*")):
        if len(entries) >= 40:
            break
        if not p.is_file():
            continue
        rel = p.relative_to(ent.path).as_posix()
        if _SKIP.search(rel + "/"):
            continue
        entries.append(rel)
    return {"ok": True, "operation": "catalog", "subject": "<the directory>",
            "value": f"{len(entries)} entr(ies)", "body": entries,
            "detail": f"listed {len(entries)} file(s) under {ent.rel}",
            "claims": []}


_AGGREGATES = {
    "sum": ("SUM", lambda vs: sum(vs)),
    "max": ("MAX", lambda vs: max(vs)),
    "min": ("MIN", lambda vs: min(vs)),
    "mean": ("MEAN", lambda vs: sum(vs) / len(vs)),
}


def _op_aggregate(ent: Entity, words: list[str], want: str | None) -> dict:
    """sum / max / min / mean over a column the question names.

    `want` is None when the question did not choose one of the four; the caller then
    tries them all and keeps what verifies, which is how "what is the total of the
    amounts" and "largest amount" reach the same operation without a verb list.
    """
    if ent.kind != "file":
        return {"ok": False, "why": "not a file"}
    table = _table(ent.path)
    if table is None:
        return {"ok": False, "why": "not a table"}
    header, rows = table
    col = _match_column(header, words)
    if col is None:
        # "how much is it altogether in sales.csv" names no column. If the table has
        # exactly ONE numeric column, that column is the referent and the tree resolves
        # it -- the question does not have to use the header's spelling. More than one
        # candidate is genuinely ambiguous, and guessing there would be the template
        # behaviour this replaces.
        numeric_cols = []
        for i, h in enumerate(header):
            vals = [r[i] if i < len(r) else "" for r in rows]
            if _numeric(vals) is not None:
                numeric_cols.append(h)
        if len(numeric_cols) != 1:
            return {"ok": False, "why": "no column matched the question"}
        col = numeric_cols[0]
    idx = header.index(col)
    values = [r[idx] if idx < len(r) else "" for r in rows]
    nums = _numeric(values)
    if nums is None:
        return {"ok": False, "why": f"column {col!r} is not numeric"}
    op = want or "sum"
    label, fn = _AGGREGATES[op]
    value = fn(nums)
    shown = int(value) if float(value).is_integer() else round(value, 6)
    return {"ok": True, "operation": f"aggregate_{op}", "subject": ent.rel,
            "value": shown,
            "detail": (f"{label} of column {col!r} over {len(nums)} numeric value(s) "
                       f"in {ent.rel}"),
            "claims": [], "column": col}


def _op_locate(ent: Entity, word: str) -> dict:
    if ent.kind != "file":
        return {"ok": False, "why": "not a file"}
    text = _read(ent.path)
    if text is None:
        return {"ok": False, "why": "unreadable"}
    # A word boundary in Python regex treats `_` as a word character, so `\bdefine\b`
    # does NOT match `define_it`. Asked "what does data.py define", the door looked for a
    # whole-word `define`, found none in a file that is full of `define_` names, and
    # refused a question it could answer. The boundary is what the language considers a
    # separator here, not what `\b` assumes.
    pat = re.compile(r"(?<![A-Za-z0-9])" + re.escape(word) + r"(?![A-Za-z0-9])", re.I)
    hits = []
    for i, line in enumerate(_lines_of(text), start=1):
        if pat.search(line):
            hits.append({"file": ent.rel, "line": i, "term": word,
                         "text": line.strip()[:200]})
    if not hits:
        return {"ok": False, "why": f"{word!r} does not appear"}
    # REPORT THE LINE, NOT HOW MANY LINES.
    #
    # "what is retries in conf.json" asks what the value IS. Answering "1 occurrence(s)"
    # gives a true fact about the search instead of the answer to the question -- the
    # same substitution, one operation down, as answering a sum with a line count.
    # The line that was found IS the answer; its number travels in `hits`/`detail`.
    found = hits[0]["text"]
    value = found if len(hits) == 1 else f"{found} (+{len(hits) - 1} more)"
    return {"ok": True, "operation": "locate", "subject": ent.rel,
            "value": value, "hits": hits,
            "detail": f"{word!r} appears {len(hits)} time(s) in {ent.rel}, first at line {hits[0]['line']}",
            "claims": []}


# ---------------------------------------------------------------------------
# Verification. Nothing is reported unless it re-checks against the tree.
# ---------------------------------------------------------------------------

def verify(comp: dict, root: str) -> bool:
    """Re-do the work independently and compare.

    This is the same discipline the counts already had, extended to every operation:
    an answer is only an answer if doing it again gives the same thing.
    """
    op = comp.get("operation")
    root_path = Path(root)

    if op == "read_content":
        path = root_path / comp["subject"]
        if not path.is_file():
            return False
        actual = _lines_of(path.read_text(errors="replace"))
        return actual[:len(comp.get("body") or [])] == list(comp.get("body") or [])

    if op == "count_lines":
        path = root_path / comp["subject"]
        return path.is_file() and comp["value"] == len(_lines_of(path.read_text(errors="replace")))

    if op == "count_rows":
        table = _table(root_path / comp["subject"])
        return table is not None and comp["value"] == len(table[1])

    if op == "count_files":
        ent = Entity(comp.get("_dir_rel") or ".", "dir", root_path / (comp.get("_dir_rel") or "."))
        again = _op_count_files(ent)
        return bool(again.get("ok")) and again["value"] == comp["value"]

    if op == "catalog":
        return comp["value"] == f"{len(comp.get('body') or [])} entr(ies)"

    if op and op.startswith("aggregate_"):
        ent = Entity(comp["subject"], "file", root_path / comp["subject"])
        again = _op_aggregate(ent, [comp.get("column") or ""], op.rsplit("_", 1)[1])
        return bool(again.get("ok")) and again["value"] == comp["value"]

    if op == "locate":
        ent = Entity(comp["subject"], "file", root_path / comp["subject"])
        again = _op_locate(ent, (comp.get("hits") or [{}])[0].get("term") or "")
        return bool(again.get("ok")) and again["value"] == comp["value"]

    return False


# ---------------------------------------------------------------------------
# The trial itself.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Which verified operation actually ANSWERED the question?
# ---------------------------------------------------------------------------

# Words that ask for an operation rather than name a thing. Kept here, next to the one
# place that uses it, and NOT used to route: routing is what the tree resolves. This
# only decides which of several VERIFIED operations the question was asking for.
_ASKS = {
    "read": {"what", "say", "says", "said", "written", "contain", "contains", "show",
             "see", "display", "cat", "print", "read", "contents", "content", "text",
             "inside", "look", "open", "quote", "file"},
    "count_lines": {"line", "lines", "long", "length", "many", "count", "number"},
    "count_rows": {"row", "rows", "record", "records", "entry", "entries", "many",
                   "count", "number", "data"},
    "count_files": {"file", "files", "many", "count", "number", "entries", "directory",
                    "dir", "folder", "here", "this", "tree", "project"},
    "catalog": {"list", "listing", "files", "file", "directory", "dir", "folder",
                "entries", "contents", "what", "which", "exist", "here"},
}
_AGG_WORDS = {
    "sum": {"total", "sum", "add", "added", "altogether", "combined", "overall"},
    "max": {"max", "maximum", "largest", "biggest", "highest", "most", "top", "greatest"},
    "min": {"min", "minimum", "smallest", "lowest", "least", "fewest", "bottom"},
    "mean": {"average", "mean", "typical", "avg"},
}
# A column reference is what makes an aggregate specific to this question.
_COLUMNISH = {"column", "field", "amount", "amounts", "value", "values", "score",
              "scores", "price", "prices", "total", "qty", "quantity", "count"}


def _asked_operation(words: list[str], ents: list['Entity'] | None = None) -> str | None:
    """Which operation the question's words point at. None when they are ambiguous."""
    low = {w.lower() for w in words}
    for agg, wants in _AGG_WORDS.items():
        if low & wants:
            return f"aggregate_{agg}"
    # "how many rows" / "how many lines" / "how many files" are distinguished by the
    # noun, and the noun is in `words` because it is not the name of anything.
    if low & _ASKS["count_rows"] and low & {"row", "rows", "record", "records", "entries", "entry"}:
        return "count_rows"
    # Consult the SET, not a second literal listing of it. Reading the same vocabulary
    # from two places is how `long` was in one and missing from the other, so "how long
    # is data.py" fell through to a plain read.
    if low & {"line", "lines", "length", "long"}:
        return "count_lines"
    if low & _ASKS["catalog"] and low & {"list", "listing", "which", "exist", "contents"}:
        # `contents` is vocabulary for BOTH reading a file and cataloguing a directory.
        # Which one it means is decided by the thing it points at, not by the word:
        # listing the contents of a directory is a catalog, the contents of a file is
        # the file. Asking this of a file's words alone made "the contents of data.py"
        # select an operation a file cannot perform, and the question went unanswered.
        if any(e.kind == "dir" for e in (ents or [])):
            return "catalog"
    if low & {"file", "files"}:
        return "count_files"
    if _word_asked_for(words):
        # A word the question wants found inside the entity. More specific than reading
        # the file out, which would verify on any text file and leave the word unaddressed.
        return "locate"
    if low & _ASKS["read"]:
        return "read"
    return None


def _word_asked_for(words: list[str]) -> bool:
    """Did the question name a specific word to find inside the entity?

    `words` never contains the entity's own name, so anything left that is not asking
    for an operation is a content word the question wants found.
    """
    asking = set()
    for v in _ASKS.values():
        asking |= v
    for v in _AGG_WORDS.values():
        asking |= v
    asking |= _COLUMNISH
    return any(w.lower() not in asking for w in words)


def accounted_words(op: str, words: list[str], comp: dict) -> set[str]:
    """Which of the question's words this answer actually deals with.

    The caller needs this to compute what is still UNRESOLVED, and it must not
    reconstruct it from a second list of English words -- that is how `altogether`
    (aggregate vocabulary) and `has` (glue) ended up reported as unanswered subjects
    of questions the door had answered correctly. The operation that ran is the only
    thing that knows what it consumed, so it says so here.
    """
    low = {w.lower() for w in words}
    out: set[str] = set()
    out |= {w for w in low if w in _GLUE}
    if op.startswith("aggregate_"):
        agg = op.rsplit("_", 1)[1]
        out |= {w for w in low if w in _AGG_WORDS.get(agg, set())}
        # every aggregate word is asking vocabulary in this question, whichever
        # aggregate was asked for -- "total" in "largest total" is still not a subject
        for ws in _AGG_WORDS.values():
            out |= {w for w in low if w in ws}
        out |= {w for w in low if w in _COLUMNISH}
        col = str(comp.get("column") or "").lower()
        if col:
            out |= {w for w in low if w == col}
            if len(col) > 3 and col.endswith("s"):
                out |= {w for w in low if w == col[:-1]}
            else:
                out |= {w for w in low if w == col + "s"}
        return out
    if op == "locate":
        for h in comp.get("hits") or []:
            out.add(str(h.get("term") or "").lower())
        return out
    if op in _ASKS:
        out |= {w for w in low if w in _ASKS[op]}
    # the nouns are shared vocabulary between several operations
    for ws in _ASKS.values():
        out |= {w for w in low if w in ws}
    out |= {w for w in low if w in _COLUMNISH}
    return out


def _accounts_for(op: str, words: list[str], comp: dict,
                  ents: list['Entity'] | None = None) -> bool:
    """Does this operation answer the words this question is made of?

    A verified operation that ignores the question is not an answer. "what is the total
    of the amounts" was answered by READING the file -- true, verified, and not what was
    asked. This is the same distinction as evidence-grounding versus question-answering,
    moved up one layer: the operation must account for the subject words, not merely
    succeed.
    """
    low = {w.lower() for w in words}
    if not low:
        return True                      # nothing to account for: any verified op does
    if op.startswith("aggregate_"):
        # The aggregate must be the one ASKED FOR. Falling back to "any aggregate" made
        # "largest amount" return the sum: both verified, and sum was tried first.
        agg = op.rsplit("_", 1)[1]
        asked = _asked_operation(words, ents)
        if asked is not None and asked.startswith("aggregate_"):
            return op == asked
        return bool(low & _AGG_WORDS[agg])
    if op == "locate":
        return True                      # the word searched for is the account
    asked = _asked_operation(words, ents)
    if asked is None:
        # Ambiguous subject words: accept an operation that explicitly consumes them.
        return op in ("read", "count_lines", "count_rows")
    # A MORE SPECIFIC OPERATION BEATS A MORE GENERAL ONE.
    #
    # `read` verifies on every text file and accounted for almost any words, so it won
    # "how many lines are in data.py" and "how many rows are in sales.csv" -- true,
    # verified, and not what was asked. Reading is the fallback, not the answer, when
    # the question asked something more precise.
    if asked in ("count_lines", "count_rows", "count_files", "catalog"):
        return op == asked
    # FINDING THE WORD BEATS DUMPING THE FILE.
    #
    # "what is retries in conf.json" asks about a word in a file. Reading the whole file
    # out verified and left `retries` unresolved, because read accounts for the reading
    # vocabulary and not for the word. `locate` is the specific operation: it either
    # finds the word at a line or reports that it is absent.
    if asked == "locate":
        # Only the operation that finds the word. `read` verified here too and was
        # tried first, so "what is retries in conf.json" came back as a line count of
        # the file -- true, verified, and not an answer.
        return op == "locate"
    if asked == "read" and op == "read":
        return not _word_asked_for(words)
    if asked == "read" and op in ("read", "locate"):
        return True
    if asked == "count_files" and op in ("count_files", "catalog"):
        return True
    if asked == "catalog" and op in ("catalog", "count_files"):
        return True
    return op == asked


def run(question: str, root: str) -> dict:
    """Try every operation the named entities permit; keep what verifies AND accounts.

    Two different questions are asked of every attempt, and conflating them is what
    made the first version of this return "4 line(s)" for "what is the total of the
    amounts":
      1. did it really happen?          -- `verify()`, re-done against the tree
      2. does it answer what was asked? -- `_accounts_for()`, against the question's words
    Reading a file is always (1) and rarely (2). Only an operation that is both is
    returned as the answer; the rest are kept in `attempted` so the caller can report
    what was tried truthfully.
    """
    ents = entities(question, root)
    if not ents:
        return {"schema": SCHEMA, "computation": None, "attempted": [],
                "words": [], "entities": [], "asked": None, "accounted": [],
                "reason": "the question names nothing that exists in this tree"}

    words = _subject_words(question, ents)
    asked = _asked_operation(words, ents)
    attempted: list[dict] = []
    verified_here: list[tuple[str, dict]] = []

    for ent in ents:
        trials: list[tuple[str, dict]] = []

        if ent.kind == "file":
            trials.append(("read", _op_read(ent)))
            trials.append(("count_lines", _op_count_lines(ent)))
            trials.append(("count_rows", _op_count_rows(ent)))
            for agg in _AGGREGATES:
                trials.append((f"aggregate_{agg}", _op_aggregate(ent, words, agg)))
            for w in words:
                trials.append((f"locate", _op_locate(ent, w)))
            # locate is tried LAST but chosen FIRST when the question asked for a word;
            # `_accounts_for` decides that, so order here is only about cost.
        else:
            trials.append(("count_files", _op_count_files(ent)))
            trials.append(("catalog", _op_catalog(ent)))

        for name, result in trials:
            if not result.get("ok"):
                attempted.append({"operation": name, "subject": ent.rel,
                                  "why": result.get("why")})
                continue
            result["_dir_rel"] = ent.rel
            held = verify(result, root)
            result.pop("_dir_rel", None)
            attempted.append({"operation": name, "subject": ent.rel,
                              "verified": held,
                              "accounts": _accounts_for(name, words, result, ents)})
            if held:
                verified_here.append((name, result))

    for name, result in verified_here:
        if _accounts_for(name, words, result, ents):
            return {"schema": SCHEMA, "computation": result, "attempted": attempted,
                    "entities": [e.rel for e in ents], "words": words,
                    "asked": asked,
                    "accounted": sorted(accounted_words(name, words, result)),
                    "reason": "verified and accounts for the question"}

    # Nothing both verified and accounted. Say which half failed, and do not hand back
    # an operation that merely succeeded.
    if verified_here:
        reason = ("operations verified but none answers these words: "
                  + ", ".join(sorted({n for n, _ in verified_here})))
    else:
        reason = "nothing the tree permits verified an answer"
    return {"schema": SCHEMA, "computation": None, "attempted": attempted,
            "entities": [e.rel for e in ents], "words": words,
            "asked": asked, "accounted": [], "reason": reason}


def render(trial: dict) -> str:
    """What was tried and what each attempt said."""
    lines = []
    for a in trial.get("attempted") or []:
        if a.get("verified") is True:
            mark = "VERIFIED"
        elif a.get("verified") is False:
            mark = "did not re-check"
        else:
            mark = a.get("why") or "not applicable"
        lines.append(f"   tried {a['operation']:22s} on {a['subject']:30s} {mark}")
    return "\n".join(lines)
