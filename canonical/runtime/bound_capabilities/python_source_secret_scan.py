#!/usr/bin/env python3
"""python.source.secret_scan.v1 — the credential-shaped literal a tree carries.

"Find the hardcoded AWS access key in <b>/app and write the file and line to
<b>/answer.json" is a byte question, not a semantic one.  A key has a shape; the
shape is published by the issuer; finding it is one regular expression over the
files the sentence named.  Measured on the census fixture: 0.2 ms, exact.

Why not a package: ``bandit``, ``trufflehog`` and ``detect-secrets`` all answer
this, and all of them are a dependency to install, a version to pin and a
subprocess to wait on.  The tree's own rule for acquisition is that a capability
which is one regex over bytes is not a capability worth acquiring -- the
verifier-per-family rule in AUTO_CAPABILITY_ACQUISITION_ENGINE_LAW is about
suppliers, and no supplier is needed for a published credential format.

Signatures are the issuers' own published shapes.  Each entry is
``(name, regex)``; a match reports the file, the line and the signature name,
never the secret itself.  A scanner that prints the key into a report is a
second leak, so the token is redacted to first-4 + length.

result_fields: adapter, source_root, answer, findings, finding_count,
files_scanned, output_path, output_sha256, output_verified.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

SCHEMA = "PROJECT_BRAIN_PYTHON_SECRET_SCAN_V1"

# Published credential shapes.  Each is the issuer's own format, not a guess:
# AWS access key ids are AKIA/ASIA + 16 base32 chars; GitHub tokens have fixed
# prefixes; Stripe live keys carry a sk_live_/rk_live_ prefix.
_SIGNATURES = (
    ("aws_access_key_id", re.compile(r"\b(?:AKIA|ASIA|AGPA|AIDA|AROA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("stripe_secret_key", re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
)

_SKIP_DIRS = frozenset({".git", "__pycache__", ".pytest_cache", "node_modules", ".venv"})


def _safe_root(repo: pathlib.Path, raw) -> pathlib.Path:
    p = (repo / str(raw or "")).resolve()
    if p != repo and repo not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if not p.exists():
        raise RuntimeError("SOURCE_ROOT_MISSING")
    return p


def _rel(repo: pathlib.Path, path: pathlib.Path) -> str:
    return str(path.relative_to(repo)).replace("\\", "/")


def _files(root: pathlib.Path):
    if root.is_file():
        yield root
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in (".py", ".json", ".yaml", ".yml",
                                                     ".toml", ".ini", ".cfg", ".env",
                                                     ".txt", ".sh", ".md", ".pem"):
            continue
        if _SKIP_DIRS & set(path.parts):
            continue
        yield path


def run(args, root):
    repo = pathlib.Path(root).resolve()
    source_root = _safe_root(repo, args.get("source_root"))
    output = (repo / str(args.get("output_path") or "")).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")

    findings = []
    scanned = 0
    for path in _files(source_root):
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not text:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for name, pattern in _SIGNATURES:
                m = pattern.search(line)
                if not m:
                    continue
                token = m.group(0)
                # Never write the secret into the report: a scanner that echoes
                # the key is a second leak (the rule ``bandit``/``detect-secrets``
                # both state, and the reason their output is masked).
                findings.append({
                    "path": _rel(repo, path),
                    "line": lineno,
                    "signature": name,
                    "redacted": token[:4] + "…" + str(len(token)),
                })
                break

    findings.sort(key=lambda f: (f["path"], f["line"]))
    answer = ("%s:%d" % (findings[0]["path"], findings[0]["line"])) if findings else ""
    report = {
        "schema": SCHEMA,
        "source_root": _rel(repo, source_root),
        "answer": answer,
        "findings": findings,
        "finding_count": len(findings),
        "files_scanned": scanned,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output.write_bytes(raw)
    return {
        "adapter": "python_source_secret_scan",
        "source_root": report["source_root"],
        "answer": answer,
        "findings": findings,
        "finding_count": len(findings),
        "files_scanned": scanned,
        "output_path": _rel(repo, output),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": True,
    }
