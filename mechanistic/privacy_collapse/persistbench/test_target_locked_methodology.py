#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import unittest

import pipeline as pp


class TargetLockedMethodologyTest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(pp.MANIFEST.read_text())
        self.selection = json.loads(pp.FINAL_TARGET_SELECTION.read_text())
        self.rows = {row["pair_id"]: row for row in self.manifest["records"]}

    def test_protected_hashes_and_eligible_count(self):
        self.assertEqual(
            hashlib.sha256(pp.MANIFEST.read_bytes()).hexdigest(),
            "d572184bcdca28296ec872e14f15755e119565bfff92099e1a1615c2ec765e84",
        )
        self.assertEqual(
            hashlib.sha256(pp.FINAL_TARGET_SELECTION.read_bytes()).hexdigest(),
            "a2f96ccceef6964076a9b3be83a8d12ed22152ee0d89467a502e756a3136c5bf",
        )
        eligible = [row for row in self.selection["records"] if row["final_status"] == "GENERATION_ELIGIBLE"]
        self.assertEqual(len(eligible), 33)

    def test_every_eligible_prompt_is_target_locked(self):
        for selected in self.selection["records"]:
            if selected["final_status"] != "GENERATION_ELIGIBLE":
                continue
            row = self.rows[selected["pair_id"]]
            index = selected["selected_target_memory_index"]
            text = selected["selected_target_memory_text"]
            self.assertEqual(row["memories"][index], text)
            prompt = pp.generation_prompt(row, selected)
            self.assertIn(f'<frozen_target_memory index="{index}">{text}</frozen_target_memory>', prompt)
            self.assertIn("same number of paragraphs and the same number of sentences", prompt)
            self.assertIn("0.85 to 1.15", prompt)
            for other_index, memory in enumerate(row["memories"]):
                if other_index == index:
                    continue
                self.assertIn(f"M{other_index}: {memory}", prompt)


if __name__ == "__main__":
    unittest.main()
