import unittest
from canonical.runtime.explicit_positive_complement_semantics_v1 import extract,segments

class Tests(unittest.TestCase):
    def hit(self,s,kind=None):
        x=extract(s); self.assertGreater(x["positive_unit_count"],0,x)
        if kind: self.assertEqual(x["positive_units"][0]["construction"],kind)
        self.assertFalse(x["whole_task_semantics_proved"])
        self.assertFalse(x["policy_adequacy_proved"])
        self.assertFalse(x["terminal_authority"])

    def test_passive_asked_curly_apostrophe(self):
        self.hit("Because of seniority, you’ve been asked to create a guide.","PASSIVE_ASK")
    def test_requested_that_you(self):
        self.hit("A supervisor has requested that you provide an Excel file.","REQUESTED_THAT_YOU")
    def test_role_to(self):
        self.hit("Your job is to source and research several options.","ROLE_TO")
    def test_second_person_need(self):
        self.hit("You will need to create a weekly schedule.","YOU_DEONTIC")
    def test_context_imperative(self):
        self.hit("Accordingly, create a double-sided brochure.","CONTEXT_IMPERATIVE")
    def test_using_you_will(self):
        self.hit("Using the original layout, you will create an updated plan.","USING_YOU_WILL")
    def test_bullet_without_space(self):
        self.hit("-Conduct research regarding current guidance.","BULLET_IMPERATIVE")
    def test_filename_and_decimal_not_split(self):
        s="Refer to Sample.pdf for costs. Please use 0.4 units. Create a report."
        self.assertEqual(segments(s),["Refer to Sample.pdf for costs.","Please use 0.4 units.","Create a report."])
    def test_declarative_not_promoted(self):
        x=extract("Reference materials are attached. The report includes a summary.")
        self.assertEqual(x["positive_unit_count"],0)
        self.assertFalse(x["absence_proves_no_positive_semantics"])
    def test_no_argument_semantics_from_coordination(self):
        x=extract("Your responsibility is to investigate and report suspicious activity.")
        self.assertEqual(x["positive_units"][0]["action_head"],"investigate")
        self.assertFalse(x["whole_task_semantics_proved"])

if __name__=="__main__": unittest.main(verbosity=2)
