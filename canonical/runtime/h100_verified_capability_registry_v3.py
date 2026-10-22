"""Registry V3: V2 plus computer use, composed not edited.

V3 preserves every V1 and V2 route unchanged and adds one separately
verified capability family: computer use.

Unknown inputs do not proceed -- but the two families refuse
differently, and the difference is deliberate rather than tidy. An
unregistered computer-use id returns a FAIL_CLOSED receipt, because
computer use is new here and its callers are new. A legacy id is
handed straight to V2, which RAISES, exactly as it always has.
Converting that into a receipt would change the behaviour of already
verified code in order to make two error shapes match, which is the
wrong trade: cosmetic consistency is not worth altering a verified
route. This is the same composition pattern V2 used for the cubic
patch, applied for the same reason -- the verified core stays
untouched, and a new family is added beside it rather than by altering
what has already been verified.

Why this matters, in one line: before this, the Brain could plan and
verify with real rigour but could only ever produce two effects --
write a receipt, append to a ledger. The effect layer was two tools
wide. Computer use closes that, and it does so by joining the
registry rather than by building a second control loop beside it.

One signature difference: computer-use capabilities act on a
filesystem, so they need a root. V2's invoke takes no root, so V3
accepts an optional one and passes it through. Every pre-existing
route is dispatched exactly as before, with root never consulted.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_verified_capability_registry_v2 as v2
from canonical.runtime import h100_computer_use_registry_v1 as cu
from canonical.runtime import h100_generic_patch_search_transfer_v1 as transfer

SCHEMA = "PROJECT_BRAIN_H100_VERIFIED_CAPABILITY_REGISTRY_V3"

# The frozen precommit is the authorization for which patch-transfer families
# V3 may route, and at which fixed shape parameter. Reading it here rather than
# restating the four families keeps the code from drifting away from the receipt
# that authorizes them.
_PRECOMMIT = (Path(__file__).resolve().parents[2]
              / "canonical/governance/H100_REGISTRY_V3_COMPILE_PRECOMMIT_V1.json")


def _authorized_transfer_families():
    """Return ``(precommit_doc, families)`` for the authorized transfer routes.

    A ``FIXED_POWER_n`` shape policy pins the family to that single power, so
    the rest of the search grid for that family is not authorized and is
    skipped. Any policy that cannot be read contributes no route at all, which
    fails closed rather than guessing a shape.
    """
    doc = json.loads(_PRECOMMIT.read_text(encoding="utf-8"))
    families = []
    for addition in doc.get("additions") or []:
        if not isinstance(addition, Mapping):
            continue
        family = str(addition.get("family") or "")
        cid = str(addition.get("capability_id") or "")
        policy = str(addition.get("shape_policy") or "")
        if not family or not cid:
            continue
        fixed_power = None
        if policy.startswith("FIXED_POWER_"):
            try:
                fixed_power = int(policy.rsplit("_", 1)[1])
            except ValueError:
                continue
        families.append({
            "family": family,
            "capability_id": cid,
            "shape_policy": policy,
            "fixed_power": fixed_power,
        })
    return doc, families


REGISTRY = tuple(v2.REGISTRY) + tuple(cu.REGISTRY)

_BY_ID = {row["capability_id"]: row for row in REGISTRY}
_COMPUTER_USE_IDS = frozenset(
    row["capability_id"] for row in cu.REGISTRY)


class CapabilityRegistryV3Error(ValueError):
    pass


def registry_snapshot() -> dict[str, Any]:
    base = v2.registry_snapshot()
    return {
        "schema": SCHEMA,
        "status": "VERIFIED_CAPABILITY_REGISTRY_V3_READY",
        "entry_count": len(REGISTRY),
        "v2_entry_count": base.get("entry_count"),
        "computer_use_entry_count": len(cu.REGISTRY),
        "capability_ids": sorted(_BY_ID),
        "persistent_learned_bytes": 0,
        "external_learned_capability_calls": 0,
        "routing_priority":
            "V1_LIBRARY_THEN_VERIFIED_CUBIC_THEN_COMPUTER_USE",
    }


def resolve_verified_capability(
    rows: Sequence[Mapping[str, Any]],
    *,
    target: str,
    input_name: str | None = None,
    exact_nrmse: float = 1e-8,
) -> dict[str, Any]:
    """Resolve a verified capability for a row set, V2 routes unchanged.

    V3 widens the registry with the computer-use rows and dispatches them from
    :func:`invoke`. Those capabilities are *invoked*, not fitted to a row set,
    so resolution itself is unchanged from V2 -- the V1 library first, then the
    verified cubic -- which is what ``routing_priority`` in
    :func:`registry_snapshot` already advertised. The envelope is re-stamped
    with this registry's schema and version so a caller can tell which registry
    answered, exactly as V2 re-stamps V1 and V4 re-stamps this module.

    V3 was the only link in the chain that never defined this function, while
    V4 through V8 each delegated down to ``v3.resolve_verified_capability``. The
    result was that every resolution above V3 died with AttributeError on the
    last hop instead of returning a verdict.

    Beyond restoring the hop, V3 is where the four independently verified
    patch-transfer families become library hits. They are read from the frozen
    precommit rather than listed here, the fit reuses the existing zero-learned
    least-squares search, and the precommit's own routing contract is enforced:
    V2 runs first unchanged, a new family must fit within ``exact_nrmse``, two
    families fitting exactly is a fail-closed ambiguity rather than a pick, and
    the unverified rational and absolute-value grammars stay unrouted.
    """
    base = v2.resolve_verified_capability(
        rows, target=target, input_name=input_name, exact_nrmse=exact_nrmse)
    if base.get("status") == "LIBRARY_HIT__VERIFY_BEFORE_USE":
        out = dict(base)
        out["schema"] = SCHEMA
        out["registry_version"] = 3
        return out

    doc, families = _authorized_transfer_families()
    name = v2._input_name(rows, target, input_name)
    hits = _exact_family_matches(rows, families, target, name, exact_nrmse)

    if len(hits) > 1:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__AMBIGUOUS_FAMILY_MATCH",
            "registry_version": 3,
            "reason": "IF_MULTIPLE_NEW_FAMILIES_PASS_EXACTLY__FAIL_CLOSED_AMBIGUOUS",
            "candidate_capability_ids": sorted(h["capability_id"] for h in hits),
            "match": None,
            "persistent_learned_bytes": 0,
            "external_learned_capability_calls": 0,
        }

    if len(hits) == 1:
        h = hits[0]
        return {
            "schema": SCHEMA,
            "status": "LIBRARY_HIT__VERIFY_BEFORE_USE",
            "registry_version": 3,
            "match": {
                "capability_id": h["capability_id"],
                "family": h["family"],
                "route": "AFFINE_PLUS_VERIFIED_TRANSFER_BASIS",
                "candidate": {
                    "shape_policy": h["shape_policy"],
                    "shape_parameter": h["shape_parameter"],
                    "coefficients": h["coefficients"],
                    "complexity_rank": h["complexity_rank"],
                    "train_nrmse": h["train_nrmse"],
                },
                "prior_verification": doc.get("authorization"),
            },
            "persistent_learned_bytes": 0,
            "external_learned_capability_calls": 0,
            "raw_synthesis_attempts_before_hit": 0,
        }

    out = dict(base)
    out["schema"] = SCHEMA
    out["registry_version"] = 3
    return out


def _exact_family_matches(rows, families, target, input_name, exact_nrmse):
    """Return the authorized families that fit ``rows`` exactly.

    Deliberately returns every exact family rather than the first one, so the
    caller can fail closed on ambiguity instead of silently preferring
    whichever family the grid happened to reach first.
    """
    if not families or input_name is None:
        return []
    xs = []
    ys = []
    for r in rows:
        xv = r.get(input_name)
        yv = r.get(target)
        if isinstance(xv, (int, float)) and isinstance(yv, (int, float)):
            xs.append(float(xv))
            ys.append(float(yv))
    if len(xs) < 3:
        return []

    hits = []
    for fam in families:
        best = None
        for fid, param, rank, feature in transfer._specs(
                None, family=fam["family"], train_x=xs):
            if fam["fixed_power"] is not None and param != fam["fixed_power"]:
                continue
            coeffs = transfer._fit_linear3(xs, ys, feature)
            if coeffs is None:
                continue
            pred = [coeffs[0] + coeffs[1] * x + coeffs[2] * feature(x) for x in xs]
            nrmse = transfer._nrmse(ys, pred)
            if nrmse <= exact_nrmse and (best is None or nrmse < best["train_nrmse"]):
                best = {
                    "capability_id": fam["capability_id"],
                    "family": fam["family"],
                    "shape_policy": fam["shape_policy"],
                    "shape_parameter": param,
                    "coefficients": coeffs,
                    "complexity_rank": rank,
                    "train_nrmse": nrmse,
                }
        if best is not None:
            hits.append(best)
    return hits


def invoke(capability_id: str, payload: Mapping[str, Any],
           root: str | None = None) -> dict[str, Any]:
    """Dispatch any registered capability, V2 routes unchanged."""
    cid = str(capability_id or "")
    if cid in _COMPUTER_USE_IDS:
        if root is None:
            return {"schema": SCHEMA, "status": "FAIL_CLOSED",
                    "reason": "ROOT_REQUIRED_FOR_COMPUTER_USE",
                    "capability_id": cid}
        out = cu.invoke(cid, payload, root)
        out["registry"] = SCHEMA
        return out
    # Unchanged path: every V1/V2 route behaves exactly as it did.
    return v2.invoke(capability_id, payload)
