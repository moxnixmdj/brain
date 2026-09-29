import importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parents[2]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

G=load("ground_runtime_test","canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py")

def test_real_registry_grounding_blocks_irrelevant_supplier_fallback():
    registry=json.loads((ROOT/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
    registry=registry.get("capabilities",registry)
    goal=(
      "Audit a PyPI wheel release by fetching authoritative JSON metadata, "
      "checking the downloaded artifact SHA256 provenance, and preserving a verified report"
    )
    out=G.ground(goal,registry)
    ids={x["capability_id"] for x in out["candidates"]}
    assert "http.json.fetch_from_state" in ids
    assert "pypi.provenance.audit_live_artifact" in ids
    assert out["status"]=="GROUNDED"
    assert out["external_discovery_allowed"] is False
    assert not any("zero" in x.lower() for x in ids)

def test_distinct_web_release_grounding_reuses_same_generic_route():
    registry=json.loads((ROOT/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
    registry=registry.get("capabilities",registry)
    goal=(
      "Check the current stable Python release from the official rendered web page "
      "and independently verify the release version over HTTP"
    )
    out=G.ground(goal,registry)
    ids={x["capability_id"] for x in out["candidates"]}
    assert "web.browser.rendered.capture.chromedriver" in ids
    assert "web.release.verify.independent_http" in ids
    assert out["status"]=="GROUNDED"
    assert out["external_discovery_allowed"] is False
