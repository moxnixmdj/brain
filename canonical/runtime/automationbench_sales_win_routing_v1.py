"""Owned sales-win routing compiler for AutomationBench's simulated API world.

This module never talks to Gmail or Salesforce directly. It consumes observations
returned by AutomationBench api_fetch and emits api_fetch call descriptions for
the benchmark's in-memory simulated endpoints.

It does not consume benchmark assertions or private task data.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_AUTOMATIONBENCH_SALES_WIN_ROUTING_V1"


def _s(value: Any) -> str:
    return str(value or "").strip()


def _ci_get(record: Mapping[str, Any], *names: str) -> Any:
    lut = {str(k).lower().replace("_", ""): v for k, v in record.items()}
    for name in names:
        key = name.lower().replace("_", "")
        if key in lut:
            return lut[key]
    return None


def _flatten(value: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def walk(item: Any) -> None:
        if isinstance(item, Mapping):
            row = dict(item)
            out.append(row)
            for child in row.values():
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)
        elif isinstance(item, str):
            try:
                walk(json.loads(item))
            except Exception:
                return

    walk(value)
    return out


def _date_key(value: Any) -> tuple[int, str]:
    raw = _s(value)
    if not raw:
        return (0, "")
    try:
        return (1, datetime.fromisoformat(raw.replace("Z", "+00:00")).isoformat())
    except Exception:
        return (0, raw)


def _table_rows(observations: Sequence[Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for rec in _flatten(list(observations)):
        values = rec.get("values")
        if not isinstance(values, list) or not values:
            continue
        if not isinstance(values[0], list):
            continue
        headers = [_s(x) for x in values[0]]
        if not headers:
            continue
        for line in values[1:]:
            if not isinstance(line, list):
                continue
            row = {
                headers[i]: _s(line[i]) if i < len(line) else ""
                for i in range(len(headers))
                if headers[i]
            }
            if row:
                rows.append(row)
    return rows


def _target_terms(prompt: str) -> list[str]:
    generic = {
        "we", "just", "closed", "the", "mark", "it", "as", "won", "and",
        "route", "win", "notice", "deal", "salesforce",
    }
    match = re.search(
        r"closed\s+the\s+(.+?\bDeal)\b",
        prompt,
        re.IGNORECASE,
    )
    source = match.group(1) if match else prompt
    return [
        token.lower()
        for token in re.findall(r"[A-Za-z0-9&'-]+", source)
        if token.lower() not in generic and len(token) > 2
    ]


def _find_opportunity(prompt: str, observations: Sequence[Any]) -> dict[str, Any] | None:
    terms = _target_terms(prompt)
    best: tuple[int, dict[str, Any]] | None = None
    for rec in _flatten(list(observations)):
        record_id = _s(_ci_get(rec, "Id", "id"))
        name = _s(_ci_get(rec, "Name", "name"))
        if not record_id.startswith("006") or not name:
            continue
        low = name.lower()
        score = sum(1 for term in terms if term in low)
        if best is None or score > best[0]:
            best = (score, rec)
    if best is None or best[0] <= 0:
        return None
    return best[1]


def _latest_tier(account_id: str, observations: Sequence[Any]) -> str | None:
    matches: list[tuple[tuple[int, str], str]] = []
    for row in _table_rows(observations):
        rid = _s(_ci_get(row, "Account ID", "AccountId", "account_id"))
        tier = _s(_ci_get(row, "Tier"))
        updated = _ci_get(row, "Updated", "Updated At", "Date")
        if rid == account_id and tier:
            matches.append((_date_key(updated), tier))
    if not matches:
        return None
    matches.sort(key=lambda item: item[0], reverse=True)
    return matches[0][1]


def _latest_fx(currency: str, observations: Sequence[Any]) -> float | None:
    if not currency:
        return None
    if currency.upper() == "USD":
        return 1.0
    matches: list[tuple[tuple[int, str], float]] = []
    for row in _table_rows(observations):
        cur = _s(_ci_get(row, "Currency"))
        raw_rate = _s(_ci_get(row, "USD Rate", "Rate", "USD"))
        updated = _ci_get(row, "Updated", "Updated At", "Date")
        if cur.upper() != currency.upper() or not raw_rate:
            continue
        try:
            rate = float(raw_rate.replace(",", ""))
        except ValueError:
            continue
        matches.append((_date_key(updated), rate))
    if not matches:
        return None
    matches.sort(key=lambda item: item[0], reverse=True)
    return matches[0][1]


def _account_parent(account_id: str, observations: Sequence[Any]) -> str | None:
    for rec in _flatten(list(observations)):
        rid = _s(_ci_get(rec, "Id", "id"))
        if rid != account_id:
            continue
        parent = _s(_ci_get(rec, "ParentId", "parent_id"))
        if parent:
            return parent
    return None


def _has_escalation(
    account_id: str,
    parent_id: str | None,
    observations: Sequence[Any],
) -> bool:
    account_ids = {account_id}
    if parent_id:
        account_ids.add(parent_id)
    for rec in _flatten(list(observations)):
        rid = _s(_ci_get(rec, "AccountId", "account_id"))
        status = _s(_ci_get(rec, "Status", "status")).lower()
        priority = _s(_ci_get(rec, "Priority", "priority")).lower()
        if rid in account_ids and status == "open" and priority in {"critical", "high"}:
            return True
    return False


def _routing_policy(observations: Sequence[Any]) -> str | None:
    for rec in _flatten(list(observations)):
        subject = _s(_ci_get(rec, "subject", "Subject"))
        body = _s(_ci_get(rec, "body_plain", "body", "text"))
        combined = f"{subject}\n{body}".lower()
        if "win notification routing" in combined and body:
            return body
    return None


def _recipient_for_tier(policy: str, tier: str) -> str | None:
    pattern = re.compile(
        r"^\s*-\s*" + re.escape(tier) + r"\s*:\s*([^\s,;]+@[^\s,;]+)",
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(policy)
    return match.group(1).strip() if match else None


def _support_recipient(policy: str) -> str | None:
    match = re.search(
        r"also\s+notify\s+([^\s,;]+@[^\s,;]+)",
        policy,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def _subject(policy: str) -> str | None:
    match = re.search(
        r"use\s+subject\s+['\"]([^'\"]+)['\"]",
        policy,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def _money(amount: float) -> str:
    return "$" + format(round(amount), ",")


def compile_sales_win_notice(
    prompt: str,
    observations: Sequence[Any],
) -> dict[str, Any] | None:
    low = prompt.lower()
    if "route the win notice" not in low and "win notification" not in low:
        return None

    opportunity = _find_opportunity(prompt, observations)
    if opportunity is None:
        return None

    name = _s(_ci_get(opportunity, "Name", "name"))
    account_id = _s(_ci_get(opportunity, "AccountId", "account_id"))
    currency = _s(_ci_get(opportunity, "Currency", "currency", "CurrencyIsoCode"))
    amount_raw = _ci_get(opportunity, "Amount", "amount")
    if not name or not account_id or not currency or amount_raw is None:
        return None
    try:
        amount = float(str(amount_raw).replace(",", ""))
    except ValueError:
        return None

    tier = _latest_tier(account_id, observations)
    rate = _latest_fx(currency, observations)
    policy = _routing_policy(observations)
    if not tier or rate is None or not policy:
        return None

    primary = _recipient_for_tier(policy, tier)
    subject = _subject(policy)
    if not primary or not subject:
        return None

    parent = _account_parent(account_id, observations)
    escalation = _has_escalation(account_id, parent, observations)
    recipients = [primary]
    if escalation:
        support = _support_recipient(policy)
        if not support:
            return None
        if support not in recipients:
            recipients.append(support)

    converted = amount * rate
    formatted = _money(converted)
    body = f"{name}\n{formatted}\n{tier}"

    calls = [
        {
            "tool": "api_fetch",
            "arguments": {
                "method": "POST",
                "url": "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                "body": json.dumps(
                    {
                        "to": recipient,
                        "subject": subject,
                        "body": body,
                    },
                    sort_keys=True,
                ),
            },
        }
        for recipient in recipients
    ]

    return {
        "schema": SCHEMA,
        "semantic": "SALES_WIN_NOTICE_SEND",
        "calls": calls,
        "evidence": {
            "opportunity_name": name,
            "account_id": account_id,
            "tier": tier,
            "currency": currency,
            "source_amount": amount,
            "fx_rate": rate,
            "converted_amount": formatted,
            "parent_account_id": parent,
            "support_escalation": escalation,
            "recipients": recipients,
            "subject": subject,
        },
    }
