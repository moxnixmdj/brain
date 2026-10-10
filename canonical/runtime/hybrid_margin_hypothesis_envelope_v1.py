"""Open-world-safe hybrid hypothesis envelope for the noun 'margin'.

Combines:
- the exact six noun senses from the pinned OEWN 2025 release;
- the exact FIBO Q2 2026 DebtInstruments/Margin concept authenticated from
  the pinned upstream commit; and
- an explicit OPEN_WORLD_REMAINDER.

This is candidate/hypothesis authority only.  It does not assert that OEWN and
FIBO hypotheses are disjoint, that the named hypotheses exhaust finance meaning,
or that any hypothesis is the intended sense.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import oewn_release_sense_universe_v1 as oewn
from canonical.runtime.https_source_fragment_projection_authority_v2 import (
    verify_projection_pack,
)

SCHEMA = "PROJECT_BRAIN_HYBRID_MARGIN_HYPOTHESIS_ENVELOPE_V1"
PACK_PATH = "canonical/evidence/FIBO_MARGIN_SOURCE_PACK_V1.json"
PACK_GIT_BLOB_SHA = "841ffcc44f39feec46bf47138af6ce8ad7e7d9bf"
FIBO_UPSTREAM_COMMIT = "f59157fe156e3d91b1c045222d0a7dc06b7d78a2"
FIBO_MARGIN_ID = (
    "https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/"
    "DebtInstruments/Margin"
)
FIBO_MARGIN_DEFINITION = (
    "a variable that is added to a specified index rate to determine the "
    "fully indexed interest rate charged to a borrower on a credit balance"
)
FIBO_MARGIN_SYNONYM = "spread"
EXPECTED_FIBO_URL = (
    "https://raw.githubusercontent.com/edmcouncil/fibo/"
    + FIBO_UPSTREAM_COMMIT
    + "/SEC/Debt/DebtInstruments.rdf"
)
EXPECTED_OEWN = {
    "margin%1:07:00::": "05127983-n",
    "margin%1:07:01::": "04757264-n",
    "margin%1:10:00::": "06401041-n",
    "margin%1:21:01::": "13372293-n",
    "margin%1:21:02::": "13281661-n",
    "margin%1:25:00::": "13926393-n",
}
ROOT = Path(__file__).resolve().parents[2]


def _git_blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "candidate_generation_authority": False,
        "semantic_truth_authority": False,
        "intended_sense_identified": False,
        "explicit_hypothesis_set_complete": False,
        "open_world_finance_semantics_complete": False,
        "hypotheses_mutually_exclusive_proved": False,
        "safe_for_exact_minimax_world_solver": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _validate_oewn(universe: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(universe, Mapping) or universe.get("schema") != oewn.SCHEMA:
        raise ValueError("OEWN_UNIVERSE_SCHEMA_INVALID")
    required = {
        "pass": True,
        "release_id": oewn.RELEASE_ID,
        "archive_sha256": oewn.RELEASE_SHA256,
        "lemma": "margin",
        "requested_part_of_speech": "n",
        "candidate_set_complete_relative_to_release": True,
        "open_world_english_sense_completeness_claimed": False,
        "intended_sense_identified": False,
    }
    bad = [k for k, v in required.items() if universe.get(k) != v]
    if bad:
        raise ValueError("OEWN_UNIVERSE_BINDING_INVALID:" + ",".join(sorted(bad)))
    senses = universe.get("senses")
    if not isinstance(senses, list) or len(senses) != len(EXPECTED_OEWN):
        raise ValueError("OEWN_MARGIN_SENSE_COUNT_INVALID")
    observed = {}
    rows = []
    for i, raw in enumerate(senses):
        if not isinstance(raw, Mapping):
            raise ValueError("OEWN_SENSE_NOT_OBJECT:" + str(i))
        sid = str(raw.get("sense_id") or "")
        syn = str(raw.get("synset_id") or "")
        if not sid or sid in observed:
            raise ValueError("OEWN_SENSE_ID_INVALID_OR_DUPLICATE:" + str(i))
        observed[sid] = syn
        rows.append(deepcopy(dict(raw)))
    if observed != EXPECTED_OEWN:
        raise ValueError("OEWN_MARGIN_RELEASE_SENSE_SET_MISMATCH")
    return rows


def _load_fibo_pack(*, repo_root: str | Path | None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    path = (root / PACK_PATH).resolve(strict=True)
    path.relative_to(root)
    if not path.is_file() or path.is_symlink():
        raise ValueError("FIBO_MARGIN_PACK_INVALID")
    raw = path.read_bytes()
    blob = _git_blob(raw)
    if blob != PACK_GIT_BLOB_SHA:
        raise ValueError("FIBO_MARGIN_PACK_GIT_BLOB_DRIFT:" + blob)
    doc = json.loads(raw.decode("utf-8"))
    if doc.get("schema") != "PROJECT_BRAIN_HTTPS_SOURCE_FRAGMENT_PROJECTION_PACK_V2":
        raise ValueError("FIBO_MARGIN_PACK_SCHEMA_INVALID")
    if doc.get("source_id") != "FIBO_Q2_2026_DEBT_INSTRUMENTS_MARGIN":
        raise ValueError("FIBO_MARGIN_SOURCE_ID_INVALID")
    if doc.get("url") != EXPECTED_FIBO_URL:
        raise ValueError("FIBO_MARGIN_SOURCE_URL_INVALID")
    fragments = doc.get("fragments")
    if not isinstance(fragments, list) or len(fragments) != 1:
        raise ValueError("FIBO_MARGIN_FRAGMENT_SET_INVALID")
    if fragments[0].get("fragment_id") != "FIBO_MARGIN_CLASS":
        raise ValueError("FIBO_MARGIN_FRAGMENT_ID_INVALID")
    return {"pack": doc, "pack_git_blob_sha": blob}


def build(
    oewn_universe: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
    projection_verifier=verify_projection_pack,
) -> dict[str, Any]:
    try:
        senses = _validate_oewn(oewn_universe)
        checked = _load_fibo_pack(repo_root=repo_root)
        source = projection_verifier(deepcopy(checked["pack"]))
        if not isinstance(source, Mapping) or source.get("pass") is not True:
            return _base(
                "FAIL_CLOSED",
                reason="FIBO_MARGIN_SOURCE_AUTHORITY_FAILED",
                fibo_source_result=source,
            )
        fragment_ids = set(
            str(x) for x in source.get("receipt", {}).get("fragment_ids", [])
        )
        if "FIBO_MARGIN_CLASS" not in fragment_ids:
            return _base(
                "FAIL_CLOSED",
                reason="FIBO_MARGIN_FRAGMENT_NOT_AUTHENTICATED",
                fibo_source_result=source,
            )

        hypotheses = []
        for sense in senses:
            hypotheses.append({
                "hypothesis_id": "OEWN::" + sense["sense_id"],
                "source_family": "OEWN_2025_RELEASE_SENSE",
                "sense_id": sense["sense_id"],
                "synset_id": sense["synset_id"],
                "part_of_speech": sense["part_of_speech"],
                "definitions": deepcopy(sense.get("definitions") or []),
                "members": deepcopy(sense.get("members") or []),
                "examples": deepcopy(sense.get("examples") or []),
                "candidate_only": True,
            })
        hypotheses.append({
            "hypothesis_id": "FIBO::" + FIBO_MARGIN_ID,
            "source_family": "FIBO_Q2_2026_PINNED_CONCEPT",
            "concept_id": FIBO_MARGIN_ID,
            "surface": "margin",
            "definition": FIBO_MARGIN_DEFINITION,
            "synonym": FIBO_MARGIN_SYNONYM,
            "candidate_only": True,
        })
        hypotheses.append({
            "hypothesis_id": "OPEN_WORLD_REMAINDER::margin:n",
            "source_family": "OPEN_WORLD_REMAINDER",
            "description": (
                "any contextually valid noun meaning of margin not yet covered "
                "by the enumerated OEWN release senses or authenticated FIBO candidate"
            ),
            "candidate_only": True,
        })
        material = {
            "oewn_release_sha256": oewn.RELEASE_SHA256,
            "oewn_sense_ids": sorted(EXPECTED_OEWN),
            "fibo_pack_git_blob_sha": checked["pack_git_blob_sha"],
            "fibo_source_receipt_sha256": source["receipt"]["receipt_sha256"],
            "fibo_margin_id": FIBO_MARGIN_ID,
            "remainder_id": "OPEN_WORLD_REMAINDER::margin:n",
        }
        return _base(
            "PASS__OPEN_WORLD_SAFE_HYBRID_MARGIN_HYPOTHESIS_ENVELOPE",
            passed=True,
            candidate_generation_authority=True,
            lemma="margin",
            part_of_speech="n",
            hypotheses=hypotheses,
            hypothesis_count=len(hypotheses),
            named_hypothesis_count=len(hypotheses) - 1,
            oewn_release_sense_count=len(senses),
            oewn_release_sense_set_complete=True,
            fibo_margin_source_authenticated=True,
            open_world_remainder_required=True,
            open_world_remainder_present=True,
            explicit_hypothesis_set_complete=False,
            hypotheses_mutually_exclusive_proved=False,
            safe_for_exact_minimax_world_solver=False,
            intended_sense_identified=False,
            envelope_sha256=_sha(material),
            fibo_source_result=source,
            boundary=(
                "OEWN_COMPLETENESS_IS_RELEASE_RELATIVE_ONLY__FIBO_EXACT_LABEL_"
                "CONCEPT_IS_CANDIDATE_ONLY__OPEN_WORLD_REMAINDER_CANNOT_BE_DROPPED__"
                "NO_HYPOTHESIS_DISJOINTNESS_GLOBAL_FINANCE_COMPLETENESS_OR_SENSE_SELECTION"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))
