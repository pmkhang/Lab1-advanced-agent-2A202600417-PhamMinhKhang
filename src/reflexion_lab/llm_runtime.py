"""LLM runtime — explicit mock/real selection with clear failure modes."""
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

RuntimeMode = str
_RUNTIME_MODE_OVERRIDE: str | None = None


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def set_runtime_mode(mode: str | None) -> None:
    global _RUNTIME_MODE_OVERRIDE
    _RUNTIME_MODE_OVERRIDE = mode


def get_runtime_mode(preferred_mode: str | None = None) -> RuntimeMode:
    """Resolve the runtime mode and fail loudly on invalid real-mode setup."""
    requested_mode = (
        preferred_mode or _RUNTIME_MODE_OVERRIDE or os.getenv("LLM_MODE") or "real"
    ).strip().lower()
    if requested_mode not in {"real", "mock", "auto"}:
        raise ValueError(
            f"Unsupported runtime mode: {requested_mode!r}. Use one of: real, mock, auto."
        )

    if _env_flag("USE_MOCK"):
        return "mock"
    if requested_mode == "mock":
        return "mock"
    if requested_mode == "auto":
        return "real" if os.getenv("OPENAI_API_KEY") else "mock"
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "Real LLM mode requires OPENAI_API_KEY. Set it, pass --mode mock, or export USE_MOCK=1."
        )
    return "real"


def get_runtime_info(preferred_mode: str | None = None) -> dict[str, str]:
    mode = get_runtime_mode(preferred_mode)
    return {
        "mode": mode,
        "model": "mock" if mode == "mock" else os.getenv("LLM_MODEL", "gpt-4o-mini"),
        "base_url": os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
    }


def _parse_json_response(content: str, step_name: str) -> dict:
    raw = re.sub(r"```[a-z]*\n?", "", content).replace("```", "").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{step_name} returned invalid JSON: {exc.msg}. Raw content: {raw}"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError(f"{step_name} must return a JSON object. Raw content: {raw}")
    return data


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
    if get_runtime_mode() == "mock":
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
    if get_runtime_mode() == "mock":
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
    data = _parse_json_response(content, "Evaluator")
    try:
        result = JudgeResult.model_validate(data)
    except Exception as exc:
        raise ValueError(f"Evaluator JSON did not match JudgeResult schema: {data}") from exc
    return result, tokens, latency


def reflector(
    example: QAExample, attempt_id: int, judge: JudgeResult
) -> tuple[ReflectionEntry, int, int]:
    """Returns (ReflectionEntry, token_estimate, latency_ms)."""
    if get_runtime_mode() == "mock":
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
    data = _parse_json_response(content, "Reflector")
    data.setdefault("attempt_id", attempt_id)
    data.setdefault("failure_reason", judge.reason)
    try:
        entry = ReflectionEntry.model_validate(data)
    except Exception as exc:
        raise ValueError(
            f"Reflector JSON did not match ReflectionEntry schema: {data}"
        ) from exc
    return entry, tokens, latency
