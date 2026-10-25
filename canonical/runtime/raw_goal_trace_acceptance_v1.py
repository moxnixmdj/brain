"""Generic raw-goal acceptance: every claimed effect is re-opened from disk.

Why this module exists
----------------------
Before this, raw-goal acceptance was keyed to ONE exact sentence, so 10 of the
11 goals the machine actually executes finished with no independent check at
all: ``semantic_acceptance_complete`` was ``False`` even though the controller
had really run and really written artifacts.

Execution success is a claim. Acceptance is a measurement. This module measures.

The rule is deliberately asymmetric:

* A capability with **no** registered re-inspector can never be accepted
  (``NO_INDEPENDENT_REINSPECTION_FOR:<cid>``). Acceptance therefore grows only
  when someone writes a real inspector, never when someone trusts a flag.
* ``output_verified`` / ``verified`` in a result are **not** evidence. They are
  only used to refuse early when the producer itself said ``False``.
* Every inspector opens bytes: the tar is re-opened with :mod:`tarfile`, the
  xlsx and docx are re-opened as OOXML packages, the PDF is re-extracted, the
  JSON artifacts are re-parsed, and every candidate the ranker scored is
  required to match the sha256 of a real file in the repository.
* Every path is required to resolve inside the repository, and every declared
  output sha256 is recomputed from the file on disk.

Nothing here calls a model. Nothing here spends. Everything fails closed.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tarfile
import zipfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

SCHEMA = "PROJECT_BRAIN_RAW_GOAL_TRACE_ACCEPTANCE_V1"
ABSORBED_MODE = "SUBGOAL_ABSORBED_BY_COMPILED_PREFIX"
DOCX_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# Argument names that carry a path, split by role. A step's outputs must exist
# on disk; its inputs must exist too, because a step cannot have consumed a
# file that was not there.
# Roles whose value is the payload a request asked to be written.  Unlike a path,
# a payload has no on-disk form to re-open, so the only independent check available
# is that the sentence actually contains it.
_TEXT_PAYLOAD_ARGS = ("content", "text", "body", "message")

# The role word that introduces a command line in a sentence.  Deliberately a
# two-word test rather than a call into the binder: the binder is the thing under
# test, and PR #6118 established that an inspector which asks the binder what it
# meant is not an inspector.
#
# This test is also what keeps the argv check honest about its own scope, and
# measuring showed why the unscoped version was wrong.  A capability declares its
# own argv in its action_template -- the 295 receipt-backed rows all run
# ["python3", "canonical/runtime/<name>.py"] -- and that argv is part of a
# definition that was independently verified at acquisition, not something a
# binder took out of a sentence.  Unscoped, the check refused 174 of the 223
# passing goals with STEP_COMMAND_NOT_IN_THE_REQUEST, because the token "python3"
# is not in "Run the <capability>."  When a sentence states no command there is
# no claim about a command to check, and inventing one is the same error the
# check exists to catch.
_COMMAND_ROLE_WORD = re.compile(r"\b(?:shell|cli|terminal)?\s*(?:command|argv)\b", re.I)


def _STATES_A_COMMAND(goal: Any) -> bool:
    """True when the sentence itself introduces a command line."""
    return bool(_COMMAND_ROLE_WORD.search(str(goal or "")))


# What may sit between a payload and the path it is being written to.
# A destination may be described, not just named.  Measured: the pattern
# allowed "to the file X" and nothing else, so every ordinary adjective between
# the article and the noun broke the match --
#
#   to the output file X       -> False
#   to the target file X       -> False
#   to the destination file X  -> False
#   into the same file X       -> False
#   to the given file X        -> False
#
# six of seven natural phrasings.  The consequence is not a refusal to write:
# the write HAPPENS and the bytes are correct, and the verifier then reports
# STEP_TEXT_PAYLOAD_NOT_IN_THE_REQUEST -- a failure reported over work that
# succeeded, the shape PR #6126 closed elsewhere.  "Write the file content
# PROJECT BRAIN to the output file X" wrote exactly those 13 bytes and was
# refused, while "Write the text 'PROJECT BRAIN' to the file X" passed, the
# only difference being one adjective.
#
# The words admitted are the ones that describe WHERE the payload goes.  The
# truncation defence is untouched, because it does not rest on this prefix: the
# lookahead still requires a path-like token to begin the instant the
# description ends, and a truncated payload is followed by the rest of the
# payload, which is prose and not a path.
_DEST_MODIFIER = r"(?:(?:output|target|destination|same|given|stated|named|following|new|existing)\s+){0,2}"

_BETWEEN_PAYLOAD_AND_DEST = re.compile(
    r"\s*(?:to|into|in|at)\s+(?:(?:the|a|an)\s+)?" + _DEST_MODIFIER +
    r"(?:file|path|folder|directory)?\s*"
    r"(?=\S*/|\S+\.[A-Za-z0-9]{1,6}\b)", re.I)
# The word that introduces a payload.  Both boundaries are needed, and measuring
# showed why one is not enough: dropping a leading article leaves a payload that
# still runs to the destination, so "archive manifest listing" satisfies the
# right-hand check inside "Write the text the archive manifest listing to X".
# What gives it away is the left edge -- it does not begin where the role word
# says the payload begins.
_PAYLOAD_ROLE_WORD = re.compile(
    r"(?:text|content|string|message|word|line|containing)\s+$", re.I)


def _payload_runs_to_the_destination(goal: str, payload: str) -> bool:
    """True when the sentence states this payload and then names where it goes.

    Substring containment is NOT sufficient, and measuring it proved why: the
    altered payloads are truncations, so every one of them is still a substring
    of the sentence that produced it.  "the results are in the attachment" was
    truncated to "results are", "results are" is plainly inside the goal, and a
    containment check accepted it.  What distinguishes the payload the sentence
    actually stated is that the sentence is DONE with it -- a destination follows
    immediately.  A truncated payload is followed by the rest of the payload
    instead, and "in the attachment" is not a destination because nothing
    path-like comes after it.

    This is re-derived here rather than read from the binder on purpose.  The
    binder is the thing under test; an inspector that asks the binder what it
    meant is not an inspector.
    """
    text = str(goal or "")
    start = text.find(payload)
    while start >= 0:
        prefix = text[:start]
        # A sentence normally QUOTES the text it states -- "write the text
        # 'hello there' to the file X" -- and the quotation marks are the
        # sentence's punctuation, not part of the payload.  Both anchors below
        # were written against unquoted sentences, so they read a quote as
        # payload: the role word had to run straight into the payload, and the
        # destination had to start the instant the payload ended.  Measured on
        # a8d35d7: every quoting style failed, and "Write the text 'hello
        # there' to the file w.txt" wrote the correct 11 bytes and was then
        # refused STEP_TEXT_PAYLOAD_NOT_IN_THE_REQUEST -- while solve() reported
        # pass=True anyway, because nothing downstream read that verdict.
        #
        # This tolerates one delimiter on each side and nothing else, so the
        # truncation defence is untouched: a truncated payload is still followed
        # by the rest of itself, which no delimiter turns into a destination.
        open_delim = _PAYLOAD_OPEN_DELIM.search(prefix)
        role_prefix = prefix[:open_delim.start()] if open_delim else prefix
        if _PAYLOAD_ROLE_WORD.search(role_prefix):
            end = start + len(payload)
            close_delim = _PAYLOAD_CLOSE_DELIM.match(text, end)
            if close_delim:
                end = close_delim.end()
            rest = text[end:]
            # Either the sentence goes on to name where the payload goes, or the
            # payload is the last thing in it ("... containing the text X").
            if not rest.strip() or _BETWEEN_PAYLOAD_AND_DEST.match(text, end):
                return True
        start = text.find(payload, start + 1)
    return False

# One quotation mark, bracket or paren on each side of a stated payload.  Kept to
# a single character deliberately: a run of them is not punctuation, it is content.
_PAYLOAD_OPEN_DELIM = re.compile(r"""[\'"\u2018\u201c(\[]\s*$""")
_PAYLOAD_CLOSE_DELIM = re.compile(r"""\s*[\'"\u2019\u201d)\]]""")

def _verified_consumed_paths(args: Mapping[str, Any], root: Path) -> tuple[str, ...]:
    """Paths this step's command removed, where the removal itself was verified.

    Asks the same postcondition table the inspector uses and returns nothing
    unless it passes, so a path is excused from the existence check only by a
    check that looked at the disk -- never by the shape of the command alone.
    """
    argv = args.get("argv")
    if not isinstance(argv, (list, tuple)) or not argv:
        return ()
    tokens = [str(tok) for tok in argv]
    if any(not tok for tok in tokens):
        return ()
    check = _MUTATING_POSTCONDITIONS.get(tokens[0].rsplit("/", 1)[-1])
    if check is None:
        return ()
    try:
        passed, _reason, evidence = check(tokens, root)
    except Exception:  # noqa: BLE001 - a postcondition that cannot run grants nothing
        return ()
    if not passed:
        return ()
    return tuple(str(item) for item in (evidence or {}).get("consumed_paths") or ())


_PATH_ARGS = (
    "output_path", "path", "json_path", "archive_path", "manifest_path",
    "input_path", "extraction_path", "result_path", "source_json_path",
)
_ROOT_ARGS = ("source_root", "search_root")

Inspector = Callable[[Mapping[str, Any], Mapping[str, Any], Path], tuple[bool, str, dict]]


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _unresolved(reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "status": "RAW_GOAL_ACCEPTANCE_UNRESOLVED",
        "pass": False,
        "reason": reason,
        "semantic_acceptance_complete": False,
        "terminal_authority": False,
        "accepted_obligation_ids": [],
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
    out.update(extra)
    return out


def _inside(root: Path, relative: Any) -> Path | None:
    """Resolve a repository-relative path, refusing anything outside the repo."""
    if not isinstance(relative, str) or not relative.strip():
        return None
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None


def _canonical_json_sha256(path: Path) -> str | None:
    """Digest of a JSON file's canonical form.

    The decision capabilities digest the *parsed content*, not the raw bytes,
    so an inspector that hashed the file would disagree with an honest
    producer. Content equality is the stronger claim anyway: it survives
    re-serialisation and still fails the moment the evidence changes.
    """
    data = _json(path)
    if data is None:
        return None
    try:
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return None
    return _digest(canonical.encode("utf-8"))


def _alternative_ids(alternatives: Any) -> set[str]:
    """Alternative identifiers, whether the evidence file spells them as
    bare strings or as ``{"id": ..., "label": ...}`` records."""
    ids: set[str] = set()
    if not isinstance(alternatives, list):
        return ids
    for row in alternatives:
        if isinstance(row, str):
            ids.add(row)
        elif isinstance(row, Mapping) and isinstance(row.get("id"), str):
            ids.add(row["id"])
    return ids


def unwrap_bound_adapter_row(row: Any) -> Any:
    """Read a trace row whether or not a verified bound adapter wrapped it.

    The verified bound adapter nests the capability's own result under
    ``result`` and its arguments under ``args.inputs``; the registry template
    action does neither. The re-inspectors were written against the flat shape
    and read arguments by the names the registry template declares, so a
    wrapped row handed to them looks empty and every artifact reads as missing.

    This is a union, not a rewrite: the wrapper's own keys win every collision,
    so the capability identity and the proof digests stay exactly as the
    adapter recorded them, and only keys the wrapper does not define are added.
    Nothing is invented, and each inspector still re-opens the artifact from
    disk and recomputes its digest, so a lifted path that does not match
    reality is refused all the same.
    """
    if not isinstance(row, Mapping):
        return row

    def _lift(outer: Any) -> Any:
        if not isinstance(outer, Mapping):
            return outer
        inner = outer.get("result") if "result" in outer else outer.get("inputs")
        if not isinstance(inner, Mapping):
            return outer
        merged = dict(outer)
        for key, value in inner.items():
            merged.setdefault(key, value)
        return merged

    out = dict(row)
    plan = row.get("plan")
    if isinstance(plan, Mapping) and isinstance(plan.get("args"), Mapping):
        out["plan"] = {**plan, "args": _lift(plan["args"])}
    if isinstance(row.get("result"), Mapping):
        out["result"] = _lift(row["result"])
    return out


def _action_rows(trace: Any) -> list[dict[str, Any]]:
    """The capability actions of a controller trace, in execution order."""
    if not isinstance(trace, list):
        return []
    rows = []
    for raw_row in trace:
        row = unwrap_bound_adapter_row(raw_row)
        if not isinstance(row, Mapping):
            continue
        plan = row.get("plan")
        args = (plan or {}).get("args") if isinstance(plan, Mapping) else None
        if isinstance(args, Mapping) and args.get("capability_id"):
            result = row.get("result")
            rows.append({
                "args": dict(args),
                "result": dict(result) if isinstance(result, Mapping) else {},
            })
    return rows


def _trace_is_finished(trace: Any) -> bool:
    """The controller must have reached its finish row, not stopped mid-plan."""
    if not isinstance(trace, list) or not trace:
        return False
    last = trace[-1]
    if not isinstance(last, Mapping):
        return False
    result = last.get("result")
    return isinstance(result, Mapping) and result.get("type") == "finish"


def _plan_chain(compiled: Any) -> list[str]:
    """What the sentence asked for, in plan order, without absorbed clauses.

    A chained plan legitimately runs MORE steps than the sentence has clauses,
    because prerequisite producers are inserted. Those must not be counted as
    clause coverage, and absorbed subgoals must not be counted as extra steps.
    """
    if not isinstance(compiled, Mapping):
        return []
    parts = compiled.get("compiled_parts")
    chain: list[str] = []
    if isinstance(parts, list) and parts:
        for part in parts:
            if not isinstance(part, Mapping):
                continue
            if part.get("mode") == ABSORBED_MODE:
                continue
            cid = part.get("selected_capability")
            if isinstance(cid, dict):
                cid = cid.get("capability_id")
            if cid:
                chain.append(str(cid))
        return chain
    single = compiled.get("selected_capability")
    if isinstance(single, dict):
        single = single.get("capability_id")
    return [str(single)] if single else []


# --------------------------------------------------------------------------
# Independent re-inspectors. Each one opens the bytes and compares them with
# what the producer claimed. Returning ``(False, reason, {})`` refuses.
# --------------------------------------------------------------------------

def _inspect_pdf_extract_text(args, result, root):
    source = _inside(root, args.get("path"))
    if source is None or not source.is_file():
        return False, "PDF_SOURCE_ABSENT_FROM_DISK", {}
    try:
        import pypdf  # the capability's own declared substrate, re-used
    except Exception:
        return False, "PDF_REINSPECTION_SUBSTRATE_UNAVAILABLE", {}
    try:
        reader = pypdf.PdfReader(str(source))
        pages = len(reader.pages)
        text = "".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return False, "PDF_NOT_A_READABLE_PDF", {}
    if pages != result.get("pages_total"):
        return False, "PDF_PAGE_COUNT_MISMATCH", {
            "reopened_pages": pages, "claimed_pages": result.get("pages_total")}
    if _digest(text.encode("utf-8")) != result.get("text_sha256"):
        return False, "PDF_TEXT_SHA256_MISMATCH", {}
    return True, "", {
        "pages_reopened": pages,
        "text_bytes_reextracted": len(text.encode("utf-8")),
        "text_sha256_recomputed": True,
    }


def _inspect_python_source_audit(args, result, root):
    out = _inside(root, result.get("output_path") or args.get("output_path"))
    if out is None or not out.is_file():
        return False, "AUDIT_OUTPUT_ABSENT_FROM_DISK", {}
    data = _json(out)
    if not isinstance(data, dict):
        return False, "AUDIT_OUTPUT_NOT_A_JSON_OBJECT", {}
    files = data.get("files")
    if not isinstance(files, list):
        return False, "AUDIT_OUTPUT_HAS_NO_FILE_LEDGER", {}
    totals = data.get("totals")
    if not isinstance(totals, dict):
        return False, "AUDIT_OUTPUT_HAS_NO_TOTALS", {}
    if len(files) != result.get("file_count") or totals.get("files") != result.get("file_count"):
        return False, "AUDIT_FILE_COUNT_MISMATCH", {
            "ledger_files": len(files), "totals_files": totals.get("files"),
            "claimed": result.get("file_count")}
    if totals.get("classes") != result.get("class_count"):
        return False, "AUDIT_CLASS_COUNT_MISMATCH", {}
    if totals.get("functions") != result.get("function_count"):
        return False, "AUDIT_FUNCTION_COUNT_MISMATCH", {}
    if totals.get("distinct_imported_modules") != result.get("distinct_imported_module_count"):
        return False, "AUDIT_IMPORT_COUNT_MISMATCH", {}
    unparseable = data.get("unparseable")
    if not isinstance(unparseable, list) or len(unparseable) != result.get("unparseable_count"):
        return False, "AUDIT_UNPARSEABLE_COUNT_MISMATCH", {}
    # Every file in the ledger must really exist, with exactly those bytes.
    audited = 0
    for row in files:
        if not isinstance(row, Mapping):
            return False, "AUDIT_LEDGER_ROW_INVALID", {}
        path = _inside(root, row.get("path"))
        if path is None or not path.is_file():
            return False, "AUDIT_LEDGER_FILE_ABSENT_FROM_REPOSITORY", {}
        if row.get("sha256") and _digest(path.read_bytes()) != row["sha256"]:
            return False, "AUDIT_LEDGER_FILE_SHA256_MISMATCH", {}
        audited += 1
    return True, "", {"ledger_files_rehashed": audited,
                     "totals_reconciled": True}


def _inspect_archive_verify(args, result, root):
    archive = _inside(root, args.get("archive_path"))
    manifest = _inside(root, args.get("manifest_path"))
    if archive is None or not archive.is_file():
        return False, "ARCHIVE_ABSENT_FROM_DISK", {}
    if manifest is None or not manifest.is_file():
        return False, "MANIFEST_ABSENT_FROM_DISK", {}
    try:
        with tarfile.open(archive, "r:gz") as handle:
            members = sorted(handle.getnames())
    except (tarfile.TarError, OSError, EOFError):
        return False, "ARCHIVE_NOT_A_READABLE_GZIP_TAR", {}
    if members != sorted(result.get("members") or []):
        return False, "ARCHIVE_MEMBERS_MISMATCH", {
            "reopened": members, "claimed": sorted(result.get("members") or [])}
    if len(members) != result.get("member_count"):
        return False, "ARCHIVE_MEMBER_COUNT_MISMATCH", {}
    if not members:
        return False, "ARCHIVE_HAS_NO_MEMBERS", {}
    for name in members:
        member = _inside(root, name)
        if member is None or not member.is_file():
            return False, "ARCHIVE_MEMBER_ABSENT_FROM_REPOSITORY", {}
    declared = result.get("archive_path")
    if declared is not None and declared != args.get("archive_path"):
        return False, "ARCHIVE_RESULT_PATH_MISMATCH", {}
    return True, "", {"archive_reopened": True, "members_relisted": len(members),
                      "archive_sha256": _digest(archive.read_bytes())}


def _inspect_xlsx_create(args, result, root):
    out = _inside(root, result.get("output_path") or args.get("output_path"))
    if out is None or not out.is_file():
        return False, "XLSX_OUTPUT_ABSENT_FROM_DISK", {}
    blob = out.read_bytes()
    if len(blob) != result.get("output_bytes"):
        return False, "XLSX_OUTPUT_BYTE_COUNT_MISMATCH", {}
    try:
        package = zipfile.ZipFile(out)
        names = package.namelist()
        sheet = package.read("xl/worksheets/sheet1.xml").decode("utf-8")
    except (zipfile.BadZipFile, KeyError, OSError, UnicodeDecodeError):
        return False, "XLSX_NOT_A_READABLE_OOXML_PACKAGE", {}
    if "xl/workbook.xml" not in names:
        return False, "XLSX_PACKAGE_HAS_NO_WORKBOOK", {}
    rows = len(re.findall(r"<row[\s>]", sheet))
    # The producer reports data rows; the sheet also carries the header row.
    if rows != int(result.get("row_count") or 0) + 1:
        return False, "XLSX_ROW_COUNT_MISMATCH", {
            "sheet_rows": rows, "claimed_data_rows": result.get("row_count")}
    first_row = sheet.split("</row>")[0]
    cells = len(re.findall(r"<c[\s>]", first_row))
    if cells != result.get("column_count"):
        return False, "XLSX_COLUMN_COUNT_MISMATCH", {
            "sheet_columns": cells, "claimed": result.get("column_count")}
    return True, "", {"ooxml_package_reopened": True, "sheet_rows": rows,
                      "sheet_columns": cells}


def _inspect_docx_verify(args, result, root):
    import xml.etree.ElementTree as ET

    doc = _inside(root, args.get("path"))
    if doc is None or not doc.is_file():
        return False, "DOCX_ABSENT_FROM_DISK", {}
    try:
        package = zipfile.ZipFile(doc)
        xml_bytes = package.read("word/document.xml")
        body = ET.fromstring(xml_bytes).find(DOCX_NS + "body")
    except (zipfile.BadZipFile, KeyError, OSError, ET.ParseError):
        return False, "DOCX_NOT_A_READABLE_OOXML_PACKAGE", {}
    if body is None:
        return False, "DOCX_PACKAGE_HAS_NO_BODY", {}
    paragraphs = [
        "".join(node.text or "" for node in para.iter(DOCX_NS + "t"))
        for para in body.iter(DOCX_NS + "p")
    ]
    observed = result.get("observed_paragraphs")
    if not isinstance(observed, list):
        return False, "DOCX_OBSERVED_PARAGRAPHS_MISSING", {}
    for expected in observed:
        if expected not in paragraphs:
            return False, "DOCX_OBSERVED_PARAGRAPH_ABSENT_FROM_FILE", {}
    tables = [
        [["".join(node.text or "" for node in cell.iter(DOCX_NS + "t"))
          for cell in tr.iter(DOCX_NS + "tc")]
         for tr in table.iter(DOCX_NS + "tr")]
        for table in body.iter(DOCX_NS + "tbl")
    ]
    claimed_tables = result.get("observed_tables")
    if not isinstance(claimed_tables, list) or claimed_tables != tables:
        return False, "DOCX_OBSERVED_TABLE_MISMATCH", {}
    if result.get("verified") is not True:
        return False, "DOCX_VERIFY_STEP_NOT_VERIFIED", {}
    return True, "", {"ooxml_package_reopened": True,
                      "paragraphs_in_file": len(paragraphs),
                      "tables_reparsed": len(tables)}


def _inspect_candidates_enumerate(args, result, root):
    out = _inside(root, result.get("output_path") or args.get("output_path"))
    if out is None or not out.is_file():
        return False, "CANDIDATE_OUTPUT_ABSENT_FROM_DISK", {}
    data = _json(out)
    if not isinstance(data, dict) or not isinstance(data.get("candidates"), list):
        return False, "CANDIDATE_OUTPUT_NOT_A_JSON_CANDIDATE_LIST", {}
    candidates = data["candidates"]
    if len(candidates) != result.get("candidate_count"):
        return False, "CANDIDATE_COUNT_MISMATCH", {}
    if not candidates:
        return False, "CANDIDATE_LIST_IS_EMPTY", {}
    search_root = _inside(root, args.get("search_root"))
    pattern = args.get("glob")
    if search_root is None or not search_root.is_dir() or not isinstance(pattern, str):
        return False, "CANDIDATE_SEARCH_ROOT_INVALID", {}
    try:
        files = [p for p in search_root.glob(pattern) if p.is_file()]
    except (OSError, ValueError):
        return False, "CANDIDATE_SEARCH_GLOB_FAILED", {}
    if len(candidates) > len(files):
        return False, "CANDIDATE_COUNT_EXCEEDS_REPOSITORY_FILES", {
            "claimed": len(candidates), "files_matching_glob": len(files)}
    # Content, not names: every candidate must be a real file with those bytes.
    digests = {_digest(p.read_bytes()) for p in files}
    for cand in candidates:
        if not isinstance(cand, Mapping) or cand.get("sha256") not in digests:
            return False, "CANDIDATE_CONTENT_ABSENT_FROM_REPOSITORY", {}
    return True, "", {"candidates_content_reverified": len(candidates),
                      "files_matching_glob": len(files),
                      "enumeration_truncated": len(candidates) != len(files)}


def _inspect_relevance_rank(args, result, root):
    out = _inside(root, result.get("output_path") or args.get("output_path"))
    if out is None or not out.is_file():
        return False, "RANK_OUTPUT_ABSENT_FROM_DISK", {}
    data = _json(out)
    if not isinstance(data, dict) or not isinstance(data.get("ranked_candidates"), list):
        return False, "RANK_OUTPUT_NOT_A_JSON_RANKING", {}
    ranked = data["ranked_candidates"]
    if len(ranked) != result.get("candidate_count"):
        return False, "RANK_CANDIDATE_COUNT_MISMATCH", {}
    if not ranked:
        return False, "RANK_OUTPUT_IS_EMPTY", {}
    scores: list[float] = []
    indexes: list[int] = []
    for row in ranked:
        if not isinstance(row, Mapping):
            return False, "RANK_ROW_INVALID", {}
        score = row.get("lexical_relevance_score")
        index = row.get("original_index")
        if not isinstance(score, (int, float)) or not isinstance(index, int):
            return False, "RANK_ROW_MISSING_SCORE_OR_INDEX", {}
        scores.append(float(score))
        indexes.append(index)
    if any(scores[i] < scores[i + 1] for i in range(len(scores) - 1)):
        return False, "RANK_ORDER_NOT_MONOTONE_NON_INCREASING", {}
    if len(set(indexes)) != len(indexes) or min(indexes) < 0 \
            or max(indexes) >= len(ranked):
        return False, "RANK_ORIGINAL_INDEXES_INVALID", {}
    # The ranker must have scored the candidates the enumerator produced.
    upstream = _inside(root, args.get("input_path"))
    if upstream is None or not upstream.is_file():
        return False, "RANK_INPUT_ABSENT_FROM_DISK", {}
    source = _json(upstream)
    if not isinstance(source, dict) \
            or source.get("candidate_count") != result.get("candidate_count"):
        return False, "RANK_INPUT_CANDIDATE_COUNT_MISMATCH", {}
    return True, "", {"ranked_candidates_reparsed": len(ranked),
                      "ranking_monotone": True,
                      "upstream_candidate_count_reconciled": True}


def _inspect_decision_locate(args, result, root):
    out = _inside(root, result.get("output_path") or args.get("output_path"))
    if out is None or not out.is_file():
        return False, "DECISION_EVIDENCE_ABSENT_FROM_DISK", {}
    data = _json(out)
    if not isinstance(data, dict):
        return False, "DECISION_EVIDENCE_NOT_A_JSON_OBJECT", {}
    alternatives = data.get("alternatives")
    evidence = data.get("evidence")
    if not isinstance(alternatives, list) or len(alternatives) != result.get("alternative_count"):
        return False, "DECISION_ALTERNATIVE_COUNT_MISMATCH", {}
    if not isinstance(evidence, list) or len(evidence) != result.get("evidence_count"):
        return False, "DECISION_EVIDENCE_COUNT_MISMATCH", {}
    if not alternatives:
        return False, "DECISION_HAS_NO_ALTERNATIVES", {}
    # Every evidence row must be about an alternative the file actually lists.
    ids = _alternative_ids(alternatives)
    if len(ids) != len(alternatives):
        return False, "DECISION_ALTERNATIVE_IDS_NOT_DISTINCT", {}
    for row in evidence:
        if not isinstance(row, Mapping) or row.get("alternative") not in ids:
            return False, "DECISION_EVIDENCE_REFERENCES_UNKNOWN_ALTERNATIVE", {}
    return True, "", {"alternatives_reparsed": len(alternatives),
                      "evidence_reparsed": len(evidence),
                      "evidence_alternatives_reconciled": True,
                      "decision_id": data.get("decision_id")}


def _inspect_decision_synthesis(args, result, root):
    out = _inside(root, result.get("output_path") or args.get("output_path"))
    if out is None or not out.is_file():
        return False, "DECISION_SYNTHESIS_ABSENT_FROM_DISK", {}
    data = _json(out)
    if not isinstance(data, dict):
        return False, "DECISION_SYNTHESIS_NOT_A_JSON_OBJECT", {}
    upstream = _inside(root, args.get("input_path"))
    if upstream is None or not upstream.is_file():
        return False, "DECISION_SYNTHESIS_INPUT_ABSENT_FROM_DISK", {}
    # The synthesis must declare the digest of the evidence it really read.
    expected = _canonical_json_sha256(upstream)
    if expected is None or data.get("input_sha256") != expected:
        return False, "DECISION_SYNTHESIS_INPUT_SHA256_MISMATCH", {}
    source = _json(upstream)
    ids = _alternative_ids((source or {}).get("alternatives") if isinstance(source, dict) else None)
    chosen = result.get("selected_alternative")
    if not ids or chosen not in ids:
        return False, "DECISION_SELECTED_ALTERNATIVE_NOT_IN_EVIDENCE", {}
    if data.get("selected_alternative") != chosen:
        return False, "DECISION_SYNTHESIS_SELECTED_ALTERNATIVE_MISMATCH", {}
    return True, "", {"synthesis_reopened": True,
                      "input_sha256_recomputed": True,
                      "selected_alternative": chosen}


def _inspect_decision_verify(args, result, root):
    produced = _inside(root, args.get("result_path"))
    if produced is None or not produced.is_file():
        return False, "DECISION_VERIFY_RESULT_ABSENT_FROM_DISK", {}
    data = _json(produced)
    if not isinstance(data, dict):
        return False, "DECISION_VERIFY_RESULT_NOT_A_JSON_OBJECT", {}
    if data.get("decision_id") != result.get("decision_id"):
        return False, "DECISION_VERIFY_DECISION_ID_MISMATCH", {}
    if data.get("selected_alternative") != result.get("selected_alternative"):
        return False, "DECISION_VERIFY_SELECTED_ALTERNATIVE_MISMATCH", {}
    if result.get("producer_independent") is not True:
        return False, "DECISION_VERIFIER_NOT_PRODUCER_INDEPENDENT", {}
    return True, "", {"verified_artifact_reopened": True,
                      "decision_id_reconciled": result.get("decision_id")}


def _inspect_tar_gz_create_from_manifest(args, result, root):
    """Re-open an archive the machine claims it built from a manifest.

    The producer's own ``output_verified`` flag is not evidence, so this reads
    the manifest and every source file back off disk, re-opens the archive that
    was supposedly written, and compares the archived bytes with the bytes still
    on disk. A claim that does not survive being re-opened is refused.

    Acceptance for this capability was impossible before: the trace verifier
    refuses any capability it has no re-inspector for, and this one had none.
    That also made the R3 raw success adapter unreachable, because any accepted
    archive goal had to carry ``archive.verify.tar_gz.gnu`` alongside the
    create, so ``selected_plan`` was never the single create capability the
    adapter requires.
    """
    archive = _inside(root, result.get("output_path") or args.get("output_path"))
    if archive is None or not archive.is_file():
        return False, "ARCHIVE_ABSENT_FROM_DISK", {}
    data = archive.read_bytes()
    claimed_sha = result.get("output_sha256")
    if _digest(data) != claimed_sha:
        return False, "ARCHIVE_SHA256_MISMATCH", {
            "recomputed_sha256": _digest(data), "claimed_sha256": claimed_sha}
    claimed_bytes = result.get("output_bytes")
    if claimed_bytes is not None and len(data) != int(claimed_bytes):
        return False, "ARCHIVE_BYTE_LENGTH_MISMATCH", {
            "reopened_bytes": len(data), "claimed_bytes": claimed_bytes}

    manifest = _inside(root, args.get("manifest_path"))
    if manifest is None or not manifest.is_file():
        return False, "MANIFEST_ABSENT_FROM_DISK", {}

    members = result.get("members")
    if not isinstance(members, list) or not members:
        return False, "ARCHIVE_MEMBER_LIST_MISSING", {}
    members = [str(m) for m in members]
    claimed_sources = result.get("source_sha256")
    if not isinstance(claimed_sources, dict):
        return False, "ARCHIVE_SOURCE_DIGESTS_MISSING", {}

    try:
        import tarfile  # the capability's own declared substrate, re-used
    except Exception:
        return False, "ARCHIVE_REINSPECTION_SUBSTRATE_UNAVAILABLE", {}
    try:
        with tarfile.open(archive, "r:gz") as handle:
            found = [m.name for m in handle.getmembers() if m.isfile()]
            archived: dict[str, bytes] = {}
            for name in found:
                member = handle.getmember(name)
                streamed = handle.extractfile(member)
                if streamed is None:
                    return False, "ARCHIVE_MEMBER_UNREADABLE", {"member": name}
                archived[name] = streamed.read()
    except Exception:
        return False, "ARCHIVE_NOT_A_READABLE_GZIP_TAR", {}

    if sorted(found) != sorted(members):
        return False, "ARCHIVE_MEMBER_SET_MISMATCH", {
            "reopened_members": sorted(found), "claimed_members": sorted(members)}
    claimed_count = result.get("member_count")
    if claimed_count is not None and len(found) != int(claimed_count):
        return False, "ARCHIVE_MEMBER_COUNT_MISMATCH", {
            "reopened_count": len(found), "claimed_count": claimed_count}

    for name in found:
        on_disk = _inside(root, name)
        if on_disk is None or not on_disk.is_file():
            return False, "ARCHIVE_SOURCE_ABSENT_FROM_DISK", {"member": name}
        live_bytes = on_disk.read_bytes()
        if _digest(live_bytes) != str(claimed_sources.get(name) or ""):
            return False, "ARCHIVE_SOURCE_SHA256_MISMATCH", {"member": name}
        # The strongest check: the bytes inside the archive are the bytes on
        # disk now, not merely a digest the producer asserted.
        if archived[name] != live_bytes:
            return False, "ARCHIVE_CONTENT_DIFFERS_FROM_SOURCE", {"member": name}

    return True, "", {
        "archive_bytes_reopened": len(data),
        "archive_sha256_recomputed": True,
        "members_reopened": len(found),
        "manifest_reread_from_disk": True,
        "members_byte_compared_to_source": len(found),
    }


def _inspect_text_file_write(args: Mapping, result: Mapping, root: Path) -> tuple[bool, str, dict]:
    """Re-open the file and compare it to the text the REQUEST asked for.

    The producer already read the bytes back and set ``output_verified``, and its
    ``output_sha256`` is checked against the disk above.  Neither is acceptance:
    both only prove the file is what the writer wrote, not that it is what was
    asked for.  The expectation this step is held to is stated in the request
    itself -- ``args["content"]`` -- so that is what is re-derived here, from the
    bytes on disk, with no reference to anything the producer reported.

    This is the capability natural sentences actually reach ("Write the text X to
    the file Y"), and before it existed every composed execution that wrote a file
    was refused with NO_INDEPENDENT_REINSPECTION_FOR:text.file.write.
    """
    out = _inside(root, result.get("output_path") or args.get("output_path"))
    if out is None or not out.is_file():
        return False, "TEXT_OUTPUT_ABSENT_FROM_DISK", {}
    wanted = args.get("content")
    if not isinstance(wanted, str) or not wanted:
        # Nothing was asked for, so there is nothing to hold the bytes to.
        return False, "TEXT_REQUEST_STATES_NO_CONTENT_TO_CHECK", {}
    blob = out.read_bytes()
    try:
        written = blob.decode("utf-8")
    except UnicodeDecodeError:
        return False, "TEXT_OUTPUT_IS_NOT_VALID_UTF8", {"bytes": len(blob)}
    if written != wanted:
        return False, "TEXT_OUTPUT_DOES_NOT_MATCH_THE_REQUESTED_TEXT", {
            "bytes_on_disk": len(blob), "bytes_requested": len(wanted.encode("utf-8"))}
    if _digest(blob) != _digest(wanted.encode("utf-8")):
        return False, "TEXT_OUTPUT_DIGEST_MISMATCH", {}
    return True, "", {"file_reopened": True, "bytes": len(blob),
                      "matches_the_requested_text": True}


# Commands that cannot change anything when they are run again.  A re-inspection
# has to go back to the world rather than to the producer's own report, and for a
# command the only way back to the world is to run it -- which is safe for these
# and not safe for anything else, so everything else is refused rather than
# guessed at.  "cp", "mv", "rm", "mkdir", "touch", "tee" and "dd" are deliberately
# absent: re-running one of those is a second side effect, not a check.
# An address, optionally a substitution composed onto it, ending in `p`: the
# shapes are `3p`, `2,4p` and `3s/.*/\U&/p`.  sed composes an address with a
# command in one script, so "the third line in upper case" is a single command
# that still names a line -- and it prints nothing at all, exiting 0, when the
# line is not there.  Matching only `<addr>p` would have left that composed form
# free to certify silence, which is the defect this predicate exists to stop.
_SED_PRINT_OF_NAMED_LINES = re.compile(r"\d+(?:,\d+)?(?:s[|/#].*)?p\Z")
_TAIL_FROM_A_NAMED_LINE = re.compile(r"\+\d+\Z")


def _asked_to_print_named_lines(tokens: Any) -> bool:
    """True when the argv's whole job was to print lines the sentence named.

    `sed -n 10p` over a four-line file exits 0 having printed nothing.  The
    program reports success and produces no answer, because the line the sentence
    named is not in the file.  `sed -n 8,9p` and `tail -n +100` are the same
    shape.  Certifying such a run reports an exact semantic answer where the
    answer is silence -- measured: "Show the tenth line of X" over a four-line
    file was accepted with stdout "" and the file itself fingerprinted as the
    output, so the check that passed was a check of the file, not of the answer.

    Deliberately narrow.  A `cat` of an empty file also prints nothing and exits
    0, and there silence IS the answer, so `cat` is not named here.  A `grep -v`
    that matches nothing also prints nothing, but it exits 1 -- the program
    itself says "nothing matched", which is an answer -- and the exit code is
    what separates the two.
    """
    parts = [str(part) for part in (tokens or [])]
    if not parts:
        return False
    if parts[0] == "sed":
        return any(_SED_PRINT_OF_NAMED_LINES.match(part) for part in parts[1:])
    if parts[0] == "tail":
        return any(_TAIL_FROM_A_NAMED_LINE.match(part) for part in parts[1:])
    return False

_READ_ONLY_COMMANDS = frozenset({
    "cat", "head", "tail", "wc", "nl", "sort", "grep", "egrep", "fgrep", "ls",
    "uniq", "tr", "cut", "sha256sum", "md5sum", "stat", "file", "diff", "cmp",
    "od", "tac", "basename", "dirname", "realpath",
    # `find` only ever reads the tree and prints what is there, so the inspector
    # can re-run it and compare stdout exactly as it does for ls.  `du` reads a
    # tree too, but no sentence reaches it, and a command the acceptance layer is
    # willing to judge that nothing can ask for is dead weight in this table.
    "find",
    # `sed` WITHOUT -i reads a file and writes nothing: the transformed text
    # comes back on stdout.  That makes it a reader as far as this table is
    # concerned, and the inspector re-runs it and compares stdout, stderr and
    # the return code exactly as it does for cat.  Whether the result is then
    # put somewhere is the caller's declaration, not the program's behaviour.
    "sed",
})
# Programs whose whole purpose is to hand back a rewritten copy of the file they
# read.  Only these may write over their own operand, and only because the
# adapter captures stdout in full BEFORE it writes, so there is no read-after-
# truncate race.  For any other program the bound output being an operand means
# the command is about to remove or replace it -- `rm A` -- and writing stdout
# there would resurrect the file.
_IN_PLACE_TRANSFORMS = frozenset({"sed"})
# A reader with an output flag is not a reader.  "sort -o FILE" writes FILE.
_SIDE_EFFECTING_FLAGS = ("-o", "--output")
# Flags that make ONE program write, and only that program.  `-i` is sed's
# in-place flag; for grep the same two characters mean ignore-case, so `-i`
# cannot join the shared tuple above without refusing a perfectly read-only
# search.  `sed` is in _READ_ONLY_COMMANDS because `sed -e s|a|b| FILE` reads a
# file and writes nothing -- but `sed -i` rewrites it in place, and re-running
# that is a second side effect, not a check.
_SIDE_EFFECTING_FLAGS_BY_PROGRAM = {"sed": ("-i", "--in-place")}


# --- postconditions for commands that change something ---------------------
# A mutating command cannot be checked by running it again, and the temptation is
# to fall back on its returncode -- which is the producer grading its own work.
# What is actually available is the world afterwards.  "cp A B" makes a promise
# about B that the file system can be asked about directly, and so can "mkdir",
# "touch" and "mv".  Each check below derives the promised end state from the
# argv -- which is already grounded in the sentence -- and then asks the disk,
# with no reference to anything the producer reported.
#
# Every one of these can fail, which is the whole point: a cp whose destination
# is missing, or whose bytes differ from the source, is refused.  Commands whose
# promise cannot be stated this precisely are absent and stay refused.
def _post_cp(tokens: list[str], root: Path) -> tuple[bool, str, dict]:
    # `cp -r A B` carries a flag, so the shape is no longer three tokens.  The
    # operands are the tokens that are not the recursive flag, and a tree promise
    # is only stateable when the flag is actually there: without it `cp` on a
    # directory is an error, and claiming a copied tree would be a lie.
    _recursive = ("-r", "-R", "-a", "--recursive")
    _flags = [t for t in tokens[1:] if t in _recursive]
    operands = [t for t in tokens[1:] if t not in _recursive]
    if len(operands) != 2 or len(_flags) + len(operands) != len(tokens) - 1:
        return False, "COMMAND_CP_PROMISE_UNSTATEABLE_FOR_THIS_SHAPE", {"argv_tokens": len(tokens)}
    src = _inside(root, operands[0])
    dst = _inside(root, operands[1])
    if src is None or dst is None:
        return False, "COMMAND_CP_PATH_OUTSIDE_REPOSITORY", {}
    if src.is_dir() or dst.is_dir():
        # `cp -r A B` copies a tree, and a promise about a tree is just as
        # stateable as a promise about a file: every path under the source must
        # exist under the destination with the same bytes, and the destination
        # must hold nothing the source did not have.  Both directions matter --
        # a copy that silently dropped a file is the failure this exists to
        # catch, and one that added a file is a copy of something else.
        if not _flags:
            return False, "COMMAND_CP_TREE_PROMISE_NEEDS_A_RECURSIVE_FLAG", {}
        if not src.is_dir():
            return False, "COMMAND_CP_SOURCE_ABSENT_FROM_DISK", {}
        if not dst.is_dir():
            return False, "COMMAND_CP_DESTINATION_ABSENT_FROM_DISK", {}
        rel_src = sorted(str(p.relative_to(src)) for p in src.rglob("*") if p.is_file())
        rel_dst = sorted(str(p.relative_to(dst)) for p in dst.rglob("*") if p.is_file())
        if rel_src != rel_dst:
            return False, "COMMAND_CP_TREE_DIFFERS_FROM_SOURCE", {
                "source_files": len(rel_src), "destination_files": len(rel_dst),
                "missing": rel_src[:4], "unexpected": rel_dst[:4]}
        total = 0
        for rel in rel_src:
            a = (src / rel).read_bytes(); b = (dst / rel).read_bytes()
            if _digest(a) != _digest(b):
                return False, "COMMAND_CP_DESTINATION_DIFFERS_FROM_SOURCE", {
                    "path": rel, "source_bytes": len(a), "destination_bytes": len(b)}
            total += len(b)
        return True, "", {"postcondition_checked": "cp", "bytes_compared": total,
                          "files_compared": len(rel_src),
                          "destination_matches_source": True}
    if not src.is_file():
        return False, "COMMAND_CP_SOURCE_ABSENT_FROM_DISK", {}
    if not dst.is_file():
        return False, "COMMAND_CP_DESTINATION_ABSENT_FROM_DISK", {}
    a, b = src.read_bytes(), dst.read_bytes()
    if _digest(a) != _digest(b):
        return False, "COMMAND_CP_DESTINATION_DIFFERS_FROM_SOURCE", {
            "source_bytes": len(a), "destination_bytes": len(b)}
    return True, "", {"postcondition_checked": "cp", "bytes_compared": len(b),
                      "destination_matches_source": True}


def _post_mv(tokens: list[str], root: Path) -> tuple[bool, str, dict]:
    if len(tokens) != 3:
        return False, "COMMAND_MV_PROMISE_UNSTATEABLE_FOR_THIS_SHAPE", {"argv_tokens": len(tokens)}
    src = _inside(root, tokens[1])
    dst = _inside(root, tokens[2])
    if src is None or dst is None:
        return False, "COMMAND_MV_PATH_OUTSIDE_REPOSITORY", {}
    if dst.is_dir():
        # `mv A D` where D is a directory does not make D the file -- it puts A
        # at D/<A's own name>.  Measured, refusing this shape reported
        # COMMAND_MV_DESTINATION_ABSENT_FROM_DISK over a move that had happened,
        # which is a report denying work that did occur.  The promise is still
        # exact and still asked of the disk: the named file is now inside the
        # named directory under the name it already had.
        moved = dst / Path(str(tokens[1])).name
        if not moved.is_file():
            return False, "COMMAND_MV_DESTINATION_ABSENT_FROM_DISK", {
                "expected_inside_directory": str(moved)}
    elif not dst.is_file():
        return False, "COMMAND_MV_DESTINATION_ABSENT_FROM_DISK", {}
    if src.exists():
        return False, "COMMAND_MV_SOURCE_STILL_PRESENT", {}
    return True, "", {"postcondition_checked": "mv", "destination_present": True,
                      "source_removed": True, "consumed_paths": [tokens[1]]}


def _post_mkdir(tokens: list[str], root: Path) -> tuple[bool, str, dict]:
    # `mkdir A B` is not a guess about anything: the sentence named both
    # directories, and the promise generalises exactly -- every one of them
    # exists.  This is deliberately NOT extended to `rm`, where a path the
    # sentence mentioned in passing would be deleted, and not to flags or globs,
    # where the operand set is not stated at all.
    targets = tokens[1:]
    if not targets:
        return False, "COMMAND_MKDIR_PROMISE_UNSTATEABLE_FOR_THIS_SHAPE", {"argv_tokens": len(tokens)}
    for raw in targets:
        target = _inside(root, raw)
        if target is None:
            return False, "COMMAND_MKDIR_PATH_OUTSIDE_REPOSITORY", {"path": raw}
        if not target.is_dir():
            return False, "COMMAND_MKDIR_DIRECTORY_ABSENT_FROM_DISK", {"path": raw}
    return True, "", {"postcondition_checked": "mkdir", "directory_present": True,
                      "directories_checked": len(targets)}


def _post_touch(tokens: list[str], root: Path) -> tuple[bool, str, dict]:
    if len(tokens) != 2:
        return False, "COMMAND_TOUCH_PROMISE_UNSTATEABLE_FOR_THIS_SHAPE", {"argv_tokens": len(tokens)}
    target = _inside(root, tokens[1])
    if target is None:
        return False, "COMMAND_TOUCH_PATH_OUTSIDE_REPOSITORY", {}
    if not target.exists():
        return False, "COMMAND_TOUCH_TARGET_ABSENT_FROM_DISK", {}
    return True, "", {"postcondition_checked": "touch", "target_present": True}


def _post_sort(tokens: list[str], root: Path) -> tuple[bool, str, dict]:
    """`sort -o B A` promises that B is A's lines, in order.

    This is the strongest postcondition in the table, and it needs no trust in
    anything the producer reported: the promised end state is recomputed from A,
    which is still on disk, and compared byte for byte with B.  A is not consumed
    by sort, so the oracle outlives the command.

    Scoped to exactly one shape -- `sort -o B A`, four tokens -- because that is
    the only shape whose promise can be stated without guessing.  `sort A` alone
    writes nothing and stays a reader; `sort -o B A C` merges several inputs and
    is refused as unstateable rather than approximated.

    Ordering is checked against BOTH the bytewise order and the locale's
    collation order, because which one `sort` applied depends on the environment
    it ran in and this check must not encode a fact about one host.  A file that
    matches neither is a real failure, not a locale artifact.
    """
    if len(tokens) != 4 or tokens[1] not in _SIDE_EFFECTING_FLAGS:
        return False, "COMMAND_SORT_PROMISE_UNSTATEABLE_FOR_THIS_SHAPE", {
            "argv_tokens": len(tokens)}
    dst = _inside(root, tokens[2])
    src = _inside(root, tokens[3])
    if src is None or dst is None:
        return False, "COMMAND_SORT_PATH_OUTSIDE_REPOSITORY", {}
    if not src.is_file():
        return False, "COMMAND_SORT_SOURCE_ABSENT_FROM_DISK", {}
    if not dst.is_file():
        return False, "COMMAND_SORT_DESTINATION_ABSENT_FROM_DISK", {}
    raw = src.read_bytes()
    lines = raw.splitlines(keepends=True)
    candidates = [b"".join(sorted(lines))]
    try:
        import locale as _locale

        collated = b"".join(sorted(lines, key=_locale.strxfrm))
        if collated not in candidates:
            candidates.append(collated)
    except Exception:  # noqa: BLE001 - no collation available, bytes still are
        pass
    got = dst.read_bytes()
    if got not in candidates:
        return False, "COMMAND_SORT_DESTINATION_IS_NOT_THE_SOURCE_IN_ORDER", {
            "source_bytes": len(raw), "destination_bytes": len(got)}
    return True, "", {"postcondition_checked": "sort", "lines_compared": len(lines),
                      "destination_matches_sorted_source": True}


# Keyed by program name.  Anything absent is refused by the caller rather than
# passed, so widening this table is a deliberate act with a test attached.
def _post_gzip(tokens: list[str], root: Path) -> tuple[bool, str, dict]:
    """`gzip A` promises three things, and all three are checkable now.

    A is gone; A.gz is there in its place; and A.gz is a COMPLETE gzip stream, so
    the content is recoverable rather than merely renamed.  The third is the one
    that makes the promise honest -- a truncated or corrupt archive satisfies the
    first two and still destroyed the file.  Decompressing it here reads the
    whole stream, which checks the stored CRC and length, using the standard
    library rather than shelling out to a second program.

    Scoped to a program and one plain operand: a flag such as `-k` changes what
    survives, so it is refused as unstateable rather than guessed at.
    """
    if len(tokens) != 2 or str(tokens[1]).startswith("-"):
        return False, "COMMAND_GZIP_PROMISE_UNSTATEABLE_FOR_THIS_SHAPE", {"argv_tokens": len(tokens)}
    source = _inside(root, tokens[1])
    if source is None:
        return False, "COMMAND_GZIP_PATH_OUTSIDE_REPOSITORY", {}
    if source.exists():
        return False, "COMMAND_GZIP_SOURCE_STILL_PRESENT", {}
    archive = source.with_name(source.name + ".gz")
    if not archive.is_file():
        return False, "COMMAND_GZIP_ARCHIVE_ABSENT_FROM_DISK", {"expected": str(archive)}
    try:
        import gzip as _gzip
        with _gzip.open(archive, "rb") as handle:
            recovered = handle.read()
    except Exception as exc:  # noqa: BLE001 - a corrupt stream is data, not a crash
        return False, "COMMAND_GZIP_ARCHIVE_NOT_A_COMPLETE_STREAM", {"error": str(exc)[:160]}
    return True, "", {"postcondition_checked": "gzip", "source_replaced_by_archive": True,
                      "archive": str(archive), "recoverable_bytes": len(recovered),
                      "consumed_paths": [tokens[1]]}


def _post_rm(tokens: list[str], root: Path) -> tuple[bool, str, dict]:
    """`rm A` promises exactly one thing about the world: A is gone.

    Scoped to the one shape whose promise can be stated precisely -- a program
    and one or more plain operands, no flags.  `rm -r` and `rm -f a b` are still
    refused as unstateable rather than guessed at, which is the same discipline
    that keeps dd, chmod, ln and sed out of this table.  Multiple operands are
    stateable and are all checked: the sentence that named them named a set.

    That the file EXISTED is not assumed and does not need to be witnessed: the
    adapter raises CLI_COMMAND_FAILED on a non-zero exit, and rm exits non-zero on
    a path that was not there.  A zero exit plus an absent path is the whole of
    the promise, and both halves are checkable now.
    """
    # The recursive flag is allowed and nothing else is.  It changes only
    # WHETHER a directory may be removed, not WHAT is promised: the operand is
    # gone.  Measured without it, "Delete the directory D" bound `rm D`, the
    # command failed on a directory that was not empty, and the report said
    # COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN -- the shape that says least about
    # what happened.  Every other flag stays unstateable, because `-f` in
    # particular would let a path that never existed count as a deletion.
    _operands: list[str] = []
    for _tok in tokens[1:]:
        _tok = str(_tok)
        if _tok in _RM_RECURSIVE_FLAGS:
            continue
        if _tok.startswith("-"):
            # Any other flag and the promise is no longer stateable from the
            # argv alone.  `-f` above all: it suppresses the very error that
            # would show a named path was never there.
            return False, "COMMAND_RM_PROMISE_UNSTATEABLE_FOR_THIS_SHAPE", {
                "argv_tokens": len(tokens), "flag": _tok}
        _operands.append(_tok)
    if not _operands:
        return False, "COMMAND_RM_PROMISE_UNSTATEABLE_FOR_THIS_SHAPE", {"argv_tokens": len(tokens)}
    # Every operand, not just the first.  A sentence may name a set of files by
    # pattern, and the promise is about the whole set: one survivor out of five
    # is a deletion that did not happen, and reporting it as done would be a lie.
    consumed: list[str] = []
    for operand in _operands:
        target = _inside(root, str(operand))
        if target is None:
            return False, "COMMAND_RM_PATH_OUTSIDE_REPOSITORY", {}
        if target.exists():
            return False, "COMMAND_RM_TARGET_STILL_PRESENT", {"survivor": str(operand)}
        consumed.append(str(operand))
    return True, "", {"postcondition_checked": "rm", "target_removed": True,
                      "targets_removed": len(consumed), "consumed_paths": consumed}


# Commands whose verified postcondition accounts for a path it CONSUMED.  Kept
# beside the table and pinned to it by test: a command listed here must return
# consumed_paths from its postcondition, so the two cannot drift apart.  This is
# what lets a caller bind output_path to the operand a command removes and say so
# honestly, instead of the adapter guessing at the command's intent.
# `gzip A` consumes A the way `rm A` does: the operand is gone afterwards and
# what replaces it is judged by _post_gzip, which reads the archive back and
# checks the stored CRC rather than trusting that a file appeared.
_CONSUMES_AN_OPERAND = frozenset({"rm", "mv", "gzip"})


# Programs that report their ANSWER as an exit status rather than as a failure.
#
# `diff` exits 1 when the files differ -- that is the whole of what anyone asks
# it, and it is not an error.  Exit 2 is "trouble", and it is deliberately absent
# here, so a genuine failure still fails.  The set is closed and each code is
# listed individually: a program whose codes are not enumerated keeps the
# adapter's unconditional refusal.
#
# Nothing downstream has to trust the code.  diff and cmp are both in
# _READ_ONLY_COMMANDS, so _inspect_shell_command_run re-runs them and compares
# stdout, stderr AND the returncode against the world -- a code the command did
# not really return is caught by COMMAND_RETURN_CODE_NOT_REPRODUCED.  What this
# table changes is only whether the producer is allowed to report the fact at
# all instead of raising over it.
#
# `grep`, `egrep` and `fgrep` are here for the identical reason, and it was
# measured rather than inferred from the man page.  Their documented codes are
# 0 = a line was selected, 1 = no line was selected, 2 = an error, and the three
# were confirmed on this host:
#
#   grep 'apple'  -> 0     grep 'zzz'        -> 1     grep 'a' <missing file> -> 2
#   egrep 'a|b'   -> 0     egrep 'zzz'       -> 1
#   fgrep 'apple' -> 0     fgrep 'zzz'       -> 1
#
# Measured without them in the table, "Search the file a.txt for the exact text
# 'zzzz'" raised RuntimeError:CLI_COMMAND_FAILED and arrived as
# COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN -- a failure reported over a search that
# ran correctly and answered "nothing matches".  That is the most ordinary
# outcome a search has, and it was the one outcome reported as a crash.  Exit 2
# is deliberately absent, so a missing file or an unreadable pattern still fails.
#
# All three are in _READ_ONLY_COMMANDS, so the inspector re-runs them and
# compares stdout, stderr AND the returncode: a code the command did not really
# return is caught by COMMAND_RETURN_CODE_NOT_REPRODUCED, exactly as for diff.
_ANSWER_IS_THE_EXIT_STATUS = {
    "diff": frozenset({0, 1}),
    "cmp": frozenset({0, 1}),
    "grep": frozenset({0, 1}),
    "egrep": frozenset({0, 1}),
    "fgrep": frozenset({0, 1}),
}


def _post_tee(tokens: list[str], root: Path) -> tuple[bool, str, dict]:
    """`tee A` promises exactly one thing that does not depend on its input.

    tee opens its operand with O_CREAT|O_TRUNC, so A exists when tee returns --
    whatever was on stdin, including nothing at all.  That is the whole of the
    unconditional promise, and it is the same promise `touch` makes, so it is
    checked the same way.

    What is deliberately NOT claimed is that A is empty.  Emptiness follows from
    stdin being empty, and stdin is not part of the argv shape this is scoped to
    -- the adapter passes no stdin, but a postcondition that asserted a fact
    about a channel it never saw would be guessing.  The bytes themselves are
    already pinned elsewhere: the adapter fingerprints the file it wrote and the
    trace check compares every declared digest.

    Scoped to one program and one operand, no flags.  `tee -a A` appends and
    `tee A B` writes two files, and neither promise is stated by this shape, so
    both are refused rather than approximated -- the same discipline that keeps
    dd, chmod, ln and sed out of this table.
    """
    if len(tokens) != 2:
        return False, "COMMAND_TEE_PROMISE_UNSTATEABLE_FOR_THIS_SHAPE", {"argv_tokens": len(tokens)}
    target = _inside(root, tokens[1])
    if target is None:
        return False, "COMMAND_TEE_PATH_OUTSIDE_REPOSITORY", {}
    if not target.is_file():
        return False, "COMMAND_TEE_TARGET_ABSENT_FROM_DISK", {}
    return True, "", {"postcondition_checked": "tee", "target_present": True}


def _post_sed(tokens: list[str], root: Path) -> tuple[bool, str, dict]:
    """`sed -i '$a TEXT' A` promises that A's last line is TEXT.

    sed only reaches this table when it carries `-i`, because that flag is what
    makes it not re-runnable -- every reading form of sed (`sed -n 3p A`,
    `sed -e s|a|b| A`) still goes to the re-run check and is unaffected by this
    function existing.  So the shape scoped here is the only one that can arrive.

    The promise is deliberately the small one.  An append consumes the file's
    previous bytes into its own prefix, so unlike `_post_sort` there is no oracle
    left on disk to recompute the whole end state from.  What the argv states
    unconditionally is the line that was added and where it went, and that is
    what is asked of the disk -- the same discipline that keeps `_post_tee` from
    claiming a file is empty because stdin happened to be.

    Refused rather than approximated for every other sed shape, including a
    substitution: `s|a|b|` has no promise about the last line at all.
    """
    if (len(tokens) != 4 or tokens[1] not in ("--in-place",) + _SIDE_EFFECTING_FLAGS_BY_PROGRAM["sed"]
            or not tokens[2].startswith("$a ")):
        return False, "COMMAND_SED_PROMISE_UNSTATEABLE_FOR_THIS_SHAPE", {
            "argv_tokens": len(tokens)}
    target = _inside(root, tokens[3])
    if target is None:
        return False, "COMMAND_SED_PATH_OUTSIDE_REPOSITORY", {}
    if not target.is_file():
        return False, "COMMAND_SED_TARGET_ABSENT_FROM_DISK", {}
    lines = target.read_bytes().splitlines()
    if not lines:
        return False, "COMMAND_SED_APPENDED_LINE_ABSENT_FROM_DISK", {}
    if lines[-1].decode("utf-8", "replace") != tokens[2][3:]:
        return False, "COMMAND_SED_LAST_LINE_IS_NOT_THE_APPENDED_TEXT", {
            "last_line": lines[-1].decode("utf-8", "replace")[:80]}
    return True, "", {"postcondition_checked": "sed", "appended_line": tokens[2][3:]}


# `rm -r` only.  `-f` is deliberately absent: it suppresses the error that is
# the only evidence a named path was ever there, so a deletion of nothing would
# look exactly like a deletion of something.
_RM_RECURSIVE_FLAGS = ("-r", "-R", "--recursive")


_MUTATING_POSTCONDITIONS = {
    "sed": _post_sed,
    "cp": _post_cp,
    "mv": _post_mv,
    "mkdir": _post_mkdir,
    "touch": _post_touch,
    "rm": _post_rm,
    "gzip": _post_gzip,
    "tee": _post_tee,
    "sort": _post_sort,
}


def _inspect_shell_command_run(args: Mapping, result: Mapping, root: Path) -> tuple[bool, str, dict]:
    """Run the stated command again and compare what comes back.

    A command has no artifact of its own to re-open, so the temptation is to
    accept ``returncode == 0`` and the ``stdout`` the adapter reported.  That is
    exactly the shape of check PR #6118 showed to be worthless: it compares the
    record to the record.  What is available instead is the world -- the command
    can be run again, and if the world still says the same thing then the report
    was not invented.

    Re-running is only safe for a command that cannot change anything, so the
    set above is closed and everything outside it is refused with a named reason
    rather than passed.  That costs coverage -- "cp", "mv" and "rm" are not
    re-inspected here -- and the honest reading of that cost is in the ledger:
    this inspector reports what it checked, and a mutating command is reported as
    unchecked rather than as accepted.
    """
    argv = args.get("argv")
    if not isinstance(argv, (list, tuple)) or not argv:
        return False, "COMMAND_ARGV_ABSENT", {}
    tokens = [str(tok) for tok in argv]
    if any(not tok for tok in tokens):
        return False, "COMMAND_ARGV_HAS_AN_EMPTY_TOKEN", {}
    program = tokens[0].rsplit("/", 1)[-1]
    takes_output_flag = any(
        tok in _SIDE_EFFECTING_FLAGS or tok.startswith("--output=")
        for tok in tokens[1:]) or any(
        tok in _SIDE_EFFECTING_FLAGS_BY_PROGRAM.get(program, ())
        for tok in tokens[1:])
    # An interpreter is not read-only in general, and it is not being treated as
    # one here.  What is allowed is the one shape the receipt-backed rows all
    # have -- ["python3", "<a .py file inside this repository>"] -- which is
    # narrow enough to reason about: no arguments to smuggle anything through,
    # and a script whose source is in the tree being judged.
    if program in ("python3", "python") and len(tokens) == 2 and tokens[1].endswith(".py"):
        if _inside(root, tokens[1]) is None:
            return False, "COMMAND_SCRIPT_OUTSIDE_REPOSITORY", {}
    elif program not in _READ_ONLY_COMMANDS or takes_output_flag:
        # Not re-runnable -- but a command that changes something still makes a
        # promise about the world, and the world is still there to be asked.
        #
        # A reader carrying an output flag belongs here too, and always did: the
        # note on _SIDE_EFFECTING_FLAGS says plainly that "sort -o FILE" writes
        # FILE, so re-running it is a second side effect and not a check.  It
        # used to be refused outright below, which was correct while nothing
        # could state what such a command promises.  Now that _post_sort can --
        # recomputing the sorted bytes from the source, which sort leaves on
        # disk -- refusing it denies work that is fully checkable.
        #
        # Nothing else changes.  A command with an output flag and NO
        # postcondition falls to the same refusal it always got, so `grep -o`,
        # whose -o means only-matching and not output, is refused exactly as
        # before rather than being re-run.
        check = _MUTATING_POSTCONDITIONS.get(program)
        if check is not None:
            return check(tokens, root)
        return False, (
            "COMMAND_TAKES_AN_OUTPUT_FLAG" if takes_output_flag
            else "COMMAND_NOT_RE_RUNNABLE_WITHOUT_SIDE_EFFECTS"), {
            "program": program, "checked": False}
    if takes_output_flag:
        return False, "COMMAND_TAKES_AN_OUTPUT_FLAG", {"program": program}
    claimed_out = result.get("stdout")
    claimed_code = result.get("returncode")
    if not isinstance(claimed_out, str) or not isinstance(claimed_code, int):
        return False, "COMMAND_RESULT_CARRIES_NO_OUTPUT_TO_CHECK", {}
    try:
        proc = subprocess.run(tokens, cwd=root, capture_output=True, timeout=60)
    except Exception as exc:  # noqa: BLE001 - a failed re-run is a refusal, not a crash
        return False, "COMMAND_RE_RUN_RAISED:" + type(exc).__name__, {}
    if proc.returncode != claimed_code:
        return False, "COMMAND_RETURN_CODE_NOT_REPRODUCED", {
            "claimed": claimed_code, "re_run": proc.returncode}
    again = proc.stdout.decode("utf-8", "replace")
    if again != claimed_out:
        return False, "COMMAND_OUTPUT_NOT_REPRODUCED", {
            "claimed_bytes": len(claimed_out.encode("utf-8")),
            "re_run_bytes": len(again.encode("utf-8"))}
    again_err = proc.stderr.decode("utf-8", "replace")
    if again_err != str(result.get("stderr") or ""):
        return False, "COMMAND_STDERR_NOT_REPRODUCED", {}
    if not again and proc.returncode == 0 and _asked_to_print_named_lines(tokens):
        # Reproducible silence is still silence.  The re-run agrees that the
        # command printed nothing, which proves the nothing was real and proves
        # nothing about whether it answers the sentence -- and for a command
        # whose whole job was to print the lines the sentence named, it does not.
        return False, "COMMAND_PRINTED_NONE_OF_THE_LINES_THE_SENTENCE_NAMED", {
            "program": program, "returncode_reproduced": proc.returncode,
            "stdout_bytes_reproduced": 0}
    return True, "", {"command_re_run": True, "program": program,
                      "returncode_reproduced": proc.returncode,
                      "stdout_bytes_reproduced": len(again.encode("utf-8"))}


INSPECTORS: dict[str, Inspector] = {
    "pdf.extract.text.pypdf": _inspect_pdf_extract_text,
    "python.source.audit.ast": _inspect_python_source_audit,
    "archive.verify.tar_gz.gnu": _inspect_archive_verify,
    "archive.tar_gz.create_from_manifest": _inspect_tar_gz_create_from_manifest,
    "xlsx.table.create_from_json_records": _inspect_xlsx_create,
    "docx.document.verify.intent_ooxml": _inspect_docx_verify,
    "source.candidates.enumerate.stdlib": _inspect_candidates_enumerate,
    "source.objective_relevance.rank.bm25": _inspect_relevance_rank,
    "structured.decision_evidence.locate.stdlib": _inspect_decision_locate,
    "decision.synthesis.typed.stdlib": _inspect_decision_synthesis,
    "decision.synthesis.verify.stdlib": _inspect_decision_verify,
    "text.file.write": _inspect_text_file_write,
    "shell.command.run": _inspect_shell_command_run,
}


# Inspectors keyed on the adapter that ran the step, for the families where one
# runner serves many capability ids and the result shape is the same for all of
# them.  Narrow by design: one adapter, one inspector.
_ADAPTER_INSPECTORS: dict[str, Inspector] = {
    "bound_capability_cli": _inspect_shell_command_run,
}


def _consumed_downstream(rows: list[dict], index: int, root: Path) -> bool:
    """True when a later step reads what this step wrote.

    A prerequisite producer the sentence never mentioned is only legitimate if
    something downstream actually consumed its output. Otherwise the plan did
    work the sentence did not ask for and nothing used it.
    """
    produced: set[str] = set()
    for name in _PATH_ARGS:
        value = rows[index]["args"].get(name)
        if isinstance(value, str) and value.strip():
            produced.add(value)
    if not produced:
        return False
    for later in rows[index + 1:]:
        for name in _PATH_ARGS:
            value = later["args"].get(name)
            if isinstance(value, str) and value in produced:
                return True
    return False


def verify(
    *,
    goal: str,
    compiled_plan: Any = None,
    execution: Any = None,
    raw_contract: Mapping[str, Any],
    root: Path,
) -> dict[str, Any]:
    """Accept only after the contract, the plan, the trace and the bytes agree."""
    try:
        if not isinstance(goal, str) or not goal.strip():
            return _unresolved("RAW_GOAL_INVALID")
        if not isinstance(raw_contract, Mapping) or raw_contract.get("pass") is not True:
            return _unresolved("RAW_TASK_CONTRACT_NOT_VERIFIED")
        if raw_contract.get("task_sha256") != _digest(goal.encode("utf-8")):
            return _unresolved("RAW_GOAL_HASH_MISMATCH")
        acceptance_contract = raw_contract.get("acceptance_contract")
        if not isinstance(acceptance_contract, Mapping):
            return _unresolved("ACCEPTANCE_CONTRACT_MISSING")
        obligations = acceptance_contract.get("obligations")
        if not isinstance(obligations, list) or not obligations:
            return _unresolved("RAW_OBLIGATIONS_MISSING")
        ids = [o.get("obligation_id") for o in obligations if isinstance(o, Mapping)]
        if (
            len(ids) != len(obligations)
            or not all(isinstance(x, str) and x for x in ids)
            or len(set(ids)) != len(ids)
            or acceptance_contract.get("required_obligation_ids") != ids
            or any(
                o.get("task_sha256") != raw_contract["task_sha256"] for o in obligations
            )
        ):
            return _unresolved("RAW_OBLIGATION_BINDING_INVALID")

        if not _trace_is_finished(execution):
            return _unresolved("TRACE_DID_NOT_REACH_FINISH")
        rows = _action_rows(execution)
        if not rows:
            return _unresolved("TRACE_HAS_NO_CAPABILITY_ACTIONS")

        # --- the trace must be the plan the sentence compiled to -----------
        chain = _plan_chain(compiled_plan)
        if not chain:
            return _unresolved("COMPILED_PLAN_HAS_NO_SELECTED_CAPABILITY")
        executed = [r["args"].get("capability_id") for r in rows]
        missing = [cid for cid in chain if cid not in executed]
        if missing:
            return _unresolved("PLAN_CAPABILITY_ABSENT_FROM_TRACE",
                               missing_capabilities=missing)
        if executed[-1] != chain[-1]:
            return _unresolved("TRACE_DOES_NOT_END_WITH_THE_PLANS_LAST_CAPABILITY",
                               last_executed=executed[-1], planned_last=chain[-1])
        for index, cid in enumerate(executed):
            if cid in chain:
                continue
            if not _consumed_downstream(rows, index, root):
                return _unresolved("UNCONSUMED_STEP_THE_SENTENCE_DID_NOT_ASK_FOR",
                                   capability_id=cid)

        # --- every path must be real, every declared digest must match -----
        for row in rows:
            cid = row["args"].get("capability_id")
            consumed = _verified_consumed_paths(row["args"], root)
            for name in _PATH_ARGS:
                value = row["args"].get(name)
                if not isinstance(value, str) or not value.strip():
                    continue
                # A command that REMOVES a path names a path that is supposed to
                # be gone, and reporting it absent contradicts the sentence that
                # asked for the removal.  The skip is not assumed from the shape
                # of the argv: it is granted only when the command's own
                # postcondition -- the same table the inspector judges by --
                # verifies the removal and names this path as the one consumed.
                # An unverified absence still fails exactly as it did before.
                if value in consumed:
                    continue
                path = _inside(root, value)
                if path is None:
                    return _unresolved("STEP_PATH_OUTSIDE_REPOSITORY",
                                       capability_id=cid, argument=name)
                # "Absent from disk" is a claim about EXISTENCE, and is_file()
                # answers a different question as well: it is False for a
                # directory that is plainly there.  Measured on a8d35d7: mkdir
                # created its directory, solve() reported pass=True, and this
                # layer returned STEP_PATH_ABSENT_FROM_DISK -- a verifier
                # contradicting the disk in the same sentence the caller was
                # ignoring.  Whether a path must be a FILE is the capability's
                # own contract, and the adapter already enforces it
                # (CLI_EXPECTED_OUTPUT_MISSING, CLI_EXPECTED_OUTPUT_NOT_A_FILE);
                # this layer's job is whether the path is real.
                if not path.exists():
                    return _unresolved("STEP_PATH_ABSENT_FROM_DISK",
                                       capability_id=cid, argument=name)
            for name in _ROOT_ARGS:
                value = row["args"].get(name)
                if not isinstance(value, str) or not value.strip():
                    continue
                path = _inside(root, value) if value not in (".", "./") else root.resolve()
                if path is None or not path.is_dir():
                    return _unresolved("STEP_ROOT_INVALID",
                                       capability_id=cid, argument=name)
            # --- a text payload must be the text the sentence stated -------
            # The re-inspection below compares the file to this argument, so an
            # argument that the binder altered is verified against its own
            # alteration and passes.  Measured on 4d859af: "Write the text the
            # results are in the attachment to the file X" wrote "results are" to
            # X, the re-inspector compared the file to "results are", found them
            # equal, and returned RAW_GOAL_ACCEPTANCE_VERIFIED.  Eight such
            # requests were accepted that way and only one of the eight files
            # matched its sentence.  Comparing bytes to the argument proves the
            # writer did what the plan said; only the sentence can prove the plan
            # said what was asked.  Both are needed, and until now only the first
            # existed.
            # --- a command line must be the one the sentence stated ---------
            # An argv is a payload with teeth: it is executed, not written.  The
            # adapter pins cwd to the repository root, clamps the timeout and
            # raises on a non-zero exit, but none of that answers whether the
            # sentence asked for THIS command.  Re-derived here from the goal
            # rather than read from the binder, for the reason PR #6118
            # established: the binder is the thing under test.
            value = row["args"].get("argv")
            if isinstance(value, (list, tuple)) and value and _STATES_A_COMMAND(goal):
                tokens = [str(tok) for tok in value]
                if any(not tok or tok not in goal for tok in tokens):
                    return _unresolved("STEP_COMMAND_NOT_IN_THE_REQUEST",
                                       capability_id=cid, argument="argv",
                                       argv_token_count=len(tokens))
            for name in _TEXT_PAYLOAD_ARGS:
                value = row["args"].get(name)
                if not isinstance(value, str) or len(value.strip()) < 2:
                    continue
                if not _payload_runs_to_the_destination(goal, value.strip()):
                    return _unresolved("STEP_TEXT_PAYLOAD_NOT_IN_THE_REQUEST",
                                       capability_id=cid, argument=name,
                                       payload_bytes=len(value.encode("utf-8")))
            result = row["result"]
            # A producer that could not fingerprint its declared output is
            # refusing to vouch for it, and that normally ends the matter.  But a
            # command that REMOVED the output has nothing to fingerprint -- the
            # absence is the result -- and its producer says so honestly with
            # output_verified False and output_absent_after_run.  Treating that
            # honesty as failure would punish the one adapter that reported the
            # truth instead of inventing a digest.  The excuse is the same earned
            # one as the existence check: a verified postcondition accounted for
            # this exact path being gone.
            declared_output = str(row["args"].get("output_path") or "")
            if result.get("output_verified") is False and declared_output not in consumed:
                return _unresolved("STEP_OUTPUT_NOT_VERIFIED_BY_ITS_PRODUCER",
                                   capability_id=cid,
                                   producer_reason=result.get("reason"))
            if result.get("verified") is False:
                return _unresolved("STEP_NOT_VERIFIED_BY_ITS_PRODUCER",
                                   capability_id=cid,
                                   producer_reason=result.get("reason"))
            claimed = result.get("output_sha256") or result.get("sha256")
            output = result.get("output_path") or row["args"].get("output_path")
            if claimed and isinstance(output, str):
                path = _inside(root, output)
                if path is None or not path.is_file():
                    return _unresolved("DECLARED_OUTPUT_ABSENT_FROM_DISK",
                                       capability_id=cid)
                if _digest(path.read_bytes()) != claimed:
                    return _unresolved("DECLARED_OUTPUT_SHA256_MISMATCH",
                                       capability_id=cid)

        # --- independent re-inspection, or refusal -------------------------
        ledger = []
        for row in rows:
            cid = str(row["args"].get("capability_id"))
            inspector = INSPECTORS.get(cid)
            if inspector is None:
                # Keyed on the adapter rather than the capability, because the
                # 294 receipt-backed rows all execute through one runner and all
                # report one result shape -- argv, returncode, stdout, stderr.
                # Measured: 221 of the 223 passing goals on the 367-prose corpus
                # were stopped by NO_INDEPENDENT_REINSPECTION_FOR naming one of
                # those rows, and 14 of 14 sampled scripts returned a byte-
                # identical returncode and stdout on a second run with no change
                # to the working tree, so the world does answer for them.
                adapter = str((row["result"] or {}).get("adapter") or "")
                inspector = _ADAPTER_INSPECTORS.get(adapter)
            if inspector is None:
                return _unresolved("NO_INDEPENDENT_REINSPECTION_FOR:" + cid)
            ok, reason, evidence = inspector(row["args"], row["result"], root)
            if not ok:
                return _unresolved(reason, capability_id=cid)
            ledger.append({"capability_id": cid, "reinspection": evidence})

        return {
            "schema": SCHEMA,
            "status": "RAW_GOAL_ACCEPTANCE_VERIFIED",
            "pass": True,
            "semantic_acceptance_complete": True,
            "terminal_authority": False,
            # An acceptance that does not say which goal and which contract it
            # judged cannot be bound to the run that produced it. Both values
            # are already in hand and the goal hash is already checked against
            # the contract above, so recording them adds no new trust -- it
            # makes the record self-identifying, which is what lets downstream
            # learning tie a retained success to this exact acceptance.
            "goal_sha256": _digest(goal.encode("utf-8")),
            "task_contract_sha256": raw_contract.get("task_contract_sha256"),
            "accepted_obligation_ids": list(ids),
            "verified_capability_chain": executed,
            "planned_capability_chain": chain,
            "reinspection_ledger": ledger,
            "reinspected_step_count": len(ledger),
            "independent_reinspection": True,
            "model_dependency_count": 0,
            "incremental_spend_usd": 0,
        }
    except Exception as exc:  # fail closed on anything unexpected
        return _unresolved("ACCEPTANCE_VERIFIER_EXCEPTION:" + type(exc).__name__)
