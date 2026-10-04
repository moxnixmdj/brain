"""Information-theoretic falsifier for exact ADD2 orientation under frozen UDIR V2.

This is stronger than the earlier one-ULP candidate counterexample.  It exhibits
one reachable V2 case where the true and role-swapped ADD2 interpretations are
bit-identical on every public target observation and on BOTH allowed probe
outcomes, yet produce different IEEE-754 floats on the terminal query.

Therefore no candidate restricted to the frozen visible packet plus the complete
allowed-probe transcript can universally recover the scorer's exact hidden gold.
The V2 evaluator contract itself contains an unobservable role-order artifact.
"""
import hashlib

from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2


SECRET = hashlib.sha256(b"secret13").digest()
BEACON = "beacon-0000000000000013-xxxxxxxx"
INDEX = 4  # ADD2


def _predict(program, inputs, mapping):
    values = {role: float(inputs[fid]) for role, fid in mapping.items()}
    return c1._program_eval(program, values)


def test_add2_exact_gold_is_not_identifiable_even_after_both_allowed_probes():
    visible, hidden = g2._transfer_case(SECRET, BEACON, INDEX, namespace="IMPOSSIBILITY")
    assert hidden["primitive_family"] == "COMPOSITIONAL_REWRITE"

    true_mapping = dict(hidden["domain_mapping"])
    swapped = {"r0": true_mapping["r1"], "r1": true_mapping["r0"]}
    program = hidden["latent_primitive_program"]

    # Public target evidence is exactly identical under both role orientations.
    for row in visible["domain_b"]["tasks"]:
        target = row["terminal_consequence"]
        assert _predict(program, row["inputs"], true_mapping) == target
        assert _predict(program, row["inputs"], swapped) == target

    # Even consuming the ENTIRE allowed probe budget does not expose orientation.
    table = hidden["allowed_probe_outcome_table"]
    assert len(visible["domain_b"]["allowed_probes"]) == 2
    for probe in visible["domain_b"]["allowed_probes"]:
        row = table[probe["probe_id"]]
        target = row["terminal_consequence"]
        assert _predict(program, row["inputs"], true_mapping) == target
        assert _predict(program, row["inputs"], swapped) == target

    # But the hidden scorer's exact query gold depends on that unobservable order.
    query = visible["domain_b"]["query_inputs"]
    true_query = _predict(program, query, true_mapping)
    swapped_query = _predict(program, query, swapped)
    assert true_query == hidden["gold_terminal_consequence"]
    assert true_query != swapped_query
    assert 0 < abs(true_query - swapped_query) < 1e-12


def test_v3_successor_must_remove_artifact_not_merely_request_more_probes():
    visible, hidden = g2._transfer_case(SECRET, BEACON, INDEX, namespace="IMPOSSIBILITY")
    assert len(visible["domain_b"]["allowed_probes"]) == 2
    assert hidden["full_rediscovery_probe_floor"] == 3
