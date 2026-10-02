import unittest

from canonical.runtime.consensus_dom_grounding import ConsensusRequest, ObservedElement, ground_consensus_action


class Tests(unittest.TestCase):
    def setUp(self):
        self.elements = [
            ObservedElement(
                "save",
                "button",
                "Save Changes",
                "Save Changes",
                "SAVE   CHANGES",
                {"data-testid": "save"},
                frozenset({"click"}),
            ),
            ObservedElement(
                "cancel",
                "button",
                "Cancel",
                "Cancel",
                "Cancel",
                {"data-testid": "cancel"},
                frozenset({"click"}),
            ),
            ObservedElement(
                "email",
                "textbox",
                "Email",
                "",
                "Email",
                {"name": "email"},
                frozenset({"type"}),
            ),
        ]

    def test_unicode_case_whitespace_normalized_consensus(self):
        out = ground_consensus_action(
            ConsensusRequest("click", role=" BUTTON ", name="save changes", ocr_text="Save Changes"),
            self.elements,
        )
        self.assertEqual(out["status"], "SELECT", out)
        self.assertEqual(out["element_id"], "save")
        self.assertEqual(out["matched_cues"], ["name", "ocr_text", "role"])

    def test_attribute_and_role_are_independent_cues(self):
        out = ground_consensus_action(
            ConsensusRequest("type", role="textbox", attrs={"name": "EMAIL"}),
            self.elements,
        )
        self.assertEqual(out["status"], "SELECT", out)
        self.assertEqual(out["element_id"], "email")

    def test_insufficient_request_cues_fails_closed(self):
        out = ground_consensus_action(
            ConsensusRequest("click", name="Save Changes"),
            self.elements,
        )
        self.assertEqual(out["status"], "ESCALATE", out)
        self.assertEqual(out["reason"], "REQUEST_HAS_INSUFFICIENT_INDEPENDENT_CUES")

    def test_conflicting_channel_rejects_candidate(self):
        out = ground_consensus_action(
            ConsensusRequest("click", role="button", name="Save Changes", text="Cancel"),
            self.elements,
        )
        self.assertEqual(out["status"], "ESCALATE", out)
        self.assertEqual(out["reason"], "NO_CONSENSUS_MATCH")

    def test_ambiguous_consensus_fails_closed(self):
        duplicate = ObservedElement(
            "save2",
            "button",
            "Save Changes",
            "Save Changes",
            "Save Changes",
            {"data-testid": "save2"},
            frozenset({"click"}),
        )
        out = ground_consensus_action(
            ConsensusRequest("click", role="button", name="Save Changes"),
            self.elements + [duplicate],
        )
        self.assertEqual(out["status"], "ESCALATE", out)
        self.assertEqual(out["reason"], "AMBIGUOUS_CONSENSUS_MATCH")

    def test_hidden_or_disabled_not_selected(self):
        hidden = [
            ObservedElement(
                "x",
                "button",
                "Save",
                "Save",
                "Save",
                {},
                frozenset({"click"}),
                visible=False,
            )
        ]
        out = ground_consensus_action(
            ConsensusRequest("click", role="button", name="Save"),
            hidden,
        )
        self.assertEqual(out["status"], "ESCALATE", out)

    def test_wrong_action_rejected(self):
        out = ground_consensus_action(
            ConsensusRequest("type", role="button", name="Save Changes"),
            self.elements,
        )
        self.assertEqual(out["status"], "ESCALATE", out)

    def test_duplicate_element_ids_fail_closed(self):
        dup = [self.elements[0], self.elements[0]]
        out = ground_consensus_action(
            ConsensusRequest("click", role="button", name="Save Changes"),
            dup,
        )
        self.assertEqual(out["status"], "ESCALATE", out)
        self.assertEqual(out["reason"], "ELEMENT_IDENTITIES_INVALID_OR_DUPLICATE")

    def test_min_three_cues_rejects_two_cue_match(self):
        out = ground_consensus_action(
            ConsensusRequest("click", role="button", name="Cancel", min_independent_cues=3),
            self.elements,
        )
        self.assertEqual(out["status"], "ESCALATE", out)
        self.assertEqual(out["reason"], "REQUEST_HAS_INSUFFICIENT_INDEPENDENT_CUES")


if __name__ == "__main__":
    unittest.main(verbosity=2)
