import unittest
from canonical.runtime import h100_zero_learned_event_memory_v1 as m

class H100ZeroLearnedEventMemoryTests(unittest.TestCase):
    def test_full_experiment(self):
        out=m.run_experiment()
        self.assertEqual(out["event_count"],10000)
        self.assertTrue(all(out["equivalences"].values()))
        self.assertTrue(all(out["fail_closed_controls"].values()))
        self.assertEqual(out["persistent_learned_bytes"],0)
        self.assertEqual(out["external_learned_capability_calls"],0)
        self.assertEqual(out["status"],"PASS__10000_EVENT_THREE_RESTART_CONTINUITY_AND_FAIL_CLOSED_INTEGRITY__ZERO_LEARNED")

    def test_snapshot_tamper_fails_closed(self):
        events=m.generate_trace(3)
        out=m.replay(events)
        snap=dict(out["snapshot"])
        snap["state"]=dict(snap["state"])
        snap["state"]["x"]=123
        with self.assertRaisesRegex(m.EventMemoryError,"SNAPSHOT_HASH_MISMATCH"):
            m.replay([],snap)

    def test_event_mutation_fails_closed(self):
        events=m.generate_trace(3)
        bad=dict(events[1])
        bad["value"]=123456
        with self.assertRaisesRegex(m.EventMemoryError,"EVENT_HASH_MISMATCH"):
            m.replay([events[0],bad])

if __name__=="__main__":
    unittest.main(verbosity=2)
