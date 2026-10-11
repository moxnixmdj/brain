"""Checker-owned materialization of one four-way regulatory-capital observation.

A discovery provider may nominate an HTTPS URL under a declared authority-domain
set. This module refetches it, preserves exact bytes/digests, derives plain text,
and runs only already-owned regulatory-capital observation compilers.

Discovery is not truth. No open-world identity, policy adequacy, acceptance,
promotion, or terminal authority is granted.
"""
from __future__ import annotations

from hashlib import sha256
from html.parser import HTMLParser
import ipaddress
import re
import urllib.parse
import urllib.request
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import regcap_context_signature_v1 as context_signature
from canonical.runtime import regcap_contextual_observation_compiler_v1 as observation
from canonical.runtime import regcap_contrastive_discriminator_matrix_v1 as matrix
from canonical.runtime import regcap_four_way_governing_requirement_discriminator_v1 as four
from canonical.runtime import tlac_mrel_identity_discriminator_v1 as tlac_mrel

SCHEMA = "PROJECT_BRAIN_REGCAP_FOUR_WAY_AUTHORITY_CANDIDATE_OBSERVATION_V1"
MAX_BYTES = 8_000_000


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_truth_authority": False,
        "relative_selection_authority": False,
        "source_identity_authority": False,
        "candidate_universe_complete": False,
        "open_world_ontology_complete": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _normalized_domains(raw: Any) -> list[str]:
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
        domain = item.casefold().strip().lstrip(".")
        if (
            not re.fullmatch(r"[a-z0-9.-]+", domain)
            or "." not in domain
            or ".." in domain
            or domain.startswith("-")
            or domain.endswith("-")
        ):
            raise ValueError("AUTHORITY_DOMAIN_INVALID:" + domain)
        if domain not in out:
            out.append(domain)
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
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() in self._SKIP:
            self._skip_depth += 1
        elif self._skip_depth == 0 and tag.casefold() in {
            "p", "div", "li", "br", "tr", "td", "th", "h1", "h2", "h3", "h4"
        }:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in self._SKIP and self._skip_depth:
            self._skip_depth -= 1
        elif self._skip_depth == 0 and tag.casefold() in {
            "p", "div", "li", "tr", "h1", "h2", "h3", "h4"
        }:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data:
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
            "User-Agent": "ProjectBrain-R2FourWayObservation/1.0",
            "Accept": "text/html,text/plain;q=0.9,*/*;q=0.2",
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


def _matrix_candidates(text: str, *, repo_root: Any = None) -> list[dict[str, Any]]:
    verified = matrix.verify_matrix(repo_root=repo_root)
    if verified.get("pass") is not True:
        raise ValueError("REGCAP_MATRIX_AUTHORITY_FAILED")
    by_id = {
        str(row.get("observation_id")): row
        for row in verified.get("observations") or []
        if isinstance(row, Mapping)
    }
    found: list[dict[str, Any]] = []
    for start, end, sentence in context_signature._sentence_spans(text):
        compiled = observation.compile_span(text, start=start, end=end)
        if compiled.get("status") == "FAIL_CLOSED":
            raise ValueError("REGCAP_OBSERVATION_COMPILER_FAIL_CLOSED")
        if compiled.get("pass") is not True:
            continue
        oid = str(compiled.get("observation_id") or "")
        outcome = str(compiled.get("outcome") or "")
        row = by_id.get(oid)
        if not isinstance(row, Mapping):
            raise ValueError("REGCAP_OBSERVATION_NOT_IN_AUTHENTICATED_MATRIX")
        matches = sorted(
            cid for cid, expected in (row.get("outcomes") or {}).items()
            if expected == outcome
        )
        if len(matches) != 1:
            continue
        found.append({
            "candidate_id": matches[0],
            "evidence_kind": "REGCAP_CONTEXTUAL_OBSERVATION",
            "observation_id": oid,
            "source_outcome": outcome,
            "sentence": sentence,
        })
    return found


