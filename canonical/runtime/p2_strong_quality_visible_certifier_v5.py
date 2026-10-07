"""P2 strong-visible quality certifier v5 with authenticated upstream bindings.

V5 recomputes lossless explicit P2 membership from raw task bytes and accepts no
opaque quality receipt strings. Every remaining quality binding is reconstructed
from a content-addressed receipt + independent-verification pair bound to the same
normalized P2 context.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.p2_explicit_contract_membership_v1 import compile_membership
from canonical.runtime.p2_quality_binding_authenticator_v1 import authenticate
from canonical.runtime.p2_strong_quality_visible_certifier_v3 import certify as certify_v3

SCHEMA = "BRAIN_P2_STRONG_QUALITY_VISIBLE_CERTIFIER_V5"
ROOT = Path(__file__).resolve().parents[2]


def certify(bundle: Any, *, repo_root: str | Path = ROOT) -> dict[str, Any]:
    if not isinstance(bundle, Mapping):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "pass": False, "errors": ["BUNDLE_NOT_OBJECT"], "terminal_authority": False}

    raw = bundle.get("raw_p2_source")
    source_id = bundle.get("raw_p2_source_id")
    if not isinstance(raw, (str, bytes)) or not isinstance(source_id, str):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "pass": False, "errors": ["RAW_P2_SOURCE_AND_ID_REQUIRED"], "terminal_authority": False}

    membership = compile_membership(raw, source_id=source_id)
    if membership.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["LOSSLESS_P2_MEMBERSHIP_RECOMPUTE_FAILED", *(membership.get("errors") or [])],
            "membership": membership,
            "terminal_authority": False,
        }

    auth = authenticate(
        bundle.get("quality_binding_references"),
        context_sha256=membership["normalized_public_sha256"],
        repo_root=repo_root,
    )
    if auth.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["QUALITY_BINDING_AUTHENTICATION_FAILED", *(auth.get("errors") or [])],
            "membership": membership,
            "quality_binding_authentication": auth,
            "terminal_authority": False,
        }

    qb = dict(auth["quality_binding"])
    qb["lossless_p2_membership_proved"] = True
    qb["lossless_p2_membership_receipt"] = membership["membership_receipt"]

    downstream = certify_v3({"public": membership["public"], "quality_binding": qb})
    out = dict(downstream)
    out["schema"] = SCHEMA
    out["membership"] = membership
    out["quality_binding_authentication"] = auth
    out["opaque_caller_receipts_permitted"] = False
    out["terminal_authority"] = False
    return out
