import json

from canonical.runtime.wikidata_p279_ontology_entailment_v1 import prove_subclass_path

def entity(qid, parents=(), deprecated=()):
    stmts=[]
    for target in parents:
        stmts.append({
            "rank":"normal",
            "mainsnak":{
                "snaktype":"value",
                "datavalue":{"value":{"id":target},"type":"wikibase-entityid"},
            },
        })
    for target in deprecated:
        stmts.append({
            "rank":"deprecated",
            "mainsnak":{
                "snaktype":"value",
                "datavalue":{"value":{"id":target},"type":"wikibase-entityid"},
            },
        })
    return json.dumps({
        "entities":{
            qid:{
                "id":qid,
                "lastrevid":123,
                "modified":"2026-10-09T00:00:00Z",
                "claims":{"P279":stmts},
            }
        }
    },sort_keys=True).encode()

def fetcher(graph):
    def fetch(qid,timeout):
        raw=graph[qid]
        return raw,f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json",200
    return fetch

def test_direct_p279_edge_proves_left_entails_right():
    out=prove_subclass_path("Q1","Q2",fetch=fetcher({"Q1":entity("Q1",["Q2"])}))
    assert out["pass"] is True
    assert out["p279_path"]==["Q1","Q2"]
    assert out["relation"]=="LEFT_ENTAILS_RIGHT"
    assert out["surface_to_qid_binding_proved"] is False
    assert out["real_world_factual_truth_proved"] is False

def test_transitive_p279_path_is_constructive():
    graph={
        "Q1":entity("Q1",["Q2"]),
        "Q2":entity("Q2",["Q3"]),
    }
    out=prove_subclass_path("Q1","Q3",fetch=fetcher(graph))
    assert out["pass"] is True
    assert out["p279_path"]==["Q1","Q2","Q3"]
    assert out["edge_count"]==2
    assert len(out["fetch_receipts"])==2

def test_deprecated_edge_cannot_prove_relation():
    out=prove_subclass_path(
        "Q1","Q2",
        fetch=fetcher({"Q1":entity("Q1",deprecated=["Q2"])}),
    )
    assert out["pass"] is False
    assert out["status"]=="OPEN__P279_PATH_NOT_ESTABLISHED_WITHIN_BOUND"
    assert out["non_entailment_authority"] is False

def test_bounded_search_failure_never_becomes_nonentailment():
    graph={"Q1":entity("Q1",["Q2"]),"Q2":entity("Q2",["Q3"])}
    out=prove_subclass_path("Q1","Q3",max_depth=1,fetch=fetcher(graph))
    assert out["pass"] is False
    assert out["non_entailment_authority"] is False

def test_malformed_entity_identity_fails_closed():
    out=prove_subclass_path(
        "Q1","Q2",
        fetch=fetcher({"Q1":entity("Q9",["Q2"])}),
    )
    assert out["pass"] is False
    assert out["status"]=="FAIL_CLOSED"
    assert "ENTITY_IDENTITY_MISMATCH" in out["reason"]

def test_invalid_qid_fails_closed():
    out=prove_subclass_path("human","Q2",fetch=lambda *_: None)
    assert out["pass"] is False
    assert out["status"]=="FAIL_CLOSED"
    assert "QID_INVALID" in out["reason"]
