# 推理服务基准测试

本项目使用 `scripts/benchmark_inference.py` 对 LiteLLM 统一网关后的流式模型接口进行可复现测试。测试对象是 `LiteLLM → vLLM` 推理链路，不把浏览器渲染和 FastAPI 业务处理时间混入推理指标。

## 指标

- `TTFT p50/p95`：请求发出到首个有效内容 Token 返回的时间。
- `Latency p50/p95`：完整响应耗时。
- `Per-request output tok/s median`：单个请求首 Token 返回后的估算生成速度，组内取中位数；该指标仍可能受 SSE 分块方式影响，不单独用于判断系统吞吐能力。
- `Aggregate output tok/s`：同一并发组成功生成的总 Token 数除以该组墙钟时间，用于衡量系统总体吞吐量。
- `Success rate`：同一并发级别下成功请求所占比例。
- `Concurrency`：同时执行的请求数。

失败请求计入成功率，但不会进入延迟百分位数。脚本不保存模型回复正文，只保存指标和截断后的错误信息。

## 本地模型测试

先确认 LiteLLM 和 Linux GPU 服务器上的 vLLM 均已启动，再从仓库根目录运行：

```powershell
$python = ".\apps\api\.venv\Scripts\python.exe"

& $python .\scripts\benchmark_inference.py `
  --models qwen2.5-7b-local `
  --concurrency 1,2,4 `
  --requests-per-level 6 `
  --max-tokens 64
```

正式本地模型测试使用固定英文 Prompt，避免 Windows 终端传递中文参数时产生编码歧义；每个并发组单独预热，并通过固定随机种子打乱并发档位执行顺序：

```powershell
$python = ".\apps\api\.venv\Scripts\python.exe"

& $python .\scripts\benchmark_inference.py `
  --models qwen2.5-7b-local `
  --concurrency 1,8,10,12,16 `
  --requests-per-level 30 `
  --repeats 3 `
  --warmup-requests 1 `
  --max-tokens 64 `
  --shuffle-seed 20260829 `
  --hardware "RTX 3090 24GB | vLLM 0.6.1.post1 | Qwen2.5-7B-Instruct | FP16"
```

结果写入：

```text
artifacts/benchmarks/<UTC时间>/results.json
artifacts/benchmarks/<UTC时间>/summary.md
```

## 云端模型对照

云端测试会产生真实 API 费用。确认费用预算后再显式指定模型：

```powershell
& $python .\scripts\benchmark_inference.py `
  --models qwen-plus,deepseek-v4-flash `
  --concurrency 1,2,4 `
  --requests-per-level 6 `
  --max-tokens 64 `
  --hardware "Cloud API through LiteLLM"
```

## 实验纪律

- 对照实验必须使用相同 Prompt、最大输出 Token、并发级别和请求数量。
- 每次报告模型 ID、硬件、日期、网关路径和完整命令。
- 本地模型测试前记录 GPU 型号、显存、vLLM 参数和模型版本。
- 正式结论至少重复三轮；报告跨轮中位数和区间，不用单轮偶然值判断容量拐点。
- 每个并发组单独预热，并打乱执行顺序，降低冷启动和固定顺序带来的偏差。
- 不用一次请求的耗时代表系统性能，不把云端与本地不同输出长度的结果直接比较。
- `max_tokens` 是输出上限；报告前必须核对各请求的实际输出 Token 数是否一致。
- “成功率 100%”只表示本次样本全部成功，不等价于系统容量上限或长期稳定性承诺。
- 简历只使用已保存原始结果、可复现命令和明确实验条件的数字。
