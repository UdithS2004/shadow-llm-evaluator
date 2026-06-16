# Shadow-Mode LLM Evaluator API Service

## Overview

This project is a FastAPI service that demonstrates shadow-mode evaluation for LLM responses.

The service receives customer traffic through `POST /generate`, calls a simulated Primary LLM synchronously, and immediately returns the Primary response to the client. It also enqueues a background Candidate LLM evaluation using `asyncio.Queue`.

The Candidate response is compared against the Primary response in the background. If the outputs differ, the service logs a mismatch and updates metrics.

## Key Behavior

- The client only waits for the Primary LLM.
- The Candidate LLM runs asynchronously in the background.
- Candidate latency does not affect the `/generate` response time.
- Candidate failures do not fail the client request.
- JSON outputs are extracted, normalized, and compared.
- Match rate is exposed through `/metrics`.

## Project Structure

```text
app/
  main.py          FastAPI app, routes, lifespan worker startup/shutdown
  background.py    Candidate shadow worker
  llms.py          Primary and Candidate LLM mocks
  json_utils.py    JSON extraction helper
  evaluator.py     JSON normalization, comparison, mismatch logging
  metrics.py       Async-safe metrics store

tests/
  test_json_utils.py
  test_evaluator.py
  test_integration.py

docs/
  architecture.md
```

## Setup

```bash
cd /workspaces/shadow-llm-evaluator
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the API

```bash
uvicorn app.main:app --reload
```

## Example Request

```bash
curl -s -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"hello"}' | jq
```

Example response:

```json
{
  "request_id": "example-request-id",
  "primary_response": {
    "model": "primary",
    "output": {
      "answer": "HELLO"
    }
  }
}
```

## Force a Mismatch

```bash
curl -s -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"hello","force_mismatch":true}' | jq
```

The Primary response still returns to the client. The Candidate response differs in the background, so a mismatch is logged and the mismatch count increases.

## Simulate a Slow Candidate

```bash
time curl -s -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"slow test","candidate_delay":2}' | jq
```

The response should return quickly even though the Candidate mock sleeps for 2 seconds.

## Metrics

```bash
curl -s http://127.0.0.1:8000/metrics | jq
```

Example response:

```json
{
  "total_comparisons": 3,
  "matches": 2,
  "mismatches": 1,
  "candidate_failures": 0,
  "match_rate_percent": 66.67,
  "queue_size": 0
}
```

## Testing

```bash
pytest
```

The integration test verifies that `/generate` returns quickly even when the Candidate model is slow.

## Architecture

See [docs/architecture.md](docs/architecture.md).

## Decoupling Explanation

The `/generate` endpoint awaits only `call_primary_llm(payload)`. Once the Primary response is available, the service creates a copied background job containing only:

```text
request_id
payload
primary_response
```

That job is pushed into an `asyncio.Queue` with `put_nowait`.

A background worker started during FastAPI lifespan consumes jobs from the queue and calls the Candidate LLM. The worker does not receive the FastAPI `Request` object and does not depend on the client HTTP connection staying open.

This design ensures that Candidate latency or failure cannot delay the Primary response.
