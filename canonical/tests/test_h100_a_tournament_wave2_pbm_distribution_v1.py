from canonical.runtime import h100_a_tournament_wave2_pbm_distribution_v1 as g

def test_deterministic():
    assert g.generate(123)==g.generate(123)

def test_seed_changes_case():
    assert g.generate(123)!=g.generate(124)

def test_family_bounds():
    for s in range(64):
        x=g.generate(s)
        vals=x["oracle"]["values"]
        assert 3<=len(vals)<=7
        assert len(set(vals))==len(vals)
        assert x["oracle"]["orientation"] in {"VERTICAL","HORIZONTAL"}
        assert x["question"]["type"] in {"ARGMAX_INDEX","ARGMIN_INDEX","COUNT_BARS","COMPARE_I_GT_J"}
        assert x["pbm_text"].startswith("P1\n80 50\n")
