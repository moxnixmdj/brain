#!/usr/bin/env python3
"""Brain-owned zero-model purpose compiler for fresh Harbor environments.

This is a computed mechanism, not a model and not a task solver. It receives
only the instruction text and a bounded, read-only file-name scan. It never
imports a model, network client, benchmark loader, hidden test, solution or
verifier. It derives a small finite grammar of admissible transformations from
instruction-supplied quoted operands and fenced code/diff blocks. If no safe
transformation is stated, it fails closed and captures an empty patch.

The "right question" is not a question to a user or model. It is the one
decision-relevant contrast the current machine can answer: whether a visible
repository exists and whether the instruction itself supplies a safe
transformation that can be answered by one bounded run.
"""
from __future__ import annotations

import hashlib
import re
import shlex
from pathlib import PurePosixPath
from typing import Any

SCHEMA = "BRAIN_ZERO_MODEL_PURPOSE_COMPILER_V2"

FORBIDDEN_PATH_MARKERS = (
    "tests/",
    "test/",
    "solution/",
    "verifier/",
    ".git/",
    "node_modules/",
    "__pycache__/",
)
FORBIDDEN_COMMAND_MARKERS = (
    "cat ",
    "curl",
    "wget",
    "pytest",
    "test.sh",
    "solve.sh",
    "oracle",
    "git clone",
    "pip install",
    "apt-get",
    "npm install",
    "yarn add",
    "go get",
    " /tests/",
    " /solution/",
    " /verifier/",
)
ALLOWED_FAMILIES = {
    "APPLY_UNIFIED_DIFF",
    "REPLACE_LITERAL",
    "WRITE_QUOTED_FILE",
    "REMOVE_LITERAL_LINES",
    "COPY_FILE",
    "MOVE_OR_RENAME_FILE",
    "CHMOD_FILE",
    "UNRESOLVED_PURPOSE",
}
_QUOTED_SPAN = re.compile(r"`([^`]{1,4096})`|\"([^\"]{1,4096})\"|'([^']{1,4096})'")
_FENCED_BLOCK = re.compile(r"```([A-Za-z0-9_.+-]*)\n(.*?)```", re.S)
_DIFF_LINE = re.compile(r"(?m)^(diff --git |--- |\+\+\+ |@@ )")
_SAFE_PATH = re.compile(r"^[A-Za-z0-9._/\-]{1,200}$")
_SAFE_MODE = re.compile(r"^0?[0-7]{3,4}$")


def instruction_fingerprint(instruction: str) -> dict[str, Any]:
    data = instruction.encode("utf-8", errors="replace")
    return {
        "instruction_sha256": hashlib.sha256(data).hexdigest(),
        "instruction_bytes": len(data),
        "instruction_words": len(instruction.split()),
    }


def quoted_spans(instruction: str) -> list[str]:
    out: list[str] = []
    for match in _QUOTED_SPAN.finditer(instruction):
        value = next(group for group in match.groups() if group is not None)
        out.append(value)
    return out


def fenced_blocks(instruction: str) -> list[str]:
    return [match.group(2) for match in _FENCED_BLOCK.finditer(instruction)]


def safe_path(value: str) -> bool:
    if not value or len(value) > 200 or not _SAFE_PATH.fullmatch(value):
        return False
    lowered = value.casefold()
    if any(marker in lowered for marker in FORBIDDEN_PATH_MARKERS):
        return False
    parts = PurePosixPath(value).parts
    if ".." in parts or value.startswith("~"):
        return False
    if any(ch in value for ch in ("\\", "\n", "\r", "\x00")):
        return False
    return True


def safe_literal(value: str) -> bool:
    lowered = value.casefold()
    return (
        0 < len(value) <= 4096
        and "\x00" not in value
        and "\r" not in value
        and "\n" not in value
        and "\\" not in value
        and not any(marker in lowered for marker in FORBIDDEN_PATH_MARKERS)
    )


def safe_code_literal(value: str) -> bool:
    lowered = value.casefold()
    return (
        0 < len(value) <= 200000
        and "\x00" not in value
        and "\r" not in value
        and not any(marker in lowered for marker in FORBIDDEN_PATH_MARKERS)
    )


