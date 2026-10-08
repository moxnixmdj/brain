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


def test_missing_policy_is_not_misdiagnosed_as_missing_discriminator():
    p=base()
    p["policies"]=[{"policy_id":"only_w0","adequate_region_ids":["w0"],
                    "adequacy_certificate_ref":None}]
    out=run(p)
    assert out["pass"] is False
    core=out["counterexample_class"]["smallest_verified_conflict_core"]
    assert len(core["region_ids"])==1 and core["minimum_cardinality_proved"] is True
    assert out["counterexample_class"]["regions_with_no_declared_adequate_policy"]
    assert (out["counterexample_class"]["minimum_missing_decision_relevant_primitive"]
            =="PROVE_OR_BUILD_ADEQUATE_POLICY")


def test_pairwise_policy_coverage_can_still_have_exact_three_region_obstruction():
    p=base()
    p["discriminators"]=[]
    p["policies"]=[
        {"policy_id":"p01","adequate_region_ids":["w0","w1"],"adequacy_certificate_ref":None},
        {"policy_id":"p12","adequate_region_ids":["w1","w2"],"adequacy_certificate_ref":None},
        {"policy_id":"p02","adequate_region_ids":["w0","w2"],"adequacy_certificate_ref":None},
    ]
    out=run(p)
    assert out["status"]=="UNSPLITTABLE_DECLARED_POLICY_CONFLICT_CLASS_FOUND"
    witness=out["counterexample_class"]
    core=witness["smallest_verified_conflict_core"]
    assert core["region_ids"]==["w0","w1","w2"],core
    assert core["minimum_cardinality_proved"] and core["irreducible_proved"]
    assert witness["regions_with_no_declared_adequate_policy"]==[]
    assert (witness["minimum_missing_decision_relevant_primitive"]
            =="ADD_TRUTHFUL_DISCRIMINATOR_OR_PROVE_COMMON_ADEQUATE_POLICY")


def test_domain_totality_is_not_fake_proof_q_or_receipt_authentication():
    out=run(base())
    assert out["pass"] is True
    assert out["declared_q_outcome_domain_total_on_h"] is True
    assert out["declared_q_complete_on_h"] is False
    assert out["q_information_library_complete_proved"] is False
    assert out["policy_certificate_bytes_bound"] is True
    assert out["policy_adequacy_semantics_verified"] is False
    assert out["terminal_authority"] is False
    assert out["u_empty_authorized"] is False


def test_minimum_core_differential_against_independent_combinatorial_oracle():
    import random
    from itertools import combinations
    rng=random.Random(20261008)
    for trial in range(140):
        region_count=rng.randint(2,7)
        policy_count=rng.randint(1,5)
        region_ids=[f"w{i}" for i in range(region_count)]
        policies=[]
        for i in range(policy_count):
            coverage=[r for r in region_ids if rng.random()<0.55]
            policies.append({"policy_id":f"p{i}","adequate_region_ids":coverage,
                             "adequacy_certificate_ref":None})
        p={"region_ids":region_ids,"discriminators":[],"policies":policies}
        actual=run(p)
        if actual["pass"]:
            assert any(set(region_ids)<=set(pol["adequate_region_ids"])
                       for pol in policies),(trial,actual)
            continue
        assert actual["status"]=="UNSPLITTABLE_DECLARED_POLICY_CONFLICT_CLASS_FOUND",(trial,actual)
        core=actual["counterexample_class"]["smallest_verified_conflict_core"]
        assert core["minimum_cardinality_proved"],(trial,core)
        oracle=None
        for k in range(1,len(region_ids)+1):
            for subset in combinations(region_ids,k):
                if not any(set(subset)<=set(pol["adequate_region_ids"])
                           for pol in policies):
                    oracle=k
                    break
            if oracle is not None:
                break
        assert oracle==len(core["region_ids"]),(trial,oracle,core,policies)
        for r in core["region_ids"]:
            subset=set(core["region_ids"])-{r}
            assert any(subset<=set(pol["adequate_region_ids"])
                       for pol in policies),(trial,core)


def test_search_budget_returns_verified_irreducible_not_fabricated_minimum():
    regions=[f"w{i}" for i in range(14)]
    p={"region_ids":regions,"discriminators":[],"policies":[
        {"policy_id":f"p{i}","adequate_region_ids":[r for r in regions if r!=f"w{i}"],
         "adequacy_certificate_ref":None}
        for i in range(len(regions))
    ]}
    out=run(p)
    assert out["status"]=="UNSPLITTABLE_DECLARED_POLICY_CONFLICT_CLASS_FOUND"
    core=out["counterexample_class"]["smallest_verified_conflict_core"]
    assert core["search_budget_exceeded"] is True
    assert core["minimum_cardinality_proved"] is False
    assert core["irreducible_proved"] is True
    assert len(core["region_ids"])==14
    assert out["terminal_credit_delta"]==0


