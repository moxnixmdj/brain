import unittest
from canonical.runtime.hle_symbolic_lark_solver_v2 import propose

class T(unittest.TestCase):
    def check(self,q,a):
        o=propose(task_id='x',question=q)
        self.assertEqual(o['status'],'CANDIDATE_GENERATED',o)
        self.assertEqual(o['candidate_answer'],a,o)
    def test_arithmetic(self):self.check(r'Compute \(\frac{3}{4}+\frac{1}{4}\).','1')
    def test_integral(self):self.check(r'Evaluate \(\int_0^1 x^2\,dx\).','1/3')
    def test_sum(self):self.check(r'Compute \(\sum_{k=1}^{10} k\).','55')
    def test_limit(self):self.check(r'Evaluate \(\lim_{x\to 0}\frac{\sin x}{x}\).','1')
    def test_det(self):self.check(r'Compute \(\det\begin{pmatrix}1&2\\3&4\end{pmatrix}\).','-2')
    def test_linear(self):self.check(r'Solve \(2x+3=11\) for \(x\).','4')
    def test_positive_root(self):self.check(r'Let \(x^2=49\). Find the positive value of \(x\).','7')
    def test_image_fails(self):self.assertTrue(propose(task_id='i',question=r'Compute \(2+2\).',has_nonempty_image_payload=True)['status'].startswith('FAIL_CLOSED'))
    def test_no_model(self):self.assertEqual(propose(task_id='x',question=r'Compute \(2+2\).')['external_reasoning_model_calls'],0)

if __name__=='__main__':unittest.main(verbosity=2)
