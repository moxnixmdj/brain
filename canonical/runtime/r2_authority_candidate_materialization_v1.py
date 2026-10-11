"""Generic checker-owned materialization for delegated authority-domain candidates.

Discovery nominates a URL. This module owns the refetch, redirect/domain checks,
exact-byte digest, and text extraction. It never upgrades the candidate into
semantic truth. The output is material for an existing checker, nothing more.
"""
from __future__ import annotations

from hashlib import sha256
from html.parser import HTMLParser
import ipaddress
import re
import urllib.parse
import urllib.request
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_R2_AUTHORITY_CANDIDATE_MATERIALIZATION_V1"
DISCOVERY_SCHEMA = "PROJECT_BRAIN_R2_AUTHORITY_DOMAIN_DISCOVERY_PROVIDER_V1"
SCOPE_KIND = "UNBOUND_SOURCE"
MAX_BYTES = 8_000_000


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "checker_material_only": True,
        "provider_authority": False,
        "source_truth_authority": False,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _domains(raw: Any) -> list[str]:
    if (
        not isinstance(raw, Sequence)
        or isinstance(raw, (str, bytes))
        or not raw
        or len(raw) > 16
    ):
        raise ValueError("AUTHORITY_DOMAINS_REQUIRED")
    out: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise ValueError("AUTHORITY_DOMAIN_INVALID")
        value = item.casefold().strip().lstrip(".")
        if (
            not re.fullmatch(r"[a-z0-9.-]+", value)
            or "." not in value
            or ".." in value
            or value.startswith("-")
            or value.endswith("-")
        ):
            raise ValueError("AUTHORITY_DOMAIN_INVALID:" + value)
        if value not in out:
            out.append(value)
    return out


def _allowed_host(host: str, domains: Sequence[str]) -> bool:
    value = str(host or "").casefold().rstrip(".")
    return bool(value) and any(
        value == domain or value.endswith("." + domain) for domain in domains
    )


def _safe_https_url(value: Any, domains: Sequence[str]) -> tuple[str, str]:
    url = str(value or "").strip()
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme.casefold() != "https" or not parsed.hostname:
        raise ValueError("AUTHORITY_CANDIDATE_HTTPS_REQUIRED")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("AUTHORITY_CANDIDATE_CREDENTIALS_FORBIDDEN")
    host = parsed.hostname.casefold().rstrip(".")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        raise ValueError("AUTHORITY_CANDIDATE_NONPUBLIC_IP_FORBIDDEN")
    if not _allowed_host(host, domains):
        raise ValueError("AUTHORITY_CANDIDATE_OUTSIDE_DECLARED_AUTHORITY")
    return url, host


