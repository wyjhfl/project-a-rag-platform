# A-v2.3 PaddleOCR 兼容性专项复盘

## 阶段 1：技术知识教学

A-v2.3 解决的问题是：PaddleOCR 能不能作为 Project A 当前默认多模态 OCR 能力承诺。

这个问题不在 RAG 主链，而在 OCR runtime：

```text
图片
-> PaddleOCRAdapter
-> paddleocr / paddlex / paddle runtime
-> OCR 文本
-> LocalVisionInterpreter / Vision LLM
-> 文档入库或故障字段提取
```

当前项目已经有两条多模态绿链：

- Vision LLM
- MinerU Linux sliced

PaddleOCR 的价值是补足本地 OCR 能力。如果它转绿，图片中文字提取可以少依赖外部视觉模型；如果它不稳定，默认演示路径继续使用 sidecar / Vision LLM 才是正确工程选择。

核心技术点：

- **runtime compatibility**：包能 import 不等于推理能运行。
- **inference backend**：PaddleOCR 3.x 当前会经过 PaddleX static runner。
- **blocked 分类**：需要区分缺包、共享库、样例损坏、模型选择和推理 runtime 不兼容。
- **formal boundary**：当多组低成本修复都失败时，应正式列为边界，而不是继续无限调参。

如果不用这种分层验收，会把问题误判成：

- 图片样例问题
- Python 包没装
- 参数没调对
- OCR 模型不适合

但 A-v1.5 和 A-v2.3 的真实证据说明，当前阻塞点稳定落在 Paddle / PaddleX runtime。

## 阶段 2：版本技术设计

### 本轮目标

- 刷新当前 Docker / WSL / PaddleOCR runtime 预检。
- 聚合 A-v1.5 最终探针和 A-v2.3 当前预检。
- 输出兼容性决策矩阵。
- 决定 PaddleOCR 是否继续作为默认演示候选。

### 本轮边界

不做：

- 不改 RAG 主链。
- 不改默认 demo 画像。
- 不把 PaddleOCR 强行接入默认路径。
- 不继续在当前 WSL profile 上盲目调参数。

只做：

- runtime 证据刷新。
- 兼容性矩阵汇总。
- formal boundary 决策。
- 文档和 bad case 记录。

### 涉及文件

- `backend/scripts/preflight_multimodal_linux_runtime.py`
- `backend/scripts/run_av23_paddleocr_compatibility.py`
- `backend/tests/test_av23_paddleocr_compatibility.py`
- `docs/A-v2.3_paddleocr_runtime_preflight_2026-05-23.json`
- `docs/A-v2.3_paddleocr_compatibility_report_2026-05-23.json`
- `docs/A-v2.3-paddleocr-compatibility-review.md`
- `docs/A-v2.3_bad_cases.md`
- `README.md`
- `docs/dev_log.md`
- `docs/debug_log.md`

## 阶段 3：最小实现

新增 `run_av23_paddleocr_compatibility.py`，聚合：

- 当前 runtime preflight
- A-v1.5 PaddleOCR final probe

输出：

- Docker 是否可作为隔离 runtime 候选。
- WSL Python 和包是否就绪。
- WSL 真实 OCR 是否可运行。
- A-v1.5 多组低成本参数尝试是否仍失败。
- 是否确认 `runtime_incompatible`。

同时为 `preflight_multimodal_linux_runtime.py` 新增 `--version`，让 A-v2.3 证据文件的版本元信息清楚。

## 阶段 4：真实运行结果

当前 runtime preflight：

```text
docker_daemon_ready = true
wsl_repo_mounted = true
wsl_python_ready = true
wsl_packages_ready = true
wsl_ocr_runtime_ready = false
recommended_path = wsl_runtime_incompatible
```

兼容性矩阵：

```text
check_count = 8
passed = 2
blocked = 6
runtime_incompatible_confirmed = true
```

通过项：

- Docker daemon ready
- WSL Python / packages ready

阻塞项：

- WSL PaddleOCR real runtime
- `FLAGS_enable_pir_api=0`
- `FLAGS_use_mkldnn=0`
- 同时关闭 PIR / MKLDNN
- PP-OCRv5 mobile profile
- PP-OCRv4 mobile profile

统一错误：

```text
NotImplementedError: ConvertPirAttribute2RuntimeAttribute
```

决策：

```text
status = formal_boundary
recommendation = Keep PaddleOCR out of the default demo path and document it as a runtime compatibility boundary.
```

## 验证

```text
python backend/scripts/preflight_multimodal_linux_runtime.py --version A-v2.3 --output docs/A-v2.3_paddleocr_runtime_preflight_2026-05-23.json

python backend/scripts/run_av23_paddleocr_compatibility.py --current-preflight docs/A-v2.3_paddleocr_runtime_preflight_2026-05-23.json --output docs/A-v2.3_paddleocr_compatibility_report_2026-05-23.json
```

已运行：

```text
python -m pytest backend/tests/test_av15_linux_runtime_preflight.py backend/tests/test_av23_paddleocr_compatibility.py -q
6 passed

python -m compileall backend\scripts\preflight_multimodal_linux_runtime.py backend\scripts\run_av23_paddleocr_compatibility.py
passed
```

## 当前代码链路如何运行

```text
preflight_multimodal_linux_runtime
-> docker / wsl / package / ocr probe
-> A-v2.3 runtime preflight JSON
-> run_av23_paddleocr_compatibility
-> compatibility matrix
-> formal boundary decision
```

## 面试讲法

> PaddleOCR 这条线我没有简单说“没跑通”，而是拆了环境层、包层、共享库层、真实推理层和参数尝试层。当前 Docker daemon 已可用，WSL 的 Python 和 OCR 包也都安装了，但真实推理仍稳定失败在 PaddleX static runner 的 `ConvertPirAttribute2RuntimeAttribute`。所以我把它正式定性为 runtime compatibility boundary，不放进默认 demo 路径；如果后续继续攻，应该单独开 Docker/Linux clean runtime matrix，而不是继续污染主线。

## 下一步衔接

推荐：

1. 默认 demo 继续使用 Vision LLM + MinerU Linux sliced。
2. PaddleOCR 从“待修”升级为“正式 runtime 边界”。
3. 后续如继续攻克，单独开 Docker clean runtime spike。
4. 下一轮可进入 A-v2.4 Provider 对比报告或演示素材补强。
