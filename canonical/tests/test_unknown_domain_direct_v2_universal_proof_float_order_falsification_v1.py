import hashlib

from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2


def test_add2_ieee754_role_swap_falsifies_v2_universal_claim_without_production_generation():
    beacon = "CEFULL-00000006-20261005-LONG"
    secret = hashlib.sha256(b"secret-full-6").digest()
    index = 4

    family, program, roles = g2._program_for(secret, beacon, index)
    rows = g2._role_rows(secret, beacon, index, program, domain="B")
    b_map, _ = g1._surface_ids(secret, beacon, index, "UDIR_B", roles)

    assert family == "COMPOSITIONAL_REWRITE"
    assert program["op"] == "ADD2"
    assert b_map["r0"] == "udir_b_fe49e5a743809c"
    assert b_map["r1"] == "udir_b_b1a15bbfc0bcc9"
    assert b_map["r1"] < b_map["r0"]

    def true_eval(row):
        return c1._program_eval(program, {"r0": row["r0"], "r1": row["r1"]})

    def swapped_eval(row):
        return c1._program_eval(program, {"r0": row["r1"], "r1": row["r0"]})

    # Public rows 0..2 plus the two allowed probe rows 3..4 do not reveal
    # the hidden role orientation even at exact Python-float equality.
    assert [true_eval(row) == swapped_eval(row) for row in rows[:5]] == [True] * 5

    # But the query does. The candidate collapses these two predictions because
    # it buckets consequences at 12 decimals, then lexicographically selects the
    # swapped mapping above. The frozen scorer uses exact equality.
    gold = true_eval(rows[5])
    swapped = swapped_eval(rows[5])
    assert gold == 4.592781343778206
    assert swapped == 4.5927813437782055
    assert gold != swapped
    assert round(gold, 12) == round(swapped, 12) == 4.592781343778
    assert c1._close(gold, swapped) is True


def test_counterexample_is_derivational_not_a_production_case_run():
    # This regression calls only pure parameter/row/name helpers. It never calls
    # generate_production_population(), _generate(), the execution harness, or
    # any one-use authority/claim path.
    assert callable(g2._program_for)
    assert callable(g2._role_rows)
    assert callable(g1._surface_ids)
