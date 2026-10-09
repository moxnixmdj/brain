"""Open English WordNet 2025 full-release sense universe V1.

This module turns the exact official OEWN 2025 JSON release bytes into a finite,
content-addressed sense universe for one exact lemma/POS.

It proves only release-relative candidate completeness. It does NOT infer the
intended sense, global synonymy, ontology identity, or English-language
completeness. Selection remains the job of downstream authenticated semantic
control.

Knowledge stays external/JIT. The Brain owns only deterministic byte checking,
safe archive parsing, complete lemma enumeration, synset binding, provenance,
and fail-closed invariants.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import io
import json
import posixpath
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence
import zipfile

SCHEMA = "PROJECT_BRAIN_OEWN_2025_RELEASE_SENSE_UNIVERSE_V1"
RELEASE_ID = "OEWN_2025_JSON"
RELEASE_DATE = "2025-12-31"
RELEASE_SHA256 = "7d749f6e2c39e6970e4997839dcf6e42fd281f3c2fae0171d2192bae8cfa4b51"
OFFICIAL_URLS = (
    "https://en-word.net/static/english-wordnet-2025-json.zip",
    "https://en-word.net/downloads/english-wordnet-2025-json.zip",
)
POS = frozenset({"n", "v", "a", "s", "r"})


class OEWNReleaseError(ValueError):
    pass


def _base(status: str, *, passed: bool, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "release_id": RELEASE_ID,
        "release_date": RELEASE_DATE,
        "candidate_set_complete_relative_to_release": False,
        "intended_sense_identified": False,
        "open_world_english_sense_completeness_claimed": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _norm_lemma(value: Any) -> str:
    if not isinstance(value, str):
        raise OEWNReleaseError("LEMMA_MUST_BE_STRING")
    text = " ".join(value.strip().split()).casefold()
    if not text:
        raise OEWNReleaseError("LEMMA_REQUIRED")
    return text


def _read_archive_bytes(archive: bytes | bytearray | str | Path) -> bytes:
    if isinstance(archive, (bytes, bytearray)):
        raw = bytes(archive)
    elif isinstance(archive, (str, Path)):
        target = Path(archive)
        if not target.is_file() or target.is_symlink():
            raise OEWNReleaseError("ARCHIVE_PATH_INVALID")
        raw = target.read_bytes()
    else:
        raise OEWNReleaseError("ARCHIVE_BYTES_OR_PATH_REQUIRED")
    if not raw:
        raise OEWNReleaseError("ARCHIVE_EMPTY")
    return raw


def _safe_members(zf: zipfile.ZipFile) -> list[str]:
    names = zf.namelist()
    if not names:
        raise OEWNReleaseError("ZIP_EMPTY")
    if len(names) != len(set(names)):
        raise OEWNReleaseError("ZIP_DUPLICATE_MEMBER_NAME")
    safe: list[str] = []
    for raw_name in names:
        name = str(raw_name)
        p = PurePosixPath(name)
        if (
            not name
            or name.startswith("/")
            or name.startswith("\\")
            or p.is_absolute()
            or ".." in p.parts
            or posixpath.normpath(name) != name.rstrip("/")
        ):
            raise OEWNReleaseError("ZIP_UNSAFE_MEMBER:" + name)
        safe.append(name)
    return safe


def _load_json_member(zf: zipfile.ZipFile, name: str) -> Any:
    try:
        raw = zf.read(name)
    except KeyError as exc:
        raise OEWNReleaseError("ZIP_MEMBER_MISSING:" + name) from exc
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise OEWNReleaseError("JSON_INVALID:" + name) from exc


def _member_lemma(value: Any) -> str | None:
    if isinstance(value, str):
        return _norm_lemma(value)
    if isinstance(value, Mapping):
        lemma = value.get("lemma")
        return _norm_lemma(lemma) if isinstance(lemma, str) and lemma.strip() else None
    return None


def _normalize_synset_record(
    *,
    synset_id: str,
    lexname: str,
    raw: Mapping[str, Any],
    lemma: str,
) -> dict[str, Any]:
    members_raw = raw.get("members")
    if not isinstance(members_raw, Sequence) or isinstance(members_raw, (str, bytes)):
        raise OEWNReleaseError("SYNSET_MEMBERS_INVALID:" + synset_id)
    members = []
    for item in members_raw:
        member = _member_lemma(item)
        if member and member not in members:
            members.append(member)
    if lemma not in members:
        raise OEWNReleaseError("SYNSET_DOES_NOT_CONTAIN_LEMMA:" + synset_id)

    definitions_raw = raw.get("definition", raw.get("definitions", []))
    if isinstance(definitions_raw, str):
        definitions_raw = [definitions_raw]
    if not isinstance(definitions_raw, Sequence) or isinstance(definitions_raw, (str, bytes)):
        raise OEWNReleaseError("SYNSET_DEFINITION_INVALID:" + synset_id)
    definitions = [
        " ".join(str(x).strip().split())
        for x in definitions_raw
        if isinstance(x, str) and x.strip()
    ]

    examples_raw = raw.get("example", raw.get("examples", []))
    if isinstance(examples_raw, str):
        examples_raw = [examples_raw]
    if not isinstance(examples_raw, Sequence) or isinstance(examples_raw, (str, bytes)):
        raise OEWNReleaseError("SYNSET_EXAMPLE_INVALID:" + synset_id)
    examples = [
        " ".join(str(x).strip().split())
        for x in examples_raw
        if isinstance(x, str) and x.strip()
    ]

    relation_fields = {}
    for key, value in raw.items():
        if key in {
            "members", "definition", "definitions", "example", "examples",
            "ili", "partOfSpeech",
        }:
            continue
        relation_fields[str(key)] = deepcopy(value)

    return {
        "synset_id": synset_id,
        "part_of_speech": str(raw.get("partOfSpeech") or synset_id.rsplit("-", 1)[-1]),
        "lexname": lexname,
        "members": members,
        "definitions": definitions,
        "examples": examples,
        "ili": raw.get("ili"),
        "relations": relation_fields,
    }


def _enumerate_unchecked(
    raw: bytes,
    lemma: str,
    pos: str | None,
) -> dict[str, Any]:
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except Exception as exc:
        raise OEWNReleaseError("ARCHIVE_NOT_VALID_ZIP") from exc

    with zf:
        names = _safe_members(zf)
        entry_files = sorted(
            n for n in names
            if n.startswith("entries-") and n.endswith(".json") and "/" not in n
        )
        if not entry_files:
            raise OEWNReleaseError("ENTRY_FILES_MISSING")

        entry_rows: list[tuple[str, Mapping[str, Any]]] = []
        for name in entry_files:
            data = _load_json_member(zf, name)
            if not isinstance(data, Mapping):
                raise OEWNReleaseError("ENTRY_FILE_NOT_OBJECT:" + name)
            for surface, payload in data.items():
                if _norm_lemma(surface) == lemma:
                    if not isinstance(payload, Mapping):
                        raise OEWNReleaseError("LEMMA_ENTRY_INVALID:" + name)
                    entry_rows.append((name, payload))

        if len(entry_rows) > 1:
            raise OEWNReleaseError("LEMMA_DUPLICATED_ACROSS_ENTRY_FILES")

        if not entry_rows:
            return {
                "lemma": lemma,
                "requested_part_of_speech": pos,
                "entry_files_scanned": len(entry_files),
                "entry_file": None,
                "senses": [],
                "release_relative_absence": True,
            }

        entry_file, payload = entry_rows[0]
        raw_senses: list[dict[str, str]] = []
        for pos_key, pos_payload in payload.items():
            pos_key = str(pos_key)
            if pos is not None and pos_key != pos:
                continue
            if pos_key not in POS:
                continue
            if not isinstance(pos_payload, Mapping):
                raise OEWNReleaseError("POS_ENTRY_INVALID:" + pos_key)
            senses = pos_payload.get("sense")
            if not isinstance(senses, Sequence) or isinstance(senses, (str, bytes)):
                raise OEWNReleaseError("SENSE_LIST_INVALID:" + pos_key)
            for i, sense in enumerate(senses):
                if not isinstance(sense, Mapping):
                    raise OEWNReleaseError(f"SENSE_INVALID:{pos_key}:{i}")
                sense_id = str(sense.get("id") or "").strip()
                synset_id = str(sense.get("synset") or "").strip()
                if not sense_id or not synset_id:
                    raise OEWNReleaseError(f"SENSE_ID_OR_SYNSET_MISSING:{pos_key}:{i}")
                raw_senses.append({
                    "sense_id": sense_id,
                    "synset_id": synset_id,
                    "part_of_speech": pos_key,
                })

        sense_ids = [x["sense_id"] for x in raw_senses]
        if len(sense_ids) != len(set(sense_ids)):
            raise OEWNReleaseError("DUPLICATE_SENSE_ID")
        sense_pairs = [(x["part_of_speech"], x["synset_id"]) for x in raw_senses]
        if len(sense_pairs) != len(set(sense_pairs)):
            raise OEWNReleaseError("DUPLICATE_SYNSET_FOR_LEMMA_POS")

        synset_targets = {x["synset_id"] for x in raw_senses}
        found: dict[str, tuple[str, Mapping[str, Any]]] = {}
        synset_files = sorted(
            n for n in names
            if n.endswith(".json")
            and not n.startswith("entries-")
            and n != "frames.json"
            and "/" not in n
        )
        if synset_targets and not synset_files:
            raise OEWNReleaseError("SYNSET_FILES_MISSING")

        for name in synset_files:
            data = _load_json_member(zf, name)
            if not isinstance(data, Mapping):
                raise OEWNReleaseError("SYNSET_FILE_NOT_OBJECT:" + name)
            overlap = synset_targets.intersection(str(k) for k in data.keys())
            for sid in overlap:
                if sid in found:
                    raise OEWNReleaseError("SYNSET_DUPLICATED_ACROSS_FILES:" + sid)
                record = data.get(sid)
                if not isinstance(record, Mapping):
                    raise OEWNReleaseError("SYNSET_RECORD_INVALID:" + sid)
                found[sid] = (name, record)

        missing = sorted(synset_targets - set(found))
        if missing:
            raise OEWNReleaseError("REFERENCED_SYNSET_MISSING:" + ",".join(missing))

        out = []
        for sense in raw_senses:
            sid = sense["synset_id"]
            filename, record = found[sid]
            lexname = filename[:-5]
            normalized = _normalize_synset_record(
                synset_id=sid,
                lexname=lexname,
                raw=record,
                lemma=lemma,
            )
            out.append({
                **sense,
                **normalized,
                "synset_source_file": filename,
            })

        out.sort(key=lambda x: (x["part_of_speech"], x["sense_id"], x["synset_id"]))
        return {
            "lemma": lemma,
            "requested_part_of_speech": pos,
            "entry_files_scanned": len(entry_files),
            "entry_file": entry_file,
            "senses": out,
            "release_relative_absence": len(out) == 0,
        }


def enumerate_senses(
    archive: bytes | bytearray | str | Path,
    lemma: str,
    *,
    part_of_speech: str | None = None,
) -> dict[str, Any]:
    """Enumerate all OEWN-2025 senses for one exact normalized lemma/POS.

    A successful result means the candidate list is complete relative to the
    exact content-addressed OEWN 2025 JSON release bytes. It never means the
    intended contextual sense has been identified.
    """
    try:
        raw = _read_archive_bytes(archive)
        digest = sha256(raw).hexdigest()
        if digest != RELEASE_SHA256:
            return _base(
                "FAIL_CLOSED__OEWN_2025_RELEASE_HASH_MISMATCH",
                passed=False,
                observed_archive_sha256=digest,
                expected_archive_sha256=RELEASE_SHA256,
            )

        lemma_n = _norm_lemma(lemma)
        pos = None if part_of_speech is None else str(part_of_speech).strip().lower()
        if pos is not None and pos not in POS:
            raise OEWNReleaseError("PART_OF_SPEECH_INVALID")

        result = _enumerate_unchecked(raw, lemma_n, pos)
        senses = result["senses"]
        return _base(
            (
                "PASS__OEWN_2025_RELEASE_RELATIVE_SENSE_UNIVERSE_ENUMERATED"
                if senses
                else "PASS__LEMMA_OR_POS_ABSENT_FROM_OEWN_2025_RELEASE"
            ),
            passed=True,
            archive_sha256=digest,
            official_release_urls=list(OFFICIAL_URLS),
            lemma=lemma_n,
            requested_part_of_speech=pos,
            entry_file=result["entry_file"],
            entry_files_scanned=result["entry_files_scanned"],
            sense_count=len(senses),
            senses=senses,
            release_relative_absence=result["release_relative_absence"],
            candidate_set_complete_relative_to_release=True,
            knowledge_scope=(
                "EXACT_OEWN_2025_JSON_RELEASE_BYTES_ONLY__"
                "NOT_OPEN_WORLD_ENGLISH_COMPLETENESS"
            ),
            intended_sense_identified=False,
            open_world_english_sense_completeness_claimed=False,
        )
    except Exception as exc:
        return _base(
            "FAIL_CLOSED",
            passed=False,
            reason=type(exc).__name__ + ":" + str(exc),
        )
