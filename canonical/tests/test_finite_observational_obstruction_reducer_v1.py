import json, pathlib, tempfile
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.finite_observational_obstruction_reducer_v1 import reduce_obstruction

def base():
    return {
      "region_ids":["w0","w1","w2"],
      "discriminators":[
        {"discriminator_id":"q1","outcomes":{"w0":"A","w1":"A","w2":"B"}},
        {"discriminator_id":"q2","outcomes":{"w0":"X","w1":"X","w2":"X"}},
      ],
      "policies":[
        {"policy_id":"p01","adequate_region_ids":["w0","w1"],"adequacy_certificate_ref":None},
        {"policy_id":"p2","adequate_region_ids":["w2"],"adequacy_certificate_ref":None},
      ],
    }

def run(payload, stale_policy=None):
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        for i,row in enumerate(payload.get("policies",[])):
            p=root/f"cert{i}.json"
            raw=json.dumps({"schema":"TEST_CERT","id":row.get("policy_id")},sort_keys=True).encode()
            p.write_bytes(raw)
            sha=git_blob_id(raw,object_format="sha1")
            if stale_policy==row.get("policy_id"):
                sha="0"*40
            row["adequacy_certificate_ref"]={"path":p.name,"git_blob_sha":sha}
        return reduce_obstruction(payload,repo_root=root)

def test_all_final_classes_covered():
    out=run(base())
    assert out["pass"] is True
    assert out["final_class_count"]==2
    assert out["all_final_observational_classes_structurally_covered"] is True
    assert out["policy_certificate_bytes_bound"] is True
    assert out["policy_adequacy_semantics_verified"] is False
    assert out["u_empty_authorized"] is False

def test_exact_unsplittable_conflict_witness():
    p=base(); p["policies"][0]["adequate_region_ids"]=["w0"]
    out=run(p)
    assert out["pass"] is False
    assert out["status"]=="UNSPLITTABLE_DECLARED_POLICY_CONFLICT_CLASS_FOUND"
    assert out["counterexample_class"]["region_ids"]==["w0","w1"]
    assert out["counterexample_class"]["common_declared_policy_ids"]==[]

def test_distinguishable_regions_need_not_share_policy():
    p=base()
    p["discriminators"][0]["outcomes"]["w1"]="C"
    p["policies"]=[
      {"policy_id":"p0","adequate_region_ids":["w0"],"adequacy_certificate_ref":None},
      {"policy_id":"p1","adequate_region_ids":["w1"],"adequacy_certificate_ref":None},
      {"policy_id":"p2","adequate_region_ids":["w2"],"adequacy_certificate_ref":None},
    ]
    out=run(p)
    assert out["pass"] is True
    assert out["final_class_count"]==3

def test_incomplete_discriminator_domain_fails():
    p=base(); del p["discriminators"][0]["outcomes"]["w2"]
    assert run(p)["reason"]=="DISCRIMINATOR_OUTCOME_DOMAIN_INCOMPLETE"

def test_extra_discriminator_region_fails():
    p=base(); p["discriminators"][0]["outcomes"]["ghost"]="Z"
    assert run(p)["reason"]=="DISCRIMINATOR_OUTCOME_DOMAIN_INCOMPLETE"

def test_policy_outside_domain_fails():
    p=base(); p["policies"][0]["adequate_region_ids"].append("ghost")
    assert run(p)["reason"]=="POLICY_REGION_SET_OUT_OF_DOMAIN"

def test_stale_certificate_blob_rejected():
    out=run(base(),stale_policy="p01")
    assert out["reason"]=="POLICY_ADEQUACY_CERTIFICATE_BINDING_INVALID"

def test_receipt_shaped_flags_are_not_part_of_contract():
    p=base()
    p["policies"][0]["independent_verified"]=True
    out=run(p)
    assert out["reason"]=="POLICY_FIELDS_INVALID"

def test_empty_q_is_valid_and_tests_global_common_policy():
    p=base(); p["discriminators"]=[]
    p["policies"]=[{"policy_id":"pall","adequate_region_ids":["w0","w1","w2"],"adequacy_certificate_ref":None}]
    out=run(p)
    assert out["pass"] is True
    assert out["final_class_count"]==1

def test_empty_q_with_no_global_common_policy_returns_whole_h():
    p=base(); p["discriminators"]=[]
    out=run(p)
    assert out["status"]=="UNSPLITTABLE_DECLARED_POLICY_CONFLICT_CLASS_FOUND"
    assert out["counterexample_class"]["region_ids"]==["w0","w1","w2"]

def test_overlapping_policies_allowed():
    p=base()
    p["policies"].append({"policy_id":"pall","adequate_region_ids":["w0","w1","w2"],"adequacy_certificate_ref":None})
    assert run(p)["pass"] is True

def test_duplicate_region_rejected():
    p=base(); p["region_ids"].append("w0")
    assert run(p)["reason"]=="INVALID_INPUT"

def test_no_policy_rows_rejected():
    p=base(); p["policies"]=[]
    assert run(p)["reason"]=="POLICIES_INVALID_OR_EMPTY"