def test_exact_minimum_observations_avoids_redundant_checks():
    p=base()
    p["discriminators"]=[
        {"discriminator_id":"q_critical","outcomes":{"w0":"left","w1":"left","w2":"right"}},
    ]+[
        {"discriminator_id":f"q_redundant_{i}",
         "outcomes":{"w0":"same","w1":"same","w2":"same"}}
        for i in range(7)
    ]
    out=run(p)
    assert out["pass"] is True,out
    plan=out["minimum_declared_observation_plan"]
    assert plan["minimum_proved"] is True,plan
    assert plan["observation_count"]==1,plan
    assert plan["selected_discriminator_ids"]==["q_critical"],plan
    assert plan["avoided_declared_observations"]==7,plan
    assert out["policy_adequacy_semantics_verified"] is False
    assert out["terminal_credit_delta"]==0


def test_zero_observation_common_policy_is_proved_minimum():
    p=base()
    p["policies"].append(
        {"policy_id":"pall","adequate_region_ids":["w0","w1","w2"],
         "adequacy_certificate_ref":None}
    )
    out=run(p)
    assert out["pass"] is True,out
    plan=out["minimum_declared_observation_plan"]
    assert plan["minimum_proved"] is True
    assert plan["selected_discriminator_ids"]==[]
    assert plan["observation_count"]==0


def test_more_than_twelve_observations_returns_no_fake_minimum():
    p=base()
    p["discriminators"]=[
        {"discriminator_id":f"q{i}","outcomes":{"w0":"left","w1":"left","w2":"right"}}
        for i in range(13)
    ]
    out=run(p)
    assert out["pass"] is True
    plan=out["minimum_declared_observation_plan"]
    assert plan["status"]=="UNPROVED_TOO_MANY_DECLARED_DISCRIMINATORS"
    assert plan["minimum_proved"] is False


def test_minimum_q_subset_differential_exhaustive_oracle():
    import itertools,random
    rng=random.Random(20261008)
    for trial in range(110):
        nr=rng.randint(2,6)
        nq=rng.randint(0,6)
        np=rng.randint(1,6)
        regs=[f"w{i}" for i in range(nr)]
        policies=[{
            "policy_id":f"p{i}",
            "adequate_region_ids":[r for r in regs if rng.random()<0.6],
            "adequacy_certificate_ref":None,
        } for i in range(np)]
        qs=[{
            "discriminator_id":f"q{i}",
            "outcomes":{r:rng.choice(["a","b","c"]) for r in regs},
        } for i in range(nq)]
        p={"region_ids":regs,"discriminators":qs,"policies":policies}
        out=run(p)
        if not out["pass"]:
            assert out["status"]=="UNSPLITTABLE_DECLARED_POLICY_CONFLICT_CLASS_FOUND",(trial,out)
            continue
        plan=out["minimum_declared_observation_plan"]
        assert plan["minimum_proved"],(trial,plan)
        found=None
        for k in range(nq+1):
            for sub in itertools.combinations(qs,k):
                buckets={}
                for reg in regs:
                    signature=tuple(x["outcomes"][reg] for x in sub)
                    buckets.setdefault(signature,[]).append(reg)
                if all(any(set(members)<=set(pol["adequate_region_ids"])
                           for pol in policies) for members in buckets.values()):
                    found=k
                    break
            if found is not None:break
        assert found==plan["observation_count"],(trial,found,plan)
        assert len(plan["selected_discriminator_ids"])==found


def test_top_level_unknown_requirements_fail_closed_without_false_proof():
    p=base()
    p["required_global_policy_score"]="OPUS_PARITY"
    out=run(p)
    assert out["pass"] is False,out
    assert out["reason"]=="UNMODELED_OBSTRUCTION_INPUT_FIELDS"
    assert out["u_empty_authorized"] is False


def test_discriminator_extra_semantic_requirement_fails_closed():
    p=base()
    p["discriminators"][0]["must_be_authoritative"]=True
    out=run(p)
    assert out["pass"] is False,out
    assert out["reason"]=="UNMODELED_DISCRIMINATOR_FIELDS"
    assert out["terminal_credit_delta"]==0


def test_nonstring_region_identity_is_not_silently_coerced():
    p=base()
    p["region_ids"]=[0,"w1","w2"]
    out=run(p)
    assert out["pass"] is False,out
    assert out["reason"]=="INVALID_INPUT"
    assert out["terminal_authority"] is False
