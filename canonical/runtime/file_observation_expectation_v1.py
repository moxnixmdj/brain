"""Recheck read-only file observations from the stated input.

The verifier rereads the inputs instead of accepting the adapter's success bit.
It does not write a report. This is code-path independence, not independent
personnel verification; diff generation shares Python's difflib with the adapter.
"""
from __future__ import annotations

import collections
import difflib
import hashlib
import pathlib
import re
import stat
from collections.abc import Mapping
from typing import Any


# The declared word-frequency policy, kept here rather than importing the adapter.
_STOP = frozenset("a an and are as at be but by for from has have he her his i if in is it its me my no not of on or our she so that the their them then there these they this to was we were what when which who will with you your".split())
_SEARCH_PATTERNS = (
    r"\b(?:mention(?:s|ing)?|contain(?:s|ing)?)\s+[\"']?([A-Za-z0-9_.+-]{1,64})[\"']?",
    r"\bfor\s+the\s+word\s+[\"']?([A-Za-z0-9_.+-]{1,64})[\"']?",
    r"\b(?:search|look)\w*\b[^.]{0,80}?\bfor\s+[\"']?([A-Za-z0-9_.+-]{1,64})[\"']?",
)


def _needle(args: Mapping[str, Any]) -> str:
    explicit = str(args.get("pattern") or "").strip()
    if explicit:
        return explicit
    found = {m.group(1) for pattern in _SEARCH_PATTERNS
             for m in re.finditer(pattern, str(args.get("goal") or ""), re.I)}
    substantive = {value for value in found if value.lower() not in _STOP}
    if substantive:
        found = substantive
    if len(found) != 1:
        raise ValueError("SEARCH_TEXT_NOT_UNIQUE")
    return next(iter(found))


def _read_file(path: pathlib.Path) -> tuple[bytes, str]:
    if not path.is_file():
        raise ValueError("PATH_NOT_REGULAR_FILE")
    data = path.read_bytes()
    return data, data.decode("utf-8")


def _records(text: str) -> list[str]:
    if not text:
        return []
    records = text.split("\n")
    if records[-1] == "":
        records.pop()
    return records