class _TextExtractor(HTMLParser):
    _SKIP = {"script", "style", "noscript", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = tag.casefold()
        if name in self._SKIP:
            self.skip_depth += 1
        elif self.skip_depth == 0 and name in {
            "p", "div", "li", "br", "tr", "td", "th", "h1", "h2", "h3", "h4"
        }:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        name = tag.casefold()
        if name in self._SKIP and self.skip_depth:
            self.skip_depth -= 1
        elif self.skip_depth == 0 and name in {
            "p", "div", "li", "tr", "h1", "h2", "h3", "h4"
        }:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth == 0 and data:
            self.parts.append(data)


def _plain_text(raw: bytes, content_type: str) -> str:
    text = raw.decode("utf-8", errors="strict")
    if "html" not in str(content_type or "").casefold():
        return text
    parser = _TextExtractor()
    parser.feed(text)
    parser.close()
    material = "".join(parser.parts)
    material = re.sub(r"[ \t\r\f\v]+", " ", material)
    material = re.sub(r"\n\s*\n+", "\n", material)
    return material.strip()


def _fetch(
    url: str,
    *,
    domains: Sequence[str],
    max_bytes: int,
    timeout_s: int,
) -> tuple[bytes, str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ProjectBrain-R2AuthorityCandidateMaterializer/1.0",
            "Accept": "text/html,text/plain,application/json;q=0.9,*/*;q=0.2",
            "Accept-Encoding": "identity",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        final_url = str(response.geturl())
        _safe_https_url(final_url, domains)
        raw = response.read(max_bytes + 1)
        content_type = str(response.headers.get("Content-Type") or "")
    if len(raw) > max_bytes:
        raise ValueError("AUTHORITY_CANDIDATE_SIZE_LIMIT_EXCEEDED")
    return raw, final_url, content_type


def materialize(
    request_packet: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    fetcher: Callable[..., tuple[bytes, str, str]] = _fetch,
) -> dict[str, Any]:
    try:
        if not isinstance(request_packet, Mapping):
            return _base("FAIL_CLOSED", reason="REQUEST_PACKET_MAPPING_REQUIRED")
        if not isinstance(candidate, Mapping):
            return _base("FAIL_CLOSED", reason="CANDIDATE_MAPPING_REQUIRED")
        if (
            candidate.get("schema") != DISCOVERY_SCHEMA
            or candidate.get("pass") is not True
            or candidate.get("candidate_only") is not True
            or candidate.get("semantic_truth_authority") is True
        ):
            return _base("FAIL_CLOSED", reason="DISCOVERY_CANDIDATE_INVALID")

        scope = request_packet.get("source_scope")
        if not isinstance(scope, Mapping) or scope.get("kind") != SCOPE_KIND:
            return _base("NOT_APPLICABLE__UNBOUND_SOURCE_SCOPE_REQUIRED")

        scope_domains = _domains(scope.get("authority_domains"))
        candidate_domains = _domains(candidate.get("authority_domains"))
        if scope_domains != candidate_domains:
            return _base("FAIL_CLOSED", reason="DISCOVERY_AUTHORITY_DOMAIN_DRIFT")

        chosen_url, chosen_host = _safe_https_url(
            candidate.get("chosen_url"), scope_domains
        )
        if str(candidate.get("chosen_host") or "").casefold().rstrip(".") != chosen_host:
            return _base("FAIL_CLOSED", reason="DISCOVERY_HOST_URL_HOST_MISMATCH")

        timeout_s = scope.get("timeout_s", 20)
        max_bytes = scope.get("max_bytes", 1_500_000)
        if (
            isinstance(timeout_s, bool)
            or not isinstance(timeout_s, int)
            or timeout_s < 1
            or timeout_s > 60
        ):
            return _base("FAIL_CLOSED", reason="CANDIDATE_TIMEOUT_INVALID")
        if (
            isinstance(max_bytes, bool)
            or not isinstance(max_bytes, int)
            or max_bytes < 10_000
            or max_bytes > MAX_BYTES
        ):
            return _base("FAIL_CLOSED", reason="CANDIDATE_MAX_BYTES_INVALID")

        raw, final_url, content_type = fetcher(
            chosen_url,
            domains=scope_domains,
            max_bytes=max_bytes,
            timeout_s=timeout_s,
        )
        if not isinstance(raw, bytes) or not raw:
            return _base("FAIL_CLOSED", reason="MATERIALIZED_BYTES_INVALID")
        if len(raw) > max_bytes:
            return _base("FAIL_CLOSED", reason="MATERIALIZED_BYTES_LIMIT_EXCEEDED")
        _, final_host = _safe_https_url(final_url, scope_domains)

        raw_digest = sha256(raw).hexdigest()
        try:
            source_text = _plain_text(raw, content_type)
        except UnicodeDecodeError:
            return _base(
                "OPEN__AUTHORITY_CANDIDATE_NON_UTF8_TEXT_CHECKER_UNAVAILABLE",
                materialized=True,
                chosen_url=chosen_url,
                final_url=final_url,
                final_host=final_host,
                raw_sha256=raw_digest,
                raw_size_bytes=len(raw),
                content_type=content_type,
            )
        if not source_text:
            return _base(
                "OPEN__AUTHORITY_CANDIDATE_TEXT_EMPTY",
                materialized=True,
                chosen_url=chosen_url,
                final_url=final_url,
                final_host=final_host,
                raw_sha256=raw_digest,
                raw_size_bytes=len(raw),
                content_type=content_type,
            )

        material = {
            "source_text": source_text,
            "source_id": "authority-candidate-sha256:" + raw_digest,
            "raw_sha256": raw_digest,
            "raw_size_bytes": len(raw),
            "chosen_url": chosen_url,
            "final_url": final_url,
            "final_host": final_host,
            "content_type": content_type,
            "authority_domains": scope_domains,
            "query": str(candidate.get("query") or scope.get("query") or "").strip(),
            "discovery_evidence_path": str(candidate.get("discovery_evidence_path") or ""),
        }
        return _base(
            "PASS__AUTHORITY_CANDIDATE_MATERIALIZED_FOR_EXISTING_CHECKER",
            passed=True,
            materialized=True,
            checker_material=material,
            raw_sha256=raw_digest,
            final_url=final_url,
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))
