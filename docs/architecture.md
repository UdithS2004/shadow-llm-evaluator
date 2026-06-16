# Architecture Diagram

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI /generate
    participant Primary as Primary LLM Mock
    participant Queue as asyncio.Queue
    participant Worker as Background Worker
    participant Candidate as Candidate LLM Mock
    participant Eval as JSON Extract + Compare
    participant Logs as Mismatch Logs
    participant Metrics as Metrics Store

    Client->>API: POST /generate
    API->>Primary: Await primary response
    Primary-->>API: Primary response
    API->>Queue: Enqueue copied shadow job
    API-->>Client: Return primary response immediately

    Queue-->>Worker: Dequeue shadow job
    Worker->>Candidate: Await candidate response
    Candidate-->>Worker: Candidate response
    Worker->>Eval: Compare primary output vs candidate output

    alt Outputs match
        Eval->>Metrics: record_match()
    else Outputs differ
        Eval->>Logs: log_mismatch()
        Eval->>Metrics: record_mismatch()
    end

    alt Candidate fails
        Worker->>Metrics: record_candidate_failure()
    end
```

## Decoupling

The `/generate` endpoint awaits only the Primary LLM mock. After the Primary response is available, the endpoint copies the request payload, request ID, and Primary response into an `asyncio.Queue`.

The Candidate LLM is called later by a lifespan-managed background worker. Because the request handler does not await the Candidate call, Candidate latency or failure does not delay the client response.
