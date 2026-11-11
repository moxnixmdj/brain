#!/usr/bin/env python3
"""Rewrite ONE stated file with ONE stated transformation, atomically.

Four of the ordinary requests still refused are the same shape:

    Uppercase every line in <f>      -> the file, changed
    Delete the last line of <f>      -> the file, changed
    Add a line containing delta to <f>  -> the file, changed
    Compress <f>                     -> a new file beside it

They need an IN-PLACE EDIT, and the machine has no row for one. This is that row
for the three that do not change the file's type. Every rule here is a refusal,
because a wrong rewrite of a file destroys the caller's bytes with no record:

* the file must be NAMED by the sentence. A path that arrived from binding and
  is not in the sentence is a path the caller never pointed at;
* the file must be a regular UTF-8 file inside the repository;
* SOURCE CODE IS OUT OF SCOPE. Rewriting `.py` in place is a code edit, and a
  text transformation is not one: upper-casing a module's identifiers destroys
  it while looking like it worked. This row refuses those suffixes by name;
* the expected result is computed BEFORE anything is written, written to a
  temporary file in the same directory, read back and compared, and only then
  moved onto the source with `os.replace`. A failed comparison leaves the
  original untouched;
* the source is re-read and re-digested after the move, and if the file now
  holds anything other than the expected bytes, the original is put back;
* a transformation that would change nothing is REPORTED as unchanged rather
  than written -- a write that cannot be observed is worse than no write;
* a line is never appended from an unstated value: "add a line" with no line
  reads as "add something", and an invented line is an invented edit.

What the answer means: `output_verified` is true only when the bytes on disk
after the run are exactly the bytes this adapter computed from the bytes it
read, and `before_sha256` / `after_sha256` are both recomputed from disk.
"""
from __future__ import annotations

from canonical.runtime.bound_capabilities.stated_file_path import names_path

import hashlib
import os
import pathlib
import re

_MAX_BYTES = 64 * 1024 * 1024

#: Rewriting one of these in place is a code edit, not a text transformation.
_SOURCE_SUFFIXES = (".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".rs", ".go",
                    ".java", ".c", ".h", ".cpp", ".hpp", ".rb", ".cs", ".kt",
                    ".php", ".swift", ".mjs", ".cjs")

#: Words that introduce the value a sentence wants appended.
#
# The last alternative is the plainest English of the three -- "Add the line
# epsilon to <f>" -- and it was the one shape this table could not read, so the
# row refused with THE_LINE_TO_ADD_IS_NOT_STATED a request it exists to serve
# (measured 2026-11-02: two of twenty-four paraphrases of already-served
# sentences failed on this alone).  It comes last and refuses the other
# introducers, because "a line containing delta" also contains the word "line":
# without the negative lookahead this branch would claim "containing" as the
# text to add.
_STATED_TEXT = re.compile(
    r"""["'`](?P<quoted>[^"'`\n]+)["'`]"""
    r"""|\b(?:containing|that\s+says|reading|saying|with\s+the\s+text)\s+"""
    r"""(?P<bare>[^,.;\n]+?)(?=\s+(?:to|into|onto|at\s+the\s+end)\b|[,.;]|$)"""
    r"""|\bline\s+(?P<named>(?!(?:containing|that\s+says|reading|saying)\b)"""
    r"""(?!(?:to|into|onto|at)\b)"""
    r"""[^,.;"'`\n]+?)(?=\s+(?:to|into|onto|at\s+the\s+end)\b|[,.;]|$)""",
    re.I,
)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source(args, root: pathlib.Path) -> tuple[pathlib.Path, bytes, str]:
    raw = args.get("path") or args.get("input_path")
    if not str(raw or "").strip():
        raise RuntimeError("PATH_REQUIRED")
    path = (root / str(raw)).resolve()
    if path != root and root not in path.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if not path.is_file():
        raise RuntimeError("PATH_NOT_A_REGULAR_FILE")
    if path.suffix.lower() in _SOURCE_SUFFIXES:
        raise RuntimeError("REFUSES_TO_REWRITE_SOURCE_CODE_IN_PLACE:" + path.suffix)
    if path.stat().st_size > _MAX_BYTES:
        raise RuntimeError("FILE_TOO_LARGE")
    stated = str(args.get("goal") or "")
    path_statement = stated
    if (str(args.get("command") or "").strip().lower() == "append_line"
            and not _NOT_AN_APPEND.search(stated)):
        line_match = _STATED_TEXT.search(stated)
        if line_match is not None:
            path_statement = stated[:line_match.start()] + " " + stated[line_match.end():]
    if not names_path(path_statement, path, root):
        raise RuntimeError("PATH_NOT_STATED_IN_THE_SENTENCE:" + path.name)
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("FILE_IS_NOT_UTF8") from exc
    return path, text, stated


