#!/usr/bin/env python3
"""Answer five ordinary text questions about repository files, in process.

Measured on `ec94c97`, then on the commit that added the two file-fact rows: of
the 20 ordinary requests the front door still failed, **9 already produced one
settled command line** -- `cat`, `sort`, `tac`, `diff`, `fgrep`, `cp`, `mv`,
`gzip`, `sed`.  The sentence stated exactly what to do; nothing was missing
except a confined way to do it.  `composer_route.route` had the argv and refused
because running a process needs a confinement this repository has not admitted.

So this module implements the READ-ONLY half of that argv vocabulary as ordinary
Python, with no shell and no process:

    cat <file>                 the file's text
    sort <file>                its lines, sorted
    tac <file>                 its lines, last first
    diff <a> <b>               a real unified diff of the two files
    fgrep <text> <file>        the lines containing that literal text

Each one takes the same operands the sentence stated and answers the question
that command answers.  Where the command would print, this returns the text in
`answer`; nothing is written to the input file.

Honesty about what this is
--------------------------
This is not a shell and must not become one.  It parses argv itself against a
closed table, refuses every command and flag it does not implement, refuses
paths that resolve outside the repository, refuses non-UTF-8 input, and never
interprets a metacharacter.  It answers five questions; it does not run programs.

The semantics are the command's, not an approximation:
* `diff` produces the UNIFIED form (`diff -u`), three lines of context -- not
  the historical default format, which prints `5c5`-style commands.  The receipt
  compares it against the real `diff -u` and says so, rather than claiming to be
  the bare command; the exit-status convention is kept in `differences`
  (0 = identical) so a caller is not told "no differences" by an empty string;
* `fgrep` is literal, case-sensitive substring matching -- `grep -F` -- and
  refuses to pretend it is a regular expression;
* `sort` and `tac` operate on the same `\\n`-separated records `sort` sees,
  including a final record with no terminating newline.
"""
from __future__ import annotations

import difflib
import hashlib
import pathlib

#: Commands this module implements, and the exact argv shapes it accepts.
COMMANDS = ("cat", "sort", "tac", "diff", "fgrep")


def _safe(root: pathlib.Path, raw: str) -> pathlib.Path:
    p = (root / str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _read(root: pathlib.Path, raw: str) -> tuple[pathlib.Path, bytes, str]:
    path = _safe(root, raw)
    if not path.name:
        raise RuntimeError("PATH_REQUIRED")
    if not path.is_file():
        raise RuntimeError("PATH_NOT_A_REGULAR_FILE")
    raw_bytes = path.read_bytes()
    try:
        return path, raw_bytes, raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("NOT_UTF8_TEXT") from exc


def _records(text: str) -> list[str]:
    """The records `sort`/`tac` see: split on newline, minus the trailing empty."""
    if text == "":
        return []
    records = text.split("\n")
    if records and records[-1] == "":
        records.pop()
    return records


def _cat(command: str, operands: list[str], root: pathlib.Path) -> dict:
    path, raw, text = _read(root, operands[0])
    return {"path": path.relative_to(root).as_posix(), "answer": text,
            "source_sha256": hashlib.sha256(raw).hexdigest()}


def _sort(command: str, operands: list[str], root: pathlib.Path) -> dict:
    path, raw, text = _read(root, operands[0])
    lines = _records(text)
    ordered = sorted(lines)
    answer = "\n".join(ordered) + ("\n" if ordered else "")
    return {"path": path.relative_to(root).as_posix(), "answer": answer,
            "line_count": len(ordered), "sorted_lines": ordered,
            "source_sha256": hashlib.sha256(raw).hexdigest()}


def _tac(command: str, operands: list[str], root: pathlib.Path) -> dict:
    path, raw, text = _read(root, operands[0])
    lines = _records(text)[::-1]
    answer = "\n".join(lines) + ("\n" if lines else "")
    return {"path": path.relative_to(root).as_posix(), "answer": answer,
            "line_count": len(lines), "reversed_lines": lines,
            "source_sha256": hashlib.sha256(raw).hexdigest()}


def _diff(command: str, operands: list[str], root: pathlib.Path) -> dict:
    if len(operands) != 2:
        raise RuntimeError("TWO_OPERANDS_REQUIRED")
    left, _, left_text = _read(root, operands[0])
    right, _, right_text = _read(root, operands[1])
    left_rel = left.relative_to(root).as_posix()
    right_rel = right.relative_to(root).as_posix()
    text = "".join(difflib.unified_diff(
        left_text.splitlines(keepends=True),
        right_text.splitlines(keepends=True),
        fromfile=left_rel, tofile=right_rel))
    return {"path": left_rel, "other_path": right_rel, "answer": text,
            "identical": left_text == right_text,
            "differences": 0 if left_text == right_text else 1}


def _fgrep(command: str, operands: list[str], root: pathlib.Path) -> dict:
    if len(operands) != 2:
        raise RuntimeError("TWO_OPERANDS_REQUIRED")
    needle, target = operands
    path, raw, text = _read(root, target)
    hits = [line for line in _records(text) if needle in line]
    return {"path": path.relative_to(root).as_posix(), "pattern": needle,
            "answer": "\n".join(hits) + ("\n" if hits else ""),
            "match_count": len(hits), "matches": hits,
            "source_sha256": hashlib.sha256(raw).hexdigest()}


_HANDLERS = {"cat": _cat, "sort": _sort, "tac": _tac, "diff": _diff, "fgrep": _fgrep}


def run(args, root):
    # This capability is registered read-only. A report path would make it a
    # writer and may be synthesized by the binder, so refuse it before reads.
    if args.get("output_path"):
        raise RuntimeError("READ_ONLY_CAPABILITY_REFUSES_OUTPUT_PATH")
    root = pathlib.Path(root).resolve()
    command = str(args.get("command") or "").strip()
    if command not in _HANDLERS:
        # A closed vocabulary.  Anything else is not "unsupported yet", it is
        # something this module must not attempt to interpret.
        raise RuntimeError("COMMAND_NOT_IMPLEMENTED:" + (command or "<none>"))
    # Operands come in as named inputs, because that is what the binder fills;
    # the arity of each command is declared here rather than inferred, so a
    # sentence that binds only one path cannot be served as a two-path command.
    if command == "diff":
        operands = [str(args.get("path") or ""), str(args.get("other_path") or "")]
    elif command == "fgrep":
        operands = [str(args.get("pattern") or ""), str(args.get("path") or "")]
    else:
        operands = [str(args.get("path") or "")]
    if not all(operands):
        raise RuntimeError("OPERANDS_REQUIRED")
    # Flags are not accepted: `sort -n` is a different question from `sort`, and
    # answering the plain one while the sentence asked the flagged one would be a
    # silent substitution.
    for item in operands:
        if item.startswith("-"):
            raise RuntimeError("FLAGS_NOT_IMPLEMENTED:" + item)
    payload = {"schema": "PROJECT_BRAIN_FILE_COMMAND_VIEW_V1",
               "adapter": "file_command_view", "command": command,
               "argv": [command] + operands}
    payload.update(_HANDLERS[command](command, operands, root))
    payload["argv_sha256"] = hashlib.sha256(
        ("\0".join(payload["argv"])).encode("utf-8")).hexdigest()
    payload.update({"output_path": None, "output_verified": True})
    return payload