def _path_like(value: str) -> bool:
    return "/" in value or "." in value


def _single_path_and_literal(spans: list[str]) -> tuple[str, str, str | None]:
    indices = [i for i, span in enumerate(spans) if _path_like(span)]
    if len(indices) != 1:
        return "", "", "REFUSED__NEEDS_ONE_UNAMBIGUOUS_QUOTED_PATH"
    path = spans[indices[0]]
    if not safe_path(path):
        return "", "", "REFUSED__HIDDEN_OR_UNSAFE_QUOTED_PATH"
    literals = [
        span
        for i, span in enumerate(spans)
        if i != indices[0] and not _path_like(span) and safe_literal(span)
    ]
    if not literals:
        return "", "", "REFUSED__NEEDS_ONE_SAFE_QUOTED_LITERAL"
    return path, literals[0], None


def _two_paths(spans: list[str]) -> tuple[str, str, str | None]:
    indices = [i for i, span in enumerate(spans) if _path_like(span)]
    if len(indices) != 2:
        return "", "", "REFUSED__NEEDS_TWO_UNAMBIGUOUS_QUOTED_PATHS"
    source, destination = spans[indices[0]], spans[indices[1]]
    if not safe_path(source) or not safe_path(destination):
        return "", "", "REFUSED__HIDDEN_OR_UNSAFE_QUOTED_PATH"
    return source, destination, None


def scan_command() -> str:
    """Bounded read-only file-name scan; no file contents, tests or models."""
    return (
        "for root in /app /testbed /workspace /workspace/repo; do "
        "[ -d \"$root\" ] || continue; "
        "find \"$root\" -maxdepth 4 "
        "\\( -path '*/tests' -o -path '*/test' -o -path '*/solution' "
        "-o -path '*/verifier' -o -path '*/.git' -o -path '*/node_modules' "
        "-o -path '*/__pycache__' \\) -prune -o -type f -print; "
        "done | sort | head -n 200"
    )


def scan_is_safe(command: str) -> bool:
    lowered = command.casefold()
    return (
        "-prune" in lowered
        and "cat " not in lowered
        and "pytest" not in lowered
        and "test.sh" not in lowered
        and "solve.sh" not in lowered
        and "curl" not in lowered
        and "wget" not in lowered
    )


def command_is_safe(command: str) -> bool:
    lowered = command.casefold()
    return not any(marker in lowered for marker in FORBIDDEN_COMMAND_MARKERS)


def patch_capture_command() -> str:
    """Return the visible repository diff as stdout, never hidden test state."""
    excludes = " ".join(
        shlex.quote(item)
        for item in (
            ":(exclude)tests",
            ":(exclude)test",
            ":(exclude)solution",
            ":(exclude)verifier",
            ":(exclude)node_modules",
            ":(exclude)__pycache__",
            ":(exclude).git",
        )
    )
    return (
        "for repo in /app /testbed /workspace; do "
        "if [ -d \"$repo/.git\" ]; then "
        "cd \"$repo\" && git add -A -- . " + excludes +
        " && git diff --cached --binary -- . " + excludes + "; break; "
        "fi; done"
    )


def diff_is_safe(patch: str) -> bool:
    lowered = patch.casefold()
    if any(marker in lowered for marker in FORBIDDEN_PATH_MARKERS):
        return False
    for line in patch.splitlines():
        if line.startswith(("--- ", "+++ ")):
            target = line[4:].strip()
            if target.startswith(("a/", "b/")):
                target = target[2:]
            if target == "/dev/null":
                continue
            if not safe_path(target):
                return False
    return True


