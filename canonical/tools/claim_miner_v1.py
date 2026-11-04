#!/usr/bin/env python3
"""Find things to be wrong about, without a person listing what to be wrong about.

The defect this file exists to remove
-------------------------------------
Thirteen logs produced an organism with initiative, surprise, persistence, a model that
generalises, and a world-forge that reads its own refusals. Measured 2026-11-04:

    every target the organism can ever attend to   14
    of those, typed by a person                    14

It has an agenda and no curiosity. Its entire universe is the list I wrote. Every "detector" in
this repository is a predicate a person wrote about a defect a person imagined, and that is why
the unaided closure rate for classes that matter is still zero: the system has never once decided
what to look at.

The first principle that fixes it
---------------------------------
**Every check is a test of a claim.** A detector must be enumerated by someone. A claim is already
written down -- and claims are everywhere, in registry fields, in artifacts, in docstrings. Counted
2026-11-04:

    registry structured claims (result_fields, requires, limitations, provides)   1,916
    behaviour-asserting docstring sentences                                          340
    assert statements                                                            14,662
    verification artifacts holding hash / size / path / count fields             17,121

A claim asserts something about the world. Asserting it and then testing it is a hypothesis
generated from the corpus rather than from my imagination, and the corpus grows whenever anybody
writes anything. Nobody enumerated the 6,576 file claims below; they were already there.

What this deliberately refuses to do
-----------------------------------
An artifact's `count` field usually records a number that was true at one moment -- how many files
existed then. Testing it against now produces a "defect" every time the repository changes, which
is not a defect, it is history. So counts are classified HISTORICAL and never reported as
contradictions. A claim is only tested when it is about something durable: a file's content, or a
file's presence.

The rule that keeps precision honest: **a claim is only tested where the thing it names can be
found.** A hash with no path beside it is UNPAIRED, not FALSE. Reporting unpaired claims as defects
is how a miner produces a thousand findings and zero facts.

Usage::

    python -m canonical.tools.claim_miner_v1              # measure
    python -m canonical.tools.claim_miner_v1 --write
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_CLAIM_MINER_V1"
ARTIFACT = ROOT / "canonical/verification/CLAIM_MINE_V1.json"
REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
ARTIFACT_DIR = ROOT / "canonical/verification"

HOLDS = "HOLDS"
CONTRADICTED = "CONTRADICTED"
UNTESTABLE = "UNTESTABLE"
UNPAIRED = "UNPAIRED"
HISTORICAL = "HISTORICAL"

HASH_FIELDS = re.compile(r"(sha256|sha1|md5|checksum|_hash|^hash|digest)", re.I)
SIZE_FIELDS = re.compile(r"(size|bytes|length|nbytes)", re.I)
PATH_FIELDS = re.compile(r"(path|file|target|source|receipt|artifact)", re.I)
COUNT_FIELDS = re.compile(r"(count|n_|_n$|total|number)", re.I)
# A recorded hash of a temporary file is a true statement about something that no longer exists.
EPHEMERAL = re.compile(r"(/tmp/|/var/folders/|forge_|world_|tmp[a-z0-9]{6,})")


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


KNOWN_SUFFIX = re.compile(r"\.(py|json|md|txt|toml|cfg|ini|ya?ml|tar|gz|zip|db|sqlite|csv|log|sh|xml|html)$", re.I)
PATH_SHAPE = re.compile(r"^[A-Za-z0-9._\-/@+]+$")
HEX = re.compile(r"^[0-9a-f]{16,128}$", re.I)


def _looks_like_path(value: str) -> bool:
    """A value is a path claim only if it is shaped like one.

    Measured 2026-11-04: the first version of this miner produced 962 contradictions, and most
    were prose. `{"source": "The writing must reflect a thorough understanding ..."}` resolved to
    a file path, was not found, and was reported as a defect. A miner whose findings are mostly
    its own reading errors is worse than no miner, because it trains everyone to ignore it.
    """
    if not isinstance(value, str) or not value or len(value) > 240:
        return False
    if not PATH_SHAPE.match(value):
        return False                      # spaces, punctuation, prose
    if value.count("/") > 12:
        return False
    if re.fullmatch(r"[0-9]+/[0-9]+", value):
        return False                      # a fraction, not a path
    if "/" not in value:
        # A dotted token is usually a capability id far more
        # often than it is a file. Demand a file extension we can actually open.
        return bool(KNOWN_SUFFIX.search(value))
    return True


_EVER_EXISTED: dict[str, bool] = {}


def _ever_existed(relative: str) -> bool:
    """Did this repository ever track this path?

    Measured 2026-11-04: without this, the miner reported `src/chartography/scorer.py` and
    `codex/causal-cut-gate-v2-20261003` as contradictions. Those are claims about OTHER
    repositories recorded in this one's artifacts. They were true where they were written and
    they say nothing about here. Git is the authority on what this world ever contained, so a
    claim naming something this repository never had is untestable here -- not false.
    """
    if relative in _EVER_EXISTED:
        return _EVER_EXISTED[relative]
    import subprocess
    try:
        done = subprocess.run(["git", "log", "--all", "--oneline", "-1", "--", relative],
                              cwd=ROOT, capture_output=True, text=True, timeout=20)
        answer = bool(done.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        answer = True            # unknown: do not use ignorance to excuse a claim
    _EVER_EXISTED[relative] = answer
    return answer


_LAST_COMMIT: dict[str, int] = {}


def _last_commit(relative: str) -> int:
    """When this path last changed, as a unix timestamp. 0 if git cannot say."""
    if relative in _LAST_COMMIT:
        return _LAST_COMMIT[relative]
    import subprocess
    try:
        done = subprocess.run(["git", "log", "-1", "--format=%ct", "--", relative],
                              cwd=ROOT, capture_output=True, text=True, timeout=20)
        stamp = int(done.stdout.strip() or 0)
    except (OSError, ValueError, subprocess.SubprocessError):
        stamp = 0
    _LAST_COMMIT[relative] = stamp
    return stamp


def _resolve(value: str) -> Path | None:
    """A path claim is only testable if it names something inside this repository."""
    if not _looks_like_path(value):
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = ROOT / value
    try:
        candidate.resolve().relative_to(ROOT.resolve())
    except (ValueError, OSError):
        return None
    return candidate


def _pairs(node: Any, trail: str = "") -> Iterator[tuple[str, dict]]:
    """Every dict in a document, with where it came from."""
    if isinstance(node, dict):
        yield trail, node
        for key, value in node.items():
            yield from _pairs(value, f"{trail}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node[:200]):
            yield from _pairs(value, f"{trail}[{index}]")


def _stem(key: str) -> str:
    """`payload_sha256` is about the payload. `artifact_bytes` is about the artifact."""
    return re.split(r"[_.]", str(key).lower())[0]


def _paired_path(row: dict, key: str) -> str | None:
    """The path a hash or size field is about -- and it has to be the SAME subject.

    Measured 2026-11-04: taking any path in the same row produced findings like
    `payload_sha256` compared against an unrelated file, which is 2609 bytes against 5951. That
    is not a defect in the artifact; it is the miner comparing two different things and calling
    the difference a fault. The stems must agree, or the claim is unpaired.
    """
    stem = _stem(key)
    # If two different quantity keys share this stem, we cannot tell which path they are about.
    # Measured 2026-11-04: `source_contract_sha256` and `source_model_projection_sha256` both
    # paired to `source_path` and both "failed" against it. That is one file and two subjects.
    same_stem = [k for k in row if HASH_FIELDS.search(str(k)) or SIZE_FIELDS.search(str(k))]
    same_stem = [k for k in same_stem if _stem(k) == stem]
    if len({str(k) for k in same_stem}) > 1 and str(key) in {str(k) for k in same_stem}:
        return None
    for candidate_key, value in row.items():
        if not isinstance(value, str) or not PATH_FIELDS.search(str(candidate_key)):
            continue
        if _stem(candidate_key) != stem:
            continue
        if _resolve(value) is not None:
            return value
    return None


# --------------------------------------------------------------------------- mining
def mine_file_claims(limit_files: int | None = None) -> list[dict]:
    """Claims of the form 'this file is H' and 'this file exists', straight out of artifacts."""
    claims: list[dict] = []
    documents = sorted(ARTIFACT_DIR.glob("*.json"))
    if limit_files:
        documents = documents[:limit_files]
    for document in documents:
        try:
            body = json.loads(document.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        source = str(document.relative_to(ROOT))
        for trail, row in _pairs(body):
            subject = None
            for key, value in row.items():
                low = str(key)
                if (isinstance(value, str) and HASH_FIELDS.search(low)
                        and HEX.match(value.strip())):
                    claims.append({
                        "kind": "FILE_HASH", "source": source, "where": f"{trail}/{key}",
                        "asserts": f"{key} = {value}",
                        "subject": _paired_path(row, key),
                        "held": value,
                    })
                elif isinstance(value, int) and not isinstance(value, bool) and SIZE_FIELDS.search(low):
                    claims.append({
                        "kind": "FILE_SIZE", "source": source, "where": f"{trail}/{key}",
                        "asserts": f"{key} = {value}",
                        "subject": _paired_path(row, key),
                        "held": value,
                    })
                elif isinstance(value, int) and COUNT_FIELDS.search(low):
                    claims.append({
                        "kind": "COUNT", "source": source, "where": f"{trail}/{key}",
                        "asserts": f"{key} = {value}", "subject": subject,
                        "held": value,
                    })
            subject = next((v for k, v in row.items()
                            if isinstance(v, str) and PATH_FIELDS.search(str(k))
                            and _resolve(v) is not None), None)
            if subject is not None and _looks_like_path(subject) and all(
                    not HASH_FIELDS.search(str(k)) for k in row):
                claims.append({"kind": "FILE_EXISTS", "source": source,
                               "where": f"{trail}", "asserts": f"{subject} exists",
                               "subject": subject, "held": None})
    return claims


def mine_registry_claims() -> list[dict]:
    """Claims a capability makes about itself: what it returns, what it needs, what it forbids."""
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
    claims: list[dict] = []
    for capability_id, entry in sorted(registry.items()):
        for field in entry.get("result_fields") or []:
            claims.append({"kind": "RESULT_FIELD", "source": "registry", "where": capability_id,
                           "asserts": f"{capability_id} returns {field}", "subject": field,
                           "held": capability_id, "capability": capability_id})
        for requirement in entry.get("requires") or []:
            claims.append({"kind": "REQUIRES", "source": "registry", "where": capability_id,
                           "asserts": f"{capability_id} requires {requirement}",
                           "subject": requirement, "held": capability_id,
                           "capability": capability_id})
        for limitation in entry.get("limitations") or []:
            claims.append({"kind": "LIMITATION", "source": "registry", "where": capability_id,
                           "asserts": str(limitation), "subject": capability_id,
                           "held": capability_id, "capability": capability_id})
    return claims


# --------------------------------------------------------------------------- testing
def test_claim(claim: dict) -> dict:
    """One claim, one verdict. No branch here knows a capability's name or a document's purpose."""
    kind = claim["kind"]
    if kind == "COUNT":
        # A count records a moment. Testing it against now produces a 'defect' every time a file
        # changes, which is history, not a fault.
        return {**claim, "verdict": HISTORICAL,
                "detail": "a recorded count describes a past moment, not a present fact"}
    if kind in ("LIMITATION", "REQUIRES"):
        return {**claim, "verdict": UNTESTABLE,
                "detail": "prose claim; no mechanical test is defined for it yet"}
    if kind == "RESULT_FIELD":
        return _test_result_field(claim)

    subject = claim.get("subject")
    if subject is None:
        return {**claim, "verdict": UNPAIRED, "detail": "no path in the same row to test it against"}
    if EPHEMERAL.search(str(subject)) or EPHEMERAL.search(str(claim.get("held") or "")):
        return {**claim, "verdict": UNPAIRED, "detail": "names a temporary location"}

    path = _resolve(subject)
    if path is None:
        return {**claim, "verdict": UNPAIRED, "detail": "names a location outside the repository"}

    try:
        relative = str(path.resolve().relative_to(ROOT.resolve()))
    except (ValueError, OSError):
        return {**claim, "verdict": UNPAIRED, "detail": "names a location outside the repository"}
    if not _ever_existed(relative):
        return {**claim, "verdict": UNPAIRED,
                "detail": f"names {relative}, which this repository never contained"}

    # Durability. A hash of a file that has legitimately changed since the claim was written is
    # a TRUE statement about a past moment. Measured 2026-11-04: all five surviving findings were
    # this, and every one was a false alarm. Git is the authority: if the subject changed after
    # the document that describes it, the claim is history.
    if kind in ("FILE_HASH", "FILE_SIZE"):
        try:
            source_rel = str((ROOT / claim["source"]).resolve().relative_to(ROOT.resolve()))
        except (ValueError, OSError):
            source_rel = claim["source"]
        if _last_commit(relative) > _last_commit(source_rel):
            return {**claim, "verdict": HISTORICAL,
                    "detail": f"{relative} changed after {source_rel} described it"}

    if kind == "FILE_EXISTS":
        if path.exists():
            return {**claim, "verdict": HOLDS, "detail": "present"}
        return {**claim, "verdict": CONTRADICTED,
                "detail": f"{subject} does not exist"}

    if not path.is_file():
        return {**claim, "verdict": UNTESTABLE, "detail": f"{subject} is not a readable file"}

    if kind == "FILE_SIZE":
        actual = path.stat().st_size
        if actual == claim["held"]:
            return {**claim, "verdict": HOLDS, "detail": f"{actual} bytes"}
        return {**claim, "verdict": CONTRADICTED,
                "detail": f"claims {claim['held']} bytes, file is {actual}"}

    if kind == "FILE_HASH":
        actual = _sha256(path)
        if actual is None:
            return {**claim, "verdict": UNTESTABLE, "detail": "unreadable"}
        if actual == claim["held"]:
            return {**claim, "verdict": HOLDS, "detail": "matches"}
        return {**claim, "verdict": CONTRADICTED,
                "detail": f"claims {str(claim['held'])[:16]}..., file is {actual[:16]}..."}

    return {**claim, "verdict": UNTESTABLE, "detail": "no test defined for this kind"}


_RUNS: dict[str, dict] = {}


def _run(capability_id: str) -> dict:
    """Drive a capability in a world the forge builds from its own refusals. Cached per capability:
    one run answers every claim that capability makes about what it returns."""
    if capability_id in _RUNS:
        return _RUNS[capability_id]
    from canonical.tools.capability_world_v1 import registry
    from canonical.tools.sandboxed_world_v1 import run_in_sandbox
    try:
        module = registry()[capability_id].get("adapter_module") or ""
        # Ask for OUTPUT, not merely for a verdict. Measured 2026-11-04: with the forge's own
        # goal, 24 capabilities refused cleanly and settled none of their 222 claims -- a
        # refusal is a good outcome for a capability and useless for a claim about what it
        # returns. The goal decides what counts as finished.
        #
        # And run it in a sandbox: a capability that shells out is imported from a throwaway
        # copy of the tree, so the paths it derives from __file__ point inside the copy. The
        # boundary is satisfied rather than removed.
        outcome = run_in_sandbox(capability_id, module, goal="OUTPUT")
    except Exception as exc:                                            # noqa: BLE001
        outcome = {"reached": False, "stopped_by": f"ERROR:{type(exc).__name__}"}
    _RUNS[capability_id] = outcome
    return outcome


def _test_result_field(claim: dict) -> dict:
    """'This capability returns field F' -- tested by running it and looking.

    This is the class of claim where a false one costs something. A declaration that names a
    field the capability never returns is a contract nobody can rely on, and there are 1,106 of
    these in the registry with nothing in this repository checking any of them.
    """
    capability_id = claim["capability"]
    outcome = _run(capability_id)
    if not outcome.get("reached"):
        return {**claim, "verdict": UNTESTABLE,
                "detail": f"no world drives it: {outcome.get('stopped_by') or 'unknown'}"}
    keys = outcome.get("returned_keys")
    if not keys:
        return {**claim, "verdict": UNTESTABLE, "detail": "it ran but returned nothing to inspect"}
    if claim["subject"] in keys:
        return {**claim, "verdict": HOLDS, "detail": f"returned it ({outcome['verdict']})"}
    if outcome.get("verdict") != "CLAIM_CHECKED":
        # The run took a degraded path and the capability said so. A field that only exists on
        # one branch is not a false claim. Measured 2026-11-04: ten of eleven contradictions
        # were exactly this, and reporting them would have been the miner inventing defects.
        return {**claim, "verdict": UNTESTABLE,
                "detail": f"only the {outcome.get('verdict')} path was exercised"}
    return {**claim, "verdict": CONTRADICTED,
            "detail": f"the run REPORTED SUCCESS and declares {claim['subject']!r}, but returned "
                      f"{len(keys)} keys without it"}


def _tally(rows, key) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        value = row.get(key)
        out[str(value)] = out.get(str(value), 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def measure(write: bool = False) -> dict:
    mined = mine_file_claims() + mine_registry_claims()
    tested = [test_claim(claim) for claim in mined]
    contradicted = [row for row in tested if row["verdict"] == CONTRADICTED]

    by_kind: dict[str, dict[str, int]] = {}
    for row in tested:
        by_kind.setdefault(row["kind"], {})
        by_kind[row["kind"]][row["verdict"]] = by_kind[row["kind"]].get(row["verdict"], 0) + 1

    doc = {
        "schema": SCHEMA,
        "question": "Can the system generate things to be wrong about from the claims already "
                    "written down, instead of from a list a person typed?",
        "claims_mined": len(mined),
        "claims_enumerated_by_a_person": 0,
        "by_verdict": _tally(tested, "verdict"),
        "by_kind": by_kind,
        "contradicted": [{k: r[k] for k in ("kind", "source", "where", "asserts", "detail")}
                         for r in contradicted[:200]],
        "contradicted_total": len(contradicted),
        "why_unpaired_is_not_false": "A hash with no path beside it cannot be tested. Calling it "
                                     "false would manufacture a finding from an absence.",
        "why_counts_are_not_defects": "A recorded count describes a moment. Comparing it to now "
                                      "reports history as a fault.",
        "non_claims": [
            "A_CONTRADICTION_IS_A_LEAD_NOT_A_PROVEN_DEFECT",
            "THE_MINER_READS_STRUCTURE_NOT_MEANING",
            "UNTESTABLE_IS_THE_MAJORITY_AND_IS_REPORTED_AS_SUCH",
        ],
        "authority": "NO_CAPABILITY_CREDIT_HYPOTHESIS_GENERATION_ONLY",
    }
    if write:
        ARTIFACT.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    doc = measure(write=args.write)
    print(f"claims mined: {doc['claims_mined']}   enumerated by a person: "
          f"{doc['claims_enumerated_by_a_person']}")
    print(f"  verdicts: {doc['by_verdict']}")
    for kind, counts in sorted(doc["by_kind"].items()):
        print(f"  {kind:14s} {counts}")
    print(f"\ncontradicted: {doc['contradicted_total']}")
    for row in doc["contradicted"][:12]:
        print(f"  {row['source'][:40]:42s} {row['asserts'][:46]:48s} {row['detail'][:60]}")
    if args.write:
        print(f"\nwrote {ARTIFACT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
