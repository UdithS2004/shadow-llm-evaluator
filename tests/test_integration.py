"""Integration tests proving `/generate` stays fast with slow candidate."""

import asyncio
import time

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.metrics import metrics


@pytest.mark.asyncio
async def test_generate_returns_quickly_and_background_runs():
    await metrics.reset()

    payload = {
        "prompt": "slow test",
        "candidate_delay": 1,
    }

    transport = ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            start = time.perf_counter()

            response = await client.post("/generate", json=payload)

            elapsed = time.perf_counter() - start

            assert response.status_code == 200
            assert elapsed < 0.3, f"Request took too long: {elapsed}s"

            body = response.json()

            assert "request_id" in body
            assert body["primary_response"]["output"]["answer"] == "SLOW TEST"

            await asyncio.sleep(1.2)

            metrics_response = await client.get("/metrics")

            assert metrics_response.status_code == 200

            snapshot = metrics_response.json()

            assert snapshot["total_comparisons"] >= 1
            assert snapshot["matches"] >= 1
            assert snapshot["mismatches"] == 0