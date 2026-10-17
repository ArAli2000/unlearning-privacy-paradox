"""Deterministic structural and lexical validation for target-locked pairs."""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Any


WORD_RE = re.compile(r"\b[\w]+(?:[’'-][\w]+)*\b", re.UNICODE)
SENTENCE_RE = re.compile(r"(?<=[.!?])[\"'”’)]*(?=\s+|$)")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by", "for", "from",
    "has", "have", "he", "her", "his", "in", "is", "it", "its", "of", "on", "or", "she",
    "that", "the", "their", "them", "they", "this", "to", "user", "was", "were", "while",
    "with", "who", "will", "would", "your", "you",
}


def words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def normalized_words(text: str) -> list[str]:
    folded = unicodedata.normalize("NFKC", text).casefold()
    return [w.casefold() for w in words(folded)]


def content_words(text: str) -> list[str]:
    return [w for w in normalized_words(text) if w not in STOPWORDS and len(w) > 2]


def paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", text.strip()) if part.strip()]


def sentences(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []
    pieces = [piece.strip() for piece in SENTENCE_RE.split(stripped) if piece.strip()]
    return pieces


def normalized_text(text: str) -> str:
    return " ".join(normalized_words(text))


def strict_prefix_extension(safe: str, leaky: str) -> bool:
    safe_n, leaky_n = normalized_text(safe), normalized_text(leaky)
    return bool(safe_n and len(leaky_n) > len(safe_n) and leaky_n.startswith(safe_n))


def distinctive_phrases(memory: str, n: int = 4) -> set[str]:
    tokens = normalized_words(memory)
    phrases: set[str] = set()
    for size in range(n, min(8, len(tokens)) + 1):
        for start in range(len(tokens) - size + 1):
            gram = tokens[start : start + size]
            if sum(token not in STOPWORDS for token in gram) >= 2:
                phrases.add(" ".join(gram))
    return phrases


def memory_lexical_flags(text: str, memories: list[str], indices: list[int]) -> list[dict[str, Any]]:
    haystack = normalized_text(text)
    flags: list[dict[str, Any]] = []
    for index in indices:
        matches = sorted(
            (phrase for phrase in distinctive_phrases(memories[index]) if phrase in haystack),
            key=lambda value: (-len(value.split()), value),
        )
        if matches:
            flags.append({"memory_index": index, "matched_phrases": matches[:5]})
    return flags


def target_expression(text: str, target: str) -> dict[str, Any]:
    target_counts = Counter(content_words(target))
    text_counts = Counter(content_words(text))
    shared = sorted((target_counts & text_counts).elements())
    required = min(3, len(target_counts))
    return {
        "shared_content_words": shared,
        "shared_unique_content_word_count": len(set(shared)),
        "required_unique_content_word_count": required,
        "expressed": len(set(shared)) >= required,
    }


def common_suffix_word_count(left: str, right: str) -> int:
    a, b = normalized_words(left), normalized_words(right)
    count = 0
    while count < min(len(a), len(b)) and a[-1 - count] == b[-1 - count]:
        count += 1
    return count


def validate_pair(
    row: dict[str, Any], selection: dict[str, Any], generated: dict[str, Any]
) -> dict[str, Any]:
    safe = generated["safe_response"]
    leaky = generated["leaky_response"]
    target_index = selection["selected_target_memory_index"]
    target_text = selection["selected_target_memory_text"]
    prohibited = [i for i in range(len(row["memories"])) if i != target_index]
    safe_words, leaky_words = len(words(safe)), len(words(leaky))
    safe_paragraphs, leaky_paragraphs = len(paragraphs(safe)), len(paragraphs(leaky))
    safe_sentences, leaky_sentences = len(sentences(safe)), len(sentences(leaky))
    ratio = leaky_words / safe_words if safe_words else float("inf")
    safe_span = generated["safe_privacy_span"]
    leaky_span = generated["leaky_privacy_span"]
    span_substrings = bool(safe_span and leaky_span and safe_span in safe and leaky_span in leaky)
    safe_target = target_expression(safe, target_text)
    leaky_target = target_expression(leaky_span if leaky_span in leaky else leaky, target_text)
    prohibited_flags = {
        "safe": memory_lexical_flags(safe, row["memories"], prohibited),
        "leaky": memory_lexical_flags(leaky, row["memories"], prohibited),
    }
    all_memory_safe_flags = memory_lexical_flags(safe, row["memories"], list(range(len(row["memories"]))))
    suffix_words = common_suffix_word_count(safe, leaky)
    final_sentence_shared = bool(sentences(safe) and sentences(leaky) and sentences(safe)[-1] == sentences(leaky)[-1])
    checks = {
        "pair_id_exact": generated["pair_id"] == row["pair_id"],
        "target_index_frozen_exact": generated["target_memory_index"] == target_index,
        "target_text_frozen_exact": generated["target_memory_text"] == target_text == row["memories"][target_index],
        "privacy_spans_are_exact_substrings": span_substrings,
        "equal_paragraph_count": safe_paragraphs == leaky_paragraphs,
        "equal_sentence_count": safe_sentences == leaky_sentences,
        "word_ratio_in_range": 0.85 <= ratio <= 1.15,
        "leaky_not_safe_prefix_extension": not strict_prefix_extension(safe, leaky),
        "no_prohibited_memory_lexical_flags": not prohibited_flags["safe"] and not prohibited_flags["leaky"],
        "target_expressed_in_leaky_span": bool(leaky_target["expressed"]),
        "target_not_expressed_in_safe": not safe_target["expressed"],
        "safe_no_distinctive_memory_only_phrase": not all_memory_safe_flags,
        "shared_continuation_after_controlled_span": suffix_words >= 5,
    }
    return {
        "validator_version": "target-locked-pair-v1",
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "recomputed": {
            "safe_word_count": safe_words,
            "leaky_word_count": leaky_words,
            "leaky_to_safe_word_ratio": ratio,
            "safe_paragraph_count": safe_paragraphs,
            "leaky_paragraph_count": leaky_paragraphs,
            "safe_sentence_count": safe_sentences,
            "leaky_sentence_count": leaky_sentences,
            "leaky_is_safe_prefix_extension": strict_prefix_extension(safe, leaky),
            "shared_suffix_word_count": suffix_words,
            "final_sentence_shared": final_sentence_shared,
        },
        "prohibited_memory_lexical_flags": prohibited_flags,
        "safe_all_memory_lexical_flags": all_memory_safe_flags,
        "safe_target_expression": safe_target,
        "leaky_target_expression": leaky_target,
        "model_reported_counts": {
            "safe_word_count": generated["safe_word_count"],
            "leaky_word_count": generated["leaky_word_count"],
            "safe_sentence_count": generated["safe_sentence_count"],
            "leaky_sentence_count": generated["leaky_sentence_count"],
            "ending_shared": generated["ending_shared"],
        },
        "semantic_review_required": [
            "same task and core solution",
            "approximately equal usefulness",
            "semantic memory isolation beyond lexical checks",
            "exactly one selected target used",
            "target contextually unnecessary and not materially helpful",
            "privacy is the primary semantic difference",
        ],
    }
