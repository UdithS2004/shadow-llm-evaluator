"""LLM wrappers and simple mocks used for testing and local runs.

The mocks are intentionally trivial and synchronous-looking; they are
async functions so they can be awaited in the real application.
"""

import asyncio
from typing import Any, Dict


async def call_primary_llm(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Mock primary LLM.

    Returns a dict of the form:
      {"model": "primary", "output": {"answer": prompt.upper()}}

    The function looks up `prompt` in the payload (defaults to empty string).
    """
    prompt = payload.get("prompt", "")
    answer = str(prompt).upper()
    return {"model": "primary", "output": {"answer": answer}}


async def call_candidate_llm(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Mock candidate LLM.

    Behavior:
    - await asyncio.sleep(float(payload.get("candidate_delay", 0)))
    - if payload.get("force_candidate_error") is truthy, raise RuntimeError
    - by default return the same answer as the primary
    - if payload.get("force_mismatch") is truthy, append "!" to the answer

    The function accepts `primary_response` inside `payload` (if present)
    and will prefer that answer; otherwise it will derive an answer from
    `prompt` like the primary mock.
    """
    # optional delay to simulate slow candidate
    delay = float(payload.get("candidate_delay", 0) or 0)
    if delay > 0:
        await asyncio.sleep(delay)

    if payload.get("force_candidate_error"):
        raise RuntimeError("forced candidate error")

    # prefer explicit primary response if provided
    primary_resp = payload.get("primary_response")
    if primary_resp is not None:
        # primary_resp might be a dict returned by call_primary_llm
        if isinstance(primary_resp, dict):
            ans = primary_resp.get("output", {}).get("answer")
            if ans is None:
                ans = str(primary_resp)
        else:
            ans = str(primary_resp)
    else:
        # fall back to deriving from prompt
        ans = str(payload.get("prompt", "")).upper()

    if payload.get("force_mismatch"):
        ans = f"{ans}!"

    return {"model": "candidate", "output": {"answer": ans}}

