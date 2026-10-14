"""True-capability adapters for the DOCX span/transaction/story-part editors
(canonical/laws/TRUE_CAPABILITY_TEST_LAW_V1.md).

The editors are byte-pinned by governance records, so the pure adapters that
turn a described instance (base64 package + edit arguments) into a call on the
public function live here.  No editing logic is in this file.
"""
from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import docx_run_span_replace as _span
from canonical.runtime import docx_story_part_replace as _story
from canonical.runtime import docx_text_edit_transaction as _txn


def _finish(res: Mapping[str, Any], dst: Path) -> dict[str, Any]:
    out = {k: v for k, v in res.items() if k != "output_path"}
    out["output_docx_b64"] = base64.b64encode(dst.read_bytes()).decode("ascii") if (res.get("status") == "PASS" and dst.exists()) else None
    out["output_file_left_behind_on_failure"] = bool(res.get("status") != "PASS" and dst.exists())
    return out


def solve_span(instance: Mapping[str, Any]) -> dict[str, Any]:
    """DOCX_RUN_SPAN_REPLACE_V1: instance = {docx_b64, old, new}."""
    with tempfile.TemporaryDirectory() as td:
        src, dst = Path(td) / "in.docx", Path(td) / "out.docx"
        src.write_bytes(base64.b64decode(instance["docx_b64"]))
        return _finish(_span.replace_unique_paragraph_span(src, dst, old=instance["old"], new=instance["new"]), dst)


def solve_transaction(instance: Mapping[str, Any]) -> dict[str, Any]:
    """DOCX_TEXT_EDIT_TRANSACTION_V1: instance = {docx_b64, edits: [{old, new}, ...]}."""
    with tempfile.TemporaryDirectory() as td:
        src, dst = Path(td) / "in.docx", Path(td) / "out.docx"
        src.write_bytes(base64.b64decode(instance["docx_b64"]))
        edits = [_txn.TextEdit(old=e["old"], new=e["new"]) for e in instance["edits"]]
        return _finish(_txn.apply_text_edit_transaction(src, dst, edits=edits), dst)


def solve_story(instance: Mapping[str, Any]) -> dict[str, Any]:
    """DOCX_STORY_PART_REPLACE_V1: instance = {docx_b64, part_name, old, new}."""
    with tempfile.TemporaryDirectory() as td:
        src, dst = Path(td) / "in.docx", Path(td) / "out.docx"
        src.write_bytes(base64.b64decode(instance["docx_b64"]))
        return _finish(_story.replace_unique_story_part_span(src, dst, part_name=instance["part_name"], old=instance["old"], new=instance["new"]), dst)
