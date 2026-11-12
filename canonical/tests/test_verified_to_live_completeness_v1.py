import json
from pathlib import Path
from canonical.runtime import verified_to_live_completeness_v1 as v

def test_schema_scan(tmp_path:Path):
    g=tmp_path/"canonical/governance"
    q=tmp_path/"canonical/verification"
    g.mkdir(parents=True)
    q.mkdir(parents=True)
    (g/"x.json").write_text(json.dumps({"schema":"PROJECT_BRAIN_R2_DIRECT_ROUTE_DEPLOYMENT_CANDIDATE_V1"}))
    (q/"y.json").write_text(json.dumps({"schema":"PROJECT_BRAIN_R2_DIRECT_ROUTE_DEPLOYMENT_INDEPENDENT_RECEIPT_V1"}))
    c,r=v._scan(tmp_path)
    assert len(c)==1
    assert len(r)==1
