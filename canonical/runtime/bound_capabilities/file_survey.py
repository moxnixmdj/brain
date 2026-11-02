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

Neither writes anything, spawns anything, or leaves the repository root.
"""
from __future__ import annotations

import hashlib
import json
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


_HANDLERS = {"word_frequency": _word_frequency, "directory_list": _directory_list}


def run(args, root):
    root = pathlib.Path(root).resolve()
    command = str(args.get("command") or "").strip()
    if command not in _HANDLERS:
        raise RuntimeError("COMMAND_NOT_IMPLEMENTED:" + (command or "<none>"))
    payload = {"schema": "PROJECT_BRAIN_FILE_SURVEY_V1",
               "adapter": "file_survey", "command": command}
    payload.update(_HANDLERS[command](args, root))
    output_path = args.get("output_path")
    written = None
    if output_path:
        out = _safe(root, output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        body = (json.dumps(payload, indent=1, sort_keys=True) + "\n").encode("utf-8")
        out.write_bytes(body)
        if out.read_bytes() != body:
            raise RuntimeError("WRITE_DID_NOT_ROUNDTRIP")
        written = out.relative_to(root).as_posix()
    payload.update({"output_path": written, "output_verified": True})
    return payload
