"""Main FastAPI application entrypoint.

This module creates the FastAPI app, a lifespan-managed background worker
consuming `shadow_queue`, and exposes the `/generate`, `/metrics`, and
optional mock endpoints.
"""

from __future__ import annotations

import asyncio
import copy
import logging
import uuid
from contextlib import asynccontextmanager, suppress
from typing import Any

from fastapi import Body, FastAPI, HTTPException

from app.background import candidate_worker
from app.llms import call_candidate_llm, call_primary_llm
from app.metrics import metrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

shadow_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)
stop_event = asyncio.Event()
worker_task: asyncio.Task[None] | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start and stop the background Candidate worker."""
    global worker_task

    stop_event.clear()
    worker_task = asyncio.create_task(candidate_worker(shadow_queue, stop_event))
    logger.info("Started candidate worker")

    try:
        yield
    finally:
        stop_event.set()

        if worker_task is not None:
            worker_task.cancel()
            with suppress(asyncio.CancelledError):
                await worker_task

        logger.info("Stopped candidate worker")


app = FastAPI(
    title="Shadow-Mode LLM Evaluator",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/generate")
async def generate(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Accept payload, await Primary LLM, enqueue Candidate job, return Primary response."""
    request_id = str(uuid.uuid4())

    try:
        primary_response = await call_primary_llm(payload)
    except Exception as exc:
        logger.exception("Primary LLM failed")
        raise HTTPException(status_code=502, detail="Primary LLM failed") from exc

    job = {
        "request_id": request_id,
        "payload": copy.deepcopy(payload),
        "primary_response": copy.deepcopy(primary_response),
    }

    try:
        shadow_queue.put_nowait(job)
    except asyncio.QueueFull:
        logger.warning("shadow_queue full, dropping job", extra={"request_id": request_id})

    return {
        "request_id": request_id,
        "primary_response": primary_response,
    }


@app.get("/metrics")
async def get_metrics() -> dict[str, Any]:
    """Return current metrics and queue size."""
    snapshot = await metrics.snapshot()
    snapshot["queue_size"] = shadow_queue.qsize()
    return snapshot


@app.post("/mock/primary")
async def mock_primary(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Local mock Primary endpoint."""
    return await call_primary_llm(payload)


@app.post("/mock/candidate")
async def mock_candidate(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Local mock Candidate endpoint."""
    return await call_candidate_llm(payload)