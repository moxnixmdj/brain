"""Bounded N-filing semantic-contract stability for SEC issuer extensions.

This module generalizes the verified pairwise V1 theorem to a bounded group.
Every filing is independently rederived from its raw XSD and label bytes before
comparison. The group result proves only equality or drift of the Brain-owned
semantic contract over the exact supplied filing set.

It does not prove concept identity, standard-taxonomy equivalence, open-world
completeness, or future stability.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import pathlib
from typing import Any, Mapping, Sequence

from canonical.runtime import sec_issuer_extension_cross_filing_stability_v1 as pairwise

SCHEMA = "PROJECT_BRAIN_SEC_ISSUER_EXTENSION_CROSS_FILING_STABILITY_V2"
MIN_MEMBERS = 2
MAX_MEMBERS = 64


def _base(status: str, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "bounded_group_semantic_contract_stable": False,
        "bounded_group_semantic_stability_authority": False,
        "concept_identity_authority": False,
        "standard_taxonomy_equivalence_authority": False,
        "future_stability_claimed": False,
        "open_world_finance_semantics_complete": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _member_paths(root: pathlib.Path, raw: Mapping[str, Any]) -> dict[str, pathlib.Path]:
    return {
        "xsd": pairwise._safe(root, raw.get("xsd_path")),
        "label": pairwise._safe(root, raw.get("label_path")),
        "semantic": pairwise._safe(root, raw.get("semantic_path")),
    }


def verify_group(
    *,
    root: Any,
    members: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    try:
        if not isinstance(members, Sequence) or isinstance(
            members, (str, bytes, bytearray)
        ):
            return _base("FAIL_CLOSED", reason="MEMBERS_SEQUENCE_REQUIRED")
        if len(members) < MIN_MEMBERS or len(members) > MAX_MEMBERS:
            return _base(
                "FAIL_CLOSED",
                reason="MEMBER_COUNT_OUT_OF_BOUNDS",
                member_count=len(members),
                min_members=MIN_MEMBERS,
                max_members=MAX_MEMBERS,
            )

        root_path = pathlib.Path(root).resolve()
        rows: list[dict[str, Any]] = []
        issuer_cik: str | None = None
        local_name: str | None = None
        filing_dirs: set[str] = set()

        for index, raw in enumerate(members):
            if not isinstance(raw, Mapping):
                return _base(
                    "FAIL_CLOSED",
                    reason="MEMBER_NOT_OBJECT",
                    member_index=index,
                )
            paths = _member_paths(root_path, raw)
            verified = pairwise.concept_verify.verify(
                root=root_path,
                xsd_path=str(paths["xsd"].relative_to(root_path)),
                label_path=str(paths["label"].relative_to(root_path)),
                semantic_path=str(paths["semantic"].relative_to(root_path)),
            )
            if verified.get("verified") is not True:
                return _base(
                    "FAIL_CLOSED",
                    reason="UPSTREAM_CONCEPT_SEMANTICS_REDERIVATION_FAILED",
                    member_index=index,
                    member_verification=verified,
                )

            doc = pairwise._load(paths["semantic"])
            cik, filing_dir = pairwise._filing(doc.get("xsd_url"))
            signature = pairwise._signature(doc)

            if issuer_cik is None:
                issuer_cik = cik
            elif cik != issuer_cik:
                return _base(
                    "FAIL_CLOSED",
                    reason="CROSS_ISSUER_GROUP_FORBIDDEN",
                    member_index=index,
                    expected_issuer_cik=issuer_cik,
                    observed_issuer_cik=cik,
                )

            current_local = str(signature.get("local_name") or "")
            if local_name is None:
                local_name = current_local
            elif current_local != local_name:
                return _base(
                    "FAIL_CLOSED",
                    reason="LOCAL_NAME_MISMATCH",
                    member_index=index,
                    expected_local_name=local_name,
                    observed_local_name=current_local,
                )

            if filing_dir in filing_dirs:
                return _base(
                    "FAIL_CLOSED",
                    reason="DISTINCT_FILING_DIRECTORIES_REQUIRED",
                    duplicate_filing_directory=filing_dir,
                )
            filing_dirs.add(filing_dir)

            rows.append(
                {
                    "member_index": index,
                    "filing_directory": filing_dir,
                    "concept_qname": doc.get("concept_qname"),
                    "signature": signature,
                    "signature_sha256": _sha(signature),
                    "xsd_sha256": doc.get("xsd_sha256"),
                    "label_sha256": doc.get("label_sha256"),
                }
            )

        assert issuer_cik is not None
        assert local_name is not None

        by_signature: dict[str, list[int]] = {}
        for row in rows:
            by_signature.setdefault(row["signature_sha256"], []).append(
                row["member_index"]
            )

        signatures = {
            digest: deepcopy(rows[indexes[0]]["signature"])
            for digest, indexes in by_signature.items()
        }

        material = {
            "issuer_cik": issuer_cik,
            "local_name": local_name,
            "member_count": len(rows),
            "filing_directories": [row["filing_directory"] for row in rows],
            "member_semantic_receipts": [
                {
                    "member_index": row["member_index"],
                    "filing_directory": row["filing_directory"],
                    "concept_qname": row["concept_qname"],
                    "signature_sha256": row["signature_sha256"],
                    "xsd_sha256": row["xsd_sha256"],
                    "label_sha256": row["label_sha256"],
                }
                for row in rows
            ],
        }

        if len(by_signature) == 1:
            only_digest = next(iter(by_signature))
            return _base(
                "PASS__BOUNDED_GROUP_CROSS_FILING_SEMANTIC_CONTRACT_STABILITY_PROVED",
                passed=True,
                bounded_group_semantic_contract_stable=True,
                bounded_group_semantic_stability_authority=True,
                semantic_contract_equality_proved=True,
                issuer_cik=issuer_cik,
                local_name=local_name,
                member_count=len(rows),
                filing_directories=[row["filing_directory"] for row in rows],
                semantic_signature=deepcopy(signatures[only_digest]),
                semantic_signature_sha256=only_digest,
                member_semantic_receipts=material["member_semantic_receipts"],
                stability_receipt_sha256=_sha(material),
                relation="SAME_BRAIN_OWNED_SEMANTIC_CONTRACT_ACROSS_BOUNDED_FILING_SET",
                boundary=(
                    "BOUNDED_SAME_ISSUER_SAME_LOCAL_NAME_EXACT_SUPPLIED_FILING_SET__"
                    "EACH_MEMBER_INDEPENDENTLY_REDERIVED_FROM_RAW_XSD_AND_LABEL_BYTES__"
                    "NO_CONCEPT_IDENTITY_STANDARD_TAXONOMY_EQUIVALENCE_OPEN_WORLD_"
                    "COMPLETENESS_OR_FUTURE_STABILITY"
                ),
            )

        baseline = rows[0]["signature"]
        differing_fields = sorted(
            {
                key
                for row in rows[1:]
                for key in sorted(set(baseline) | set(row["signature"]))
                if baseline.get(key) != row["signature"].get(key)
            }
        )
        partitions = [
            {
                "signature_sha256": digest,
                "member_indexes": list(indexes),
                "filing_directories": [
                    rows[index]["filing_directory"] for index in indexes
                ],
                "semantic_signature": deepcopy(signatures[digest]),
            }
            for digest, indexes in sorted(by_signature.items())
        ]
        return _base(
            "PASS__BOUNDED_GROUP_CROSS_FILING_SEMANTIC_CONTRACT_DRIFT_DETECTED",
            passed=True,
            bounded_group_semantic_contract_stable=False,
            bounded_group_semantic_stability_authority=True,
            semantic_contract_equality_proved=True,
            issuer_cik=issuer_cik,
            local_name=local_name,
            member_count=len(rows),
            filing_directories=[row["filing_directory"] for row in rows],
            member_semantic_receipts=material["member_semantic_receipts"],
            signature_partition_count=len(partitions),
            signature_partitions=partitions,
            differing_fields=differing_fields,
            relation="SEMANTIC_CONTRACT_DIFFERS_WITHIN_BOUNDED_FILING_SET",
            boundary=(
                "EXACT_BOUNDED_SET_COMPARISON_OF_BRAIN_OWNED_ISSUER_EXTENSION_"
                "SEMANTIC_FIELDS_ONLY__NO_GENERAL_INSTABILITY_OR_IDENTITY_CLAIM"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))


def run(args: Mapping[str, Any], root: Any) -> dict[str, Any]:
    return verify_group(root=root, members=args.get("members"))
