"""Source-structural binding for colon-introduced directive lists.

The binder recognizes a bounded pattern:
  explicit imperative directive ending in ':' followed by one or more contiguous
  bullet/numbered lines.

It binds each child item to the parent directive by exact source spans. Child
content remains opaque. It does not infer list meaning, nesting semantics,
completeness beyond the contiguous marked block, or P2 membership.
"""
from __future__ import annotations

import re
from typing import Any

from canonical.runtime.bounded_task_directive_semantics_v1 import ACTION_VERBS

SCHEMA = "BRAIN_BOUNDED_TASK_LIST_CONTINUATION_V1"
_HEAD = re.compile(r"^(?P<prefix>\s*(?:[-*•]\s*|\d+[.)]\s*)?(?:please\s+)?)(?P<verb>[A-Za-z][A-Za-z-]*)\b(?P<tail>.*)$", re.I)
_CHILD = re.compile(r"^(?P<leading>\s*)(?P<marker>(?:[-*•]{1,3}|\d+[.)]))\s*(?P<item>\S.*)$")


def bind_continuations(source_text: str) -> dict[str, Any]:
    if not isinstance(source_text, str) or not source_text.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["SOURCE_TEXT_MISSING"], "terminal_authority": False}

    lines = source_text.splitlines(keepends=True)
    offsets = []
    pos = 0
    for line in lines:
        offsets.append(pos)
        pos += len(line)

    blocks = []
    for i, line_raw in enumerate(lines):
        line = line_raw.rstrip("\r\n")
        hm = _HEAD.match(line)
        if not hm:
            continue
        verb = hm.group("verb").lower()
        tail = hm.group("tail").strip()
        if verb not in ACTION_VERBS or not tail.endswith(":") or ";" in tail:
            continue

        parent_start = offsets[i] + len(line) - len(line.lstrip())
        verb_start = offsets[i] + hm.start("verb")
        tail_start_local = hm.start("tail") + (len(hm.group("tail")) - len(hm.group("tail").lstrip()))
        tail_start = offsets[i] + tail_start_local
        parent = {
            "line_index": i,
            "action": verb,
            "action_span": [verb_start, verb_start + len(hm.group("verb"))],
            "continuation_label": tail,
            "continuation_label_span": [tail_start, tail_start + len(tail)],
            "parent_line_span": [parent_start, offsets[i] + len(line)],
        }

        children = []
        j = i + 1
        while j < len(lines):
            child_line = lines[j].rstrip("\r\n")
            if not child_line.strip():
                if children:
                    break
                j += 1
                continue
            cm = _CHILD.match(child_line)
            if not cm:
                break
            item = cm.group("item").strip()
            marker_start = offsets[j] + cm.start("marker")
            item_start = offsets[j] + cm.start("item")
            children.append({
                "line_index": j,
                "marker": cm.group("marker"),
                "marker_span": [marker_start, marker_start + len(cm.group("marker"))],
                "item": item,
                "item_span": [item_start, item_start + len(item)],
                "child_line_span": [offsets[j], offsets[j] + len(child_line)],
                "relation": "CONTIGUOUS_MARKED_CONTINUATION_ITEM_OF_DIRECTIVE",
                "item_semantics": "OPAQUE_SOURCE_BOUND",
            })
            j += 1

        if children:
            blocks.append({
                "parent": parent,
                "children": children,
                "captured_child_count": len(children),
                "structural_relation_only": True,
                "semantic_completeness_claim": False,
            })

    return {
        "schema": SCHEMA,
        "status": "BOUND" if blocks else "NO_BOUND_CONTINUATIONS",
        "block_count": len(blocks),
        "child_item_count": sum(len(x["children"]) for x in blocks),
        "blocks": blocks,
        "terminal_authority": False,
        "semantic_completeness_claim": False,
        "p2_membership_claim": False,
        "soundness_boundary": (
            "ONLY_CONTIGUOUS_SOURCE_MARKED_CHILD_LINES_AFTER_A_COLON_TERMINATED_BOUND_DIRECTIVE;"
            "CHILD_TEXT_REMAINS_OPAQUE_AND_NO_LIST_OR_TASK_COMPLETENESS_IS_INFERRED"
        ),
    }
