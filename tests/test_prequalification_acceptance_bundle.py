from canonical.runtime.prequalification_acceptance_bundle import assess_prequalification_bundle

def req(rid, scenario):
    return {
        "id": rid,
        "critical": True,
        "dependencies": [],
        "children": [],
        "open_questions": [],
        "clauses": [{"id": rid+"-C1", "keyword": "MUST", "covered_by_scenarios": [scenario]}],
        "scenarios": [{"id": scenario, "given": ["input"], "when": ["act"], "then": ["observable outcome"]}],
    }

def base_bundle():
    requirements=[req("R1","S1"),req("R2","S2")]
    return {
        "requirements": requirements,
        "expected_required_ids": ["R1","R2"],
        "calculation_nodes": [
            {"id":"r1","requirement_id":"R1"},
            {"id":"r2","requirement_id":"R2"},
            {"id":"mid"},{"id":"out"},
        ],
        "calculation_edges": [
            {"from":"r1","to":"mid"},
            {"from":"r2","to":"mid"},
            {"from":"mid","to":"out"},
        ],
        "outputs":["out"],
        "acceptance_model":{
            "requirements":[
                {"id":"R1","critical":True,"must_detect_failure_modes":["semantic_variant"],"builder_dependencies":["raw:input","builder:path-a"]},
                {"id":"R2","critical":True,"must_detect_failure_modes":["boundary_variant"],"builder_dependencies":["raw:input","builder:path-a"]},
            ],
            "checks":[
                {"id":"oracle-r1","covers":["R1"],"provenance":"independent_oracle","dependencies":["raw:input","oracle:r1"],"detects":["semantic_variant"]},
                {"id":"oracle-r2","covers":["R2"],"provenance":"independent_oracle","dependencies":["raw:input","oracle:r2"],"detects":["boundary_variant"]},
            ],
        },
        "verifier_mutants":[
            {
                "id":"drop-r2-output-lineage",
                "structured_case":{
                    "calculation_edges":[{"from":"r1","to":"mid"},{"from":"mid","to":"out"}]
                },
            },
            {
                "id":"shared-builder-semantic-check",
                "acceptance_model":{
                    "requirements":[
                        {"id":"R1","critical":True,"must_detect_failure_modes":["semantic_variant"],"builder_dependencies":["raw:input","semantic:same"]},
                        {"id":"R2","critical":True,"must_detect_failure_modes":["boundary_variant"],"builder_dependencies":["raw:input","builder:path-a"]},
                    ],
                    "checks":[
                        {"id":"shared","covers":["R1"],"provenance":"same_semantic_interpretation","dependencies":["raw:input","semantic:same"],"detects":["semantic_variant"]},
                        {"id":"oracle-r2","covers":["R2"],"provenance":"independent_oracle","dependencies":["raw:input","oracle:r2"],"detects":["boundary_variant"]},
                    ],
                },
            },
        ],
    }

def test_complete_composed_bundle_passes_and_kills_seeded_mutants():
    out=assess_prequalification_bundle(base_bundle())
    assert out["pass"] is True
    assert out["verifier_mutation"]["killed"] == 2
    assert out["fresh_execution_authorized_by_this_bundle"] is False

def test_spent_saccr_missing_requirement_lineage_fails():
    b=base_bundle()
    b["requirements"].append(req("SUPERVISORY_DURATION","SD"))
    b["expected_required_ids"].append("SUPERVISORY_DURATION")
    b["calculation_nodes"].append({"id":"sd","requirement_id":"SUPERVISORY_DURATION"})
    out=assess_prequalification_bundle(b)
    assert out["pass"] is False
    assert "SUPERVISORY_DURATION:NO_OUTPUT_PATH" in out["structured_method"]["output_reachability"]["uncovered"]

def test_spent_cad_local_only_acceptance_fails_global_obligations():
    b=base_bundle()
    b["acceptance_model"]={
        "requirements":[{
            "id":"CAD_GLOBAL_SOLID","critical":True,
            "transform_kinds":["geometry_reconstruction"],
            "builder_dependencies":["raw:drawing","builder:cad"]
        }],
        "checks":[{
            "id":"watertight-only","covers":["CAD_GLOBAL_SOLID"],
            "provenance":"independent_oracle",
            "dependencies":["raw:drawing","oracle:watertight"],
            "detects":["watertightness"]
        }],
    }
    out=assess_prequalification_bundle(b)
    assert out["pass"] is False
    uncovered=set(out["independent_acceptance"]["requirements"][0]["uncovered"])
    assert {"global_mass_property","topology","envelope","curvature"} <= uncovered

def test_spent_kg_shared_semantic_acceptance_fails():
    b=base_bundle()
    b["acceptance_model"]={
        "requirements":[{
            "id":"KG","critical":True,
            "must_detect_failure_modes":["identifier_variant"],
            "builder_dependencies":["raw:records","semantic:identity"]
        }],
        "checks":[{
            "id":"shared","covers":["KG"],
            "provenance":"same_semantic_interpretation",
            "dependencies":["raw:records","semantic:identity"],
            "detects":["identifier_variant"]
        }],
    }
    out=assess_prequalification_bundle(b)
    assert out["pass"] is False
    assert out["independent_acceptance"]["requirements"][0]["independent_checks"] == ()

def test_spent_bun_builder_only_policy_check_fails():
    b=base_bundle()
    b["acceptance_model"]={
        "requirements":[{
            "id":"BUN","critical":True,
            "must_detect_failure_modes":["policy_or_semantic_variant"],
            "builder_dependencies":["raw:instruction","semantic:policy"]
        }],
        "checks":[{
            "id":"self","covers":["BUN"],
            "provenance":"builder_derived",
            "dependencies":["raw:instruction","semantic:policy"],
            "detects":["policy_or_semantic_variant"]
        }],
    }
    out=assess_prequalification_bundle(b)
    assert out["pass"] is False

def test_missing_verifier_mutants_fails_closed():
    b=base_bundle(); b["verifier_mutants"]=[]
    out=assess_prequalification_bundle(b)
    assert out["pass"] is False
    assert out["verifier_mutation"]["failure"]=="NO_VERIFIER_MUTANTS"
