"""Resource-conditioned lower bound on persistent capability bits.

The bound operates on policy classes, not raw world identities.

Let:
  tau = size of a minimum adequate policy cover,
  S   = number of *joint effective* nonpersistent separator states available
        after restart before commitment,
  C   = guaranteed number of policy classes the owned suffix can resolve per
        separator state within the remaining resource envelope,
  R   = number of persistent index states.

A necessary capacity condition is R*S*C >= tau. Therefore
R >= ceil(tau/(S*C)), and persistent bits are at least ceil(log2(R)).

This is a necessary finite capacity lower bound. It is not a general
sufficiency theorem for arbitrary structured decision problems.
"""
from __future__ import annotations

SCHEMA = "PROJECT_BRAIN_BYTES_RESOURCE_PERSISTENCE_CAPACITY_CUT_V1"


class PersistenceCapacityError(ValueError):
    pass


def _positive_int(value: int, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise PersistenceCapacityError(name + "_INVALID")
    return value


def _nonnegative_int(value: int, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise PersistenceCapacityError(name + "_INVALID")
    return value


def ceil_div(n: int, d: int) -> int:
    n = _positive_int(n, "NUMERATOR")
    d = _positive_int(d, "DENOMINATOR")
    return (n + d - 1) // d


def ceil_log2_states(n: int) -> int:
    n = _positive_int(n, "STATE_COUNT")
    return 0 if n == 1 else (n - 1).bit_length()


def minimum_persistent_index_states(
    *,
    policy_cover_size: int,
    effective_nonpersistent_separator_states: int,
    suffix_resolution_capacity: int,
) -> int:
    tau = _positive_int(policy_cover_size, "POLICY_COVER_SIZE")
    s = _positive_int(
        effective_nonpersistent_separator_states,
        "NONPERSISTENT_SEPARATOR_STATES",
    )
    c = _positive_int(suffix_resolution_capacity, "SUFFIX_RESOLUTION_CAPACITY")
    return ceil_div(tau, s * c)


def minimum_persistent_index_bits(
    *,
    policy_cover_size: int,
    effective_nonpersistent_separator_states: int,
    suffix_resolution_capacity: int,
) -> int:
    states = minimum_persistent_index_states(
        policy_cover_size=policy_cover_size,
        effective_nonpersistent_separator_states=effective_nonpersistent_separator_states,
        suffix_resolution_capacity=suffix_resolution_capacity,
    )
    return ceil_log2_states(states)


def capacity_certificate(
    *,
    policy_cover_size: int,
    effective_nonpersistent_separator_states: int,
    suffix_resolution_capacity: int,
) -> dict[str, int | bool | str]:
    tau = _positive_int(policy_cover_size, "POLICY_COVER_SIZE")
    s = _positive_int(
        effective_nonpersistent_separator_states,
        "NONPERSISTENT_SEPARATOR_STATES",
    )
    c = _positive_int(suffix_resolution_capacity, "SUFFIX_RESOLUTION_CAPACITY")
    states = ceil_div(tau, s * c)
    bits = ceil_log2_states(states)
    represented = (1 << bits) * s * c
    less_bits_capacity = 0 if bits == 0 else (1 << (bits - 1)) * s * c
    return {
        "schema": SCHEMA,
        "policy_cover_size_tau": tau,
        "effective_nonpersistent_separator_states_S": s,
        "suffix_resolution_capacity_C": c,
        "nonpersistent_capacity_S_times_C": s * c,
        "minimum_persistent_index_states_lower_bound": states,
        "minimum_persistent_index_bits_lower_bound": bits,
        "capacity_with_lower_bound_bits": represented,
        "lower_bound_bits_capacity_sufficient_for_cardinality": represented >= tau,
        "one_fewer_bit_capacity_insufficient_when_bits_positive":
            True if bits == 0 else less_bits_capacity < tau,
        "zero_persistent_bits_lower_bound": bits == 0,
        "hard_nonclaim":
            "CARDINALITY_CAPACITY_IS_NECESSARY_NOT_GENERAL_STRUCTURAL_SUFFICIENCY",
    }


def absolute_candidate_elimination_resolution_capacity(
    max_candidate_checks: int,
) -> int:
    """Worst-case candidate classes resolvable with q absolute yes/no checks.

    If the candidate set is known and finite, every negative check eliminates
    one candidate and the last remaining candidate may be inferred. Therefore
    q checks can resolve at most q+1 candidates under these assumptions.
    """
    q = _nonnegative_int(max_candidate_checks, "MAX_CANDIDATE_CHECKS")
    return q + 1


def candidate_check_persistent_bits(
    *,
    policy_cover_size: int,
    effective_nonpersistent_separator_states: int,
    max_candidate_checks: int,
) -> int:
    c = absolute_candidate_elimination_resolution_capacity(max_candidate_checks)
    return minimum_persistent_index_bits(
        policy_cover_size=policy_cover_size,
        effective_nonpersistent_separator_states=effective_nonpersistent_separator_states,
        suffix_resolution_capacity=c,
    )


def verify_finite_cut(max_tau: int = 128) -> dict[str, int | bool | str]:
    max_tau = _positive_int(max_tau, "MAX_TAU")
    checked = 0
    for tau in range(1, max_tau + 1):
        for s in range(1, 9):
            for c in range(1, 9):
                cert = capacity_certificate(
                    policy_cover_size=tau,
                    effective_nonpersistent_separator_states=s,
                    suffix_resolution_capacity=c,
                )
                bits = int(cert["minimum_persistent_index_bits_lower_bound"])
                assert ((1 << bits) * s * c) >= tau
                if bits > 0:
                    assert ((1 << (bits - 1)) * s * c) < tau
                checked += 1
    return {
        "schema": SCHEMA,
        "status": "PASS",
        "checked_finite_instances": checked,
        "max_policy_cover_size": max_tau,
        "exact_integer_arithmetic": True,
    }
