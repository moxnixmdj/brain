import unittest

from canonical.runtime.bounded_request_complement_semantics_v1 import parse_request_complement


class TestBoundedRequestComplementSemanticsV1(unittest.TestCase):
    def test_requested_that_you(self):
        x=parse_request_complement("Your supervisor has requested that you provide an Excel file.")
        self.assertEqual(x["status"],"RESOLVED_ONE_SIDED_REQUEST_COMPLEMENT")
        self.assertEqual(x["directive"]["predicate"],"provide")

    def test_you_will_need_to(self):
        x=parse_request_complement("You will need to calculate the percentage of total funds.")
        self.assertEqual(x["directive"]["predicate"],"calculate")

    def test_you_are_required_to(self):
        x=parse_request_complement("You are required to keep track of all items received.")
        self.assertEqual(x["directive"]["predicate"],"keep" if x["status"]=="RESOLVED_ONE_SIDED_REQUEST_COMPLEMENT" else "keep")

    def test_asked_to(self):
        x=parse_request_complement("Your manager asked you to create a schedule.")
        self.assertEqual(x["directive"]["predicate"],"create")

    def test_would_like_you_to(self):
        x=parse_request_complement("Your manager would like you to build a sample production plan.")
        self.assertEqual(x["directive"]["predicate"],"build")

    def test_using_context(self):
        s="Using the attached file, prepare a file in Excel."
        x=parse_request_complement(s)
        self.assertEqual(x["directive"]["predicate"],"prepare")
        cs,ce=x["context"]["span"]
        self.assertEqual(s[cs:ce],"the attached file")

    def test_bullet_without_space(self):
        x=parse_request_complement("-Conduct research regarding current guidance.")
        self.assertEqual(x["directive"]["predicate"],"conduct")

    def test_please_account_for(self):
        x=parse_request_complement("Please account for this in your API design.")
        self.assertEqual(x["directive"]["predicate"],"account")

    def test_you_should(self):
        x=parse_request_complement("You should edit these out and replace them with silence.")
        self.assertEqual(x["directive"]["predicate"],"edit")
        self.assertFalse(x["directive"]["coordination_split"])

    def test_declarative_not_promoted(self):
        x=parse_request_complement("The report includes a summary.")
        self.assertEqual(x["status"],"UNRESOLVED")

    def test_no_whole_task_claim(self):
        x=parse_request_complement("Please create a short report.")
        self.assertFalse(x["semantic_completeness_claim"])
        self.assertFalse(x["terminal_authority"])


if __name__=="__main__":
    unittest.main(verbosity=2)
