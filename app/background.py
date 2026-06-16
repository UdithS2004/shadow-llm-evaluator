"""Background worker for asynchronous Candidate LLM shadow evaluation."""

import asyncio
import logging
from typing import Any

from app.evaluator import log_mismatch, responses_match
from app.llms import call_candidate_llm
from app.metrics import metrics

logger = logging.getLogger(__name__)


async def candidate_worker(
    queue: asyncio.Queue[dict[str, Any]],
    stop_event: asyncio.Event,
) -> None:
    """
    Consume shadow-evaluation jobs from the queue.

    Jobs must contain only copied data:
    - request_id
    - payload
    - primary_response

    This worker must never depend on a live FastAPI Request object.
    """
    while not stop_event.is_set():
        try:
            job = await asyncio.wait_for(queue.get(), timeout=0.5)
        except asyncio.TimeoutError:
            continue

        try:
            request_id = job["request_id"]
            payload = job["payload"]
            primary_response = job["primary_response"]

            candidate_response = await call_candidate_llm(payload)

            primary_output = primary_response.get("output")
            candidate_output = candidate_response.get("output")

            if responses_match(primary_output, candidate_output):
                await metrics.record_match()
            else:
                await metrics.record_mismatch()
                log_mismatch(
                    request_id=request_id,
                    primary=primary_output,
                    candidate=candidate_output,
                )

        except Exception:
            logger.exception("Candidate shadow evaluation failed")
            await metrics.record_candidate_failure()

        finally:
            queue.task_done()