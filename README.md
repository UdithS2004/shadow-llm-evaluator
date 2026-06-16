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
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open the browser docs:

```text
http://127.0.0.1:8000/docs
```

## Endpoints

```text
POST /generate
GET  /metrics
POST /mock/primary
POST /mock/candidate
```

## Demo 1: Normal Request

```json
{
  "prompt": "hello"
}
```

Expected Primary response:

```json
{
  "model": "primary",
  "output": {
    "answer": "HELLO"
  }
}
```

Then check:

```text
GET /metrics
```

`matches` should increase.

## Demo 2: Forced Mismatch

```json
{
  "prompt": "hello",
  "force_mismatch": true
}
```

The client still receives the Primary response:

```json
{
  "answer": "HELLO"
}
```

The Candidate returns:

```json
{
  "answer": "HELLO!"
}
```

Then check:

```text
GET /metrics
```

`mismatches` should increase.

## Demo 3: Slow Candidate

```json
{
  "prompt": "slow test",
  "candidate_delay": 2
}
```

The Candidate sleeps for 2 seconds in the background, but `/generate` still returns quickly with:

```json
{
  "answer": "SLOW TEST"
}
```

This proves Candidate latency does not delay the Primary response.

## Demo 4: Candidate Failure

```json
{
  "prompt": "hello",
  "force_candidate_error": true
}
```

The client still receives the Primary response. The Candidate failure is handled in the background.

Then check:

```text
GET /metrics
```

`candidate_failures` should increase.

## Metrics Example

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

## Run Tests

```bash
pytest
```

Expected:

```text
18 passed
```

## Key Implementation Details

`/generate` waits only for the Primary LLM:

```python
primary_response = await call_primary_llm(payload)
```

Then it copies the payload, request ID, and Primary response into a queue job:

```python
shadow_queue.put_nowait(job)
```

The Candidate LLM runs later in `app/background.py`.

The worker compares only the `output` fields, because model metadata like `"primary"` and `"candidate"` is expected to differ.

JSON outputs are extracted and normalized before comparison so formatting differences, markdown fences, and key order do not cause false mismatches.

## Production Notes

This interview version uses an in-memory `asyncio.Queue` and in-memory metrics.

For production, I would add:

```text
Durable queue: Redis, SQS, Kafka, or Celery
Persistent mismatch storage
Structured logging
LLM timeouts and retries
Authentication and rate limiting
Prometheus metrics
Shared metrics backend for multi-instance deployments
```
