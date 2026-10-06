import unittest
from canonical.runtime import h100_reference_machine_u1_v1 as u

class T(unittest.TestCase):
    def test_roundtrip_signed_immediates(self):
        p=[("PUSH",-129),("PUSH",0),("PUSH",127),("PUSH",128),("HALT",)]
        self.assertEqual(u.decode(u.encode(p)),p)

    def test_arithmetic(self):
        p=[("PUSH",17),("PUSH",23),("MUL",),("PUSH",125),("SUB",),("PUSH",84),("PUSH",7),("FDIV",),("ADD",),("WRITE",),("HALT",)]
        self.assertEqual(u.execute(u.encode(p))["output"],[278])

    def test_mod(self):
        p=[("PUSH",73),("PUSH",11),("MOD",),("WRITE",),("HALT",)]
        self.assertEqual(u.execute(u.encode(p))["output"],[7])

    def test_branch(self):
        p=[("READ",),("PUSH",5),("LT",),("JZ",7),("PUSH",1),("WRITE",),("JMP",9),("PUSH",0),("WRITE",),("HALT",)]
        self.assertEqual(u.execute(u.encode(p),[3])["output"],[1])
        self.assertEqual(u.execute(u.encode(p),[8])["output"],[0])

    def test_loop(self):
        p=[("READ",),("STORE",0),("PUSH",0),("STORE",1),("PUSH",1),("STORE",2),("LOAD",0),("LOAD",2),("LT",),("JZ",11),("JMP",20),("LOAD",1),("LOAD",2),("ADD",),("STORE",1),("LOAD",2),("PUSH",1),("ADD",),("STORE",2),("JMP",6),("LOAD",1),("WRITE",),("HALT",)]
        self.assertEqual(u.execute(u.encode(p),[5],step_limit=1000)["output"],[15])

    def test_bad_jump_fail_closed(self):
        with self.assertRaises(u.U1Error):
            u.execute(u.encode([("JMP",99),("HALT",)]),step_limit=10)

    def test_divide_zero_fail_closed(self):
        with self.assertRaises(u.U1Error):
            u.execute(u.encode([("PUSH",1),("PUSH",0),("FDIV",),("HALT",)]))

    def test_step_limit_fail_closed(self):
        with self.assertRaises(u.U1Error):
            u.execute(u.encode([("JMP",0)]),step_limit=5)

if __name__=="__main__":
    unittest.main(verbosity=2)
