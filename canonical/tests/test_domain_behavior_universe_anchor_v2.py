import importlib.util
import pathlib

MODULE=pathlib.Path(__file__).resolve().parents[1]/"runtime"/"domain_behavior_universe_anchor_v2.py"

def load():
    spec=importlib.util.spec_from_file_location("anchor2",MODULE)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_all_five_domains_source_anchored_and_none_closed():
    out=load().compile_anchor()
    assert out["domain_count"]==5
    assert out["source_anchored_domain_count"]==5
    assert out["source_incomplete_domains"]==[]
    assert out["closed_domain_count"]==0

def test_healthcare_and_arxivmath_surfaces_present():
    m=load().default_manifest()
    assert "HEALTHBENCH_PROFESSIONAL" in m["domains"]["HEALTHCARE"]["observed_surfaces"]
    assert "PHYSICIANBENCH" in m["domains"]["HEALTHCARE"]["observed_surfaces"]
    assert any(x.startswith("ARXIVMATH_") for x in m["domains"]["MATHEMATICAL_REASONING_ARXIVMATH"]["observed_surfaces"])

def test_source_anchor_does_not_imply_closure():
    mod=load(); m=mod.default_manifest()
    m["domains"]["HEALTHCARE"]["state"]="CLOSED"
    try:
        mod.validate_manifest(m)
    except mod.AnchorError as exc:
        assert "UNSOUND_DOMAIN_CLOSURE" in str(exc)
    else:
        raise AssertionError("source anchor must not close healthcare")
