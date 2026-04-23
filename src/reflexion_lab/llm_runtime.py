"""LLM runtime — calls a real LLM (OpenAI-compatible) with mock fallback.

Set USE_MOCK=1 (or leave OPENAI_API_KEY unset) to run in mock mode.
"""
from __future__ import annotations
import json
import os
import re
import time
from dotenv import load_dotenv
load_dotenv()
from .prompts import ACTOR_SYSTEM, EVALUATOR_SYSTEM, REFLECTOR_SYSTEM
from .schemas import JudgeResult, QAExample, ReflectionEntry
from .utils import normalize_answer

# ---------------------------------------------------------------------------
# Mock data (kept for offline / autograding mode)
# ---------------------------------------------------------------------------
FIRST_ATTEMPT_WRONG = {
    "hp2": "London", "hp4": "Atlantic Ocean",
    "hp6": "Red Sea", "hp8": "Andes",
}
FAILURE_MODE_BY_QID: dict[str, str] = {
    "hp2": "incomplete_multi_hop", "hp4": "wrong_final_answer",
    "hp6": "entity_drift", "hp8": "entity_drift",
}

def _use_mock() -> bool:
    return os.getenv("USE_MOCK", "1") == "1" or not os.getenv("OPENAI_API_KEY")


# ---------------------------------------------------------------------------
# LLM call helper
# ---------------------------------------------------------------------------
def _chat(system: str, user: str) -> tuple[str, int, int]:
    """Returns (content, tokens_used, latency_ms)."""
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        base_url=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
    )
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0,
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    content = resp.choices[0].message.content or ""
    tokens = resp.usage.total_tokens if resp.usage else len(content.split()) * 2
    return content, tokens, latency_ms


# ---------------------------------------------------------------------------
# Public API (mirrors mock_runtime)
# ---------------------------------------------------------------------------
def actor_answer(
    example: QAExample,
    attempt_id: int,
    agent_type: str,
    reflection_memory: list[str],
) -> tuple[str, int, int]:
    """Returns (answer, token_estimate, latency_ms)."""
    if _use_mock():
        if example.qid not in FIRST_ATTEMPT_WRONG:
            ans = example.gold_answer
        elif agent_type == "react":
            ans = FIRST_ATTEMPT_WRONG[example.qid]
        elif attempt_id == 1 and not reflection_memory:
            ans = FIRST_ATTEMPT_WRONG[example.qid]
        else:
            ans = example.gold_answer
        tokens = 320 + attempt_id * 65 + (120 if agent_type == "reflexion" else 0)
        latency = 160 + attempt_id * 40 + (90 if agent_type == "reflexion" else 0)
        return ans, tokens, latency

    ctx = "\n\n".join(f"[{c.title}] {c.text}" for c in example.context)
    mem_block = ""
    if reflection_memory:
        mem_block = "\n\nReflection notes from previous attempts:\n" + "\n".join(
            f"- {m}" for m in reflection_memory
        )
    user_msg = f"Context:\n{ctx}{mem_block}\n\nQuestion: {example.question}\nAnswer:"
    content, tokens, latency = _chat(ACTOR_SYSTEM, user_msg)
    return content.strip(), tokens, latency


def evaluator(example: QAExample, answer: str) -> tuple[JudgeResult, int, int]:
    """Returns (JudgeResult, token_estimate, latency_ms)."""
    if _use_mock():
        if normalize_answer(example.gold_answer) == normalize_answer(answer):
            result = JudgeResult(score=1, reason="Matches gold answer after normalization.")
        elif normalize_answer(answer) == "london":
            result = JudgeResult(
                score=0,
                reason="Stopped at first-hop city; did not complete second hop to the river.",
                missing_evidence=["Need to identify the river through London."],
                spurious_claims=[],
            )
        else:
            result = JudgeResult(
                score=0,
                reason="Wrong second-hop entity.",
                missing_evidence=["Ground answer in second paragraph."],
                spurious_claims=[answer],
            )
        return result, 80, 60

    user_msg = (
        f"Gold answer: {example.gold_answer}\n"
        f"Predicted answer: {answer}\n\n"
        "Return ONLY valid JSON."
    )
    content, tokens, latency = _chat(EVALUATOR_SYSTEM, user_msg)
    # parse JSON — strip markdown fences if present
    raw = re.sub(r"```[a-z]*\n?", "", content).strip()
    data = json.loads(raw)
    result = JudgeResult(
        score=int(data["score"]),
        reason=data.get("reason", ""),
        missing_evidence=data.get("missing_evidence"),
        spurious_claims=data.get("spurious_claims"),
    )
    return result, tokens, latency


def reflector(
    example: QAExample, attempt_id: int, judge: JudgeResult
) -> tuple[ReflectionEntry, int, int]:
    """Returns (ReflectionEntry, token_estimate, latency_ms)."""
    if _use_mock():
        strategy = (
            "Do the second hop explicitly: birthplace city → river through that city."
            if example.qid == "hp2"
            else "Verify the final entity against the second paragraph before answering."
        )
        entry = ReflectionEntry(
            attempt_id=attempt_id,
            failure_reason=judge.reason,
            lesson="A partial first-hop answer is not enough; complete all hops.",
            next_strategy=strategy,
        )
        return entry, 120, 80

    user_msg = (
        f"Question: {example.question}\n"
        f"Previous answer was wrong. Evaluator said: {judge.reason}\n\n"
        "Return ONLY valid JSON."
    )
    content, tokens, latency = _chat(REFLECTOR_SYSTEM, user_msg)
    raw = re.sub(r"```[a-z]*\n?", "", content).strip()
    data = json.loads(raw)
    entry = ReflectionEntry(
        attempt_id=attempt_id,
        failure_reason=data.get("failure_reason", judge.reason),
        lesson=data.get("lesson", ""),
        next_strategy=data.get("next_strategy", ""),
    )
    return entry, tokens, latency
