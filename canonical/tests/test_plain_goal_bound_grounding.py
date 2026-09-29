import importlib.util, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[2]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
P=load("ground","canonical/runtime/bound_capabilities/plain_goal_bound_grounding.py")
V=load("ground_verify","canonical/runtime/bound_capabilities/plain_goal_bound_grounding_verify.py")

def entry(provides,keywords=(),requires=(),cost=0,status="VERIFIED_BOUND_CAPABILITY"):
    return {"status":status,"incremental_spend_usd":cost,"provides":list(provides),"keywords":list(keywords),"requires":list(requires)}

def test_multi_candidate_grounding_and_abstention():
    reg={
      "http.json.fetch":entry(["http.json.fetch"],["http","json","fetch","metadata"]),
      "json.query.jq":entry(["json.query.transform"],["json","query","transform","table"]),
      "pdf.extract":entry(["pdf.extract.text"],["pdf","extract","text"]),
      "noise.zero":entry(["game.play"],["zero"]),
      "paid.json":entry(["json.query.transform"],["json","query"],cost=1),
    }
    goal="Fetch authoritative JSON metadata and query the JSON records into a structured table"
    out=P.ground(goal,reg)
    ids={x["capability_id"] for x in out["candidates"]}
    assert "http.json.fetch" in ids
    assert "json.query.jq" in ids
    assert "noise.zero" not in ids and "paid.json" not in ids and "pdf.extract" not in ids
    ok,reason=V.verify(out,reg); assert ok,reason
    none=P.ground("ponder an unrelated philosophical ambiguity",reg)
    assert none["status"]=="ABSTAIN_NO_JUSTIFIED_BOUND_CAPABILITY"
    assert none["external_discovery_allowed"] is True

def test_multiple_alternatives_are_preserved_not_forced_to_one():
    reg={
      "codec.alpha":entry(["structured.binary.encode.alpha"],["alpha","encode"]),
      "codec.beta":entry(["structured.binary.encode.beta"],["beta","encode"]),
    }
    out=P.ground("Compare alpha encoding and beta encoding for structured binary output",reg)
    assert [x["capability_id"] for x in out["candidates"]]==["codec.alpha","codec.beta"]
    assert out["external_discovery_allowed"] is False
