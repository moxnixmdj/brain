#!/usr/bin/env python3
"""Two ordinary questions about files and directories, answered in process.

Measured on `6219ead`, over the same 25-request ordinary probe: 5 of the 17
failures were not refusals at all -- the door EXECUTED a capability that has
nothing to do with the question and then reported the capability's own refusal:

    "What is the most common word in <f>?"   -> docx.document.verify.intent_...
    "Which files in <d> contain beta?"       -> python.source.audit.ast

An execution spent on the wrong row is a worse answer than a refusal, because
the report names a capability the caller never asked for. This module supplies
two of those questions with the smallest correct implementation:

    word_frequency <f>   the most common word, and the counts behind it
    directory_list <d>   the entries, with type and size
    directory_search <d> the files under <d> whose text contains a stated string

Neither writes anything, spawns anything, or leaves the repository root.
"""
from __future__ import annotations

import hashlib
import pathlib
import re

#: Words that carry no information about frequency. Small and literal: a list
#: this module invented wholesale would be an opinion about prose, and the
#: answer is already reported with its own counts so a reader can disagree.
_STOP_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "has",
    "have", "he", "her", "his", "i", "if", "in", "is", "it", "its", "me", "my",
    "no", "not", "of", "on", "or", "our", "she", "so", "that", "the", "their",
    "them", "then", "there", "these", "they", "this", "to", "was", "we", "were",
    "what", "when", "which", "who", "will", "with", "you", "your",
})

_WORD = re.compile(r"[A-Za-z0-9']+")


