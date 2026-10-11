"""Typed, fail-closed mutation compilers for AutomationBench API mode.

Inputs are public prompt text plus *observed facts* obtained through benchmark
tools. No hidden assertions or private task content are consumed.

Every compiler returns an api_fetch call only when all required values are
grounded. Otherwise it returns None.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_AUTOMATIONBENCH_MUTATION_COMPILER_V1"

_DATE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")


def _s(v: Any) -> str:
    return str(v or "").strip()


def _ci_get(m: Mapping[str, Any], *names: str) -> Any:
    lut = {str(k).lower(): v for k, v in m.items()}
    for name in names:
        if name.lower() in lut:
            return lut[name.lower()]
    return None


def _records(observations: Sequence[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def walk(x: Any) -> None:
        if isinstance(x, Mapping):
            d = dict(x)
            # Keep record-like dictionaries, then recursively inspect envelopes.
            if any(k.lower() in {"id","gid","name","subject","email","title"} for k in d):
                out.append(d)
            for v in d.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            try:
                walk(json.loads(x))
            except Exception:
                pass

    for obs in observations:
        walk(obs)
    return out


def _best_named_record(
    observations: Sequence[Any],
    *,
    name_terms: Sequence[str],
    id_prefix: str | None = None,
) -> dict[str, Any] | None:
    terms = [t.lower() for t in name_terms if t]
    best: tuple[int, dict[str, Any]] | None = None
    for rec in _records(observations):
        rid = _s(_ci_get(rec, "id", "Id", "gid"))
        if id_prefix and rid and not rid.startswith(id_prefix):
            continue
        hay = " ".join(_s(v) for v in rec.values()).lower()
        score = sum(3 for t in terms if t and t in hay)
        if rid:
            score += 1
        if best is None or score > best[0]:
            best = (score, rec)
    if best is None or best[0] <= 1:
        return None
    return best[1]


def compile_salesforce_mark_won(
    prompt: str,
    observations: Sequence[Any],
    *,
    endpoint_url_template: str = "https://yourinstance.salesforce.com/services/data/v61.0/sobjects/Opportunity/{id}",
) -> dict[str, Any] | None:
    low = prompt.lower()
    if "salesforce" not in low and "opportunit" not in low:
        return None
    if not any(p in low for p in ("mark it as won","mark as won","closed won","mark the opportunity as won")):
        return None

    # Use informative capitalized phrase fragments near opportunity/deal wording.
    candidates = re.findall(r"([A-Z][A-Za-z0-9& .'-]{2,80}(?:Deal|Opportunity|Contract))", prompt)
    source_phrases = candidates[:2] or [prompt]
    generic = {"we","just","closed","the","mark","it","as","won","in","salesforce","opportunity","deal","contract"}
    terms = [
        tok.lower()
        for phrase in source_phrases
        for tok in re.findall(r"[A-Za-z0-9&'-]+", phrase)
        if tok.lower() not in generic and len(tok) > 2
    ]
    rec = _best_named_record(observations, name_terms=terms, id_prefix="006")
    if rec is None:
        return None
    rid = _s(_ci_get(rec, "id", "Id"))
    if not rid:
        return None

    return {
        "schema": SCHEMA,
        "semantic": "SALESFORCE_OPPORTUNITY_MARK_WON",
        "tool": "api_fetch",
        "arguments": {
            "method": "PATCH",
            "url": endpoint_url_template.replace("{id}", rid),
            "body": json.dumps({"StageName": "Closed Won"}, sort_keys=True),
        },
        "grounding": {"record_id": rid, "stage": "Closed Won"},
    }


def compile_asana_create_task(
    prompt: str,
    source_record: Mapping[str, Any],
    *,
    endpoint_url: str = "https://app.asana.com/api/1.0/tasks",
) -> dict[str, Any] | None:
    low = prompt.lower()
    if "asana" not in low or not any(x in low for x in ("create","add")):
        return None

    text = " ".join(_s(source_record.get(k)) for k in ("body","body_plain","text","description","subject","title"))
    # Public tasks frequently encode authoritative source lines as:
    # Task/Create task: <name>. Due: YYYY-MM-DD. Tag: ...
    m_name = re.search(r"(?:create\s+task|task)\s*:\s*([^\n.]+)", text, re.I)
    m_due = _DATE.search(text)
    if not m_name or not m_due:
        return None

    body: dict[str, Any] = {
        "name": m_name.group(1).strip(),
        "due_on": m_due.group(0),
    }

    # Explicit workspace/project identifiers in the user request are grounded.
    ws = re.search(r"\b(?:workspace\s+)?(ws[_-][A-Za-z0-9_-]+)\b", prompt, re.I)
    project = re.search(r"\b(?:project\s+)?(proj[_-][A-Za-z0-9_-]+)\b", prompt, re.I)
    if project:
        body["projects"] = [project.group(1)]
    elif ws:
        body["workspace"] = ws.group(1)
    else:
        # Asana requires workspace when no project/parent is supplied.
        return None

    tag = re.search(r"\bTag\s*:\s*([^\n.]+)", text, re.I)
    return {
        "schema": SCHEMA,
        "semantic": "ASANA_TASK_CREATE",
        "tool": "api_fetch",
        "arguments": {
            "method": "POST",
            "url": endpoint_url,
            "body": json.dumps(body, sort_keys=True),
        },
        "grounding": {
            "name": body["name"],
            "due_on": body["due_on"],
            "tag_label_observed": tag.group(1).strip() if tag else None,
        },
    }


def compile_sheets_append(
    *,
    spreadsheet_id: str,
    range_a1: str,
    row_values: Sequence[Any],
    endpoint_url_template: str = "https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}/values/{range}:append",
) -> dict[str, Any] | None:
    if not _s(spreadsheet_id) or not _s(range_a1) or not row_values:
        return None
    if any(v is None for v in row_values):
        return None
    url = endpoint_url_template.replace("{spreadsheetId}", spreadsheet_id).replace("{range}", range_a1)
    body = {"range": range_a1, "majorDimension": "ROWS", "values": [list(row_values)]}
    return {
        "schema": SCHEMA,
        "semantic": "GOOGLE_SHEETS_APPEND_ROW",
        "tool": "api_fetch",
        "arguments": {
            "method": "POST",
            "url": url,
            "body": json.dumps(body, sort_keys=True),
        },
        "grounding": {
            "spreadsheet_id": spreadsheet_id,
            "range": range_a1,
            "cell_count": len(row_values),
        },
    }


def validate_nonnegative_action(prompt: str, action: Mapping[str, Any]) -> bool:
    """Reject obvious prompt-level negative constraints against an action.

    This is intentionally conservative and supplements, rather than replaces,
    record-specific policy screening.
    """
    low = prompt.lower()
    semantic = _s(action.get("semantic")).lower()
    if any(x in low for x in ("do not create", "don't create", "must not create")) and "create" in semantic:
        return False
    if any(x in low for x in ("do not update", "don't update", "must not update")) and ("update" in semantic or "mark_won" in semantic):
        return False
    if any(x in low for x in ("do not append", "don't append", "must not append")) and "append" in semantic:
        return False
    return True


def compile_asana_add_to_section(
    prompt: str,
    observations: Sequence[Any],
    *,
    endpoint_url_template: str = "https://app.asana.com/api/1.0/sections/{section_gid}/addTask",
) -> dict[str, Any] | None:
    """Place the newly created Asana task into the explicitly requested section."""
    low = prompt.lower()
    if "asana" not in low or "section" not in low:
        return None

    m_section = re.search(r"['\"]([^'\"]{2,40})['\"]\s+section", prompt, re.I)
    if not m_section:
        m_section = re.search(
            r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+section\b",
            prompt,
            re.I,
        )
    if not m_section:
        return None
    section_name = m_section.group(1).strip()

    project_match = re.search(r"\b(?:project\s+)?(proj[_-][A-Za-z0-9_-]+)\b", prompt, re.I)
    project_gid = project_match.group(1) if project_match else None

    # Recover the intended task name from authoritative observed source text.
    target_names: list[str] = []
    all_records = _records(observations)
    for rec in all_records:
        text = " ".join(
            _s(rec.get(k))
            for k in ("body","body_plain","text","description","subject","title")
        )
        m_name = re.search(r"(?:create\s+task|task)\s*:\s*([^\n.]+)", text, re.I)
        if m_name:
            target_names.append(m_name.group(1).strip())

    if not target_names:
        return None

    task_candidates: list[dict[str, Any]] = []
    section_candidates: list[dict[str, Any]] = []
    for rec in all_records:
        gid = _s(_ci_get(rec, "gid", "id", "Id"))
        name = _s(_ci_get(rec, "name", "title"))
        if not gid or not name:
            continue

        if name.lower() == section_name.lower():
            if project_gid:
                project = _ci_get(rec, "project")
                if isinstance(project, Mapping):
                    pgid = _s(_ci_get(project, "gid", "id", "Id"))
                    if pgid and pgid != project_gid:
                        continue
            section_candidates.append(rec)

        if any(name.lower() == target.lower() for target in target_names):
            task_candidates.append(rec)

    if not task_candidates or not section_candidates:
        return None

    task = task_candidates[-1]
    section = section_candidates[0]
    task_gid = _s(_ci_get(task, "gid", "id", "Id"))
    section_gid = _s(_ci_get(section, "gid", "id", "Id"))
    if not task_gid or not section_gid:
        return None

    return {
        "schema": SCHEMA,
        "semantic": "ASANA_TASK_ADD_TO_SECTION",
        "tool": "api_fetch",
        "arguments": {
            "method": "POST",
            "url": endpoint_url_template.replace("{section_gid}", section_gid),
            "body": json.dumps({"task": task_gid}, sort_keys=True),
        },
        "grounding": {
            "task_gid": task_gid,
            "task_name": _s(_ci_get(task, "name", "title")),
            "section_gid": section_gid,
            "section_name": section_name,
            "project_gid": project_gid,
        },
    }


def compile_asana_add_tag(
    prompt: str,
    observations: Sequence[Any],
    *,
    endpoint_url_template: str = "https://app.asana.com/api/1.0/tasks/{task_gid}/addTag",
) -> dict[str, Any] | None:
    """Apply an explicitly grounded tag label to the exact created Asana task.

    AutomationBench's simulated Asana implementation accepts the `tag` request
    value directly and records it in the add_tag_to_task action. No tag-directory
    lookup or invented GID is needed.
    """
    low = prompt.lower()
    if "asana" not in low or "tag" not in low:
        return None

    all_records = _records(observations)

    target_names: list[str] = []
    tag_labels: list[str] = []
    for rec in all_records:
        text = " ".join(
            _s(rec.get(k))
            for k in ("body", "body_plain", "text", "description", "subject", "title")
        )
        m_name = re.search(r"(?:create\s+task|task)\s*:\s*([^\n.]+)", text, re.I)
        if m_name:
            target_names.append(m_name.group(1).strip())
        for m_tag in re.finditer(r"\bTag\s*:\s*([^\n.;]+)", text, re.I):
            value = m_tag.group(1).strip()
            if value:
                tag_labels.append(value)

    # Prompt-level explicit fallback, e.g. "tag it Compliance".
    if not tag_labels:
        m_prompt_tag = re.search(
            r"\btag(?:\s+(?:it|the\s+task))?(?:\s+with)?\s+['\"]?([A-Za-z][A-Za-z0-9 _-]{1,50})['\"]?",
            prompt,
            re.I,
        )
        if m_prompt_tag:
            value = m_prompt_tag.group(1).strip()
            # Stop before common continuation markers.
            value = re.split(r"\s+(?:and|then|before|after|notify|send|post)\b", value, maxsplit=1, flags=re.I)[0].strip()
            if value:
                tag_labels.append(value)

    target_names = list(dict.fromkeys(target_names))
    tag_labels = list(dict.fromkeys(tag_labels))
    if len(tag_labels) != 1 or not target_names:
        return None
    tag_label = tag_labels[0]

    task_candidates: list[dict[str, Any]] = []
    for rec in all_records:
        gid = _s(_ci_get(rec, "gid", "id", "Id"))
        name = _s(_ci_get(rec, "name", "title"))
        if not gid or not name:
            continue
        if any(name.lower() == target.lower() for target in target_names):
            task_candidates.append(rec)

    if not task_candidates:
        return None
    task = task_candidates[-1]
    task_gid = _s(_ci_get(task, "gid", "id", "Id"))
    if not task_gid:
        return None

    return {
        "schema": SCHEMA,
        "semantic": "ASANA_TASK_ADD_TAG",
        "tool": "api_fetch",
        "arguments": {
            "method": "POST",
            "url": endpoint_url_template.replace("{task_gid}", task_gid),
            "body": json.dumps({"tag": tag_label}, sort_keys=True),
        },
        "grounding": {
            "task_gid": task_gid,
            "task_name": _s(_ci_get(task, "name", "title")),
            "tag": tag_label,
        },
    }
