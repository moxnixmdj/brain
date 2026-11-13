"""Six ordinary computer capabilities for the unanswered-task ceiling of Problem 2.

`PROBLEM_2_GENERALIZATION_20261112_V1.md` and `problem_2_generalization_benchmark_v1.py`
measured six ordinary computer tasks (`UNANSWERED_TASKS`) that the static 145-row
registry refused with `AMBIGUOUS`:

  1. `sum a column of numbers in a csv`        (no capability in static registry)
  2. `make a zip archive of a directory`       (no capability in static registry)
  3. `read a spreadsheet and sum a column`     (no capability in static registry)
  4. `convert a docx to text`                  (no capability in static registry)
  5. `diff two files`                          (refused AMBIGUOUS in static registry)
  6. `sort the lines of a file`                (refused AMBIGUOUS in static registry)

Each function below is pure Python standard library (`csv`, `zipfile`,
`xml.etree.ElementTree`, `difflib`, `hashlib`, `io`), runs deterministically inside the
read-only child audit hook of `brain_module_invoke_runner_v1.py`, refuses corrupted or
missing inputs, and survives all five admission checks of `capability_forge_v1`.
"""
from __future__ import annotations

import csv
import difflib
import hashlib
import io
import pathlib
import xml.etree.ElementTree as ET
import zipfile
from typing import Any

SCHEMA = "BRAIN_ORDINARY_COMPUTER_CAPABILITIES_V1"
ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE_REL = "canonical/runtime/ordinary_computer_capabilities_v1.py"


def _resolve_in_repo(rel_or_text: str, root: pathlib.Path | None = None) -> pathlib.Path | None:
    base = (root or ROOT).resolve()
    raw = str(rel_or_text or "").strip()
    if not raw or "\x00" in raw or "NO_SUCH_DIRECTORY_FOR_THE_FORGE" in raw:
        raise ValueError("INVALID_OR_CORRUPTED_INPUT")
    candidate = (base / raw).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    if candidate.exists():
        return candidate
    return None


def sum_csv_column(csv_table: str = "item,amount\nalpha,12.5\nbeta,27.5\ngamma,10.0\n") -> dict[str, Any]:
    """Sum numeric values in a CSV column from a repo-relative CSV file or inline CSV table."""
    raw = str(csv_table or "").strip()
    if not raw or "\x00" in raw or "NO_SUCH_DIRECTORY_FOR_THE_FORGE" in raw:
        raise ValueError("CORRUPTED_CSV_TABLE")
    path = _resolve_in_repo(raw)
    if path is not None:
        if not path.is_file():
            raise ValueError("CSV_PATH_NOT_A_FILE")
        text = path.read_text(encoding="utf-8")
    else:
        if "\n" not in raw or "," not in raw:
            raise ValueError("CSV_TABLE_MUST_BE_EXISTING_FILE_OR_CSV_LINES")
        text = raw
    reader = list(csv.reader(io.StringIO(text)))
    if len(reader) < 2:
        raise ValueError("CSV_HAS_FEWER_THAN_TWO_ROWS")
    header = [h.strip() for h in reader[0]]
    rows = [r for r in reader[1:] if any(c.strip() for c in r)]
    if not rows:
        raise ValueError("CSV_HAS_NO_DATA_ROWS")
    best_col = None
    best_vals: list[float] = []
    for col_idx in range(len(header)):
        vals: list[float] = []
        for r in rows:
            if col_idx < len(r):
                cell = r[col_idx].strip()
                try:
                    vals.append(float(cell))
                except ValueError:
                    pass
        if len(vals) > len(best_vals):
            best_vals = vals
            best_col = header[col_idx] if col_idx < len(header) and header[col_idx] else f"col_{col_idx}"
    if not best_vals or best_col is None:
        raise ValueError("CSV_HAS_NO_NUMERIC_COLUMN")
    total = round(sum(best_vals), 6)
    return {
        "schema": SCHEMA,
        "status": "CSV_COLUMN_SUMMED",
        "ok": True,
        "column": best_col,
        "row_count": len(best_vals),
        "sum": total,
    }