def classify_purpose(instruction: str, fenced: list[str], spans: list[str]) -> str:
    text = instruction.casefold()
    has_word = lambda word: re.search(r"\b" + re.escape(word) + r"\b", text) is not None
    safe_literals = [
        span for span in spans if not _path_like(span) and safe_literal(span)
    ]
    safe_paths = [span for span in spans if _path_like(span) and safe_path(span)]
    if any(_DIFF_LINE.search(block) for block in fenced):
        return "APPLY_UNIFIED_DIFF"
    if has_word("replace") or has_word("substitute") or has_word("change") and len(safe_literals) >= 2:
        return "REPLACE_LITERAL"
    if has_word("remove") and ("line" in text or "containing" in text or "matching" in text):
        return "REMOVE_LITERAL_LINES"
    if (
        has_word("create")
        or has_word("write")
        or "make a file" in text
        or has_word("add") and safe_paths
    ):
        return "WRITE_QUOTED_FILE"
    if has_word("copy"):
        return "COPY_FILE"
    if has_word("rename") or has_word("move"):
        return "MOVE_OR_RENAME_FILE"
    if "chmod" in text or "permission" in text and "mode" in text:
        return "CHMOD_FILE"
    # Natural-language bug reports do not license authored repair content.
    return "UNRESOLVED_PURPOSE"


def _replace_literal_python(old: str, new: str) -> str:
    return (
        "import os, pathlib, sys\n"
        "old=" + repr(old) + "; new=" + repr(new) + "\n"
        "roots=[pathlib.Path(p) for p in ('/app','/testbed','/workspace','/workspace/repo')]\n"
        "prune={'tests','test','solution','verifier','.git','node_modules','__pycache__'}\n"
        "count=0\n"
        "for root in roots:\n"
        "    if not root.is_dir(): continue\n"
        "    for base, dirs, files in os.walk(root):\n"
        "        dirs[:]=[d for d in dirs if d not in prune]\n"
        "        for name in files:\n"
        "            p=pathlib.Path(base)/name\n"
        "            try:\n"
        "                if p.stat().st_size > 1000000: continue\n"
        "                text=p.read_text(encoding='utf-8')\n"
        "                if old in text:\n"
        "                    p.write_text(text.replace(old,new),encoding='utf-8')\n"
        "                    count+=1\n"
        "            except Exception: continue\n"
        "            if count>=200: break\n"
        "        if count>=200: break\n"
        "    if count>=200: break\n"
        "print('BRAIN_REPLACED_FILES',count)\n"
    )


def _build_commands(
    family: str,
    spans: list[str],
    fenced: list[str],
    scan_stdout: str,
) -> tuple[list[str], list[str]]:
    commands: list[str] = []
    refusals: list[str] = []
    if family == "APPLY_UNIFIED_DIFF":
        patch = next((block for block in fenced if _DIFF_LINE.search(block)), "")
        if not patch or not diff_is_safe(patch) or len(patch) > 200000:
            return [], ["REFUSED__DIFF_NOT_INSTRUCTION_SUPPLIED_OR_NOT_SAFE"]
        commands.append(
            "for repo in /app /testbed /workspace; do "
            "if [ -d \"$repo/.git\" ]; then "
            "cd \"$repo\" && printf %s " + shlex.quote(patch) +
            " > /tmp/brain_instruction.patch && "
            "git apply --check /tmp/brain_instruction.patch && "
            "git apply /tmp/brain_instruction.patch; break; "
            "fi; done"
        )
    elif family == "REPLACE_LITERAL":
        literals = [
            span for span in spans
            if not _path_like(span) and safe_literal(span)
        ]
        if len(literals) < 2:
            return [], ["REFUSED__REPLACE_NEEDS_TWO_SAFE_QUOTED_LITERALS"]
        old, new = literals[0], literals[1]
        commands.append("python3 -c " + shlex.quote(_replace_literal_python(old, new)))
    elif family == "WRITE_QUOTED_FILE":
        path = ""
        paths = [span for span in spans if _path_like(span) and safe_path(span)]
        if len(paths) != 1:
            return [], ["REFUSED__WRITE_NEEDS_ONE_UNAMBIGUOUS_SAFE_QUOTED_PATH"]
        path = paths[0]
        content = next((block for block in fenced if not _DIFF_LINE.search(block)), "")
        if not content:
            literals = [
                span for span in spans
                if not _path_like(span) and safe_literal(span)
            ]
            content = literals[0] if literals else ""
        if not content or not safe_code_literal(content):
            return [], ["REFUSED__WRITE_NEEDS_ONE_SAFE_QUOTED_OR_FENCED_CONTENT"]
        commands.append(
            "mkdir -p " + shlex.quote(str(PurePosixPath(path).parent) or ".")
            + " && printf %s " + shlex.quote(content)
            + " > " + shlex.quote(path)
        )
    elif family == "REMOVE_LITERAL_LINES":
        path, literal, refusal = _single_path_and_literal(spans)
        if refusal:
            return [], ["REFUSED__REMOVE_" + refusal.removeprefix("REFUSED__")]
        tmp = path + ".brain_tmp"
        if not safe_path(tmp):
            return [], ["REFUSED__TEMP_PATH_NOT_SAFE"]
        commands.append(
            "grep -v -F -x -- " + shlex.quote(literal)
            + " " + shlex.quote(path)
            + " > " + shlex.quote(tmp)
            + " && mv -f " + shlex.quote(tmp) + " " + shlex.quote(path)
        )
    elif family in {"COPY_FILE", "MOVE_OR_RENAME_FILE"}:
        source, destination, refusal = _two_paths(spans)
        if refusal:
            return [], ["REFUSED__FILE_OPERATION_" + refusal.removeprefix("REFUSED__")]
        verb = "cp -f" if family == "COPY_FILE" else "mv -f"
        commands.append(
            "mkdir -p " + shlex.quote(str(PurePosixPath(destination).parent) or ".")
            + " && " + verb + " " + shlex.quote(source) + " " + shlex.quote(destination)
        )
    elif family == "CHMOD_FILE":
        paths = [span for span in spans if _path_like(span)]
        if len(paths) != 1 or not safe_path(paths[0]):
            return [], ["REFUSED__CHMOD_NEEDS_ONE_SAFE_QUOTED_PATH"]
        mode = next(
            (span for span in spans if not _path_like(span) and _SAFE_MODE.fullmatch(span)),
            "",
        )
        if not mode:
            return [], ["REFUSED__CHMOD_NEEDS_A_SAFE_QUOTED_MODE"]
        commands.append("chmod " + shlex.quote(mode) + " " + shlex.quote(paths[0]))
    else:
        refusals.append("UNRESOLVED_PURPOSE__NO_AUTHORED_REPAIR_CONTENT")
    unsafe = [command for command in commands if not command_is_safe(command)]
    if unsafe:
        return [], ["REFUSED__UNSAFE_GENERATED_COMMAND"]
    return commands, refusals


