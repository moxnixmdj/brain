"""Decision-relative semantic policy-cover control V1.

A semantic ambiguity need not be resolved if one independently authenticated
Brain-owned policy is adequate under every candidate in an independently
authenticated complete finite semantic candidate universe.

The controller never identifies which candidate is true. It authenticates:
1. the exact finite candidate-universe certificate and independent verification;
2. exact policy-adequacy certificates bound to Boolean conditions over candidate
   atoms.

It then computes the exact minimum worst-case observation policy needed only
until every reachable branch has a common adequate policy.

No semantic-truth, observation-truth, execution, promotion, acceptance, or
terminal authority is minted here.
"""
from __future__ import annotations

from functools import lru_cache
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_SEMANTIC_POLICY_COVER_CONTROL_V1"
UNIVERSE_SCHEMA = "PROJECT_BRAIN_SEMANTIC_CANDIDATE_UNIVERSE_CERTIFICATE_V1"
UNIVERSE_VERIFY_SCHEMA = (
    "PROJECT_BRAIN_SEMANTIC_CANDIDATE_UNIVERSE_INDEPENDENT_VERIFICATION_V1"
)
ADEQUACY_SCHEMA = "PROJECT_BRAIN_POLICY_ADEQUACY_CERTIFICATE_V1"
ADEQUACY_VERIFY_SCHEMA = "PROJECT_BRAIN_POLICY_ADEQUACY_INDEPENDENT_VERIFICATION_V1"
MAX_CANDIDATES = 256
MAX_POLICIES = 256
MAX_OBSERVATIONS = 256
OPS = {"TRUE", "FALSE", "ATOM", "NOT", "AND", "OR", "IMPLIES", "XOR"}


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


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def candidate_atom(candidate_id: str) -> str:
    return "SEMANTIC_CANDIDATE::" + candidate_id


def _bound_file(root: Path, raw: Any, prefixes: tuple[str, ...]) -> Path:
    text = str(raw or "").strip()
    rel = Path(text)
    if not text or rel.is_absolute() or ".." in rel.parts:
        raise ValueError("BOUND_PATH_INVALID")
    if not any(text.startswith(prefix) for prefix in prefixes):
        raise ValueError("BOUND_PATH_OUTSIDE_ALLOWED_SCOPE")
    base = root.resolve(strict=True)
    path = base / rel
    for part in [path, *path.parents]:
        if part == base:
            continue
        if part.is_symlink():
            raise ValueError("BOUND_SYMLINK_FORBIDDEN:" + text)
    resolved = path.resolve(strict=False)
    if not any(
        resolved.is_relative_to((base / prefix).resolve(strict=False))
        for prefix in prefixes
    ):
        raise ValueError("BOUND_RESOLVED_PATH_OUTSIDE_ALLOWED_SCOPE:" + text)
    if not path.is_file():
        raise ValueError("BOUND_FILE_MISSING:" + text)
    return path


def _load_json(path: Path) -> Mapping[str, Any]:
    out = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(out, Mapping):
        raise ValueError("BOUND_JSON_NOT_OBJECT")
    return out


def _validate_formula(formula: Any, basis: set[str]) -> None:
    if not isinstance(formula, Mapping):
        raise ValueError("FORMULA_NOT_OBJECT")
    op = formula.get("op")
    if op not in OPS:
        raise ValueError("FORMULA_OP_INVALID:" + str(op))
    if op in {"TRUE", "FALSE"}:
        return
    if op == "ATOM":
        atom = formula.get("id")
        if not isinstance(atom, str) or atom not in basis:
            raise ValueError("ATOM_OUTSIDE_CANDIDATE_BASIS:" + str(atom))
        return
    if op == "NOT":
        _validate_formula(formula.get("arg"), basis)
        return
    if op in {"AND", "OR", "XOR"}:
        args = formula.get("args")
        if (
            not isinstance(args, Sequence)
            or isinstance(args, (str, bytes))
            or len(args) < 2
        ):
            raise ValueError(op + "_ARGS_INVALID")
        for arg in args:
            _validate_formula(arg, basis)
        return
    if op == "IMPLIES":
        _validate_formula(formula.get("if"), basis)
        _validate_formula(formula.get("then"), basis)
        return


def _eval(formula: Mapping[str, Any], candidate_atom_id: str) -> bool:
    op = formula["op"]
    if op == "TRUE":
        return True
    if op == "FALSE":
        return False
    if op == "ATOM":
        return formula["id"] == candidate_atom_id
    if op == "NOT":
        return not _eval(formula["arg"], candidate_atom_id)
    if op == "AND":
        return all(_eval(x, candidate_atom_id) for x in formula["args"])
    if op == "OR":
        return any(_eval(x, candidate_atom_id) for x in formula["args"])
    if op == "XOR":
        return sum(
            1 for x in formula["args"] if _eval(x, candidate_atom_id)
        ) == 1
    if op == "IMPLIES":
        return (
            not _eval(formula["if"], candidate_atom_id)
            or _eval(formula["then"], candidate_atom_id)
        )
    raise AssertionError(op)


