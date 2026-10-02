import unittest

from canonical.runtime.gdt_reference import extract_known_gdt_tokens, lookup_gdt_symbol


class GdtReferenceTests(unittest.TestCase):
    def test_position_symbol(self):
        out=lookup_gdt_symbol("⌖",standard="ASME_Y14_5_2018")
        self.assertEqual(out["status"],"MATCH")
        self.assertEqual(out["kind"],"CHARACTERISTIC")
        self.assertEqual(out["record"]["characteristic"],"Position")
        self.assertEqual(out["standard_status"],"active")

    def test_concentricity_withdrawn_in_asme_but_active_iso(self):
        asme=lookup_gdt_symbol("◎",standard="ASME_Y14_5_2018")
        iso=lookup_gdt_symbol("◎",standard="ISO_1101")
        self.assertEqual(asme["standard_status"],"withdrawn")
        self.assertEqual(iso["standard_status"],"active")

    def test_mmc_modifier(self):
        out=lookup_gdt_symbol("Ⓜ")
        self.assertEqual(out["kind"],"MODIFIER")
        self.assertEqual(out["record"]["modifier"],"MMC")

    def test_extract_mixed_frame_tokens(self):
        out=extract_known_gdt_tokens("⌖ ⌀0.05 Ⓜ A B C")
        self.assertEqual([x["symbol"] for x in out["tokens"]],["⌖","⌀","Ⓜ"])
        self.assertEqual(out["count"],3)

    def test_unknown_fails_closed(self):
        out=lookup_gdt_symbol("?")
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["error"],"UNKNOWN_SYMBOL")

    def test_unsupported_standard_fails_closed(self):
        out=lookup_gdt_symbol("⌖",standard="MADE_UP")
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["error"],"UNSUPPORTED_STANDARD")


if __name__=="__main__":
    unittest.main()
