# llama.cpp Server API Research

## Key Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/v1/chat/completions` | POST | Primary inference (OpenAI-compatible) |
| `/v1/completions` | POST | Legacy text completion |
| `/v1/embeddings` | POST | Vector embeddings |
| `/health` | GET | Server status (`ok`, `loading`, `no_slot_available`) |
| `/metrics` | GET | Prometheus-formatted metrics |
| `/props` | GET | Server config and model metadata |
| `/slots` | GET | Real-time inference slot status |

## Timing Fields in Responses

llama.cpp includes timing data in API responses (when `timings_per_token` is enabled or in the final response):

- `prompt_ms` — Total prompt processing time (ms)
- `prompt_per_token_ms` — Average ms per prompt token
- `prompt_per_second` — Prompt tokens per second
- `predicted_n` — Number of generated tokens
- `predicted_ms` — Total generation time (ms)
- `predicted_per_token_ms` — Average ms per generated token
- `predicted_per_second` — Generation tokens per second
- `total_ms` (derived) — Total request time

## Token Usage Fields

- `prompt_tokens` — Number of tokens in the prompt
- `completion_tokens` — Number of generated tokens
- `total_tokens` — Sum of prompt + completion tokens

## Streaming Support

Uses SSE (Server-Sent Events) when `stream: true`. The proxy needs to handle streaming responses transparently, capturing the final timing chunk.

## Architecture Implication

The proxy will:
1. Intercept POST to `/v1/chat/completions` and `/v1/completions`
2. Forward to llama.cpp at localhost:8000
3. Parse response for timing/token fields
4. Store metrics in SQLite
5. Forward response to client unchanged
