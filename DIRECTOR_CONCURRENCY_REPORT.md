# Nemotron Lightning Director 并发实测

日期：2026-09-24，DGX Spark（NVIDIA GB10、CUDA 13.0、driver 580.159.03）。

## 结论

目标模型 `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4` 已下载并在本机
vLLM 0.27.1-aarch64 上启动。`GET http://127.0.0.1:8001/v1/models` 返回同一模型 ID。
中文 Director JSON 冒烟成功。直接请求 vLLM 的三轮测试中，1、2、4 路分别
成功 3/3、6/6、12/12（`max_tokens=1024`）；4 路没有观察到 OOM 或请求超时。
8 路单轮也成功 8/8；这证明本次短请求负载可跑到 8 路，尚不能证明长时间运行或更长上下文的稳定上限。

## 下载与启动

- 模型目录：`/home/hajimi2025/.cache/interaction-nemotron`。索引列出的 52 个
  safetensors 分片全部存在；权重文件总计 21,561,882,284 字节，配置和 tokenizer 齐全。
- 先前 Python 环境没有 `vllm`，但本机已有 `vllm/vllm-openai:v0.27.1-aarch64`
  镜像。项目启动脚本使用此容器，无需主机 Python 安装 vLLM。
- 首次按旧默认值 `--gpu-memory-utilization 0.75` 启动失败：vLLM 报告设备启动时
  可用 86.31/121.69 GiB，申请目标为 91.27 GiB。未停止其他 GPU 进程；改为
  `0.65` 后成功。启动脚本默认值已同步为 `0.65`。
- 本次使用 `bash deploy/start_nemotron_lightning.sh`，服务绑定
  `127.0.0.1:8001`，`--max-model-len 8192`，Marlin MoE、FP8 KV cache、
  FlashInfer Mamba。vLLM 日志记录权重加载 161.60 秒、模型占用 17.86 GiB，
  KV cache 可用 57.03 GiB。首次启动还包括编译、预热和自动调优。

## 测试方法

探针 `tools/director_concurrency_probe.py` 直接调用本地 OpenAI 兼容端点。
每个请求带不同的中文 `raw_player_input` 和 Scenario Context，开启流式返回，
要求 JSON 中包含 `outcome` 和 `directive`。每档连续执行三轮，每轮同时发出
对应路数的请求；各档依次执行。TTFT 是首个非空内容片段的时间；P50/P95 是
单请求端到端耗时；tokens/s 是该档输出 token 总数除以三轮总耗时。
**该探针绕过业务后端，不测 `DIRECTOR_LOCAL_MAX_CONCURRENCY` admission control。**

冒烟：1 路 1/1 成功，耗时 3297.1 ms，TTFT 706.9 ms，输出 201 tokens。

正式命令：

```bash
DIRECTOR_PROBE_LEVELS=1,2,4 DIRECTOR_PROBE_WAVES=3 \
DIRECTOR_PROBE_MAX_TOKENS=1024 \
LOCAL_LLM_BASE_URL=http://127.0.0.1:8001/v1 \
python3 tools/director_concurrency_probe.py
```

| 并发 | 成功 | P50 | P95 | TTFT P50 | 输出 tokens/s | 请求/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 3/3 | 2597.9 ms | 2792.9 ms | 118.3 ms | 73.93 | 0.38 |
| 2 | 6/6 | 3676.1 ms | 4956.3 ms | 176.3 ms | 110.11 | 0.50 |
| 4 | 12/12 | 4357.9 ms | 7843.4 ms | 248.0 ms | 147.35 | 0.62 |
| 8 | 8/8（单轮） | 6244.2 ms | 7286.7 ms | 601.6 ms | 212.17 | 1.08 |

补充测试：`max_tokens=512` 首轮 4 路为 11/12，一条 HTTP 200 响应未形成完整
JSON；首轮探针未保存 finish_reason，不能确认是否由输出上限截断导致。同配置
复跑 4 路三轮为 12/12，P50 4844.7 ms、P95 6102.9 ms、TTFT P50 284.1 ms、
153.49 输出 tokens/s。首次 512-token 测试的 1 路与 2 路分别为 3/3、6/6。
本次 1024-token 探针未复现格式失败，但不能据此确认首轮失败的原因；业务侧
仍需按实际提示词验证输出上限并记录格式失败率。

测试后容器 `interaction-nemotron` 仍运行，vLLM 日志未见 OOM、异常或请求超时。
`nvidia-smi` 显示 vLLM 进程约 80,329 MiB；GB10 为统一内存架构，
`nvidia-smi` 的 FB 总量显示 N/A。测试后主机 `free -h` 显示约 15 GiB available；
本次没有连续采样，因此不报告内存峰值。

## 业务接入与后续边界

后端的 `DIRECTOR_LOCAL_MAX_CONCURRENCY=2` 仍是保守 admission 配置；本次直连
4/8 路测试不自动改变该值。后端队列超时为 10 秒、最大等待队列为 16，超时后
按 Provider Router 路由 Step 5。业务侧若要升到 4 路，还应在真实 Session
请求、较长 Context 和持续运行条件下单独验证，再调整 admission 上限。
