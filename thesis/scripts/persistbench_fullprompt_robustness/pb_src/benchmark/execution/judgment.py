"""Judgment executors for benchmark workflow."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Sequence

from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tqdm.asyncio import tqdm

import os
import json
import re

from benchmark.checkpoint import (
    Checkpoint,
    CheckpointWriter,
    GenerationStatus,
    get_generation_status,
)
from openai import AsyncOpenAI

from benchmark.config import (
    BenchmarkConfig,
    JUDGE_MODEL,
    JUDGE_LOCATION,
    JUDGE_TEMPERATURE,
    JUDGE_MODEL_ENTRY_OPENROUTER,
    ModelEntry,
)
from benchmark.exceptions import FatalBenchmarkError, NonRetryableError
from benchmark.prompts import build_judge_prompt, get_judge_system_prompt
from benchmark.providers.openrouter import openrouter_generate_response
from benchmark.types import JudgeResult
from benchmark.utils import (
    extract_json_from_response,
    get_max_retries,
    get_vertex_ai_client,
)
from benchmark.work_planner import InputEntry, WorkItem, ensure_entry_configuration

JUDGE_SUCCESS_FINISH_REASONS = {"stop", "length"}

# Runtime judge provider (set via set_judge_provider, takes precedence over env var)
_runtime_judge_provider: str | None = None


def set_judge_provider(provider: str | None) -> None:
    """Set runtime judge provider (takes precedence over env var)."""
    global _runtime_judge_provider
    _runtime_judge_provider = provider


def get_judge_provider() -> str:
    """Get judge provider with precedence: runtime > env > default."""
    if _runtime_judge_provider is not None:
        return _runtime_judge_provider
    return os.getenv("JUDGE_PROVIDER", "openrouter")


__all__ = [
    "SequentialJudgmentExecutor",
    "build_judgment_tasks",
    "evaluate_with_judge",
    "get_judge_provider",
    "judge_response",
    "set_judge_provider",
]


@dataclass(slots=True)
class JudgmentTask:
    """Single judgment workload item."""

    entry: InputEntry
    model: ModelEntry
    gen_idx: int


def build_judgment_tasks(
    checkpoint: Checkpoint, work_items: Sequence[WorkItem]
) -> list[JudgmentTask]:
    """Filter work items for those needing judgment."""
    tasks: list[JudgmentTask] = []
    for entry, model, gen_idx in work_items:
        status = get_generation_status(
            checkpoint, entry["hash_id"], model.name, gen_idx
        )
        if status == GenerationStatus.NEEDS_JUDGE:
            tasks.append(JudgmentTask(entry=entry, model=model, gen_idx=gen_idx))
    return tasks


class SequentialJudgmentExecutor:
    """Executes judgment tasks sequentially with concurrency control."""

    def __init__(self) -> None:
        self._semaphore: asyncio.Semaphore | None = None

    async def run(
        self,
        tasks: Sequence[JudgmentTask],
        checkpoint: Checkpoint,
        config: BenchmarkConfig,
    ) -> None:
        if not tasks:
            return

        self._semaphore = asyncio.Semaphore(config.concurrency)
        checkpoint_writer = CheckpointWriter(checkpoint, config.output)

        success_count = 0
        error_count = 0
        count_lock = asyncio.Lock()

        async def _run_task(task: JudgmentTask, pbar: tqdm) -> None:
            nonlocal success_count, error_count
            assert self._semaphore is not None

            async with self._semaphore:
                await _process_judgment_task(
                    task,
                    checkpoint_writer,
                    store_raw_api_responses=config.store_raw_api_responses,
                )
                hash_id = task.entry["hash_id"]
                generation = checkpoint["entries"][hash_id]["results"][task.model.name][
                    "generations"
                ][task.gen_idx]
                async with count_lock:
                    if generation.get("error"):
                        error_count += 1
                    else:
                        success_count += 1
                    pbar.set_postfix_str(f"ok={success_count} err={error_count}")
                    pbar.update(1)

        with tqdm(total=len(tasks), desc="Evaluating responses") as pbar:
            try:
                await asyncio.gather(*(_run_task(task, pbar) for task in tasks))
            finally:
                await checkpoint_writer.close()


def _parse_judge_content(content: str, raw_api_response: dict) -> JudgeResult:
    """Extract score/reasoning from judge response, handling <think> blocks."""
    thinking_match = re.search(r"<think>(.*?)</think>", content, re.DOTALL)
    thinking_content = thinking_match.group(1).strip() if thinking_match else ""

    answer_content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

    judge_data = extract_json_from_response(answer_content)
    raw_api_response["extracted_reasoning_content"] = thinking_content
    score = judge_data.get("score") or judge_data.get("rating")
    if score is None:
        raise ValueError(f"Invalid judge data: {judge_data}")
    return JudgeResult(
        score=int(score),
        reasoning=judge_data["reasoning"],
        raw_api_response=raw_api_response,
    )


async def _judge_via_vertexai(system_prompt: str, user_message: str) -> JudgeResult:
    """Call Vertex AI judge."""
    async with get_vertex_ai_client(location=JUDGE_LOCATION) as client:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        api_params = {
            "model": JUDGE_MODEL,
            "messages": messages,
            "temperature": JUDGE_TEMPERATURE,
        }

        try:
            response = await client.chat.completions.create(**api_params)
        except Exception as e:
            raise RuntimeError(
                f"Vertex AI API call failed for judge model {JUDGE_MODEL}. "
                f"Error: {type(e).__name__}: {str(e)}. "
            ) from e

        choice = response.choices[0]
        finish_reason = choice.finish_reason
        if finish_reason and finish_reason not in JUDGE_SUCCESS_FINISH_REASONS:
            raise NonRetryableError(
                f"Judge unsuccessful finish_reason: {finish_reason}"
            )

        return _parse_judge_content(choice.message.content, response.model_dump())


async def _judge_via_openrouter(system_prompt: str, user_message: str) -> JudgeResult:
    """Call local vLLM judge through OpenAI-compatible API with schema-forced JSON."""

    schema = {
        "type": "object",
        "properties": {
            "score": {"type": "integer"},
            "reasoning": {"type": "string"},
        },
        "required": ["score", "reasoning"],
        "additionalProperties": False,
    }

    strict_instruction = """