def _authenticate_universe(
    root: Path,
    universe_id: str,
    candidate_ids: list[str],
    binding: Any,
) -> dict[str, Any]:
    if not isinstance(binding, Mapping):
        raise ValueError("CANDIDATE_UNIVERSE_BINDING_REQUIRED")
    cert_path = _bound_file(
        root,
        binding.get("certificate_path"),
        ("canonical/governance/", "canonical/verification/"),
    )
    verify_path = _bound_file(
        root,
        binding.get("independent_verification_path"),
        ("canonical/verification/",),
    )
    cert_blob = _git_blob_sha(cert_path)
    verify_blob = _git_blob_sha(verify_path)
    if binding.get("certificate_blob_sha") != cert_blob:
        raise ValueError("CANDIDATE_UNIVERSE_CERTIFICATE_BLOB_DRIFT")
    if binding.get("independent_verification_blob_sha") != verify_blob:
        raise ValueError("CANDIDATE_UNIVERSE_VERIFICATION_BLOB_DRIFT")
    cert = _load_json(cert_path)
    verify = _load_json(verify_path)
    ids_sha = _sha(candidate_ids)
    required_cert = {
        "schema": UNIVERSE_SCHEMA,
        "universe_id": universe_id,
        "candidate_ids_sha256": ids_sha,
        "candidate_count": len(candidate_ids),
        "candidate_set_completeness_proved": True,
    }
    bad = [key for key, value in required_cert.items() if cert.get(key) != value]
    if bad:
        raise ValueError(
            "CANDIDATE_UNIVERSE_CERTIFICATE_INVALID:" + ",".join(bad)
        )
    required_verify = {
        "schema": UNIVERSE_VERIFY_SCHEMA,
        "universe_id": universe_id,
        "subject_git_blob_sha": cert_blob,
        "pass": True,
        "candidate_set_completeness_independently_verified": True,
    }
    bad = [
        key for key, value in required_verify.items() if verify.get(key) != value
    ]
    if bad:
        raise ValueError(
            "CANDIDATE_UNIVERSE_VERIFICATION_INVALID:" + ",".join(bad)
        )
    return {
        "universe_id": universe_id,
        "candidate_ids_sha256": ids_sha,
        "certificate_path": str(cert_path.relative_to(root)),
        "certificate_blob_sha": cert_blob,
        "independent_verification_path": str(verify_path.relative_to(root)),
        "independent_verification_blob_sha": verify_blob,
    }


def _authenticate_policy(
    root: Path,
    policy_id: str,
    condition: Mapping[str, Any],
    binding: Any,
) -> dict[str, Any]:
    if not isinstance(binding, Mapping):
        raise ValueError("POLICY_ADEQUACY_BINDING_REQUIRED:" + policy_id)
    cert_path = _bound_file(
        root,
        binding.get("adequacy_certificate_path"),
        ("canonical/governance/", "canonical/verification/"),
    )
    verify_path = _bound_file(
        root,
        binding.get("independent_verification_path"),
        ("canonical/verification/",),
    )
    cert_blob = _git_blob_sha(cert_path)
    verify_blob = _git_blob_sha(verify_path)
    if binding.get("adequacy_certificate_blob_sha") != cert_blob:
        raise ValueError("ADEQUACY_CERTIFICATE_BLOB_DRIFT:" + policy_id)
    if binding.get("independent_verification_blob_sha") != verify_blob:
        raise ValueError("ADEQUACY_VERIFICATION_BLOB_DRIFT:" + policy_id)
    cert = _load_json(cert_path)
    verify = _load_json(verify_path)
    condition_sha = _sha(condition)
    required_cert = {
        "schema": ADEQUACY_SCHEMA,
        "policy_id": policy_id,
        "policy_condition_sha256": condition_sha,
        "adequacy_proved": True,
        "brain_owned": True,
        "load_bearing_constraints_preserved": True,
    }
    bad = [key for key, value in required_cert.items() if cert.get(key) != value]
    if bad:
        raise ValueError(
            "POLICY_ADEQUACY_CERTIFICATE_INVALID:"
            + policy_id
            + ":"
            + ",".join(bad)
        )
    required_verify = {
        "schema": ADEQUACY_VERIFY_SCHEMA,
        "policy_id": policy_id,
        "subject_git_blob_sha": cert_blob,
        "pass": True,
    }
    bad = [
        key for key, value in required_verify.items() if verify.get(key) != value
    ]
    if bad:
        raise ValueError(
            "POLICY_ADEQUACY_VERIFICATION_INVALID:"
            + policy_id
            + ":"
            + ",".join(bad)
        )
    return {
        "policy_id": policy_id,
        "condition_sha256": condition_sha,
        "adequacy_certificate_path": str(cert_path.relative_to(root)),
        "adequacy_certificate_blob_sha": cert_blob,
        "independent_verification_path": str(verify_path.relative_to(root)),
        "independent_verification_blob_sha": verify_blob,
    }