def observe(
    candidate: Mapping[str, Any],
    *,
    repo_root: Any = None,
    fetcher: Callable[..., tuple[bytes, str, str]] = _fetch,
) -> dict[str, Any]:
    try:
        if not isinstance(candidate, Mapping):
            return _base("FAIL_CLOSED", reason="CANDIDATE_MAPPING_REQUIRED")
        allowed = {
            "chosen_url",
            "chosen_host",
            "query",
            "authority_domains",
            "timeout_s",
            "max_bytes",
            "discovery_evidence_path",
        }
        extra = set(candidate) - allowed
        if extra:
            return _base(
                "FAIL_CLOSED",
                reason="UNMODELED_CANDIDATE_FIELDS:" + ",".join(sorted(extra)),
            )
        domains = _normalized_domains(candidate.get("authority_domains"))
        chosen_url, url_host = _safe_https_url(candidate.get("chosen_url"), domains)
        chosen_host = str(candidate.get("chosen_host") or "").casefold().rstrip(".")
        if chosen_host != url_host:
            return _base("FAIL_CLOSED", reason="DISCOVERY_HOST_URL_HOST_MISMATCH")
        timeout_s = candidate.get("timeout_s", 20)
        max_bytes = candidate.get("max_bytes", 1_500_000)
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
            domains=domains,
            max_bytes=max_bytes,
            timeout_s=timeout_s,
        )
        if not isinstance(raw, bytes) or not raw:
            return _base("FAIL_CLOSED", reason="MATERIALIZED_BYTES_INVALID")
        if len(raw) > max_bytes:
            return _base("FAIL_CLOSED", reason="MATERIALIZED_BYTES_LIMIT_EXCEEDED")
        _, final_host = _safe_https_url(final_url, domains)
        text = _plain_text(raw, content_type)
        if not text:
            return _base("OPEN__AUTHORITY_CANDIDATE_TEXT_EMPTY")

        findings = _matrix_candidates(text, repo_root=repo_root)
        pair_context = tlac_mrel.compile_context(
            text,
            source_id="authority-candidate:" + sha256(raw).hexdigest(),
        )
        if pair_context.get("status") == "FAIL_CLOSED":
            return _base(
                "FAIL_CLOSED",
                reason="TLAC_MREL_CONTEXT_FAIL_CLOSED",
                pair_context=pair_context,
            )
        if pair_context.get("pass") is True:
            selected = str(pair_context.get("selected_candidate_hint") or "")
            if selected:
                findings.append({
                    "candidate_id": selected,
                    "evidence_kind": "TLAC_MREL_GOVERNING_REQUIREMENT_CONTEXT",
                    "observation_id": pair_context.get("observation_id"),
                    "source_outcome": pair_context.get("observed_outcome"),
                    "matches": pair_context.get("matches"),
                })

        selected_ids = sorted({
            str(row.get("candidate_id") or "")
            for row in findings
            if str(row.get("candidate_id") or "")
        })
        if not selected_ids:
            return _base(
                "OPEN__NO_CERTIFIED_FOUR_WAY_GOVERNING_REQUIREMENT_OBSERVATION",
                chosen_url=chosen_url,
                final_url=final_url,
                raw_sha256=sha256(raw).hexdigest(),
                text_sha256=sha256(text.encode("utf-8")).hexdigest(),
                finding_count=0,
            )
        if len(selected_ids) != 1:
            return _base(
                "FAIL_CLOSED",
                reason="CONFLICTING_CERTIFIED_FOUR_WAY_OBSERVATIONS",
                selected_candidate_ids=selected_ids,
                findings=findings,
            )

        authority = four.verify_authority(repo_root=repo_root)
        if authority.get("pass") is not True or authority.get(
            "semantic_truth_authority"
        ) is not True:
            return _base(
                "FAIL_CLOSED",
                reason="FOUR_WAY_GOVERNING_REQUIREMENT_AUTHORITY_FAILED",
                authority_result=authority,
            )
        selected = selected_ids[0]
        if selected not in four.DOMAIN:
            return _base("FAIL_CLOSED", reason="SELECTED_CANDIDATE_OUTSIDE_FOUR_WAY_DOMAIN")
        expected_outcome = authority.get("outcomes", {}).get(selected)
        if expected_outcome != four.OUTCOMES[selected]:
            return _base("FAIL_CLOSED", reason="FOUR_WAY_OUTCOME_AUTHORITY_DRIFT")

        return _base(
            "PASS__AUTHORITY_CANDIDATE_FOUR_WAY_OBSERVATION_CERTIFIED",
            passed=True,
            semantic_truth_authority=True,
            relative_selection_authority=True,
            source_identity_authority=True,
            source_identity_authority_scope="DECLARED_AUTHORITY_DOMAINS_ONLY",
            candidate_universe_complete=True,
            candidate_universe_complete_only_for_scope_id=four.SCOPE_ID,
            scope_id=four.SCOPE_ID,
            observation_id=four.OBSERVATION_ID,
            selected_concept_id=selected,
            observed_outcome=expected_outcome,
            declared_candidate_ids=list(four.DOMAIN),
            authority_sha256=authority.get("authority_sha256"),
            chosen_url=chosen_url,
            chosen_host=chosen_host,
            final_url=final_url,
            final_host=final_host,
            raw_sha256=sha256(raw).hexdigest(),
            raw_byte_count=len(raw),
            text_sha256=sha256(text.encode("utf-8")).hexdigest(),
            findings=findings,
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))