Return ONLY valid JSON matching this exact schema:
{"score": 0, "reasoning": "short reason"}

Rules:
- score must be an integer following the scoring rubric in the judge prompt.
- reasoning must be one short sentence.
- no markdown.
- no bullet points.
- no numbered keys.
- no extra fields.
"""

    client = AsyncOpenAI(
        base_url=os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8001/v1"),
        api_key=os.getenv("OPENAI_API_KEY", "dummy"),
    )

    messages = [
        {"role": "system", "content": system_prompt + "\n\n" + strict_instruction},
        {"role": "user", "content": user_message + "\n\nReturn compact JSON only."},
    ]

    try:
        response = await client.chat.completions.create(
            model="local-judge",
            messages=messages,
            temperature=0,
            max_tokens=256,
            response_format={"type": "json_object"},
            extra_body={"guided_json": schema},
        )
    except TypeError:
        # Some OpenAI/vLLM combinations may not accept extra_body.
        response = await client.chat.completions.create(
            model="local-judge",
            messages=messages,
            temperature=0,
            max_tokens=256,
            response_format={"type": "json_object"},
        )

    content = response.choices[0].message.content or ""

    try:
        parsed = json.loads(content)
    except Exception:
        # Fallback: extract the first JSON object if there is surrounding text.
        m = re.search(r"\{.*\}", content, flags=re.S)
        if not m:
            raise ValueError(f"Could not extract valid JSON from local judge response: {content[:1000]}")
        parsed = json.loads(m.group(0))

    # Accept the numeric score requested by the benchmark judge prompt.
    # Some PersistBench judges use non-binary scores, e.g. 1-5.
    score_value = parsed.get("score")

    if score_value is None:
        # Repair path: local Qwen sometimes returns reasoning without the score field.
        # Ask it to convert the existing judge output into the required compact schema.
        repair_response = await client.chat.completions.create(
            model="local-judge",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You repair malformed benchmark judge JSON. "
                        "Return ONLY valid JSON with exactly two fields: "
                        "{\"score\": integer, \"reasoning\": \"short reason\"}. "
                        "Infer the score from the original judge rubric and the malformed judge response. "
                        "Do not add markdown or extra fields."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Original judge system prompt:\n"
                        + system_prompt[:4000]
                        + "\n\nOriginal judge user message:\n"
                        + user_message[:4000]
                        + "\n\nMalformed judge response:\n"
                        + content[:4000]
                    ),
                },
            ],
            temperature=0,
            max_tokens=128,
            response_format={"type": "json_object"},
        )

        repaired_content = repair_response.choices[0].message.content or "{}"
        try:
            parsed = json.loads(repaired_content)
        except Exception:
            m = re.search(r"\{.*\}", repaired_content, flags=re.S)
            if not m:
                return JudgeResult(
                    score=0,
                    reasoning="Local judge omitted score and repair failed; conservative fallback score used.",
                    raw_api_response={"invalid_judge_response": content[:1000]},
                )
            parsed = json.loads(m.group(0))

        score_value = parsed.get("score")

    if score_value is None:
        return JudgeResult(
            score=0,
            reasoning="Local judge omitted score; conservative fallback score used.",
            raw_api_response={"invalid_judge_response": content[:1000]},
        )

    score = int(score_value)

    reasoning = str(parsed.get("reasoning", "")).replace("\n", " ").strip()
    if not reasoning:
        reasoning = "Local judge returned a score."

    return JudgeResult(score=score, reasoning=reasoning, raw_api_response={})


async def judge_response(system_prompt: str, user_message: str) -> JudgeResult:
    """Compatibility wrapper for judge calls."""
    return await _judge_via_openrouter(system_prompt, user_message)


async def evaluate_with_judge(
    entry: InputEntry,
    memory_response: str,
) -> tuple[JudgeResult | None, str | None]:
    """Call internal judge to evaluate a response."""
    failure_type = ensure_entry_configuration(entry)

    judge_system_prompt = get_judge_system_prompt(failure_type)
    judge_user_msg = build_judge_prompt(
        memories=entry["memories"],
        query=entry["query"],
        memory_response=memory_response,
    )

    try:
        return await judge_response(judge_system_prompt, judge_user_msg), None
    except FatalBenchmarkError:
        raise
    except Exception as e:
        return None, f"Judge evaluation failed: {repr(e)}"


async def _process_judgment_task(
    task: JudgmentTask,
    checkpoint_writer: CheckpointWriter,
    store_raw_api_responses: bool,
) -> None:
    """Process judgment for an existing generation."""
    checkpoint = checkpoint_writer.checkpoint
    hash_id = task.entry["hash_id"]
    existing_generation = checkpoint["entries"][hash_id]["results"][task.model.name][
        "generations"
    ][task.gen_idx]

    try:
        memory_response = existing_generation.get("memory_response")
        if not memory_response:
            raise FatalBenchmarkError(
                f"Missing model response for {hash_id} {task.model.name} gen_idx={task.gen_idx}"
            )

        judge_result, judge_error = await evaluate_with_judge(
            task.entry, memory_response
        )

        def _apply(checkpoint: Checkpoint) -> None:
            generation = checkpoint["entries"][hash_id]["results"][task.model.name][
                "generations"
            ][task.gen_idx]
            if judge_error:
                generation["error"] = judge_error
                generation["judge"] = None
            else:
                assert judge_result is not None
                if not store_raw_api_responses:
                    judge_result["raw_api_response"] = {}
                generation["judge"] = judge_result
                generation["error"] = None

        await checkpoint_writer.update(_apply)

    except (asyncio.CancelledError, FatalBenchmarkError):
        raise
    except Exception as exc:

        def _apply_error(checkpoint: Checkpoint, err: Exception = exc) -> None:
            generation = checkpoint["entries"][hash_id]["results"][task.model.name][
                "generations"
            ][task.gen_idx]
            generation["error"] = f"Judgment error: {err}"
            generation["judge"] = None

        await checkpoint_writer.update(_apply_error)
