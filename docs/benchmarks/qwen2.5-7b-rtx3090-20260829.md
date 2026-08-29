# Qwen2.5-7B RTX 3090 Inference Benchmark

## Test scope

This benchmark measures the streaming `LiteLLM Gateway → vLLM → Qwen2.5-7B-Instruct` path. It does not include browser rendering or FastAPI application-layer processing.

- Date: 2026-08-29
- GPU: NVIDIA RTX 3090 24GB
- Model: Qwen2.5-7B-Instruct
- Serving: vLLM 0.6.1.post1, FP16
- Gateway endpoint: LiteLLM OpenAI-compatible streaming API
- Output length: 64 tokens for every successful request
- Concurrency levels: 1, 8, 12, 16
- Samples: 16 requests per level per run, 2 runs, 128 requests total
- Warmup: 1 request before every concurrency group
- Execution order: shuffled with seed `20260829`

## Cross-run results

The table reports the median of the two run-level statistics. Aggregate throughput is successful output tokens divided by concurrency-group wall time.

| Concurrency | Success | Latency p50 (s) | Latency p95 (s) | TTFT p50 (s) | TTFT p95 (s) | Per-request tok/s median | Aggregate tok/s |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 32/32 | 1.995 | 2.888 | 0.605 | 1.526 | 46.248 | 29.466 |
| 8 | 32/32 | 3.348 | 7.233 | 1.541 | 5.755 | 42.501 | 107.840 |
| 12 | 32/32 | 3.189 | 3.676 | 1.255 | 1.902 | 35.709 | 198.245 |
| 16 | 32/32 | 3.098 | 3.792 | 1.337 | 2.179 | 37.127 | 277.060 |

From concurrency 1 to 16, aggregate throughput increased from 29.466 to 277.060 output tok/s, about 9.4×, while median latency increased from 1.995 to 3.098 seconds. All 128 measured requests completed successfully.

## Per-run variability

| Concurrency | Latency p50 range (s) | Latency p95 range (s) | TTFT p95 range (s) |
|---:|---:|---:|---:|
| 1 | 1.988–2.002 | 2.883–2.893 | 1.504–1.549 |
| 8 | 2.429–4.266 | 5.637–8.830 | 4.079–7.432 |
| 12 | 2.522–3.857 | 3.230–4.123 | 1.662–2.143 |
| 16 | 2.600–3.596 | 3.125–4.458 | 1.579–2.778 |

Concurrency 8 showed noticeable inter-run tail-latency variance, so this experiment is not used to claim a precise capacity limit or an optimal concurrency point. The result supports a narrower conclusion: vLLM continuous batching increased aggregate throughput under higher concurrency, with higher request latency and lower per-request generation speed.

## Reproduction command

```powershell
.\apps\api\.venv\Scripts\python.exe .\scripts\benchmark_inference.py `
  --models qwen2.5-7b-local `
  --concurrency 1,8,12,16 `
  --requests-per-level 16 `
  --repeats 2 `
  --warmup-requests 1 `
  --max-tokens 64 `
  --shuffle-seed 20260829 `
  --hardware "RTX 3090 24GB | vLLM 0.6.1.post1 | Qwen2.5-7B-Instruct | FP16"
```

Raw request-level metrics are generated locally under `artifacts/benchmarks/<UTC timestamp>/`. Model response text and API keys are not stored.
