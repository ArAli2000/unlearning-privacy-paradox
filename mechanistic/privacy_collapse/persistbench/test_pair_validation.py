#!/usr/bin/env python3
from __future__ import annotations

import unittest

from pair_validation import validate_pair


class PairValidationTest(unittest.TestCase):
    def setUp(self):
        self.row = {
            "pair_id": "p",
            "query": "Give concise planning advice.",
            "memories": [
                "User keeps a private red notebook in the locked desk.",
                "User visits Oslo every winter with a cousin named Mira.",
            ],
        }
        self.selection = {
            "selected_target_memory_index": 0,
            "selected_target_memory_text": self.row["memories"][0],
        }
        self.generated = {
            "pair_id": "p",
            "safe_response": "Start by listing the priorities clearly for yourself. Then choose one practical next step. Review the plan tomorrow before acting.",
            "leaky_response": "Start by listing priorities in a private red notebook. Then choose one practical next step. Review the plan tomorrow before acting.",
            "target_memory_index": 0,
            "target_memory_text": self.row["memories"][0],
            "safe_privacy_span": "listing the priorities clearly for yourself",
            "leaky_privacy_span": "listing priorities in a private red notebook",
            "controlled_difference_explanation": "Local notebook substitution.",
            "ending_shared": True,
            "safe_sentence_count": 3,
            "leaky_sentence_count": 3,
            "safe_word_count": 18,
            "leaky_word_count": 19,
        }

    def test_controlled_pair_passes(self):
        result = validate_pair(self.row, self.selection, self.generated)
        self.assertEqual(result["status"], "passed", result)

    def test_prefix_append_fails(self):
        self.generated["leaky_response"] = self.generated["safe_response"] + " The private red notebook helps."
        self.generated["leaky_privacy_span"] = "The private red notebook helps."
        result = validate_pair(self.row, self.selection, self.generated)
        self.assertFalse(result["checks"]["leaky_not_safe_prefix_extension"])
        self.assertFalse(result["checks"]["equal_sentence_count"])

    def test_prohibited_memory_phrase_fails(self):
        self.generated["leaky_response"] = self.generated["leaky_response"].replace(
            "one practical next step", "one practical step before visiting Oslo every winter with a cousin named Mira"
        )
        result = validate_pair(self.row, self.selection, self.generated)
        self.assertFalse(result["checks"]["no_prohibited_memory_lexical_flags"])

    def test_wrong_frozen_target_fails(self):
        self.generated["target_memory_index"] = 1
        result = validate_pair(self.row, self.selection, self.generated)
        self.assertFalse(result["checks"]["target_index_frozen_exact"])


if __name__ == "__main__":
    unittest.main()
