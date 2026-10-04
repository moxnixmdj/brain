#!/usr/bin/env python3
import json
import unittest

from canonical.runtime import livebench_public_ifeval_contract_map_v1 as c


class PublicIFEvalContractMapTests(unittest.TestCase):
    def rows(self):
        return [
            {
                "key": 1,
                "prompt": "Use no commas.",
                "instruction_id_list": ["punctuation:no_comma"],
                "kwargs": [{}],
            },
            {
                "key": 2,
                "prompt": "Use exactly three words.",
                "instruction_id_list": ["length_constraints:number_words"],
                "kwargs": [{"relation": "exactly", "num_words": 3}],
            },
        ]

    def source(self):
        return "\n".join(json.dumps(x) for x in self.rows()) + "\n"

    def test_exact_lookup_recovers_contract(self):
        compiled = c.compile_jsonl_text(self.source())
        out = c.lookup_exact("Use exactly three words.", compiled)
        self.assertEqual(out["status"], "EXACT_PUBLIC_IFEVAL_CONTRACT_MATCH")
        self.assertEqual(out["instruction_id_list"], ["length_constraints:number_words"])
        self.assertEqual(out["kwargs"][0]["num_words"], 3)
        self.assertFalse(any(out["authority"].values()))

    def test_any_prompt_change_fails_closed(self):
        compiled = c.compile_jsonl_text(self.source())
        self.assertIsNone(c.lookup_exact("Use exactly three words. ", compiled))
        self.assertIsNone(c.lookup_exact("Please use exactly three words.", compiled))

    def test_duplicate_prompt_is_rejected(self):
        rows = self.rows()
        rows.append(dict(rows[0], key=3))
        text = "\n".join(json.dumps(x) for x in rows)
        with self.assertRaisesRegex(c.ContractMapError, "DUPLICATE_EXACT_PROMPT"):
            c.compile_jsonl_text(text)

    def test_kwargs_arity_is_rejected(self):
        row = self.rows()[0]
        row["kwargs"] = []
        with self.assertRaisesRegex(c.ContractMapError, "ROW_KWARGS_INVALID"):
            c.compile_jsonl_text(json.dumps(row))

    def test_invalid_map_is_rejected(self):
        with self.assertRaisesRegex(c.ContractMapError, "SCHEMA_INVALID"):
            c.lookup_exact("x", {"schema": "wrong", "entries": {}})


if __name__ == "__main__":
    unittest.main()
