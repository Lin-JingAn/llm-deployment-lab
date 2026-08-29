import unittest

from scripts.benchmark_inference import (
    GroupMeasurement,
    RequestResult,
    build_rollup,
    build_summary,
    parse_sse_json,
    percentile,
)


class BenchmarkInferenceTest(unittest.TestCase):
    def test_percentile_interpolates_values(self):
        self.assertEqual(percentile([1.0, 2.0, 3.0], 0.5), 2.0)
        self.assertEqual(percentile([1.0, 3.0], 0.5), 2.0)

    def test_sse_parser_ignores_done_marker(self):
        self.assertIsNone(parse_sse_json("data: [DONE]"))
        self.assertEqual(
            parse_sse_json('data: {"usage": {"total_tokens": 3}}'),
            {"usage": {"total_tokens": 3}},
        )

    def test_summary_excludes_failures_from_latency(self):
        results = [
            RequestResult(
                model="local",
                concurrency=1,
                repeat=1,
                success=True,
                total_latency_seconds=2.0,
                ttft_seconds=0.5,
                input_tokens=10,
                output_tokens=20,
                output_tokens_per_second=12.0,
            ),
            RequestResult(
                model="local",
                concurrency=1,
                repeat=1,
                success=False,
                total_latency_seconds=30.0,
                ttft_seconds=None,
                input_tokens=0,
                output_tokens=0,
                output_tokens_per_second=None,
                error_type="TimeoutError",
                error_message="timed out",
            ),
        ]

        summary = build_summary(results)[0]

        self.assertEqual(summary["success_rate"], 0.5)
        self.assertEqual(summary["latency_p50_seconds"], 2.0)
        self.assertEqual(summary["mean_output_tokens_per_second"], 12.0)
        self.assertEqual(summary["median_output_tokens_per_second"], 12.0)

    def test_summary_includes_group_aggregate_throughput(self):
        results = [
            RequestResult(
                model="local",
                concurrency=2,
                repeat=1,
                success=True,
                total_latency_seconds=2.0,
                ttft_seconds=0.5,
                input_tokens=10,
                output_tokens=20,
                output_tokens_per_second=12.0,
            )
        ]
        measurements = [
            GroupMeasurement(
                model="local",
                concurrency=2,
                repeat=1,
                wall_seconds=2.0,
                total_output_tokens=20,
                aggregate_output_tokens_per_second=10.0,
            )
        ]

        summary = build_summary(results, measurements)[0]

        self.assertEqual(
            summary["aggregate_output_tokens_per_second"],
            10.0,
        )

    def test_rollup_uses_median_across_repeats(self):
        rows = [
            {
                "model": "local",
                "concurrency": 8,
                "repeat": 1,
                "requests": 10,
                "successes": 10,
                "latency_p50_seconds": 2.0,
                "latency_p95_seconds": 3.0,
                "ttft_p50_seconds": 0.5,
                "ttft_p95_seconds": 1.0,
                "mean_output_tokens_per_second": 30.0,
                "median_output_tokens_per_second": 30.0,
                "aggregate_output_tokens_per_second": 100.0,
            },
            {
                "model": "local",
                "concurrency": 8,
                "repeat": 2,
                "requests": 10,
                "successes": 9,
                "latency_p50_seconds": 4.0,
                "latency_p95_seconds": 5.0,
                "ttft_p50_seconds": 1.5,
                "ttft_p95_seconds": 2.0,
                "mean_output_tokens_per_second": 20.0,
                "median_output_tokens_per_second": 20.0,
                "aggregate_output_tokens_per_second": 80.0,
            },
        ]

        rollup = build_rollup(rows)[0]

        self.assertEqual(rollup["success_rate"], 0.95)
        self.assertEqual(
            rollup["latency_p50_seconds_median"],
            3.0,
        )
        self.assertEqual(
            rollup["latency_p50_seconds_range"],
            [2.0, 4.0],
        )


if __name__ == "__main__":
    unittest.main()