_QUOTE_MARKS = "\"'`"


def _quoting_marks(stated: str) -> list[int]:
    """Positions of the marks that quote something: every mark except one inside a word (it's)."""
    found = []
    for index, char in enumerate(stated):
        if char in _QUOTE_MARKS:
            inside_a_word = (0 < index < len(stated) - 1
                             and stated[index - 1].isalnum() and stated[index + 1].isalnum())
            if not inside_a_word:
                found.append(index)
    return found


def _stated_line(stated: str) -> str:
    """The one line the sentence states, without its quotation marks; refuses none, two, or unclear.

    Each refusal below was measured 2026-11-11 on fresh instances through the front door.  In each,
    the write had been re-read from disk and reported verified: the disk held what the adapter
    wrote, and what the adapter wrote was not what the sentence said.

    * `add a line containing "v481f vc31f" to <f>` appended the line WITH its quotation marks.  The
      search is leftmost-first, so the introducer branch ("containing ...") wins over the quoted
      branch whenever an introducer stands in front of the quotes, and it captured the marks as part
      of the text.
    * `add a line encrypted to the file <f> containing "vcea1 vc03c"` appended `encrypted` and said
      nothing about the quoted text.  A sentence that states two different lines has not said which
      one it wants; taking the leftmost is a guess.
    * A quoted line with a mark inside it was cut at that mark.

    So: when exactly two marks quote something, the line is the text between them, and any other
    line the sentence states must be that same text.  One mark, or more than two, cannot be read.
    """
    marks = _quoting_marks(stated)
    if len(marks) not in (0, 2):
        raise RuntimeError("THE_QUOTATION_MARKS_AROUND_THE_LINE_DO_NOT_PAIR")
    quoted = stated[marks[0] + 1:marks[1]].strip() if marks else None
    if marks and (not quoted or "\n" in quoted):
        raise RuntimeError("THE_LINE_TO_ADD_IS_NOT_STATED")
    lines: list[str] = [quoted] if quoted else []
    for match in _STATED_TEXT.finditer(stated):
        if match.group("quoted"):
            continue        # read above, from the marks themselves
        line = (match.group("bare") or match.groupdict().get("named") or "").strip()
        if len(line) >= 2 and line[0] in _QUOTE_MARKS and line[-1] in _QUOTE_MARKS:
            line = line[1:-1].strip()
        if line and line not in lines:
            lines.append(line)
    if not lines:
        raise RuntimeError("THE_LINE_TO_ADD_IS_NOT_STATED")
    if len(lines) > 1:
        raise RuntimeError("THE_SENTENCE_STATES_MORE_THAN_ONE_LINE_TO_ADD")
    return lines[0]


def _uppercase(text: str, args, stated: str) -> str:
    return "\n".join(line.upper() for line in text.split("\n"))


