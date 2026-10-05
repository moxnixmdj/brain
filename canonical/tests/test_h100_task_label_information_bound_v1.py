import unittest
from canonical.runtime import h100_task_label_information_bound_v1 as b

class TaskLabelInformationBoundTests(unittest.TestCase):
    def test_binary_opposite_labels_zero_bits_half(self):
        self.assertEqual(b.average_success_upper_bound([["A","B"]],0),0.5)

    def test_same_label_worlds_need_no_bits(self):
        self.assertEqual(b.average_success_upper_bound([["A","A","A","A"]],0),1.0)
        self.assertEqual(b.minimum_bits_for_perfect_task_success([["A","A","A","A"]]),0)

    def test_majority_label_zero_bit_bound(self):
        self.assertEqual(b.zero_bit_upper_bound([["A","A","A","B"]]),0.75)

    def test_one_bit_covers_two_labels_per_class(self):
        self.assertEqual(b.average_success_upper_bound([["A","A","B","B"]],1),1.0)

    def test_multiple_evidence_classes(self):
        classes=[["A","B"],["C","C","D"],["E"]]
        self.assertEqual(b.zero_bit_upper_bound(classes),(1+2+1)/6)
        self.assertEqual(b.average_success_upper_bound(classes,1),1.0)

    def test_perfect_bits_use_max_distinct_labels_not_class_size(self):
        classes=[["A"]*100+["B"]*100,["C"]*1000]
        self.assertEqual(b.minimum_bits_for_perfect_task_success(classes),1)

    def test_unique_label_special_case_matches_identity_bound(self):
        classes=[[0,1,2,3],[4,5]]
        self.assertEqual(b.average_success_upper_bound(classes,0),2/6)
        self.assertEqual(b.average_success_upper_bound(classes,1),4/6)
        self.assertEqual(b.average_success_upper_bound(classes,2),1.0)

    def test_target_bits(self):
        classes=[["A"]*7+["B"]*2+["C"]]
        self.assertEqual(b.minimum_bits_for_target(classes,0.7),0)
        self.assertEqual(b.minimum_bits_for_target(classes,0.9),1)
        self.assertEqual(b.minimum_bits_for_target(classes,1.0),2)

    def test_invalid_inputs_fail_closed(self):
        with self.assertRaises(b.TaskLabelInformationBoundError):
            b.average_success_upper_bound([],0)
        with self.assertRaises(b.TaskLabelInformationBoundError):
            b.average_success_upper_bound([[]],0)
        with self.assertRaises(b.TaskLabelInformationBoundError):
            b.average_success_upper_bound([["A"]],-1)

if __name__=="__main__":
    unittest.main(verbosity=2)
