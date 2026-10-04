#!/usr/bin/env python3
"""Hermetic NLTK runtime binding for the frozen LiveBench legacy15 scorer.

Only two active legacy15 checker families depend on NLTK semantics:
- length_constraints:number_words
- length_constraints:number_sentences

The package wheel and Punkt data identities were already frozen by the Brain's
independently verified LiveBench hermetic-input binding. This module reuses
those exact artifact identities and additionally verifies that the installed
NLTK package files and extracted tokenizer data equal the pinned archives before
the legacy15 pointwise solver may claim proof-grade exact postvalidation.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
from pathlib import Path
import sys
import zipfile
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_HERMETIC_NLTK_BINDING_V1"

PINNED_PYTHON = (3, 12)
PINNED_NLTK_VERSION = "3.10.3"
PINNED_NLTK_WHEEL_SHA256 = "ff9598a8e20518ee0d557745890cc4435b9578489e2dcbc69c4f81fa060caf7c"
PINNED_NLTK_DATA_COMMIT = "550b6625bcef1f2abff2ff770a5a0d272c9c6b2a"
PINNED_DATA_ARCHIVES = {
    ("tokenizers", "punkt.zip"): "da7ffbd1e6fd6cc5c2f6879c2d4da23c7691944c",
    ("tokenizers", "punkt_tab.zip"): "5e5ff6137d5ee6025e400d1c3a7b21914c48b635",
}
NLTK_DEPENDENT_ACTIVE_IDS = frozenset({
    "length_constraints:number_words",
    "length_constraints:number_sentences",
})


class HermeticNLTKError(ValueError):
    pass


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _safe_member(name: str) -> Path:
    rel = Path(name)
    if rel.is_absolute() or ".." in rel.parts:
        raise HermeticNLTKError("UNSAFE_ARCHIVE_MEMBER:" + name)
    return rel


def _verify_installed_nltk_against_wheel(wheel_path: Path) -> int:
    import nltk

    package_root = Path(nltk.__file__).resolve().parent
    site_root = package_root.parent
    checked = 0

    with zipfile.ZipFile(wheel_path) as zf:
        names = [n for n in zf.namelist() if n.startswith("nltk/") and not n.endswith("/")]
        if not names:
            raise HermeticNLTKError("NLTK_WHEEL_CONTAINS_NO_PACKAGE_FILES")
        for name in names:
            rel = _safe_member(name)
            installed = site_root / rel
            if not installed.is_file():
                raise HermeticNLTKError("NLTK_INSTALLED_FILE_MISSING:" + str(rel))
            if installed.read_bytes() != zf.read(name):
                raise HermeticNLTKError("NLTK_INSTALLED_FILE_DRIFT:" + str(rel))
            checked += 1

    return checked


def _verify_data_archive_and_extraction(
    nltk_data_root: Path,
    category: str,
    archive_name: str,
    expected_git_blob: str,
) -> int:
    archive = nltk_data_root / category / archive_name
    if not archive.is_file():
        raise HermeticNLTKError("NLTK_DATA_ARCHIVE_MISSING:" + str(archive))
    actual = _git_blob_sha(archive)
    if actual != expected_git_blob:
        raise HermeticNLTKError(
            "NLTK_DATA_ARCHIVE_DRIFT:"
            + category
            + "/"
            + archive_name
            + ":"
            + actual
        )

    checked = 0
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            rel = _safe_member(info.filename)
            extracted = nltk_data_root / category / rel
            if not extracted.is_file():
                raise HermeticNLTKError("NLTK_DATA_EXTRACTED_FILE_MISSING:" + str(extracted))
            if extracted.read_bytes() != zf.read(info.filename):
                raise HermeticNLTKError("NLTK_DATA_EXTRACTED_FILE_DRIFT:" + str(extracted))
            checked += 1
    return checked


def verify_and_bind(
    nltk_wheel_path: str | Path,
    nltk_data_root: str | Path,
) -> dict[str, Any]:
    if tuple(sys.version_info[:2]) != PINNED_PYTHON:
        raise HermeticNLTKError(
            "PYTHON_VERSION_DRIFT:"
            + ".".join(map(str, sys.version_info[:2]))
        )

    observed_version = importlib.metadata.version("nltk")
    if observed_version != PINNED_NLTK_VERSION:
        raise HermeticNLTKError("NLTK_VERSION_DRIFT:" + observed_version)

    wheel = Path(nltk_wheel_path).resolve()
    if not wheel.is_file():
        raise HermeticNLTKError("NLTK_WHEEL_MISSING:" + str(wheel))
    wheel_sha = _sha256(wheel)
    if wheel_sha != PINNED_NLTK_WHEEL_SHA256:
        raise HermeticNLTKError("NLTK_WHEEL_SHA256_DRIFT:" + wheel_sha)

    package_files = _verify_installed_nltk_against_wheel(wheel)

    data_root = Path(nltk_data_root).resolve()
    if not data_root.is_dir():
        raise HermeticNLTKError("NLTK_DATA_ROOT_MISSING:" + str(data_root))

    extracted_files = 0
    archive_blobs: dict[str, str] = {}
    for (category, archive_name), expected_blob in PINNED_DATA_ARCHIVES.items():
        extracted_files += _verify_data_archive_and_extraction(
            data_root, category, archive_name, expected_blob
        )
        archive_blobs[category + "/" + archive_name] = expected_blob

    import nltk
    nltk.data.path[:] = [str(data_root)]
    try:
        nltk.data.load("nltk:tokenizers/punkt/english.pickle")
    except Exception as exc:
        raise HermeticNLTKError(
            "PINNED_PUNKT_RUNTIME_LOAD_FAILED:"
            + type(exc).__name__
            + ":"
            + str(exc)
        ) from exc

    return {
        "schema": SCHEMA,
        "status": "PASS__HERMETIC_NLTK_PACKAGE_AND_PUNKT_BYTES_BOUND",
        "python_major_minor": list(PINNED_PYTHON),
        "nltk_version": observed_version,
        "nltk_wheel_sha256": wheel_sha,
        "nltk_data_commit": PINNED_NLTK_DATA_COMMIT,
        "nltk_data_archive_git_blobs": archive_blobs,
        "verified_installed_nltk_package_file_count": package_files,
        "verified_extracted_nltk_data_file_count": extracted_files,
        "nltk_data_search_path": [str(data_root)],
        "network_used": False,
        "terminal_data_used": False,
        "acceptance_credit": False,
    }


def contracts_require_nltk(contracts) -> bool:
    return any(
        str(c.get("instruction_id") or "") in NLTK_DEPENDENT_ACTIVE_IDS
        for c in contracts
    )


def run(args: dict[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = args or {}
    wheel = args.get("nltk_wheel_path")
    data = args.get("nltk_data_root")
    if not wheel or not data:
        raise HermeticNLTKError("NLTK_WHEEL_PATH_AND_DATA_ROOT_REQUIRED")
    return verify_and_bind(wheel, data)


if __name__ == "__main__":
    import json
    payload = json.load(sys.stdin)
    print(json.dumps(run(payload), indent=2, sort_keys=True))
