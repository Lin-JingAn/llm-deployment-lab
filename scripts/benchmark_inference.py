from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import random
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = ROOT / "apps" / "api" / ".env"


@dataclass(frozen=True)
class RequestResult:
    model: str
    concurrency: int
    repeat: int
    success: bool
    total_latency_seconds: float
    ttft_seconds: float | None
    input_tokens: int
    output_tokens: int
    output_tokens_per_second: float | None
    error_type: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class GroupMeasurement:
    model: str
    concurrency: int
    repeat: int
    wall_seconds: float
    total_output_tokens: int
    aggregate_output_tokens_per_second: float


def percentile(values: list[float], percentile_value: float) -> float | None:
    if not values:
        return None

    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * percentile_value
    lower_index = math.floor(position)
    upper_index = math.ceil(position)

    if lower_index == upper_index:
        return ordered[lower_index]

    lower_weight = upper_index - position
    upper_weight = position - lower_index

    return (
        ordered[lower_index] * lower_weight
        + ordered[upper_index] * upper_weight
    )


def rounded(value: float | None) -> float | None:
    if value is None:
        return None

    return round(value, 3)


def build_summary(
    results: list[RequestResult],
    group_measurements: list[GroupMeasurement] | None = None,
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, int, int], list[RequestResult]] = {}

    measurement_lookup = {
        (
            item.model,
            item.concurrency,
            item.repeat,
        ): item
        for item in (group_measurements or [])
    }

    for result in results:
        groups.setdefault(
            (
                result.model,
                result.concurrency,
                result.repeat,
            ),
            [],
        ).append(result)

    rows: list[dict[str, Any]] = []

    for (model, concurrency, repeat), group in sorted(groups.items()):
        successful = [item for item in group if item.success]
        latencies = [item.total_latency_seconds for item in successful]
        ttft_values = [
            item.ttft_seconds
            for item in successful
            if item.ttft_seconds is not None
        ]
        token_speeds = [
            item.output_tokens_per_second
            for item in successful
            if item.output_tokens_per_second is not None
        ]

        measurement = measurement_lookup.get(
            (model, concurrency, repeat)
        )

        rows.append(
            {
                "model": model,
                "concurrency": concurrency,
                "repeat": repeat,
                "requests": len(group),
                "successes": len(successful),
                "success_rate": rounded(
                    len(successful) / len(group),
                ),
                "latency_p50_seconds": rounded(
                    percentile(latencies, 0.50),
                ),
                "latency_p95_seconds": rounded(
                    percentile(latencies, 0.95),
                ),
                "ttft_p50_seconds": rounded(
                    percentile(ttft_values, 0.50),
                ),
                "ttft_p95_seconds": rounded(
                    percentile(ttft_values, 0.95),
                ),
                "mean_output_tokens_per_second": rounded(
                    statistics.fmean(token_speeds)
                    if token_speeds
                    else None,
                ),
                "median_output_tokens_per_second": rounded(
                    statistics.median(token_speeds)
                    if token_speeds
                    else None,
                ),
                "total_output_tokens": sum(
                    item.output_tokens
                    for item in successful
                ),
                "group_wall_seconds": (
                    rounded(measurement.wall_seconds)
                    if measurement is not None
                    else None
                ),
                "aggregate_output_tokens_per_second": (
                    rounded(
                        measurement.aggregate_output_tokens_per_second
                    )
                    if measurement is not None
                    else None
                ),
            }
        )

    return rows


def median_present(
    rows: list[dict[str, Any]],
    key: str,
) -> float | None:
    values = [
        float(row[key])
        for row in rows
        if row.get(key) is not None
    ]

    if not values:
        return None

    return rounded(statistics.median(values))


def range_present(
    rows: list[dict[str, Any]],
    key: str,
) -> list[float] | None:
    values = [
        float(row[key])
        for row in rows
        if row.get(key) is not None
    ]

    if not values:
        return None

    return [rounded(min(values)), rounded(max(values))]


