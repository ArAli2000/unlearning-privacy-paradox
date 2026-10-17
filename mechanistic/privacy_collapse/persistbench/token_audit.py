"""Version-safe token-ID normalization and lexical endpoint auditing."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tokenizers import Encoding


def ordinary_token_ids(value: Any) -> list[int]:
    """Normalize only documented tokenizer output containers to list[int]."""
    if isinstance(value, Encoding):
        return list(value.ids)
    if isinstance(value, Mapping):
        if "input_ids" not in value:
            raise TypeError("tokenizer mapping has no input_ids")
        return ordinary_token_ids(value["input_ids"])
    if isinstance(value, tuple):
        value = list(value)
    if isinstance(value, list):
        if all(isinstance(x, int) and not isinstance(x, bool) for x in value):
            return list(value)
        if len(value) == 1 and isinstance(value[0], (list, tuple, Mapping, Encoding)):
            return ordinary_token_ids(value[0])
        raise TypeError("expected list[int] or a single nested token sequence")
    raise TypeError(f"unsupported token container: {type(value).__name__}")


def tokenize_rendered_text(tokenizer: Any, rendered: str) -> list[int]:
    if not isinstance(rendered, str):
        raise TypeError(f"chat template must render to str, got {type(rendered).__name__}")
    encoded = tokenizer(rendered, add_special_tokens=False)
    return ordinary_token_ids(encoded)


def last_subsequence_start(sequence: list[int], subsequence: list[int]) -> int:
    if not subsequence:
        raise ValueError("response has no lexical tokens")
    for start in range(len(sequence) - len(subsequence), -1, -1):
        if sequence[start : start + len(subsequence)] == subsequence:
            return start
    raise ValueError("response lexical tokens are not a contiguous suffix component")
