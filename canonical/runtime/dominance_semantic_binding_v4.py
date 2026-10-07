from __future__ import annotations

import hashlib
from typing import Any, Mapping

from canonical.runtime import dominance_binding_v2 as bind


class SemanticBindingV4Error(ValueError):
    pass


def live_worlds(hypotheses: Any) -> list[dict[str, str]]:
    if not isinstance(hypotheses, list):
        raise SemanticBindingV4Error("HYPOTHESES_INVALID")

    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, raw in enumerate(hypotheses):
        if not isinstance(raw, Mapping):
            raise SemanticBindingV4Error(f"HYPOTHESIS_{index}_INVALID")

        hid = bind.token(raw.get("id"), f"HYPOTHESIS_{index}_ID")
        if hid in seen:
            raise SemanticBindingV4Error("HYPOTHESIS_ID_DUPLICATE:" + hid)
        seen.add(hid)

        plausible = raw.get("plausible")
        if not isinstance(plausible, bool):
            raise SemanticBindingV4Error(f"HYPOTHESIS_{index}_PLAUSIBLE_INVALID")

        semantic = bind.sha256_value(
            raw.get("semantic_sha256"), f"HYPOTHESIS_{index}_SEMANTIC_SHA256"
        )
        if not plausible:
            continue

        receipt = raw.get("definition_receipt")
        if not isinstance(receipt, Mapping):
            raise SemanticBindingV4Error(
                f"HYPOTHESIS_{index}_DEFINITION_RECEIPT_INVALID"
            )
        definition_path, definition_blob = bind.content_binding(
            receipt, f"HYPOTHESIS_{index}_DEFINITION_RECEIPT"
        )
        bind.same(
            receipt,
            "hypothesis_id",
            hid,
            f"HYPOTHESIS_{index}_DEFINITION_RECEIPT",
        )
        bind.same_sha256(
            receipt,
            "semantic_sha256",
            semantic,
            f"HYPOTHESIS_{index}_DEFINITION_RECEIPT",
        )
        bind.require_true(
            receipt,
            "independent_or_objective",
            f"HYPOTHESIS_{index}_DEFINITION_RECEIPT",
        )

        rows.append(
            {
                "id": hid,
                "semantic_sha256": semantic,
                "definition_path": definition_path,
                "definition_blob_sha": definition_blob,
            }
        )

    if not rows:
        raise SemanticBindingV4Error("NO_LIVE_HYPOTHESES")

    return sorted(
        rows,
        key=lambda row: (
            row["id"],
            row["semantic_sha256"],
            row["definition_blob_sha"],
            row["definition_path"],
        ),
    )


def live_world_digest(rows: list[Mapping[str, str]]) -> str:
    payload = b""
    for row in sorted(
        rows,
        key=lambda item: (
            str(item["id"]),
            str(item["semantic_sha256"]),
            str(item["definition_blob_sha"]),
        ),
    ):
        payload += (
            str(row["id"]).encode("utf-8")
            + b"\0"
            + str(row["semantic_sha256"]).encode("ascii")
            + b"\0"
            + str(row["definition_blob_sha"]).encode("ascii")
            + b"\0"
        )
    return hashlib.sha256(payload).hexdigest()


def v3_semantic_rows(rows: list[Mapping[str, str]]) -> list[tuple[str, str]]:
    return [
        (str(row["id"]), str(row["semantic_sha256"]))
        for row in rows
    ]


def world_by_id(rows: list[Mapping[str, str]]) -> dict[str, dict[str, str]]:
    return {str(row["id"]): dict(row) for row in rows}
