import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "canonical/governance/TERMINAL_ARCHITECTURE_SELF_TOURNAMENT_20261007_V1.json"

def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def test_exact_source_bindings():
    d=load(ART)
    for b in d["source_bindings"].values():
        p=ROOT / b["path"]
        assert p.is_file(), b["path"]
        assert git_blob_sha(p)==b["git_blob_sha"], (b["path"],git_blob_sha(p),b["git_blob_sha"])

def test_universal_route_is_exact_minimum_declared_cover():
    d=load(ART)
    attack=load(ROOT / d["source_bindings"]["one_shot_attack_manifest"]["path"])
    obligations={x["id"] for x in attack["obligations"]}
    routes={x["id"]:set(x["can_discharge"]) for x in attack["routes"]}
    assert routes["SCOPE_COMPLETE_UNIVERSAL_COVER"]==obligations
    for rid,cov in routes.items():
        if rid!="SCOPE_COMPLETE_UNIVERSAL_COVER":
            assert cov <= routes["SCOPE_COMPLETE_UNIVERSAL_COVER"]
    # no zero-route solution can cover a nonempty obligation set
    assert obligations
    assert d["route_tournament"]["exact_set_cover_result"]["minimum_route_count"]==1
    assert d["route_tournament"]["exact_set_cover_result"]["minimum_route_set"]==["SCOPE_COMPLETE_UNIVERSAL_COVER"]

def test_direct_obligations_are_not_individually_logically_necessary():
    d=load(ART)
    # Constructive Boolean countermodel for every ri:
    # F=True, U=True, all rj=False still gives T=True.
    F=True; U=True
    rs=[False]*13
    T=F and (U or all(rs))
    assert T is True
    assert d["formal_terminal_acceptance_shape"]["wolfram_exact_result"]["each_ri_logically_necessary"] is False
    # Conversely F is necessary in the declared normal form.
    for Uv in (False,True):
        for rv in (False,True):
            assert (False and (Uv or rv)) is False

def test_current_single_research_root_matches_live_authority():
    d=load(ART)
    auth=load(ROOT / d["source_bindings"]["current_terminal_authority"]["path"])
    u=load(ROOT / d["source_bindings"]["primitive_u_frontier"]["path"])
    db=load(ROOT / d["source_bindings"]["sound_db_union_v13"]["path"])
    assert auth["live_truth"]["current_U_empty_proved"] is False
    assert auth["live_truth"]["current_live_research_root_count"]==1
    assert auth["live_truth"]["current_live_research_roots"]==["PROVE_ONE_SOUND_TERMINAL_ACCEPTANCE_ROUTE"]
    assert u["current_truth"]["single_live_primitive_count"]==1
    assert u["current_truth"]["U_empty"] is False
    assert db["saturation_result"]["known_sound_D_B_certificate_record_count"]==17
    assert d["architecture_necessity_tournament"]["irreducible_research_cut"]==["U_EMPTY"]
    assert d["architecture_necessity_tournament"]["irreducible_research_cut_size"]==1

def test_finality_not_deleted():
    d=load(ART)
    assert "POST_U_MECHANICAL_FINALIZATION_TAIL" in d["architecture_necessity_tournament"]["D_finality"]
    assert "NO_CLAIM_TERMINAL_TRUE." in d["hard_nonclaims"]
    assert d["accounting"]["terminal_credit_delta"]==0

if __name__=="__main__":
    tests=[v for k,v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print("PASS",t.__name__)
    print("PASS_COUNT",len(tests))