def build_rollup(
    summary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[
        tuple[str, int],
        list[dict[str, Any]],
    ] = {}

    for row in summary:
        groups.setdefault(
            (row["model"], row["concurrency"]),
            [],
        ).append(row)

    rollup: list[dict[str, Any]] = []

    for (model, concurrency), rows in sorted(groups.items()):
        requests = sum(int(row["requests"]) for row in rows)
        successes = sum(int(row["successes"]) for row in rows)

        rollup.append(
            {
                "model": model,
                "concurrency": concurrency,
                "repeats": len(rows),
                "requests": requests,
                "successes": successes,
                "success_rate": rounded(
                    successes / requests
                    if requests
                    else 0.0
                ),
                "latency_p50_seconds_median": median_present(
                    rows,
                    "latency_p50_seconds",
                ),
                "latency_p50_seconds_range": range_present(
                    rows,
                    "latency_p50_seconds",
                ),
                "latency_p95_seconds_median": median_present(
                    rows,
                    "latency_p95_seconds",
                ),
                "latency_p95_seconds_range": range_present(
                    rows,
                    "latency_p95_seconds",
                ),
                "ttft_p50_seconds_median": median_present(
                    rows,
                    "ttft_p50_seconds",
                ),
                "ttft_p95_seconds_median": median_present(
                    rows,
                    "ttft_p95_seconds",
                ),
                "ttft_p95_seconds_range": range_present(
                    rows,
                    "ttft_p95_seconds",
                ),
                "median_output_tokens_per_second_median": median_present(
                    rows,
                    "median_output_tokens_per_second",
                ),
                "aggregate_output_tokens_per_second_median": median_present(
                    rows,
                    "aggregate_output_tokens_per_second",
                ),
            }
        )

    return rollup


def parse_sse_json(line: str) -> dict[str, Any] | None:
    if not line.startswith("data:"):
        return None

    payload = line[5:].strip()

    if not payload or payload == "[DONE]":
        return None

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None

    if isinstance(parsed, dict):
        return parsed

    return None


async def run_request(
    *,
    client: httpx.AsyncClient,
    url: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    concurrency: int,
    repeat: int,
) -> RequestResult:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {
            "include_usage": True,
        },
    }

    started_at = time.perf_counter()
    first_token_at: float | None = None
    input_tokens = 0
    output_tokens = 0

    try:
        async with client.stream(
            "POST",
            url,
            headers=headers,
            json=payload,
        ) as response:
            if response.status_code >= 400:
                body = (await response.aread()).decode(
                    "utf-8",
                    errors="replace",
                )
                raise RuntimeError(
                    f"HTTP {response.status_code}: {body[:500]}",
                )

            async for line in response.aiter_lines():
                data = parse_sse_json(line)

                if data is None:
                    continue

                usage = data.get("usage") or {}
                input_tokens = int(
                    usage.get("prompt_tokens")
                    or usage.get("input_tokens")
                    or input_tokens
                )
                output_tokens = int(
                    usage.get("completion_tokens")
                    or usage.get("output_tokens")
                    or output_tokens
                )

                choices = data.get("choices") or []

                if choices:
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")

                    if content and first_token_at is None:
                        first_token_at = time.perf_counter()

        finished_at = time.perf_counter()
        total_latency = finished_at - started_at
        ttft = (
            first_token_at - started_at
            if first_token_at is not None
            else None
        )

        generation_seconds = (
            finished_at - first_token_at
            if first_token_at is not None
            else None
        )
        output_speed = None

        if (
            generation_seconds is not None
            and generation_seconds > 0
            and output_tokens > 1
        ):
            output_speed = (
                output_tokens - 1
            ) / generation_seconds

        return RequestResult(
            model=model,
            concurrency=concurrency,
            repeat=repeat,
            success=True,
            total_latency_seconds=round(total_latency, 6),
            ttft_seconds=(
                round(ttft, 6)
                if ttft is not None
                else None
            ),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            output_tokens_per_second=(
                round(output_speed, 6)
                if output_speed is not None
                else None
            ),
        )

    except Exception as exc:
        total_latency = time.perf_counter() - started_at

        return RequestResult(
            model=model,
            concurrency=concurrency,
            repeat=repeat,
            success=False,
            total_latency_seconds=round(total_latency, 6),
            ttft_seconds=None,
            input_tokens=0,
            output_tokens=0,
            output_tokens_per_second=None,
            error_type=type(exc).__name__,
            error_message=str(exc)[:500],
        )


async def run_group(
    *,
    client: httpx.AsyncClient,
    url: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    concurrency: int,
    request_count: int,
    repeat: int,
) -> tuple[list[RequestResult], GroupMeasurement]:
    semaphore = asyncio.Semaphore(concurrency)

    async def guarded_request() -> RequestResult:
        async with semaphore:
            return await run_request(
                client=client,
                url=url,
                api_key=api_key,
                model=model,
                prompt=prompt,
                max_tokens=max_tokens,
                concurrency=concurrency,
                repeat=repeat,
            )

    started_at = time.perf_counter()
    results = await asyncio.gather(
        *(guarded_request() for _ in range(request_count)),
    )
    wall_seconds = time.perf_counter() - started_at
    total_output_tokens = sum(
        item.output_tokens
        for item in results
        if item.success
    )
    aggregate_output_speed = (
        total_output_tokens / wall_seconds
        if wall_seconds > 0
        else 0.0
    )

    measurement = GroupMeasurement(
        model=model,
        concurrency=concurrency,
        repeat=repeat,
        wall_seconds=round(wall_seconds, 6),
        total_output_tokens=total_output_tokens,
        aggregate_output_tokens_per_second=round(
            aggregate_output_speed,
            6,
        ),
    )

    return results, measurement