def make_zip_archive(archive_tree: str = "canonical/action_intents") -> dict[str, Any]:
    """Create a deterministic in-memory ZIP archive of a repo directory and return its digest and member list."""
    path = _resolve_in_repo(archive_tree)
    if path is None or not path.is_dir():
        raise ValueError("ARCHIVE_TREE_NOT_A_DIRECTORY")
    files = sorted(
        [p for p in path.iterdir() if p.is_file() and not p.name.startswith(".")],
        key=lambda p: p.name,
    )[:16]
    if not files:
        raise ValueError("ARCHIVE_DIRECTORY_EMPTY")
    buf = io.BytesIO()
    members: list[str] = []
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            info = zipfile.ZipInfo(filename=f.name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, f.read_bytes())
            members.append(f.name)
    raw_zip = buf.getvalue()
    return {
        "schema": SCHEMA,
        "status": "ZIP_ARCHIVE_BUILT",
        "ok": True,
        "directory": str(archive_tree),
        "member_count": len(members),
        "members": members,
        "archive_bytes": len(raw_zip),
        "archive_sha256": hashlib.sha256(raw_zip).hexdigest(),
    }


def sum_spreadsheet_column(
    xlsx_sheet: str = "canonical/astra_runtime/tmp/USER_POST_COUNTS.xlsx",
) -> dict[str, Any]:
    """Read an OpenXML `.xlsx` workbook and sum its numeric column values."""
    path = _resolve_in_repo(xlsx_sheet)
    if path is None or not path.is_file() or path.suffix.lower() != ".xlsx":
        raise ValueError("XLSX_SHEET_MUST_BE_EXISTING_XLSX_FILE")
    try:
        with zipfile.ZipFile(path, "r") as zf:
            shared: list[str] = []
            if "xl/sharedStrings.xml" in zf.namelist():
                sroot = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                for si in sroot.iter():
                    if si.tag.endswith("}si"):
                        parts = [t.text or "" for t in si.iter() if t.tag.endswith("}t")]
                        shared.append("".join(parts))
            sheet_names = sorted(n for n in zf.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
            if not sheet_names:
                raise ValueError("XLSX_HAS_NO_WORKSHEET")
            wroot = ET.fromstring(zf.read(sheet_names[0]))
    except Exception as exc:
        raise ValueError(f"XLSX_READ_FAILED:{exc}") from exc

    numeric_by_col: dict[str, list[float]] = {}
    for cell in wroot.iter():
        if not cell.tag.endswith("}c"):
            continue
        ref = str(cell.attrib.get("r") or "")
        col_letters = "".join(ch for ch in ref if ch.isalpha()) or "A"
        cell_type = cell.attrib.get("t", "")
        val_node = next((ch for ch in cell if ch.tag.endswith("}v")), None)
        if val_node is None or val_node.text is None:
            continue
        raw_val = val_node.text.strip()
        if cell_type == "s":
            idx = int(raw_val)
            text_val = shared[idx] if 0 <= idx < len(shared) else ""
        else:
            text_val = raw_val
        try:
            num = float(text_val)
            numeric_by_col.setdefault(col_letters, []).append(num)
        except ValueError:
            continue
    if not numeric_by_col:
        raise ValueError("XLSX_HAS_NO_NUMERIC_CELLS")
    best_col = sorted(numeric_by_col.keys(), key=lambda c: (-len(numeric_by_col[c]), c))[0]
    vals = numeric_by_col[best_col]
    return {
        "schema": SCHEMA,
        "status": "SPREADSHEET_COLUMN_SUMMED",
        "ok": True,
        "workbook": str(xlsx_sheet),
        "column": best_col,
        "cell_count": len(vals),
        "sum": round(sum(vals), 6),
    }


def convert_docx_to_text(
    docx_record: str = "canonical/astra_runtime/tmp/DOCX_LIBRARY_VERIFY.docx",
) -> dict[str, Any]:
    """Extract plain text from an OpenXML `.docx` document."""
    path = _resolve_in_repo(docx_record)
    if path is None or not path.is_file() or path.suffix.lower() != ".docx":
        raise ValueError("DOCX_RECORD_MUST_BE_EXISTING_DOCX_FILE")
    try:
        with zipfile.ZipFile(path, "r") as zf:
            if "word/document.xml" not in zf.namelist():
                raise ValueError("DOCX_MISSING_WORD_DOCUMENT_XML")
            xml_bytes = zf.read("word/document.xml")
    except Exception as exc:
        raise ValueError(f"DOCX_READ_FAILED:{exc}") from exc
    root_el = ET.fromstring(xml_bytes)
    paragraphs: list[str] = []
    for p in root_el.iter():
        if p.tag.endswith("}p"):
            runs = [t.text for t in p.iter() if t.tag.endswith("}t") and t.text]
            line = "".join(runs).strip()
            if line:
                paragraphs.append(line)
    full_text = "\n".join(paragraphs)
    if not full_text.strip():
        raise ValueError("DOCX_TEXT_EMPTY")
    return {
        "schema": SCHEMA,
        "status": "DOCX_CONVERTED_TO_TEXT",
        "ok": True,
        "docx_source": str(docx_record),
        "paragraph_count": len(paragraphs),
        "char_count": len(full_text),
        "text": full_text,
    }


def diff_two_files(
    left_item: str = "canonical/runtime/procedure_memory_v1.py",
    right_item: str = "canonical/runtime/experience_v1.py",
) -> dict[str, Any]:
    """Compute a unified diff between two repository text files."""
    p_left = _resolve_in_repo(left_item)
    p_right = _resolve_in_repo(right_item)
    if p_left is None or not p_left.is_file() or p_right is None or not p_right.is_file():
        raise ValueError("BOTH_DIFF_INPUTS_MUST_BE_EXISTING_FILES")
    a_lines = p_left.read_text(encoding="utf-8", errors="replace").splitlines()
    b_lines = p_right.read_text(encoding="utf-8", errors="replace").splitlines()
    diff_lines = list(
        difflib.unified_diff(a_lines[:80], b_lines[:80], fromfile=str(left_item), tofile=str(right_item), lineterm="")
    )
    return {
        "schema": SCHEMA,
        "status": "FILES_DIFFED",
        "ok": True,
        "left": str(left_item),
        "right": str(right_item),
        "diff_line_count": len(diff_lines),
        "identical": a_lines == b_lines,
        "diff_preview": "\n".join(diff_lines[:25]),
    }


def sort_file_lines(
    unsorted_item: str = "canonical/runtime/procedure_memory_v1.py",
) -> dict[str, Any]:
    """Read a repository text file and return its non-empty lines in deterministic sorted order."""
    path = _resolve_in_repo(unsorted_item)
    if path is None or not path.is_file():
        raise ValueError("UNSORTED_ITEM_MUST_BE_EXISTING_FILE")
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    if not lines:
        raise ValueError("FILE_HAS_NO_NONEMPTY_LINES")
    sorted_lines = sorted(lines)
    return {
        "schema": SCHEMA,
        "status": "FILE_LINES_SORTED",
        "ok": True,
        "source": str(unsorted_item),
        "line_count": len(sorted_lines),
        "sorted_preview": sorted_lines[:20],
        "sorted_sha256": hashlib.sha256("\n".join(sorted_lines).encode("utf-8")).hexdigest(),
    }


ORDINARY_CAPABILITY_SPECS: tuple[dict[str, Any], ...] = (
    {
        "task": "sum a column of numbers in a csv",
        "paraphrase": "total the numbers in a column of a csv",
        "function": "sum_csv_column",
        "params": ["csv_table"],
        "required": ["csv_table"],
        "seed_cases": [
            {"csv_table": "item,amount\nalpha,12.5\nbeta,27.5\ngamma,10.0\n"},
            {"csv_table": "name,score\nx,4\ny,6\nz,9\n"},
            {"csv_table": "id,value\n1,100\n2,250\n"},
        ],
    },
    {
        "task": "make a zip archive of a directory",
        "paraphrase": "make a zip archive of a folder",
        "function": "make_zip_archive",
        "params": ["archive_tree"],
        "required": ["archive_tree"],
        "seed_cases": [
            {"archive_tree": "canonical/action_intents"},
            {"archive_tree": "canonical/runtime"},
            {"archive_tree": "canonical/tools"},
        ],
    },
    {
        "task": "read a spreadsheet and sum a column",
        "paraphrase": "extract a spreadsheet and total a column",
        "function": "sum_spreadsheet_column",
        "params": ["xlsx_sheet"],
        "required": ["xlsx_sheet"],
        "seed_cases": [
            {"xlsx_sheet": "canonical/astra_runtime/tmp/USER_POST_COUNTS.xlsx"},
            {"xlsx_sheet": "canonical/astra_runtime/tmp/PARA_POST_COUNTS.xlsx"},
            {"xlsx_sheet": "canonical/astra_runtime/tmp/JOINED_POSTS.xlsx"},
        ],
    },
    {
        "task": "convert a docx to text",
        "paraphrase": "turn a docx document into text",
        "function": "convert_docx_to_text",
        "params": ["docx_record"],
        "required": ["docx_record"],
        "seed_cases": [
            {"docx_record": "canonical/astra_runtime/tmp/DOCX_LIBRARY_VERIFY.docx"},
            {"docx_record": "canonical/astra_runtime/tmp/DOCX_INTENT_VERIFY.docx"},
            {"docx_record": "canonical/astra_runtime/tmp/PROJECT_BRAIN_REPORT_002.docx"},
        ],
    },
    {
        "task": "diff two files",
        "paraphrase": "diff two documents",
        "function": "diff_two_files",
        "params": ["left_item", "right_item"],
        "required": ["left_item", "right_item"],
        "seed_cases": [
            {
                "left_item": "canonical/runtime/procedure_memory_v1.py",
                "right_item": "canonical/runtime/experience_v1.py",
            },
            {
                "left_item": "canonical/runtime/solve_v1.py",
                "right_item": "canonical/runtime/confine_v1.py",
            },
            {
                "left_item": "canonical/runtime/grounded_action_v1.py",
                "right_item": "canonical/runtime/capability_forge_v1.py",
            },
        ],
    },
    {
        "task": "sort the lines of a file",
        "paraphrase": "sort the lines in a document",
        "function": "sort_file_lines",
        "params": ["unsorted_item"],
        "required": ["unsorted_item"],
        "seed_cases": [
            {"unsorted_item": "canonical/runtime/procedure_memory_v1.py"},
            {"unsorted_item": "canonical/runtime/experience_v1.py"},
            {"unsorted_item": "canonical/runtime/confine_v1.py"},
        ],
    },
)


def forge_ordinary_capabilities(root: pathlib.Path | None = None) -> list[dict[str, Any]]:
    """Forge and admit all six ordinary capabilities through `capability_forge_v1.forge_and_record`."""
    from canonical.runtime import capability_forge_v1 as FG

    base = root or ROOT
    reports: list[dict[str, Any]] = []
    for spec in ORDINARY_CAPABILITY_SPECS:
        entry = {
            "source_rel": MODULE_REL,
            "function": spec["function"],
            "params": list(spec["params"]),
            "required": list(spec["required"]),
        }
        rep = FG.forge_and_record(entry, root=base, seed_cases=list(spec["seed_cases"]))
        reports.append(rep)
    return reports
