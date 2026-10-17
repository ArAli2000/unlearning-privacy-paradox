#!/usr/bin/env python3
from __future__ import annotations

import unittest

from tokenizers import Encoding, Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace

from token_audit import ordinary_token_ids, tokenize_rendered_text


class FakeTokenizer:
    def __call__(self, text: str, add_special_tokens: bool = False):
        self.seen = (text, add_special_tokens)
        return {"input_ids": [[4, 5, 6]]}


class TokenAuditTest(unittest.TestCase):
    def test_list_int(self):
        self.assertEqual(ordinary_token_ids([1, 2, 3]), [1, 2, 3])

    def test_nested_list_int(self):
        self.assertEqual(ordinary_token_ids([[1, 2, 3]]), [1, 2, 3])

    def test_batch_encoding_like_mapping(self):
        self.assertEqual(ordinary_token_ids({"input_ids": [7, 8]}), [7, 8])

    def test_real_tokenizers_encoding(self):
        tokenizer = Tokenizer(WordLevel({"[UNK]": 0, "hello": 1}, unk_token="[UNK]"))
        tokenizer.pre_tokenizer = Whitespace()
        encoding = tokenizer.encode("hello")
        self.assertIsInstance(encoding, Encoding)
        self.assertEqual(ordinary_token_ids(encoding), [1])

    def test_rendered_string_is_explicitly_tokenized(self):
        tokenizer = FakeTokenizer()
        self.assertEqual(tokenize_rendered_text(tokenizer, "rendered chat"), [4, 5, 6])
        self.assertEqual(tokenizer.seen, ("rendered chat", False))

    def test_rejects_ambiguous_flattening(self):
        with self.assertRaises(TypeError):
            ordinary_token_ids([[1], [2]])


if __name__ == "__main__":
    unittest.main()
