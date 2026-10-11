import hashlib
import unittest
from canonical.runtime.hle_exact_retrieval_extract_v2 import propose

P={
 "https://a.test":"The synthetic blue mechanism uses Quartz Lattice to stabilize the fictional reactor.",
 "https://b.test":"Independent synthetic notes describe Quartz Lattice as the stabilizing mechanism.",
}
def search(q,limit=12):return {'status':'PASS','results':[{'url':u} for u in P]}
def fetch(u,max_bytes=600000):
    t=P[u]
    return {'status':'PASS','url':u,'final_url':u,'body_excerpt':t,
            'body_sha256':hashlib.sha256(t.encode()).hexdigest()}

class T(unittest.TestCase):
    def test_general_fallback(self):
        o=propose(task_id='g',question='Describe the stabilizing mechanism used by the synthetic blue reactor.',search_fn=search,fetch_fn=fetch)
        self.assertEqual(o['status'],'CANDIDATE_GENERATED')
        self.assertTrue(o['fallback_general_form'])
        self.assertEqual(o['external_model_calls'],0)

    def test_specific_delegates(self):
        o=propose(task_id='y',question='In what year was the fictional device invented?',
                  search_fn=lambda q,limit=12:{'status':'PASS','results':[]},fetch_fn=fetch)
        self.assertFalse(o['fallback_general_form'])

    def test_image_still_fails(self):
        o=propose(task_id='i',question='Describe it.',has_nonempty_image_payload=True,search_fn=search,fetch_fn=fetch)
        self.assertTrue(o['status'].startswith('FAIL_CLOSED'))

if __name__=='__main__':
    unittest.main(verbosity=2)
