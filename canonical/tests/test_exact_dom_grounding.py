import unittest
from canonical.runtime.exact_dom_grounding import Element,GroundRequest,ground_exact_action

class ExactDomGroundingTests(unittest.TestCase):
    def setUp(self):
        self.elements=[
            Element("e1","button","Save","Save",{"data-testid":"save"},frozenset({"click"})),
            Element("e2","button","Cancel","Cancel",{"data-testid":"cancel"},frozenset({"click"})),
            Element("e3","textbox","Email","",{"name":"email"},frozenset({"type"})),
        ]
    def test_unique_exact(self):
        o=ground_exact_action(GroundRequest("click",role="button",name="Save"),self.elements)
        self.assertEqual(o["status"],"SELECT"); self.assertEqual(o["element_id"],"e1")
    def test_wrong_action_rejected(self):
        o=ground_exact_action(GroundRequest("type",role="button",name="Save"),self.elements)
        self.assertEqual(o["status"],"ESCALATE")
    def test_ambiguous_fails_closed(self):
        es=self.elements+[Element("e4","button","Save","Save",{},frozenset({"click"}))]
        o=ground_exact_action(GroundRequest("click",role="button",name="Save"),es)
        self.assertEqual(o["reason"],"AMBIGUOUS_EXACT_MATCH")
    def test_hidden_not_selected(self):
        es=[Element("e1","button","Save","Save",{},frozenset({"click"}),visible=False)]
        self.assertEqual(ground_exact_action(GroundRequest("click",name="Save"),es)["status"],"ESCALATE")
    def test_attribute_binding(self):
        o=ground_exact_action(GroundRequest("type",attrs={"name":"email"}),self.elements)
        self.assertEqual(o["element_id"],"e3")
if __name__=="__main__": unittest.main()
