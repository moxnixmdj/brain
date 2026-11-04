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
        # A filename hit and a content hit are the same FILE. Recording both would
        # count one file twice and inflate `grounded`, which is the number the verdict
        # is computed from -- so the name is recorded only when this loop finds no
        # content hit for the same file. The check has to span the whole file, not the
        # hits so far: content is scanned line by line AFTER this point, so a
        # `rel in hits` test made at the top missed every file that matched both ways.
        name_hit_added = False
        # Suppress the name hit only when THIS SAME TERM was found in the body. A
        # different term matching the body is a different fact and must not hide the
        # fact that the file the question named was selected.
        same_term_in_body = any(
            pat.search(text)
            for term, pat in zip(terms, patterns)
            if re.search(r"\b" + re.escape(term) + r"\b", rel, re.I)
        )
        if name_matched and not same_term_in_body:
            hits.append({
                "file": rel,
                "line": 0,
                "term": name_matched[0],
                "text": "",
                "matched": "filename",
            })
            name_hit_added = True
            if len(hits) >= limit:
                break
        if name_hit_added:
            continue
        for index, line in enumerate(text.splitlines(), start=1):
            for i, pat in enumerate(patterns):
                if pat.search(line):
                    hits.append({
                        "file": rel,
                        "line": index,
                        "term": terms[i],
                        "text": line.strip()[:200],
                    })
                    break
            if len(hits) >= limit:
                break
    return hits


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
    hits = find(root, terms, limit=limit)

    try:
        import grounding_v1 as G
    except Exception:
        G = None

    claims, results = [], []
    for h in hits:
        if h.get("matched") == "filename":
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

    if not hits:
        verdict = "NOTHING_FOUND"
    elif unverifiable:
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
        "all_grounded": bool(hits) and grounded == len(hits),
        "grounding_summary": summary,
    }


def render(result: dict) -> str:
    """The answer, as evidence a person can check."""
    lines = [f"Q: {result['question']}", f"   verdict: {result['verdict']}"
             f"  ({result['grounded']}/{result['total']} grounded)"]
    for h in result["hits"][:20]:
        lines.append(f"   {h['file']}:{h['line']}  [{h['verdict'][:4]}]  {h['text'][:88]}")
    if not result["hits"]:
        lines.append("   nothing found for: " + ", ".join(result["terms"][:6]))
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    q = sys.argv[2] if len(sys.argv) > 2 else "how many test files are here"
    print(render(answer(q, root)))
