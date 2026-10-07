"""Strong visible P2 quality certifier with recomputed explicit-source membership.

This wrapper prevents callers from self-asserting lossless P2 membership for the
strict explicit JSON source class. Membership is recomputed from raw bytes and its
receipt is injected internally before the existing v3 quality certifier runs.

Other quality-binding receipts remain separate upstream obligations.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.p2_explicit_contract_membership_v1 import compile_membership
from canonical.runtime.p2_strong_quality_visible_certifier_v3 import certify as certify_v3

SCHEMA = "BRAIN_P2_STRONG_QUALITY_VISIBLE_CERTIFIER_V4"


def certify(bundle: Any) -> dict[str, Any]:
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

    quality = bundle.get("quality_binding")
    if not isinstance(quality, Mapping):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "pass": False, "errors": ["QUALITY_BINDING_INVALID"], "membership": membership, "terminal_authority": False}

    qb = dict(quality)
    qb["lossless_p2_membership_proved"] = True
    qb["lossless_p2_membership_receipt"] = membership["membership_receipt"]
    downstream = certify_v3({"public": membership["public"], "quality_binding": qb})
    out = dict(downstream)
    out["schema"] = SCHEMA
    out["membership"] = membership
    out["membership_self_assertion_permitted"] = False
    out["terminal_authority"] = False
    return out
