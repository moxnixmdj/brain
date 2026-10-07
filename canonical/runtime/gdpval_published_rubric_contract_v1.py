"""Fail-closed compiler for the published GDPval machine-readable rubric contract.

Purpose
-------
GDPval v2 publishes `rubric_json` for every public task.  This module turns that
published object into a content-addressed requirement set without pretending that
the rubric is the complete human pairwise-preference law and without silently
dropping unknown metadata.

This is a structural semantic asset.  It can prove:
* the exact published rubric rows were preserved losslessly;
* every row has a stable content identity;
* the published criterion IDs are unique;
* downstream policy/quality proofs can bind to exact criterion bytes.

It cannot prove:
* the rubric exhausts every requirement in the natural-language prompt;
* the rubric equals the full expert pairwise-preference evaluator;
* satisfying a criterion from its text is already implemented;
* GDPval, ABC, D-finality, or the terminal goal is closed.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Mapping

SCHEMA = "BRAIN_GDPVAL_PUBLISHED_RUBRIC_CONTRACT_V1"
MAX_BYTES = 8_000_000
MAX_ITEMS = 20_000
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,256}$")


class RubricContractError(ValueError):
    pass


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise RubricContractError("DUPLICATE_JSON_KEY:" + str(key))
        out[key] = value
    return out


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RubricContractError(label + "_INVALID")
    return value.strip()


def _optional_prompt_sha(value: str | None) -> str | None:
    if value is None:
        return None
    value = _token(value, "PROMPT_SHA256").lower()
    if not HEX64.fullmatch(value):
        raise RubricContractError("PROMPT_SHA256_INVALID")
    return value


def _score(value: Any, ordinal: int) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RubricContractError(f"SCORE_INVALID:{ordinal}")
    if value < 0:
        raise RubricContractError(f"SCORE_NEGATIVE:{ordinal}")
    if isinstance(value, float) and not value.is_integer():
        # Preserve non-integer public weights.  JSON NaN/Infinity is rejected
        # below by the finite check.
        if value != value or value in (float("inf"), float("-inf")):
            raise RubricContractError(f"SCORE_NONFINITE:{ordinal}")
    return value


def _tags(value: Any, ordinal: int) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise RubricContractError(f"TAGS_INVALID:{ordinal}")
    out: list[str] = []
    for i, tag in enumerate(value):
        if not isinstance(tag, str) or not tag.strip():
            raise RubricContractError(f"TAG_INVALID:{ordinal}:{i}")
        out.append(tag.strip())
    return out


def compile_published_rubric(
    rubric_json: str | bytes,
    *,
    task_id: str,
    prompt_sha256: str | None = None,
) -> dict[str, Any]:
    """Compile one GDPval published rubric into a lossless requirement contract.

    The compiler is intentionally one-sided.  It authenticates and preserves the
    published rubric structure but does not infer that the rubric is semantically
    complete relative to the task prompt or expert pairwise preferences.
    """
    try:
        tid = _token(task_id, "TASK_ID")
        if not ID_RE.fullmatch(tid):
            raise RubricContractError("TASK_ID_FORMAT_INVALID")
        psha = _optional_prompt_sha(prompt_sha256)

        raw = rubric_json.encode("utf-8") if isinstance(rubric_json, str) else rubric_json
        if not isinstance(raw, bytes):
            raise RubricContractError("RUBRIC_MUST_BE_TEXT_OR_BYTES")
        if not raw:
            raise RubricContractError("RUBRIC_EMPTY")
        if len(raw) > MAX_BYTES:
            raise RubricContractError("RUBRIC_TOO_LARGE")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RubricContractError("RUBRIC_NOT_UTF8") from exc
        try:
            doc = json.loads(
                text,
                object_pairs_hook=_pairs,
                parse_constant=lambda x: (_ for _ in ()).throw(
                    RubricContractError("NONFINITE_JSON_NUMBER:" + x)
                ),
            )
        except RubricContractError:
            raise
        except Exception as exc:
            raise RubricContractError("RUBRIC_JSON_INVALID") from exc

        if not isinstance(doc, list) or not doc:
            raise RubricContractError("RUBRIC_MUST_BE_NONEMPTY_LIST")
        if len(doc) > MAX_ITEMS:
            raise RubricContractError("RUBRIC_ITEM_LIMIT_EXCEEDED")

        seen_ids: set[str] = set()
        requirements: list[dict[str, Any]] = []
        total_weight: int | float = 0

        for ordinal, row in enumerate(doc):
            if not isinstance(row, Mapping):
                raise RubricContractError(f"RUBRIC_ROW_NOT_OBJECT:{ordinal}")

            criterion = _token(row.get("criterion"), f"CRITERION:{ordinal}")
            item_id = _token(row.get("rubric_item_id"), f"RUBRIC_ITEM_ID:{ordinal}")
            if not ID_RE.fullmatch(item_id):
                raise RubricContractError(f"RUBRIC_ITEM_ID_FORMAT_INVALID:{ordinal}")
            if item_id in seen_ids:
                raise RubricContractError("RUBRIC_ITEM_ID_DUPLICATE:" + item_id)
            seen_ids.add(item_id)

            score = _score(row.get("score"), ordinal)
            total_weight += score

            author_type = _token(row.get("author_type"), f"AUTHOR_TYPE:{ordinal}")
            required = row.get("required")
            if required is not None and not isinstance(required, bool):
                raise RubricContractError(f"REQUIRED_FLAG_INVALID:{ordinal}")
            tags = _tags(row.get("tags"), ordinal)

            full_row = dict(row)
            row_sha = sha256(_canonical_bytes(full_row)).hexdigest()
            requirements.append(
                {
                    "ordinal": ordinal,
                    "rubric_item_id": item_id,
                    "score": score,
                    "criterion_text": criterion,
                    "required": required,
                    "author_type": author_type,
                    "tags": tags,
                    "published_row_sha256": row_sha,
                    # Keep the complete row so unmodeled metadata cannot vanish.
                    "published_row": full_row,
                }
            )

        parsed_sha = sha256(_canonical_bytes(doc)).hexdigest()
        raw_sha = sha256(raw).hexdigest()
        contract_material = {
            "schema": SCHEMA,
            "task_id": tid,
            "prompt_sha256": psha,
            "rubric_parsed_sha256": parsed_sha,
            "requirements": [
                {
                    "ordinal": r["ordinal"],
                    "rubric_item_id": r["rubric_item_id"],
                    "published_row_sha256": r["published_row_sha256"],
                }
                for r in requirements
            ],
        }
        contract_sha = sha256(_canonical_bytes(contract_material)).hexdigest()

        return {
            "schema": SCHEMA,
            "status": "PASS__LOSSLESS_PUBLISHED_RUBRIC_REQUIREMENT_SET",
            "pass": True,
            "task_id": tid,
            "prompt_sha256": psha,
            "rubric_raw_sha256": raw_sha,
            "rubric_parsed_sha256": parsed_sha,
            "contract_sha256": contract_sha,
            "criterion_count": len(requirements),
            "total_published_weight": total_weight,
            "requirements": requirements,
            "published_rubric_rows_losslessly_preserved": True,
            "published_criterion_id_set_complete_for_supplied_rubric": True,
            "unknown_published_row_metadata_dropped": False,
            "prompt_to_rubric_semantic_completeness_proved": False,
            "rubric_equals_full_human_pairwise_preference_law_proved": False,
            "criterion_satisfaction_implemented_by_this_compiler": False,
            "terminal_authority": False,
        }
    except RubricContractError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [str(exc)],
            "terminal_authority": False,
        }