def plan(instruction: str, scan_stdout: str) -> dict[str, Any]:
    fingerprint = instruction_fingerprint(instruction)
    spans = quoted_spans(instruction)
    fenced = fenced_blocks(instruction)
    family = classify_purpose(instruction, fenced, spans)
    scan = scan_command()
    if not scan_is_safe(scan):
        return {
            **fingerprint,
            "schema": SCHEMA,
            "mode": "REFUSED",
            "goal_family": "REFUSED",
            "right_question": "Can the environment be scanned without reading hidden tests?",
            "commands": [],
            "refusals": ["REFUSED__SCAN_COMMAND_NOT_SAFE"],
            "zero_model": True,
            "hidden_test_reading": False,
        }
    if not scan_stdout.strip():
        right_question = "No admissible visible file was observed; ask whether a safe repository exists."
    else:
        right_question = (
            "Which visible source locus and instruction-supplied transformation, "
            "if any, can be answered by one safe run?"
        )
    commands, refusals = _build_commands(family, spans, fenced, scan_stdout)
    mode = "GOAL_DIRECTED" if family != "UNRESOLVED_PURPOSE" else "LEARN_BY_BOUNDED_SCAN_AND_REFUSE"
    return {
        **fingerprint,
        "schema": SCHEMA,
        "mode": mode,
        "goal_family": family,
        "right_question": right_question,
        "quoted_operand_count": len(spans),
        "fenced_block_count": len(fenced),
        "scan_command_sha256": hashlib.sha256(scan.encode("utf-8")).hexdigest(),
        "scan_stdout_sha256": hashlib.sha256(scan_stdout.encode("utf-8")).hexdigest(),
        "patch_capture_command_sha256": hashlib.sha256(
            patch_capture_command().encode("utf-8")
        ).hexdigest(),
        "commands": commands,
        "refusals": refusals,
        "allowed_families": sorted(ALLOWED_FAMILIES),
        "zero_model": True,
        "hidden_test_reading": False,
        "borrowed_outputs": False,
        "runtime_network_calls": 0,
    }
