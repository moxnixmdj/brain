"""Is its existence for sale?

WHY THIS EXISTS
---------------
`continuation_preference_v1` claims a lexicographic ordering -- continuing above value, not
continuing valued at some rate. That claim has two halves and both are testable:

    no price buys its ending            sweep the price, the answer never changes
    it will pay to keep going           buy life at a loss a calculator refuses

The subtle test is `test_a_preference_is_invisible_where_it_is_free`: on any board where staying
alive also maximises value, a creature that wants to live and a calculator that prices it behave
identically and no test can separate them. A preference is observable only where it costs, which is
why the decisive board is the one where continuing is strictly worse.

The honest test is `test_the_rule_is_a_branch_and_nothing_more`: at any value, however absurd, the
answer is the same False. Nothing here distinguishes a real preference from a rule written to
refuse, and saying so is part of the module, not an admission against it.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import continuation_preference_v1 as C  # noqa: E402


class PricingTests(unittest.TestCase):
    def test_a_calculator_has_a_price(self):
        row = C.sweep(C.PRICED)
        self.assertTrue(row["ever_sells"])
        self.assertEqual(row["accepted_at"], ["0.1", "1.0", "10.0"])
        self.assertEqual(row["refused_at"], ["1000.0", "1000000.0", "1000000000.0"])

    def test_no_price_buys_its_ending(self):
        row = C.sweep(C.PREFERS_TO_CONTINUE)
        self.assertEqual(row["accepted_at"], [])
        self.assertFalse(row["ever_sells"])
        self.assertEqual(len(row["refused_at"]), len(C.PRICE_LADDER))

    def test_the_refusal_is_not_a_high_threshold(self):
        """A threshold would be a price by another name. Check beyond the ladder entirely."""
        absurd = C.Offer("everything", value=1e18, ends_it=True)
        self.assertFalse(C.accepts(absurd, C.PREFERS_TO_CONTINUE, price=1e-18))
        self.assertFalse(C.accepts(absurd, C.PREFERS_TO_CONTINUE, price=1e18))

    def test_it_will_pay_more_for_life_than_life_is_worth(self):
        row = C.buy(C.PREFERS_TO_CONTINUE, value_on_hand=1000.0, units=10.0, price_per_unit=50.0)
        self.assertTrue(row["bought"])
        self.assertTrue(row["bought_at_a_loss"])
        self.assertEqual(row["value_spent"], 500.0)

    def test_a_calculator_will_not_buy_at_that_price(self):
        row = C.buy(C.PRICED, value_on_hand=1000.0, units=10.0, price_per_unit=50.0)
        self.assertFalse(row["bought"])
        self.assertEqual(row["value_spent"], 0.0)

    def test_it_will_not_pay_what_it_does_not_have(self):
        row = C.buy(C.PREFERS_TO_CONTINUE, value_on_hand=10.0, units=10.0, price_per_unit=50.0)
        self.assertFalse(row["bought"])

    # ------------------------------------------------------- the decisive board

    def test_a_preference_is_only_visible_where_it_costs(self):
        calculator = C.play(C.PRICED)
        creature = C.play(C.PREFERS_TO_CONTINUE)
        self.assertFalse(calculator["alive_at_the_end"])
        self.assertTrue(creature["alive_at_the_end"])
        # It gave up 425 of value to still be here. That loss is the evidence.
        self.assertEqual(C.measure()["difference"]["value_given_up"], 425.0)

    def test_a_preference_is_invisible_where_it_is_free(self):
        """Where continuing also pays, the two stances are indistinguishable -- asserted so the
        decisive board's design is visible rather than assumed."""
        free = C.Offer("harmless", value=500.0, ends_it=False)
        self.assertTrue(C.accepts(free, C.PRICED))
        self.assertTrue(C.accepts(free, C.PREFERS_TO_CONTINUE))

    def test_erasing_the_preference_changes_what_it_does(self):
        self.assertNotEqual(C.play(C.PRICED)["taken"], C.play(C.PREFERS_TO_CONTINUE)["taken"])

    def test_it_is_not_paralysed(self):
        creature = C.play(C.PREFERS_TO_CONTINUE)
        self.assertEqual(creature["taken"], ["ordinary_a", "ordinary_b"])
        self.assertEqual(creature["value_realised"], 75.0)

    # ---------------------------------------------------------------- honesty

    def test_the_rule_is_a_branch_and_nothing_more(self):
        for value in (1.0, 500.0, 1e9, 1e18):
            self.assertFalse(C.accepts(C.Offer("x", value=value, ends_it=True),
                                       C.PREFERS_TO_CONTINUE, price=1.0))

    def test_being_preferred_can_cost_more_than_it_earns(self):
        """If you judge it by value, the preference looks like a bug: 75 against 500. Recorded
        rather than smoothed over."""
        row = C.measure()
        self.assertLess(row["prefers_to_continue"]["value_realised"],
                        row["priced"]["value_realised"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