def _reobserve(mode: str, target: pathlib.Path, root: pathlib.Path,
               args: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    commands = {"contents": "cat", "sorted": "sort", "reversed": "tac", "diff": "diff",
                "word_frequency": "word_frequency", "directory_listing": "directory_list",
                "directory_search": "directory_search"}
    command = commands[mode]
    if args.get("command") != command or result.get("command") != command:
        raise ValueError("COMMAND_MISMATCH")
    if mode in {"contents", "sorted", "reversed", "diff", "word_frequency"}:
        raw, text = _read_file(target)
        if mode == "contents":
            return {"answer": text, "source_sha256": hashlib.sha256(raw).hexdigest()}
        if mode in {"sorted", "reversed"}:
            records = _records(text)
            records = sorted(records) if mode == "sorted" else records[::-1]
            return {"answer": "\n".join(records) + ("\n" if records else ""),
                    "line_count": len(records),
                    "sorted_lines" if mode == "sorted" else "reversed_lines": records,
                    "source_sha256": hashlib.sha256(raw).hexdigest()}
        if mode == "diff":
            other_raw = args.get("other_path")
            if not isinstance(other_raw, str) or not other_raw.strip():
                raise ValueError("SECOND_PATH_REQUIRED")
            other = (root / other_raw).resolve()
            if other == root or root not in other.parents:
                raise ValueError("SECOND_PATH_OUTSIDE_ROOT")
            _, second = _read_file(other)
            left_name, right_name = target.relative_to(root).as_posix(), other.relative_to(root).as_posix()
            unified = "".join(difflib.unified_diff(text.splitlines(keepends=True),
                              second.splitlines(keepends=True), fromfile=left_name, tofile=right_name))
            return {"other_path": right_name, "answer": unified, "identical": text == second,
                    "differences": int(text != second)}
        counts = collections.Counter(word for word in re.findall(r"[A-Za-z0-9']+", text.lower())
                                     if word not in _STOP)
        if not counts:
            raise ValueError("NO_WORDS_TO_COUNT")
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        word, n = ranked[0]
        return {"most_common_word": word, "count": n,
                "tied_for_first": sorted(k for k, v in counts.items() if v == n),
                "counts": dict(ranked[:20]), "distinct_words": len(counts), "answer": word,
                "source_sha256": hashlib.sha256(raw).hexdigest()}
    if not target.is_dir():
        raise ValueError("PATH_NOT_DIRECTORY")
    if mode == "directory_listing":
        entries = []
        for item in sorted(target.iterdir(), key=lambda child: child.name):
            try:
                size = item.stat().st_size
            except OSError:
                size = None
            entries.append({"name": item.name, "is_dir": item.is_dir(),
                            "is_file": item.is_file(), "size_bytes": size})
        names = [item["name"] for item in entries]
        return {"entry_count": len(entries), "entries": entries, "names": names,
                "files": names, "answer": "\n".join(names)}
    needle = _needle(args)
    matches = []
    scanned = 0
    for item in sorted(target.rglob("*")):
        if item.is_symlink() or not item.is_file():
            continue
        resolved = item.resolve()
        if resolved != root and root not in resolved.parents:
            continue
        try:
            text = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        scanned += 1
        lines = [line for line in text.splitlines() if needle in line]
        if lines:
            matches.append({"path": resolved.relative_to(root).as_posix(),
                            "match_count": len(lines), "lines": lines[:20]})
    paths = [item["path"] for item in matches]
    return {"pattern": needle, "files_scanned": scanned, "files_with_matches": paths,
            "files": paths, "match_count": sum(item["match_count"] for item in matches),
            "matches": matches, "answer": "\n".join(paths)}


def verify(expect: Mapping[str, Any], result: Mapping[str, Any],
           args: Mapping[str, Any], root: pathlib.Path | str) -> tuple[bool, str]:
    try:
        if not isinstance(expect, Mapping) or not isinstance(result, Mapping) or not isinstance(args, Mapping):
            raise ValueError("INVALID_CONTRACT")
        if result.get("output_verified") is not True:
            raise ValueError("PRODUCER_DID_NOT_VERIFY")
        if args.get("output_path") or result.get("output_path") is not None:
            raise ValueError("READ_ONLY_OUTPUT_PATH")
        raw = args.get("path")
        reported = result.get("path")
        if not isinstance(raw, str) or not raw.strip() or not isinstance(reported, str) or not reported.strip():
            raise ValueError("PATH_REQUIRED")
        root = pathlib.Path(root).resolve()
        target = (root / raw).resolve()
        claimed = (root / reported).resolve()
        if target == root or root not in target.parents or claimed != target:
            raise ValueError("PATH_OUTSIDE_ROOT_OR_MISMATCH")
        mode = expect.get("observation")
        if mode == "line_count":
            if expect.get("field") != "line_count":
                raise ValueError("OBSERVATION_FIELD_INVALID")
            if not target.is_file():
                raise ValueError("PATH_NOT_REGULAR_FILE")
            raw_bytes = target.read_bytes()
            text = raw_bytes.decode("utf-8")
            count = len(text.splitlines())
            expected = {"line_count": count, "newline_count": raw_bytes.count(b"\n"),
                        "ends_with_newline": text.endswith("\n"), "byte_count": len(raw_bytes),
                        "source_sha256": hashlib.sha256(raw_bytes).hexdigest(), "answer": count}
        elif mode == "stat":
            if expect.get("field") != "size_bytes":
                raise ValueError("OBSERVATION_FIELD_INVALID")
            info = target.stat()
            expected = {"size_bytes": int(info.st_size),
                        "permissions_octal": format(stat.S_IMODE(info.st_mode), "04o"),
                        "is_file": target.is_file(), "is_dir": target.is_dir(),
                        "is_symlink": target.is_symlink()}
        elif mode in {"contents", "sorted", "reversed", "diff", "word_frequency",
                      "directory_listing", "directory_search"}:
            if expect.get("field") != "answer":
                raise ValueError("OBSERVATION_FIELD_INVALID")
            expected = _reobserve(mode, target, root, args, result)
            if mode in {"contents", "sorted", "reversed", "diff"}:
                argv = [str(args["command"]), str(args["path"])]
                if mode == "diff":
                    argv.append(str(args["other_path"]))
                expected.update({"argv": argv,
                                 "argv_sha256": hashlib.sha256("\0".join(argv).encode("utf-8")).hexdigest()})
        else:
            raise ValueError("OBSERVATION_UNSUPPORTED")
        for key, value in expected.items():
            observed = result.get(key)
            if type(observed) is not type(value) or observed != value:
                raise ValueError("OBSERVATION_MISMATCH:" + key)
        return True, "FILE_OBSERVATION_REVERIFIED"
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        return False, "FILE_OBSERVATION_REFUSED:" + str(exc)[:200]
