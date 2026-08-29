# StarSail AI 简历与面试材料

## 项目名称

StarSail AI——统一大模型推理与应用平台

## 技术栈

Python、FastAPI、LiteLLM、vLLM、Linux/CUDA、Docker Compose、PostgreSQL

## 项目概述

针对云端模型接口各异、本地模型难以直接接入业务的问题，搭建统一的大模型调用与应用平台。系统同时接入 Qwen、DeepSeek 等云端模型及部署在 Linux GPU 服务器上的 Qwen2.5-7B，实现 Web、业务后端、模型网关和推理服务的完整链路。

## 核心方案

- 使用 LiteLLM 统一云端 API 与本地 vLLM 的模型标识、请求参数和响应结构，FastAPI 业务层只依赖平台内部模型协议，不直接耦合供应商接口。
- 在 Linux + RTX 3090 环境使用 vLLM 部署 Qwen2.5-7B-Instruct，将模型封装为 OpenAI-compatible API，并通过 Tailscale 私有网络接入 LiteLLM 网关。
- 设计 Model Registry 管理模型 ID、Provider、能力开关和输出限制；使用受限 Virtual Key 控制业务端可访问模型，避免在正常调用中暴露 LiteLLM 管理密钥。
- 使用 PostgreSQL、SQLAlchemy 和 Alembic 保存用户、会话、消息和模型调用记录，记录实际模型、Token 用量、TTFT、总延迟、状态及错误类型。
- 使用 Docker Compose 管理 LiteLLM 与 PostgreSQL，处理云端代理和本地模型私网流量分路，并提供一键启动、健康检查和敏感信息扫描脚本。

## 已验证结果

- 云端模型与 Qwen2.5-7B 本地模型可以通过同一 FastAPI 接口完成流式和非流式调用。
- Qwen2.5-7B-Instruct 已在 RTX 3090 上通过 vLLM 稳定提供 OpenAI-compatible API。
- 用户刷新页面后可以恢复多轮会话；不同用户的会话、消息和模型调用记录相互隔离。
- 调用记录可以追溯 Provider、请求模型、实际模型、输入/输出 Token、TTFT、总延迟、完成状态和失败原因。

## 已验证性能

- 在 RTX 3090、Qwen2.5-7B-Instruct、vLLM 0.6.1.post1、FP16 环境下完成两轮流式推理 Benchmark。
- 测试覆盖并发 1、8、12、16，每档每轮 16 个请求，固定输出 64 Token，共 128/128 个请求成功。
- 并发 1 提升至 16 时，系统聚合吞吐量中位数由 29.466 提升至 277.060 output tok/s，约为 9.4 倍；Latency p50 中位数由 1.995 秒增加至 3.098 秒。
- 单请求生成速度使用组内中位数，系统吞吐量使用总输出 Token 除以并发组墙钟时间；不使用受 SSE 分块异常值影响的算术平均数。
- 并发 8 的尾延迟存在跨轮波动，因此不将本次测试描述为容量上限或最佳并发结论。

完整实验条件、指标定义和复现命令见 `docs/benchmarks/qwen2.5-7b-rtx3090-20260829.md`。

## 简历精简版

**StarSail AI——基于 LiteLLM 与 vLLM 的多模型推理应用平台**

**技术栈：** Python、FastAPI、LiteLLM、vLLM、Linux/CUDA、Docker Compose、PostgreSQL

**项目概述：** 面向大模型统一调用与本地推理落地，独立搭建覆盖 Web 应用、业务后端、模型网关和 GPU 推理服务的完整平台，统一接入 Qwen、DeepSeek 等云端模型及本地 Qwen2.5-7B。

**统一推理与应用链路：** 使用 LiteLLM 屏蔽不同模型的标识、参数和响应差异，通过 Model Registry 与受限 Virtual Key 管理模型能力和访问权限；基于 FastAPI、JWT 与 PostgreSQL 实现流式对话、用户级会话隔离、历史恢复及 Token、TTFT、总延迟和错误信息追踪。

**本地部署与性能验证：** 在 Linux + RTX 3090 上使用 vLLM 以 FP16 部署 Qwen2.5-7B-Instruct，并接入统一网关；完成并发 1/8/12/16、固定 64 Token 的两轮测试，共 128/128 个请求成功，系统聚合吞吐量中位数由 29.5 提升至 277.1 output tok/s，Latency p50 由 2.00 秒增加至 3.10 秒。

## 面试深挖

### LiteLLM 和 vLLM 分别解决什么问题？

LiteLLM 是模型网关，负责把不同 Provider 的接口抽象成统一协议；vLLM 是本地推理服务，负责在 GPU 上加载模型、管理 KV Cache、调度请求并暴露 OpenAI-compatible API。二者位于不同层，不能互相替代。

### 为什么不让 FastAPI 直接调用每家供应商？

如果业务层分别适配每个 Provider，认证方式、模型名称、参数、错误格式和 Token 字段会进入业务代码。通过网关统一后，FastAPI 只处理用户、会话、权限、模型选择和调用记录，供应商变化不会扩散到业务接口。

### 本地模型为什么还需要 vLLM？

模型权重本身不是可调用服务。vLLM 负责把权重加载到 GPU，管理显存和 KV Cache，执行推理调度并提供 HTTP 接口，业务系统才能像调用云端 API 一样调用本地模型。

### 为什么使用 Tailscale？

Windows 应用主机和 Linux GPU 服务器不在可直接路由的同一网络。Tailscale 提供私有跨主机连接，避免把 vLLM 服务直接暴露到公网；服务器地址由环境变量注入，不写入公开仓库。

### 项目当前没有实现什么？

当前实现的是统一接入、手动模型选择、权限控制和调用观测，不应描述为自动负载均衡、健康感知路由或故障自动切换。SGLang 只做过兼容性评估，没有进入稳定链路。