def _safe(root: pathlib.Path, raw: str) -> pathlib.Path:
    p = (root / str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _word_frequency(args, root: pathlib.Path) -> dict:
    path = _safe(root, args.get("path") or "")
    if not path.is_file():
        raise RuntimeError("PATH_NOT_A_REGULAR_FILE")
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("NOT_UTF8_TEXT") from exc
    counts: dict[str, int] = {}
    for word in _WORD.findall(text.lower()):
        if word in _STOP_WORDS:
            continue
        counts[word] = counts.get(word, 0) + 1
    if not counts:
        raise RuntimeError("NO_WORDS_TO_COUNT")
    ranked = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    top_word, top_count = ranked[0]
    return {
        "path": path.relative_to(root).as_posix(),
        "most_common_word": top_word,
        "count": top_count,
        # A tie for first place is a fact about the file, and hiding it would
        # answer "the most common word" with a choice the counts do not make.
        "tied_for_first": sorted(word for word, n in ranked if n == top_count),
        "counts": dict(ranked[:20]),
        "distinct_words": len(counts),
        "answer": top_word,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
    }


def _directory_list(args, root: pathlib.Path) -> dict:
    path = _safe(root, args.get("path") or "")
    if not path.is_dir():
        raise RuntimeError("PATH_NOT_A_DIRECTORY")
    entries = []
    for child in sorted(path.iterdir(), key=lambda item: item.name):
        info = {"name": child.name,
                "is_dir": child.is_dir(),
                "is_file": child.is_file()}
        try:
            info["size_bytes"] = child.stat().st_size
        except OSError:
            info["size_bytes"] = None
        entries.append(info)
    names = [entry["name"] for entry in entries]
    return {
        "path": path.relative_to(root).as_posix(),
        "entry_count": len(entries),
        "entries": entries,
        "names": names,
        # The answer-shape gate projects an enumeration onto the noun the sentence
        # used, and for "files" that is `files`/`paths`.  Naming the field after
        # the question is what lets the delivered answer be checked instead of
        # refused as ANSWER_SHAPE_UNSERVED.
        "files": names,
        "answer": "\n".join(names),
    }


#: The grammars a sentence uses to state the string to look for. Each capture is
#: a plain word run; the value is never inferred from a path or a filename.
_SEARCH_GRAMMARS = (
    # "Which files under D mention beta" asks the same question as "...contain
    # beta" and was measured to reach this row and then be refused
    # (CAPABILITY_REFUSED_SEARCH_TEXT_NOT_STATED) because only "contain" was
    # read as the verb that states the needle.  "Mention" states it too: a file
    # that mentions a string is one whose text carries that string, which is
    # exactly what the search looks for.  The capture is the same narrow word
    # run, so this widens the verb and not the value.
    re.compile(r"\b(?:mention(?:s|ing)?|contain(?:s|ing)?)\s+[\"']?([A-Za-z0-9_.+-]{1,64})[\"']?", re.I),
    re.compile(r"\bfor\s+the\s+word\s+[\"']?([A-Za-z0-9_.+-]{1,64})[\"']?", re.I),
    re.compile(r"\b(?:search|look)\w*\b[^.]{0,80}?\bfor\s+[\"']?([A-Za-z0-9_.+-]{1,64})[\"']?", re.I),
)


def _stated_search_text(goal: str) -> str:
    """The one string the sentence says to look for, or a refusal.

    This is the only place the module reads a value out of prose, so it is the
    only place that could guess.  It refuses instead: no match, or two grammars
    that do not agree, is a refusal -- never a default.
    """
    found = set()
    for grammar in _SEARCH_GRAMMARS:
        for match in grammar.finditer(str(goal or "")):
            found.add(match.group(1))
    # "Search <d> for THE WORD beta" is caught by the looser grammar as "the".
    # A stop word can never be the value when another grammar found a real one,
    # so the stop words are dropped -- but only when something survives them, so
    # a sentence that genuinely asks for "the" still has its one answer.
    substantive = {value for value in found if value.lower() not in _STOP_WORDS}
    if substantive:
        found = substantive
    if len(found) == 1:
        return found.pop()
    raise RuntimeError("SEARCH_TEXT_NOT_STATED" if not found else "SEARCH_TEXT_AMBIGUOUS")


def _directory_search(args, root: pathlib.Path) -> dict:
    base = _safe(root, args.get("path") or "")
    if not base.is_dir():
        raise RuntimeError("PATH_NOT_A_DIRECTORY")
    needle = str(args.get("pattern") or "").strip() or _stated_search_text(args.get("goal") or "")
    matches: list[dict] = []
    scanned = 0
    for child in sorted(base.rglob("*")):
        if not child.is_file() or child.is_symlink():
            continue
        resolved = child.resolve()
        if resolved != root and root not in resolved.parents:
            continue
        try:
            text = resolved.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            # A binary or unreadable file is not a file that fails the search;
            # it is a file this question was not asked about.
            continue
        scanned += 1
        hits = [line for line in text.splitlines() if needle in line]
        if hits:
            matches.append({"path": resolved.relative_to(root).as_posix(),
                            "match_count": len(hits), "lines": hits[:20]})
    return {
        "path": base.relative_to(root).as_posix(),
        "pattern": needle,
        "files_scanned": scanned,
        "files_with_matches": [m["path"] for m in matches],
        "files": [m["path"] for m in matches],
        "match_count": sum(m["match_count"] for m in matches),
        "matches": matches,
        "answer": "\n".join(m["path"] for m in matches),
    }


_HANDLERS = {"word_frequency": _word_frequency, "directory_list": _directory_list,
             "directory_search": _directory_search}


def run(args, root):
    # This capability is registered read-only. A report path would make it a
    # writer and may be synthesized by the binder, so refuse it before reads.
    if args.get("output_path"):
        raise RuntimeError("READ_ONLY_CAPABILITY_REFUSES_OUTPUT_PATH")
    root = pathlib.Path(root).resolve()
    command = str(args.get("command") or "").strip()
    if command not in _HANDLERS:
        raise RuntimeError("COMMAND_NOT_IMPLEMENTED:" + (command or "<none>"))
    payload = {"schema": "PROJECT_BRAIN_FILE_SURVEY_V1",
               "adapter": "file_survey", "command": command}
    payload.update(_HANDLERS[command](args, root))
    payload.update({"output_path": None, "output_verified": True})
    return payload
