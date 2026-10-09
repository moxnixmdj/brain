from __future__ import annotations
from canonical.runtime import oewn_source_declared_alias_sense_v1 as subject
from canonical.runtime.oewn_release_sense_universe_v1 import RELEASE_ID,RELEASE_SHA256,SCHEMA as OEWN_SCHEMA
from canonical.runtime.https_source_fragment_projection_authority_v2 import PACK_SCHEMA

URL="https://www.sec.gov/answers/forcurr.htm"
FRAGMENT='You will be required to deposit an amount of money (usually called a “security deposit” or “margin”) with a forex dealer in order to purchase or sell an off-exchange forex contract.'

class Response:
    def __init__(self):
        self.headers={"Content-Type":"text/html"}
    def read(self):
        return ("<html><body><h3>You Could Lose Your Entire Investment or More.</h3><p>"+FRAGMENT+"</p></body></html>").encode()
    def geturl(self):
        return URL

def universe():
    return {
        "schema":OEWN_SCHEMA,"pass":True,"status":"PASS",
        "release_id":RELEASE_ID,"archive_sha256":RELEASE_SHA256,
        "lemma":"margin","candidate_set_complete_relative_to_release":True,
        "open_world_english_sense_completeness_claimed":False,
        "senses":[
            {"sense_id":"margin%1:25:00::","synset_id":"13926393-n","part_of_speech":"n","members":["margin","border","perimeter"]},
            {"sense_id":"margin%1:07:00::","synset_id":"05127983-n","part_of_speech":"n","members":["margin"]},
            {"sense_id":"margin%1:21:01::","synset_id":"13372293-n","part_of_speech":"n","members":["margin","security deposit"]},
            {"sense_id":"margin%1:21:02::","synset_id":"13281661-n","part_of_speech":"n","members":["margin","gross profit","gross profit margin"]},
            {"sense_id":"margin%1:10:00::","synset_id":"06401041-n","part_of_speech":"n","members":["margin"]},
            {"sense_id":"margin%1:07:01::","synset_id":"04757264-n","part_of_speech":"n","members":["margin","allowance","leeway","tolerance"]}
        ]
    }

def test_projection_and_alias_resolution_compose():
    pack={
        "schema":PACK_SCHEMA,"source_id":"SEC_FOREX_TEST","url":URL,
        "fragments":[{
            "fragment_id":"margin-alias",
            "section_anchor":"you could lose your entire investment or more.",
            "text":FRAGMENT,
            "max_chars_after_anchor":1000
        }]
    }
    out=subject.resolve(
        sense_universe=universe(),source_projection_pack=pack,
        fragment_id="margin-alias",ambiguous_term="margin",
        opener=lambda *_a,**_k: Response()
    )
    assert out["pass"] is True,out
    assert out["selected_sense_id"]=="margin%1:21:01::"
    assert out["selected_synset_id"]=="13372293-n"
    assert out["source_fragment_authenticated"] is True
    assert out["source_scoped_sense_binding_authority"] is True
    assert out["semantic_truth_authority"] is False
    assert out["terminal_authority"] is False