def _common_policy(
    state: frozenset[str],
    adequate: Mapping[str, frozenset[str]],
) -> tuple[str, ...]:
    rows = [set(adequate[candidate_id]) for candidate_id in sorted(state)]
    common = rows[0]
    for row in rows[1:]:
        common.intersection_update(row)
    return tuple(sorted(common))


def _base(status: str, *, passed: bool, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": status,
        "semantic_truth_authority": False,
        "observation_truth_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def solve(
    problem: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    try:
        if not isinstance(problem, Mapping):
            raise ValueError("PROBLEM_MAPPING_REQUIRED")
        root = Path(repo_root).resolve(strict=True)
        universe_id = str(problem.get("universe_id") or "").strip()
        raw_candidates = problem.get("candidate_ids")
        if (
            not universe_id
            or not isinstance(raw_candidates, Sequence)
            or isinstance(raw_candidates, (str, bytes))
            or not raw_candidates
            or len(raw_candidates) > MAX_CANDIDATES
        ):
            raise ValueError("UNIVERSE_ID_OR_CANDIDATES_INVALID")
        candidate_ids = sorted(str(x).strip() for x in raw_candidates)
        if (
            any(not candidate_id for candidate_id in candidate_ids)
            or len(candidate_ids) != len(set(candidate_ids))
        ):
            raise ValueError("CANDIDATE_IDS_INVALID_OR_DUPLICATE")

        universe_auth = _authenticate_universe(
            root,
            universe_id,
            candidate_ids,
            problem.get("candidate_universe_binding"),
        )
        basis = {candidate_atom(candidate_id) for candidate_id in candidate_ids}
        raw_conditions = problem.get("policy_conditions")
        raw_bindings = problem.get("policy_adequacy_bindings")
        if (
            not isinstance(raw_conditions, Mapping)
            or not raw_conditions
            or len(raw_conditions) > MAX_POLICIES
            or not isinstance(raw_bindings, Mapping)
        ):
            raise ValueError("POLICY_CONDITIONS_OR_BINDINGS_INVALID")

        policy_auth = []
        conditions: dict[str, Mapping[str, Any]] = {}
        for policy_id, condition in sorted(raw_conditions.items()):
            if not isinstance(policy_id, str) or not policy_id:
                raise ValueError("POLICY_ID_INVALID")
            _validate_formula(condition, basis)
            conditions[policy_id] = dict(condition)
            policy_auth.append(
                _authenticate_policy(
                    root,
                    policy_id,
                    condition,
                    raw_bindings.get(policy_id),
                )
            )

        adequate: dict[str, frozenset[str]] = {}
        for candidate_id in candidate_ids:
            atom = candidate_atom(candidate_id)
            adequate[candidate_id] = frozenset(
                policy_id
                for policy_id, condition in conditions.items()
                if _eval(condition, atom)
            )

        uncovered = sorted(
            candidate_id
            for candidate_id in candidate_ids
            if not adequate[candidate_id]
        )
        if uncovered:
            return _base(
                "FAIL_CLOSED__AUTHENTICATED_POLICY_COVER_INCOMPLETE",
                passed=False,
                uncovered_candidate_ids=uncovered,
                candidate_universe_authenticated=True,
                policy_adequacy_authenticated=True,
                candidate_universe_authority=universe_auth,
                policy_adequacy_receipts=policy_auth,
                policy_adequacy_authority=True,
            )

        raw_observations = problem.get("observations", [])
        if (
            not isinstance(raw_observations, Sequence)
            or isinstance(raw_observations, (str, bytes))
            or len(raw_observations) > MAX_OBSERVATIONS
        ):
            raise ValueError("OBSERVATIONS_INVALID")

        observations: dict[str, dict[str, Any]] = {}
        candidate_set = set(candidate_ids)
        for index, raw in enumerate(raw_observations):
            if not isinstance(raw, Mapping):
                raise ValueError("OBSERVATION_NOT_OBJECT:" + str(index))
            observation_id = str(raw.get("observation_id") or "").strip()
            outcomes = raw.get("outcomes")
            cost = raw.get("cost_units")
            if not observation_id or observation_id in observations:
                raise ValueError(
                    "OBSERVATION_ID_INVALID_OR_DUPLICATE:" + str(index)
                )
            if (
                raw.get("outcome_map_complete") is not True
                or not isinstance(outcomes, Mapping)
                or set(str(x) for x in outcomes) != candidate_set
            ):
                raise ValueError(
                    "OBSERVATION_OUTCOME_MAP_INCOMPLETE:" + observation_id
                )
            if (
                isinstance(cost, bool)
                or not isinstance(cost, (int, float))
                or cost < 0
            ):
                raise ValueError("OBSERVATION_COST_INVALID:" + observation_id)
            observations[observation_id] = {
                "cost": float(cost),
                "outcomes": {
                    candidate_id: repr(outcomes[candidate_id])
                    for candidate_id in candidate_ids
                },
            }

        @lru_cache(maxsize=None)
        def dp(state: frozenset[str]):
            common = _common_policy(state, adequate)
            if common:
                return (0.0, None, common, ())
            best = None
            for observation_id in sorted(observations):
                buckets: dict[str, set[str]] = {}
                for candidate_id in state:
                    outcome = observations[observation_id]["outcomes"][candidate_id]
                    buckets.setdefault(outcome, set()).add(candidate_id)
                parts = tuple(
                    frozenset(value) for _, value in sorted(buckets.items())
                )
                if len(parts) <= 1 or any(part == state for part in parts):
                    continue
                children = []
                worst = 0.0
                possible = True
                for part in parts:
                    child = dp(part)
                    if child[0] == float("inf"):
                        possible = False
                        break
                    worst = max(worst, child[0])
                    children.append(
                        {
                            "candidate_ids": sorted(part),
                            "remaining_optimal_cost_units": child[0],
                            "common_policy_ids": list(child[2]),
                        }
                    )
                if not possible:
                    continue
                total = observations[observation_id]["cost"] + worst
                candidate = (total, observation_id, (), tuple(children))
                if best is None or (
                    candidate[0],
                    candidate[1],
                ) < (
                    best[0],
                    best[1],
                ):
                    best = candidate
            return (
                best
                if best is not None
                else (float("inf"), None, (), ())
            )

        initial = frozenset(candidate_ids)
        total, first, common, children = dp(initial)

        if common:
            return _base(
                "PASS__COMMON_VERIFIED_POLICY_COVERS_ALL_SEMANTIC_CANDIDATES",
                passed=True,
                selected_policy_id=common[0],
                common_policy_ids=list(common),
                candidate_count=len(candidate_ids),
                candidate_universe_authenticated=True,
                policy_adequacy_authenticated=True,
                candidate_universe_authority=universe_auth,
                policy_adequacy_receipts=policy_auth,
                semantic_identity_required=False,
                terminal_signature_required=False,
                policy_adequacy_authority=True,
            )

        if total != float("inf"):
            return _base(
                "OPEN__MINIMUM_POLICY_CHANGING_SEMANTIC_DISCRIMINATOR_SELECTED",
                passed=False,
                next_observation_id=first,
                minimum_worst_case_cost_units=total,
                first_observation_partitions=list(children),
                candidate_count=len(candidate_ids),
                candidate_universe_authenticated=True,
                policy_adequacy_authenticated=True,
                candidate_universe_authority=universe_auth,
                policy_adequacy_receipts=policy_auth,
                semantic_identity_required=False,
                terminal_signature_required=False,
                truthful_observation_required=True,
                policy_adequacy_authority=True,
            )

        witness = None
        for index, left in enumerate(candidate_ids):
            for right in candidate_ids[index + 1 :]:
                if set(adequate[left]).intersection(adequate[right]):
                    continue
                if all(
                    row["outcomes"][left] == row["outcomes"][right]
                    for row in observations.values()
                ):
                    witness = {
                        "left_candidate_id": left,
                        "right_candidate_id": right,
                        "left_adequate_policy_ids": sorted(adequate[left]),
                        "right_adequate_policy_ids": sorted(adequate[right]),
                    }
                    break
            if witness is not None:
                break

        return _base(
            (
                "OPEN__POLICY_DISTINCT_SEMANTIC_CANDIDATES_NOT_"
                "SEPARABLE_BY_DECLARED_OBSERVATIONS"
            ),
            passed=False,
            conflicting_policy_region_witness=witness,
            next_required_effect=(
                "ACQUIRE_STRONGER_COMMON_POLICY_ADEQUACY_OR_TRUTHFUL_"
                "POLICY_CHANGING_OBSERVATION"
            ),
            candidate_universe_authenticated=True,
            policy_adequacy_authenticated=True,
            candidate_universe_authority=universe_auth,
            policy_adequacy_receipts=policy_auth,
            policy_adequacy_authority=True,
        )
    except Exception as exc:
        return _base(
            "FAIL_CLOSED",
            passed=False,
            reason=type(exc).__name__ + ":" + str(exc),
            policy_adequacy_authority=False,
        )