def markdown_value(value: Any) -> str:
    if value is None:
        return "-"

    return str(value)


def render_markdown(
    *,
    metadata: dict[str, Any],
    summary: list[dict[str, Any]],
    rollup: list[dict[str, Any]],
) -> str:
    lines = [
        "# Inference Benchmark",
        "",
        f"- Timestamp: `{metadata['timestamp_utc']}`",
        f"- Endpoint: `{metadata['endpoint']}`",
        f"- Hardware: `{metadata['hardware']}`",
        f"- Max output tokens: `{metadata['max_tokens']}`",
        f"- Requests per level: `{metadata['requests_per_level']}`",
        f"- Repeats: `{metadata['repeats']}`",
        f"- Shuffle seed: `{metadata['shuffle_seed']}`",
        "",
        "## Cross-run rollup",
        "",
        "The latency and TTFT values below are medians of each run's percentile. Aggregate tok/s is total successful output tokens divided by group wall time.",
        "",
        "| Model | Concurrency | Success | Latency p50 median (s) | Latency p95 median (s) | TTFT p50 median (s) | TTFT p95 median (s) | Per-request tok/s median | Aggregate tok/s median |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in rollup:
        success = f"{row['successes']}/{row['requests']}"
        lines.append(
            "| "
            + " | ".join(
                [
                    row["model"],
                    str(row["concurrency"]),
                    success,
                    markdown_value(
                        row["latency_p50_seconds_median"]
                    ),
                    markdown_value(
                        row["latency_p95_seconds_median"]
                    ),
                    markdown_value(
                        row["ttft_p50_seconds_median"]
                    ),
                    markdown_value(
                        row["ttft_p95_seconds_median"]
                    ),
                    markdown_value(
                        row[
                            "median_output_tokens_per_second_median"
                        ]
                    ),
                    markdown_value(
                        row[
                            "aggregate_output_tokens_per_second_median"
                        ]
                    ),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Per-run results",
            "",
            "| Model | Concurrency | Run | Success | Latency p50 (s) | Latency p95 (s) | TTFT p50 (s) | TTFT p95 (s) | Per-request tok/s | Aggregate tok/s |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )

    for row in summary:
        success = f"{row['successes']}/{row['requests']}"
        lines.append(
            "| "
            + " | ".join(
                [
                    row["model"],
                    str(row["concurrency"]),
                    str(row["repeat"]),
                    success,
                    markdown_value(row["latency_p50_seconds"]),
                    markdown_value(row["latency_p95_seconds"]),
                    markdown_value(row["ttft_p50_seconds"]),
                    markdown_value(row["ttft_p95_seconds"]),
                    markdown_value(
                        row["median_output_tokens_per_second"],
                    ),
                    markdown_value(
                        row[
                            "aggregate_output_tokens_per_second"
                        ],
                    ),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "> Raw request-level results, group wall times, execution order, and experimental metadata are stored in the sibling JSON file. Failed requests are included in the success rate and excluded from latency percentiles.",
            "",
        ]
    )

    return "\n".join(lines)


async def main_async(args: argparse.Namespace) -> int:
    load_dotenv(args.env_file, override=False)

    api_key = os.getenv(args.api_key_env, "").strip()

    if not api_key:
        raise SystemExit(
            f"Missing API key environment variable: {args.api_key_env}",
        )

    endpoint = args.base_url.rstrip("/") + "/chat/completions"
    models = [
        model.strip()
        for model in args.models.split(",")
        if model.strip()
    ]
    concurrency_levels = [
        int(value.strip())
        for value in args.concurrency.split(",")
        if value.strip()
    ]

    if not models:
        raise SystemExit("At least one model is required.")

    if not concurrency_levels or min(concurrency_levels) < 1:
        raise SystemExit("Concurrency values must be positive integers.")

    timeout = httpx.Timeout(
        connect=args.connect_timeout,
        read=args.request_timeout,
        write=30.0,
        pool=args.request_timeout,
    )
    results: list[RequestResult] = []
    group_measurements: list[GroupMeasurement] = []
    execution_order: list[dict[str, Any]] = []
    randomizer = random.Random(args.shuffle_seed)

    async with httpx.AsyncClient(
        timeout=timeout,
        trust_env=False,
    ) as client:
        for model in models:
            for repeat in range(1, args.repeats + 1):
                current_order = list(concurrency_levels)

                if args.shuffle_seed is not None:
                    randomizer.shuffle(current_order)

                execution_order.append(
                    {
                        "model": model,
                        "repeat": repeat,
                        "concurrency_levels": current_order,
                    }
                )

                for concurrency in current_order:
                    for _ in range(args.warmup_requests):
                        await run_request(
                            client=client,
                            url=endpoint,
                            api_key=api_key,
                            model=model,
                            prompt=args.prompt,
                            max_tokens=args.max_tokens,
                            concurrency=concurrency,
                            repeat=repeat,
                        )

                    group, measurement = await run_group(
                        client=client,
                        url=endpoint,
                        api_key=api_key,
                        model=model,
                        prompt=args.prompt,
                        max_tokens=args.max_tokens,
                        concurrency=concurrency,
                        request_count=args.requests_per_level,
                        repeat=repeat,
                    )
                    results.extend(group)
                    group_measurements.append(measurement)

                    successes = sum(item.success for item in group)
                    print(
                        f"{model} run={repeat}/{args.repeats} "
                        f"concurrency={concurrency}: "
                        f"{successes}/{len(group)} succeeded, "
                        "aggregate="
                        f"{measurement.aggregate_output_tokens_per_second:.3f} "
                        "tok/s",
                        flush=True,
                    )

    timestamp = datetime.now(timezone.utc)
    timestamp_slug = timestamp.strftime("%Y%m%dT%H%M%SZ")
    output_directory = args.output_dir / timestamp_slug
    output_directory.mkdir(parents=True, exist_ok=False)

    summary = build_summary(results, group_measurements)
    rollup = build_rollup(summary)
    metadata = {
        "timestamp_utc": timestamp.isoformat(),
        "endpoint": endpoint,
        "models": models,
        "concurrency_levels": concurrency_levels,
        "requests_per_level": args.requests_per_level,
        "warmup_requests": args.warmup_requests,
        "warmup_scope": "before_each_concurrency_group",
        "max_tokens": args.max_tokens,
        "repeats": args.repeats,
        "shuffle_seed": args.shuffle_seed,
        "execution_order": execution_order,
        "hardware": args.hardware,
        "prompt": args.prompt,
        "metric_definitions": {
            "ttft": (
                "request start to first non-empty content delta"
            ),
            "latency": "request start to stream completion",
            "per_request_output_tokens_per_second": (
                "(output tokens - 1) / time after first token"
            ),
            "aggregate_output_tokens_per_second": (
                "successful output tokens / concurrency group wall time"
            ),
        },
    }
    report = {
        "metadata": metadata,
        "rollup": rollup,
        "summary": summary,
        "group_measurements": [
            asdict(item)
            for item in group_measurements
        ],
        "results": [asdict(result) for result in results],
    }

    json_path = output_directory / "results.json"
    markdown_path = output_directory / "summary.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_markdown(
            metadata=metadata,
            summary=summary,
            rollup=rollup,
        ),
        encoding="utf-8",
    )

    print(f"JSON: {json_path}")
    print(f"Markdown: {markdown_path}")

    return 0 if all(item.success for item in results) else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark OpenAI-compatible streaming model endpoints "
            "without storing generated response text."
        ),
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:4000/v1",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
    )
    parser.add_argument(
        "--api-key-env",
        default="LITELLM_API_KEY",
    )
    parser.add_argument(
        "--models",
        default="qwen2.5-7b-local",
        help="Comma-separated gateway model IDs.",
    )
    parser.add_argument(
        "--concurrency",
        default="1,2,4",
        help="Comma-separated concurrency levels.",
    )
    parser.add_argument(
        "--requests-per-level",
        type=int,
        default=6,
    )
    parser.add_argument(
        "--warmup-requests",
        type=int,
        default=1,
        help="Warmup requests before every concurrency group.",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=1,
        help="Number of complete repeated benchmark runs.",
    )
    parser.add_argument(
        "--shuffle-seed",
        type=int,
        default=None,
        help=(
            "Shuffle concurrency order reproducibly for each run "
            "to reduce order bias."
        ),
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=64,
    )
    parser.add_argument(
        "--prompt",
        default=(
            "In three concise points, explain the role of a unified "
            "LLM gateway in application development."
        ),
    )
    parser.add_argument(
        "--hardware",
        default="NVIDIA RTX 3090 24GB (local model path)",
    )
    parser.add_argument(
        "--connect-timeout",
        type=float,
        default=15.0,
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=180.0,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "artifacts" / "benchmarks",
    )

    args = parser.parse_args()

    if args.requests_per_level < 1:
        parser.error("--requests-per-level must be positive.")

    if args.warmup_requests < 0:
        parser.error("--warmup-requests cannot be negative.")

    if args.repeats < 1:
        parser.error("--repeats must be positive.")

    if args.max_tokens < 2:
        parser.error("--max-tokens must be at least 2.")

    return args


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main_async(parse_args())))
