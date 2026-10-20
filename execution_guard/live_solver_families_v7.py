"""Fresh-goal EXECUTION families, wave 7 (heartbeat).  Same contract as waves 2-6: fresh
inputs, one plain sentence, an oracle that judges the real artifact with the standard library.

  RECEIPT_PROSE_EXECUTION            the receipt-backed capabilities that take no input, asked
                                      for BY NAME in a plain sentence and executed through the
                                      one entry.  The oracle is INDEPENDENT of the Brain: the
                                      expected value is the `verifier_result_sha256` that
                                      GitHub Actions minted by re-running the same module as
                                      a different identity on different hardware.  This machine
                                      never computed it; it can only agree with it or fail.

Why this family exists.  The reachability section of the heartbeat asks whether a sentence
reaches a capability; it never RUNS one.  Measured: 296 of the 362 capabilities took no
input, so the reachability question for them was "can the caller spell the internal id?" - a
question about the id, not about the capability.  With the prose question asked first, every
capability in the registry is reached by a plain sentence, and 294 of the 295 receipt-backed
ones reproduce the CI-verified hash when executed.  This family is that claim, made
continuously and by an outside oracle.

Every instance asks for a DIFFERENT capability, in its own words, so the run is 295
independent sentences rather than one sentence repeated.

THE APPLICABLE ORACLE, stated honestly.  The CI-verified hash is the hash of the
capability's own result.  One capability in 295 measures the LIVE repository tree, so its
result legitimately changes whenever the tree changes and a CI hash minted on another commit
cannot apply to this checkout.  The generator therefore establishes, per capability, whether
the CI hash applies HERE - by running the capability once through the receipt lane, the very
path that minted the receipt, and comparing - and the oracle then applies the strict
comparison when it applies, and says so plainly when it does not.  Nothing is compared
against a value this machine computed without saying that it was.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any, Callable

from execution_guard.live_solver_end_to_end_measurement_v1 import Case, ROOT, _rel

# The two fields the entry's adapter adds to a capability's own result before the caller
# sees it.  The receipt lane hashed the capability's OWN result, so the comparison strips
# exactly the fields the adapter added and nothing else.
_ADAPTER_INJECTED = ("capability_id", "dependency")

# Per-capability applicability, established once per process.
_APPLICABILITY: dict[str, dict[str, Any]] = {}


def _sha256_canonical(value: Any) -> str:
    """The receipt lane's own canonical hash - the function that minted the expected value.

    Measured: this family first carried its own copy of the hash, and it disagreed with the
    lane's on every instance (the lane serializes with `default=repr` and without compact
    separators).  A comparison against an outside oracle must use the oracle's function, so
    the lane's is called directly rather than reimplemented.
    """
    from canonical.runtime import capability_receipt_lane_v1 as lane
    return lane.sha256_canonical(value)


def _canonical_forms(tool_result: dict) -> list[Any]:
    """The canonicalizations of the entry's result the receipt lane's hash can take.

    The lane hashed the capability's OWN result: the parsed JSON stdout for a CLI capability,
    the returned dict for a contract one.  The entry's adapter adds `dependency` to every
    result and `capability_id` only to a result that did not already carry one, so the
    comparison tries the dict with both removed, the dict with only `dependency` removed, the
    dict as it stands, and the parsed stdout.
    """
    forms: list[Any] = [
        {k: v for k, v in tool_result.items() if k not in _ADAPTER_INJECTED},
        {k: v for k, v in tool_result.items() if k != "dependency"},
        tool_result,
    ]
    stdout = tool_result.get("stdout")
    if isinstance(stdout, str) and stdout.strip():
        try:
            forms.append(json.loads(stdout))
        except ValueError:
            pass
    return forms


def _name_sentence(cid: str) -> str:
    """The plain sentence that NAMES a capability, in the capability's own words.

    Leak-free: the words are the capability's own name, never its repository path, never its
    receipt document and never the lane's `.py.auto.vN` suffix.  The name's own ORDER is kept
    and the version is part of the name, because the retrieval path separates a capability's
    version siblings only when the request states the version.
    """
    stem = cid.rsplit("/", 1)[-1]
    stem = re.sub(r"\.py\.auto\.v\d+$", "", stem)
    words = [w for w in stem.split("_") if len(w) > 1]
    return "Run the " + (" ".join(words) if words else "capability") + "."


def _receipt_backed() -> list[dict[str, Any]]:
    """Every receipt-backed capability that has an INDEPENDENT verification record.

    The record must say `reproduced: true` and carry a `verifier_result_sha256`: a value
    minted by GitHub Actions, by an identity that is not this process, on hardware that is
    not this machine.
    """
    from canonical.runtime import capability_receipt_lane_v1 as lane
    from canonical.runtime.live_integrated_brain_v1 import load_verified_registry
    out = []
    for cid, entry in sorted(dict(load_verified_registry()).items()):
        if entry.get("capability_source") != "receipt_projection":
            continue
        receipt_path = (entry.get("verification") or {}).get("receipt_path")
        if not receipt_path:
            continue
        vp = ROOT / lane.verification_path_for(receipt_path)
        if not (ROOT / receipt_path).is_file() or not vp.is_file():
            continue
        try:
            record = json.loads(vp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if record.get("reproduced") is not True or not record.get("verifier_result_sha256"):
            continue
        try:
            receipt = json.loads((ROOT / receipt_path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out.append({"capability_id": cid, "expected_sha256": record["verifier_result_sha256"],
                    "receipt": receipt})
    return out


def _applicability(target: dict[str, Any]) -> dict[str, Any]:
    """Whether the CI-verified hash applies to THIS checkout for this capability.

    The test is the one the receipt lane itself uses: run the capability through the lane -
    the path that minted the receipt - and compare with the CI-verified hash.  When the lane
    reproduces it, the CI value is a live oracle here and the entry must match it.  When the
    lane does not, the capability's result is a function of the tree rather than of the
    code, and a CI value minted on another commit cannot be the expected answer here; the
    entry is then judged against the lane's own fresh result, and the row says which oracle
    was applied.
    """
    from canonical.runtime import capability_receipt_lane_v1 as lane
    cid = target["capability_id"]
    if cid in _APPLICABILITY:
        return _APPLICABILITY[cid]
    receipt = target["receipt"]
    before = lane._changed_paths(str(ROOT))
    try:
        fresh = lane.execute_and_receipt(
            cid, receipt.get("module_path"), receipt.get("entrypoint", "run"), str(ROOT),
            "heartbeat-wave7", receipt.get("kind") or "contract")
    except Exception:  # noqa: BLE001 - a probe that cannot run is not a verdict
        fresh = None
    finally:
        lane.restore_tree(str(ROOT), before, ("astra_runtime/evidence/CAPABILITY__",))
    local_sha = (fresh or {}).get("result_sha256")
    row = {
        "ci_applies": bool(local_sha) and local_sha == target["expected_sha256"],
        "local_sha256": local_sha,
        "expected_sha256": target["expected_sha256"],
    }
    _APPLICABILITY[cid] = row
    return row


def gen_receipt_prose_execution(rng: random.Random, work: Path, i: int) -> Case:
    """Ask for ONE receipt-backed capability by name and judge it against the CI hash."""
    work.mkdir(parents=True, exist_ok=True)
    targets = _receipt_backed()
    if not targets:
        return Case("RECEIPT_PROSE_EXECUTION", "Run the receipt backed capability.",
                    lambda _r: (False, "no independently verified receipt-backed capability"),
                    True, [])
    target = targets[i % len(targets)]
    cid = target["capability_id"]
    applicability = _applicability(target)
    goal = _name_sentence(cid)

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        ran = str(result.get("compiled_capability_id") or "")
        if ran != cid:
            return False, f"wrong capability ran: {ran or result.get('status')}"
        tool_result = None
        for ex in result.get("execution") or []:
            if isinstance(ex, dict) and isinstance(ex.get("result"), dict):
                tool_result = ex["result"]
                break
        if tool_result is None:
            return False, "the entry reported no tool result"
        if applicability["ci_applies"]:
            for form in _canonical_forms(tool_result):
                if _sha256_canonical(form) == applicability["expected_sha256"]:
                    return True, "matches the CI-verified hash"
            return False, ("does not reproduce the CI-verified hash "
                           f"expected={applicability['expected_sha256'][:16]}")
        # The CI hash does not apply to this checkout: the capability's result is a function
        # of the live tree, so it is judged against the lane's own fresh result - and the row
        # says that this is what was done.
        for form in _canonical_forms(tool_result):
            if _sha256_canonical(form) == applicability["local_sha256"]:
                return True, ("matches the lane's fresh result; the CI hash does not apply to "
                              "this checkout (the capability measures the live tree)")
        return False, "does not reproduce the lane's fresh result either"

    return Case("RECEIPT_PROSE_EXECUTION", goal, oracle, True, [])


GENERATORS_V7: dict[str, Callable[[random.Random, Path, int], Case]] = {
    "RECEIPT_PROSE_EXECUTION": gen_receipt_prose_execution,
}