# A DELETION BY POSITION IS NOT IMPLEMENTED HERE, ON PURPOSE.
#
# "Remove the last line from the file X" was implemented and served for one
# measurement, and the repository's own acceptance suite refused it: a line
# removed by position is not in the argv, so nothing on disk can answer for it
# afterwards -- the removed line is simply gone.  `test_an_edit_nothing_can_
# prove_is_refused_and_leaves_the_file_alone` is the standard, and this adapter
# meets it by not offering the operation: the sentence keeps failing closed and
# the file keeps its bytes.  Adding the handler back without a postcondition the
# disk can answer would be a weaker rule, not a feature.


#: A sentence that asks for one of these is not asking to append anything.
_NOT_AN_APPEND = re.compile(r"\b(?:delete|remove|drop|truncate|erase|strip|clear)\b", re.I)


def _append_line(text: str, args, stated: str) -> str:
    if _NOT_AN_APPEND.search(stated):
        # Measured 2026-11-02: "Delete the last line of <f>" was selected by this
        # row on the word "line".  It refused for want of a stated line, which is
        # the right outcome for the wrong reason -- so the reason is now exact.
        raise RuntimeError("THE_SENTENCE_ASKS_TO_REMOVE_SOMETHING_NOT_ADD_IT")
    line = _stated_line(stated)
    body = text if (not text or text.endswith("\n")) else text + "\n"
    return body + line + "\n"


_HANDLERS = {
    "uppercase": _uppercase,
    "append_line": _append_line,
}


def _write_atomically(path: pathlib.Path, expected: bytes) -> None:
    """Write beside the target, prove the bytes, then move them into place."""
    temporary = path.with_name(path.name + ".brain-edit-tmp")
    # Claim the scratch path exclusively before writing.  In particular, an
    # existing file or symlink at the predictable name is somebody else's data:
    # do not truncate it and do not remove it in our cleanup.
    try:
        scratch = temporary.open("xb")
    except FileExistsError as exc:
        raise RuntimeError("TEMPORARY_PATH_ALREADY_EXISTS:" + temporary.name) from exc
    try:
        with scratch:
            scratch.write(expected)
        if _digest(temporary.read_bytes()) != _digest(expected):
            raise RuntimeError("THE_EDIT_DID_NOT_ROUNDTRIP")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def run(args, root):
    root = pathlib.Path(root).resolve()
    command = str(args.get("command") or "").strip().lower()
    if command not in _HANDLERS:
        raise RuntimeError("COMMAND_NOT_IMPLEMENTED:" + (command or "<none>"))
    path, text, stated = _source(args, root)
    before = path.read_bytes()
    # The transformation must apply to the same bytes recorded as its input.
    # Refuse a competing write between _source's read and this read instead of
    # replacing the newer file with a transformation of the older contents. This
    # does not eliminate races after this check or prove atomic compare-and-swap.
    if before != text.encode("utf-8"):
        raise RuntimeError("SOURCE_CHANGED_BETWEEN_READS:" + path.name)
    expected_text = _HANDLERS[command](text, args, stated)
    expected = expected_text.encode("utf-8")
    payload = {"schema": "PROJECT_BRAIN_FILE_EDIT_V1", "adapter": "file_edit",
               "command": command, "path": path.relative_to(root).as_posix(),
               "before_sha256": _digest(before), "before_line_count": len(text.splitlines()),
               "after_line_count": len(expected_text.splitlines())}
    if expected == before:
        # Nothing to do, and saying so is the truth: a write that cannot be
        # observed would report a change that did not happen.
        payload.update({"after_sha256": _digest(before), "unchanged": True,
                        "answer": "already as asked: " + payload["path"],
                        "output_verified": True})
        return payload
    _write_atomically(path, expected)
    after = path.read_bytes()
    if after != expected:
        # Put the original back rather than leave a file nobody asked for.
        path.write_bytes(before)
        raise RuntimeError("THE_EDIT_DID_NOT_LAND:" + path.name)
    payload.update({"after_sha256": _digest(after), "unchanged": False,
                    "byte_count": len(after),
                    "answer": "%s: %d -> %d lines" % (payload["path"],
                                                      payload["before_line_count"],
                                                      payload["after_line_count"]),
                    "output_verified": True})
    return payload
