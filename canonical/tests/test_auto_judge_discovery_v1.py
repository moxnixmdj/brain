#!/usr/bin/env python3
"""Tests for automatic judge discovery & closed scan-diff-earn loop."""
from __future__ import annotations

import bz2
import json
import lzma
import os
import plistlib
import sqlite3
import tempfile
import unittest
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

from canonical.runtime import earn_a_judge_v1 as earner
from canonical.swe_kernel import auto_judge_discovery_v1 as ajd


class AutoJudgeDiscoveryTests(unittest.TestCase):
    def test_auto_discovery_earns_extended_formats_and_refuses_lazy_traps(self) -> None:
        receipt = ajd.auto_earn_judges(evaluate_all=True)
        self.assertEqual(receipt["model_calls"], 0)
        self.assertEqual(receipt["network_calls"], 0)
        self.assertEqual(receipt["parameters_stored"], 0)

        kinds = set(receipt["admitted_kinds"])
        for expected in ("bz2", "xz", "sqlite", "xml", "bplist", "wav", "pdf", "json", "zip", "tar", "gzip", "elf"):
            self.assertIn(expected, kinds, f"expected {expected} to be auto-earned")

        refused_ids = {row["candidate_id"]: row["status"] for row in receipt["refused"]}
        # Every lazy open / connect trap must be refused on evidence, never admitted
        self.assertEqual(refused_ids.get("py:bz2:lazy_open"), earner.REFUSED_ACCEPTS_EVERYTHING)
        self.assertEqual(refused_ids.get("py:lzma:lazy_open"), earner.REFUSED_ACCEPTS_EVERYTHING)
        # sqlite3.connect(p) either accepts decoy or mutates the directory -- never EARNED
        self.assertIn("py:sqlite3:connect_lazy", refused_ids)
        self.assertNotIn(refused_ids["py:sqlite3:connect_lazy"], (earner.EARNED, earner.NESTED))

    def test_closed_loop_turns_unread_room_into_understood_and_catches_lying_names(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ajd-room-") as tmp:
            room = Path(tmp) / "room"
            room.mkdir()
            # Real formats previously uncovered by Round 10-12's 7-judge seed
            with bz2.open(room / "archive.bz2", "wb") as fh:
                fh.write(b"bzip2 content\n")
            with lzma.open(room / "archive.xz", "wb", format=lzma.FORMAT_XZ) as fh:
                fh.write(b"xz content\n")
            conn = sqlite3.connect(room / "app.db")
            conn.execute("CREATE TABLE t (x INT)")
            conn.commit()
            conn.close()
            root_el = ET.Element("config")
            ET.ElementTree(root_el).write(room / "settings.xml", encoding="utf-8", xml_declaration=True)
            with open(room / "prefs.plist", "wb") as fh:
                plistlib.dump({"dark_mode": True}, fh, fmt=plistlib.FMT_BINARY)
            with wave.open(str(room / "beep.wav"), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(8000)
                wf.writeframes(b"\x00\x02" * 16)

            # Adversarial lying file: named .sqlite and .bz2, actually invalid binary garbage
            (room / "lying.sqlite").write_bytes(b"\xff\xfe\xfd\x00not_a_database")

            store = ajd.JudgeStore()
            # Cold start: 0 judges -> all 7 files UNREAD
            out = ajd.close_ignorance_loop(room, store=store)
            self.assertEqual(out["before"]["files"], 7)
            self.assertEqual(out["before"]["unread"], 7)
            # After auto-earning: the 6 real files are read; ONLY the genuinely corrupt blob stays UNREAD!
            self.assertEqual(out["after"]["unread"], 1)
            self.assertEqual(out["after"]["unread_paths"], ["lying.sqlite"])
            self.assertGreaterEqual(len(out["newly_admitted_judges"]), 10)
            self.assertGreater(out["ledger_stats_after"]["ever_helped"], 0)

            # Persistence & warm transfer to a brand-new unseen room with zero re-earning
            store_file = Path(tmp) / "store.json"
            store.save(store_file)
            saved_text = store_file.read_text(encoding="utf-8")
            # No file path from `room` may ever enter the store
            self.assertNotIn("archive.bz2", saved_text)
            self.assertNotIn("app.db", saved_text)

            warm_store = ajd.JudgeStore.load(store_file)
            unseen = Path(tmp) / "unseen"
            unseen.mkdir()
            with bz2.open(unseen / "renamed_completely.dat", "wb") as fh:
                fh.write(b"different bytes, same format\n")
            warm_out = ajd.close_ignorance_loop(unseen, store=warm_store)
            self.assertEqual(warm_out["before"]["unread"], 0)
            self.assertEqual(warm_out["before"]["known"], 1)
            self.assertEqual(warm_out["newly_admitted_judges"], [])

    def test_active_refutation_demotes_overbroad_exclusive_judge(self) -> None:
        # Plant a faulty 'exclusive' judge (`gzip -t`, which falsely accepts .zip files)
        store = ajd.JudgeStore([
            {"kind": "gzip", "argv": ["gzip", "-t"], "status": earner.EARNED},
        ])
        with tempfile.TemporaryDirectory(prefix="ajd-refute-") as tmp:
            pairs = earner.probe_pairs(tmp)
            demoted = store.refute_against_probe("zip", pairs["zip"]["real"])
            self.assertEqual(demoted, ["gzip"])
            self.assertNotIn("gzip", store.callable_validators())


if __name__ == "__main__":
    unittest.main()
