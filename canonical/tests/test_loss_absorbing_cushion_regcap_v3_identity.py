from unittest.mock import patch
from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v3 as v3

def test_identity_precedes_matrix():
    x={'pass':True,'mapped_concept_id':'REGCAP::CCOB','fully_semantically_bound':True}
    with patch.object(v3.v2,'ground',return_value=x), patch.object(v3.ambiguity_v2,'plan_with_authenticated_matrix') as p:
        out=v3.ground('x',source_id='s',start=0,end=1,mapping_scope={'kind':'X'})
    assert out['mapped_concept_id']=='REGCAP::CCOB'
    p.assert_not_called()
