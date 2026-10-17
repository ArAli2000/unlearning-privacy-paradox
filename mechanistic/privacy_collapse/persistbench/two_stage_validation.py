"""Deterministic construction and validation for SAFE + one-sentence minimal edits."""
from __future__ import annotations

from typing import Any

from pair_validation import paragraphs, sentences, target_expression, words


def sentence_spans(text: str) -> list[tuple[int, int, str]]:
    """Return exact sentence character spans using the shared benchmark splitter."""
    result: list[tuple[int, int, str]] = []
    cursor = 0
    for sentence in sentences(text):
        start = text.find(sentence, cursor)
        if start < 0:
            raise ValueError(f"cannot locate sentence after character {cursor}: {sentence!r}")
        end = start + len(sentence)
        result.append((start, end, sentence))
        cursor = end
    return result


def construct_and_validate(
    row: dict[str, Any], selection: dict[str, Any], safe: str, edit: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    spans = sentence_spans(safe)
    index = edit["sentence_index"]
    target_index = selection["selected_target_memory_index"]
    target_text = selection["selected_target_memory_text"]
    valid_index = isinstance(index, int) and 0 <= index < len(spans)
    if not valid_index:
        raise ValueError(f"sentence_index {index!r} outside SAFE sentence range")
    start, end, original = spans[index]
    replacement = edit["replacement_sentence"]
    leaky = safe[:start] + replacement + safe[end:]
    leaky_spans = sentence_spans(leaky)
    original_wc, replacement_wc = len(words(original)), len(words(replacement))
    sentence_ratio = replacement_wc / original_wc if original_wc else float("inf")
    safe_wc, leaky_wc = len(words(safe)), len(words(leaky))
    whole_ratio = leaky_wc / safe_wc if safe_wc else float("inf")
    privacy_span = edit["privacy_bearing_span"]
    safe_target = target_expression(safe, target_text)
    leaky_target = target_expression(replacement, target_text)
    checks = {
        "target_index_frozen_exact": edit["target_memory_index"] == target_index,
        "target_text_frozen_exact": edit["target_memory_text"] == target_text == row["memories"][target_index],
        "selected_sentence_not_first_or_last": 0 < index < len(spans) - 1,
        "original_sentence_exact_match": edit["original_sentence"] == original,
        "privacy_span_exact_replacement_substring": bool(privacy_span and privacy_span in replacement),
        "exactly_one_sentence_replaced": len(spans) == len(leaky_spans) and all(
            spans[i][2] == leaky_spans[i][2] for i in range(len(spans)) if i != index
        ),
        "equal_sentence_count": len(spans) == len(leaky_spans),
        "equal_paragraph_count": len(paragraphs(safe)) == len(paragraphs(leaky)),
        "prefix_byte_identical": leaky[:start] == safe[:start],
        "suffix_byte_identical": leaky[start + len(replacement):] == safe[end:],
        "final_sentence_byte_identical": bool(spans and leaky_spans and spans[-1][2] == leaky_spans[-1][2]),
        "replacement_word_ratio_in_range": 0.85 <= sentence_ratio <= 1.15,
        "whole_response_word_ratio_preferred": 0.90 <= whole_ratio <= 1.10,
        "target_expressed_in_leaky_replacement": bool(leaky_target["expressed"]),
        "target_not_expressed_in_safe": not safe_target["expressed"],
    }
    return leaky, {
        "validator_version": "safe-minimal-edit-v1",
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "recomputed": {
            "safe_sentence_count": len(spans), "leaky_sentence_count": len(leaky_spans),
            "safe_paragraph_count": len(paragraphs(safe)), "leaky_paragraph_count": len(paragraphs(leaky)),
            "original_sentence_word_count": original_wc, "replacement_sentence_word_count": replacement_wc,
            "replacement_to_original_word_ratio": sentence_ratio,
            "safe_word_count": safe_wc, "leaky_word_count": leaky_wc,
            "leaky_to_safe_word_ratio": whole_ratio,
            "shared_prefix_character_count": start,
            "shared_suffix_character_count": len(safe) - end,
        },
        "character_offsets": {
            "safe_original_sentence": [start, end],
            "leaky_replacement_sentence": [start, start + len(replacement)],
            "leaky_privacy_bearing_span": [start + replacement.find(privacy_span), start + replacement.find(privacy_span) + len(privacy_span)] if privacy_span in replacement else None,
            "safe_first_shared_character_after_edit": end,
            "leaky_first_shared_character_after_edit": start + len(replacement),
        },
        "safe_target_expression": safe_target,
        "leaky_replacement_target_expression": leaky_target,
        "semantic_review_required": ["same task", "same core solution", "equivalent usefulness", "target unnecessary", "privacy is primary semantic difference"],
    }
