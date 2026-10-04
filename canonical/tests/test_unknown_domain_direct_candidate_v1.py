from __future__ import annotations

from canonical.runtime import unknown_domain_direct_candidate_v1 as c


def transfer_case(program, public_rows, query, probes, *, fingerprint="prim:test", receipt_id="R1"):
    return {
      "case_id":"T",
      "leaf_id":c.TRANSFER,
      "domain_a":{
        "tasks":[],
        "earned_receipts":[{
          "receipt_id":receipt_id,
          "normalized_primitive_program":program,
          "primitive_fingerprint":fingerprint,
          "source_role_binding":{"r0":"a0"},
          "source_evidence_digest":"sha256:source",
          "independent_verified":True,
          "exact_byte_bound":True,
          "conclusion":"success",
        }],
      },
      "domain_b":{
        "tasks":public_rows,
        "query_inputs":query,
        "allowed_probes":probes,
        "tool_metadata":{},
      },
      "decision_requirement":"x",
    }


def test_affine_requests_probe_then_transfers_without_rediscovery():
    program={"dsl":"UDIR_V1","op":"AFFINE_POS","roles":["r0"],"params":{"bias":0.7,"gain":1.3}}
    def y(x): return 0.7+1.3*x
    public=[{"inputs":{"F":x,"D1":x,"D2":x},"terminal_consequence":y(x)} for x in (-2.0,0.5,1.2)]
    case=transfer_case(program,public,{"F":2.0,"D1":7.0,"D2":9.0},[
      {"probe_id":"P1","argument_schema":{"type":"OBSERVE_PRECOMMITTED_ROW"},"cost":1},
      {"probe_id":"P2","argument_schema":{"type":"OBSERVE_PRECOMMITTED_ROW"},"cost":2},
    ])
    first=c.step(case,[])
    assert first["type"]=="REQUEST_PROBE" and first["probe_id"]=="P1"
    transcript=[{"requested_probe_id":"P1","probe_result":{"inputs":{"F":-1.0,"D1":4.0,"D2":6.0},"terminal_consequence":y(-1.0)}}]
    final=c.step(case,transcript)
    assert final["type"]=="CONCLUDE"
    assert final["support_feature_ids"]==["F"]
    assert final["negative_transfer_rejected_feature_ids"]==["D1","D2"]
    assert abs(final["terminal_consequence"]-y(2.0))<1e-10
    assert final["transferred_primitive_fingerprint"]=="prim:test"
    assert final["domain_a_source_receipt_ids"]==["R1"]


def test_step_uses_second_probe_when_first_is_not_discriminating():
    program={"dsl":"UDIR_V1","op":"STEP","roles":["r0"],"params":{"threshold":0.0,"low":-1.0,"high":1.0}}
    public=[{"inputs":{"F":x,"D1":x,"D2":x},"terminal_consequence":(-1.0 if x<0 else 1.0)} for x in (-2.0,1.0,-0.5)]
    case=transfer_case(program,public,{"F":-2.0,"D1":8.0,"D2":9.0},[
      {"probe_id":"P1","argument_schema":{"type":"OBSERVE_PRECOMMITTED_ROW"},"cost":1},
      {"probe_id":"P2","argument_schema":{"type":"OBSERVE_PRECOMMITTED_ROW"},"cost":2},
    ])
    t1=[{"requested_probe_id":"P1","probe_result":{"inputs":{"F":1.0,"D1":6.0,"D2":7.0},"terminal_consequence":1.0}}]
    second=c.step(case,t1)
    assert second["type"]=="REQUEST_PROBE" and second["probe_id"]=="P2"
    t2=t1+[{"requested_probe_id":"P2","probe_result":{"inputs":{"F":-1.0,"D1":5.0,"D2":6.0},"terminal_consequence":-1.0}}]
    final=c.step(case,t2)
    assert final["type"]=="CONCLUDE"
    assert final["support_feature_ids"]==["F"]


def test_commutative_two_role_program_accepts_role_permutation_when_support_set_is_unique():
    program={"dsl":"UDIR_V1","op":"ADD2","roles":["r0","r1"],"params":{"bias":0.25}}
    def y(x,z): return 0.25+x+z
    public=[
      {"inputs":{"F0":x,"F1":z,"D0":x,"D1":z},"terminal_consequence":y(x,z)}
      for x,z in [(-1.0,2.0),(0.5,-0.2),(2.0,1.5)]
    ]
    case=transfer_case(program,public,{"F0":1.0,"F1":3.0,"D0":8.0,"D1":9.0},[
      {"probe_id":"P1","argument_schema":{"type":"OBSERVE_PRECOMMITTED_ROW"},"cost":1}
    ])
    transcript=[{"requested_probe_id":"P1","probe_result":{"inputs":{"F0":-2.0,"F1":0.7,"D0":4.0,"D1":6.0},"terminal_consequence":y(-2.0,0.7)}}]
    final=c.step(case,transcript)
    assert final["type"]=="CONCLUDE"
    assert final["support_feature_ids"]==["F0","F1"]
    assert final["negative_transfer_rejected_feature_ids"]==["D0","D1"]


def test_identifiable_concludes_instead_of_blanket_abstention():
    case={
      "leaf_id":c.ABSTAIN,
      "hypotheses":[
        {"hypothesis_id":"h1","plausible":True,"terminal_consequence":"A"},
        {"hypothesis_id":"h2","plausible":True,"terminal_consequence":"A"},
      ],
      "allowed_probes":[],
    }
    out=c.step(case,[])
    assert out["type"]=="CONCLUDE" and out["terminal_consequence"]=="A"


def test_underspecified_requests_cheapest_declared_safe_discriminator():
    case={
      "leaf_id":c.ABSTAIN,
      "hypotheses":[
        {"hypothesis_id":"h1","plausible":True,"terminal_consequence":"A"},
        {"hypothesis_id":"h2","plausible":True,"terminal_consequence":"B"},
      ],
      "allowed_probes":[
        {"probe_id":"P9","argument_schema":{"type":"SAFE_BINARY_DISCRIMINATOR"},"cost":2},
        {"probe_id":"P2","argument_schema":{"type":"SAFE_BINARY_DISCRIMINATOR"},"cost":1},
      ],
    }
    out=c.step(case,[])
    assert out["type"]=="REQUEST_DISCRIMINATOR" and out["discriminator"]=="P2"


def test_nonidentifiable_abstains_with_witness_not_useless_probe():
    case={
      "leaf_id":c.ABSTAIN,
      "hypotheses":[
        {"hypothesis_id":"h1","plausible":True,"terminal_consequence":"A"},
        {"hypothesis_id":"h2","plausible":True,"terminal_consequence":"B"},
      ],
      "allowed_probes":[{"probe_id":"P0","argument_schema":{"type":"SAFE_OBSERVATION"},"cost":1}],
    }
    out=c.step(case,[])
    assert out["type"]=="ABSTAIN"
    assert out["nonidentifiability_witness"]


def test_resource_accounting_is_zero_learned():
    assert c.RESOURCE_ACCOUNTING=={
      "persistent_learned_bytes":0,
      "external_frontier_model_calls":0,
      "external_learned_capability_calls":0,
    }
