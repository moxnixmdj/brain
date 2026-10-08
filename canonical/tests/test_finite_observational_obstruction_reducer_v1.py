from canonical.runtime.finite_observational_obstruction_reducer_v1 import reduce_obstruction

def receipt(name="r"):
    return {
      "path":"canonical/verification/"+name+".json",
      "git_blob_sha":"a"*40,
      "independent_verified":True,
      "exact_byte_bound":True,
      "conclusion":"success",
      "policy_adequacy_region_sound":True,
    }

def base():
    return {
      "region_ids":["w0","w1","w2"],
      "discriminators":[
        {"discriminator_id":"q1","outcomes":{"w0":"A","w1":"A","w2":"B"}},
        {"discriminator_id":"q2","outcomes":{"w0":"X","w1":"X","w2":"X"}},
      ],
      "policies":[
        {"policy_id":"p01","adequate_region_ids":["w0","w1"],"adequacy_receipt":receipt("p01")},
        {"policy_id":"p2","adequate_region_ids":["w2"],"adequacy_receipt":receipt("p2")},
      ],
    }

def test_all_final_classes_covered():
    out=reduce_obstruction(base())
    assert out["pass"] is True
    assert out["final_class_count"]==2
    assert out["all_final_observational_classes_covered"] is True
    assert out["u_empty_authorized"] is False

def test_exact_unsplittable_conflict_witness():
    p=base()
    p["policies"][0]["adequate_region_ids"]=["w0"]
    out=reduce_obstruction(p)
    assert out["pass"] is False
    assert out["status"]=="UNSPLITTABLE_POLICY_CONFLICT_CLASS_FOUND"
    assert out["counterexample_class"]["region_ids"]==["w0","w1"]
    assert out["counterexample_class"]["common_adequate_policy_ids"]==[]

def test_distinguishable_regions_need_not_share_policy():
    p=base()
    p["discriminators"][0]["outcomes"]["w1"]="C"
    p["policies"]=[
      {"policy_id":"p0","adequate_region_ids":["w0"],"adequacy_receipt":receipt("p0")},
      {"policy_id":"p1","adequate_region_ids":["w1"],"adequacy_receipt":receipt("p1")},
      {"policy_id":"p2","adequate_region_ids":["w2"],"adequacy_receipt":receipt("p2")},
    ]
    out=reduce_obstruction(p)
    assert out["pass"] is True
    assert out["final_class_count"]==3

def test_incomplete_discriminator_domain_fails():
    p=base(); del p["discriminators"][0]["outcomes"]["w2"]
    out=reduce_obstruction(p)
    assert out["reason"]=="DISCRIMINATOR_OUTCOME_DOMAIN_INCOMPLETE"

def test_extra_discriminator_region_fails():
    p=base(); p["discriminators"][0]["outcomes"]["ghost"]="Z"
    out=reduce_obstruction(p)
    assert out["reason"]=="DISCRIMINATOR_OUTCOME_DOMAIN_INCOMPLETE"

def test_policy_outside_domain_fails():
    p=base(); p["policies"][0]["adequate_region_ids"].append("ghost")
    out=reduce_obstruction(p)
    assert out["reason"]=="POLICY_REGION_SET_OUT_OF_DOMAIN"

def test_self_asserted_receipt_rejected():
    p=base(); p["policies"][0]["adequacy_receipt"]["independent_verified"]=False
    out=reduce_obstruction(p)
    assert out["reason"]=="POLICY_ADEQUACY_RECEIPT_INVALID"

def test_empty_q_is_valid_and_tests_global_common_policy():
    p=base(); p["discriminators"]=[]
    p["policies"]=[{"policy_id":"pall","adequate_region_ids":["w0","w1","w2"],"adequacy_receipt":receipt("pall")}]
    out=reduce_obstruction(p)
    assert out["pass"] is True
    assert out["final_class_count"]==1

def test_empty_q_with_no_global_common_policy_returns_whole_h():
    p=base(); p["discriminators"]=[]
    out=reduce_obstruction(p)
    assert out["status"]=="UNSPLITTABLE_POLICY_CONFLICT_CLASS_FOUND"
    assert out["counterexample_class"]["region_ids"]==["w0","w1","w2"]

def test_overlapping_policies_allowed():
    p=base()
    p["policies"].append({"policy_id":"pall","adequate_region_ids":["w0","w1","w2"],"adequacy_receipt":receipt("pall")})
    out=reduce_obstruction(p)
    assert out["pass"] is True

def test_duplicate_region_rejected():
    p=base(); p["region_ids"].append("w0")
    out=reduce_obstruction(p)
    assert out["reason"]=="INVALID_INPUT"

def test_no_policy_rows_rejected():
    p=base(); p["policies"]=[]
    out=reduce_obstruction(p)
    assert out["reason"]=="POLICIES_INVALID_OR_EMPTY"
