import unittest
from canonical.runtime.hle_symbolic_surface_solver_v1 import propose

class T(unittest.TestCase):
    def test_fraction_expression(self):
        q=r'Compute \(\frac{3}{4}+\frac{1}{4}\).'
        o=propose(task_id='a',question=q)
        self.assertEqual(o['candidate_answer'],'1')

    def test_sqrt(self):
        q=r'Evaluate \(\sqrt{81}\).'
        o=propose(task_id='b',question=q)
        self.assertEqual(o['candidate_answer'],'9')

    def test_positive_power_root(self):
        q=r'Let x satisfy \(x^2=49\). Find the positive value of x.'
        o=propose(task_id='c',question=q)
        self.assertEqual(o['candidate_answer'],'7')

    def test_linear(self):
        q=r'Solve \(3*x+5=20\) for x.'
        o=propose(task_id='d',question=q)
        self.assertEqual(o['candidate_answer'],'5')

    def test_variable_expression_fails(self):
        q=r'Evaluate \(x+2\).'
        o=propose(task_id='e',question=q)
        self.assertTrue(o['status'].startswith('FAIL_CLOSED'))

    def test_image_fails(self):
        o=propose(task_id='f',question=r'Compute \(2+2\).',has_nonempty_image_payload=True)
        self.assertIsNone(o['candidate_answer'])

    def test_no_model(self):
        o=propose(task_id='g',question=r'Compute \(2+3*4\).')
        self.assertEqual(o['candidate_answer'],'14')
        self.assertEqual(o['external_model_calls'],0)

if __name__=='__main__':
    unittest.main(verbosity=2)
