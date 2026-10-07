import json,tempfile,unittest
from pathlib import Path
from canonical.runtime.c_proof_carrying_transform_admission_v1 import git_blob_sha,verify_route,AdmissionError

def put(root,name,obj):
    p=root/name; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,sort_keys=True)+"\n",encoding="utf-8")
    return {"path":name,"git_blob_sha":git_blob_sha(p)}

class T(unittest.TestCase):
    def fixture(self):
        td=tempfile.TemporaryDirectory(); r=Path(td.name)
        src=put(r,"src.json",{"scope_complete":True,"independent_or_objective":True})
        dst=put(r,"dst.json",{"scope_complete":True,"independent_or_objective":True})
        tr=put(r,"tr.json",{"exact_transform_bound":True,"independent_or_objective":True})
        er=put(r,"er.json",{"scope_complete":True,"independent_or_objective":True,"evaluators":["e1"]})
        hr=put(r,"hr.json",{"scope_complete":True,"independent_or_objective":True,"hard_constraints":["h1"]})
        pb=put(r,"pb.json",{"proved":True,"scope_complete":True,"independent_or_objective":True,"target_evaluator_id":"e1","source_evaluator_id":"se1"})
        hp=put(r,"hp.json",{"proved":True,"scope_complete":True,"independent_or_objective":True,"hard_constraint_id":"h1"})
        edge={"source_state":src,"target_state":dst,"transform":tr,"evaluator_registry":er,"hard_constraint_registry":hr,"pullbacks":{"e1":pb},"hard_constraint_preimages":{"h1":hp}}
        reg=put(r,"edges.json",{"scope_complete":True,"independent_or_objective":True,"load_bearing_edges":["x"]})
        return td,r,{"edge_registry":reg,"edge_certificates":{"x":edge}}

    def test_valid(self):
        td,r,c=self.fixture()
        try:
            x=verify_route(r,c); self.assertTrue(x["pass"]); self.assertEqual(x["edge_count"],1)
        finally: td.cleanup()

    def test_missing_pullback_fails(self):
        td,r,c=self.fixture()
        try:
            c["edge_certificates"]["x"]["pullbacks"]={}
            with self.assertRaisesRegex(AdmissionError,"PULLBACK_SET_MISMATCH"): verify_route(r,c)
        finally: td.cleanup()

    def test_missing_hard_preimage_fails(self):
        td,r,c=self.fixture()
        try:
            c["edge_certificates"]["x"]["hard_constraint_preimages"]={}
            with self.assertRaisesRegex(AdmissionError,"HARD_PREIMAGE_SET_MISMATCH"): verify_route(r,c)
        finally: td.cleanup()

    def test_blob_drift_fails(self):
        td,r,c=self.fixture()
        try:
            (r/"tr.json").write_text("{}\n",encoding="utf-8")
            with self.assertRaisesRegex(AdmissionError,"TRANSFORM_BLOB_MISMATCH"): verify_route(r,c)
        finally: td.cleanup()

    def test_edge_omission_fails(self):
        td,r,c=self.fixture()
        try:
            c["edge_certificates"]={}
            with self.assertRaisesRegex(AdmissionError,"EDGE_CERTIFICATE_SET_MISMATCH"): verify_route(r,c)
        finally: td.cleanup()

if __name__=="__main__": unittest.main(verbosity=2)
