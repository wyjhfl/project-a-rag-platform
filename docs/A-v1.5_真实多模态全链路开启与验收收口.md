# A-v1.5 真实多模态全链路开启与验收收口

## 1. 本轮目标

A-v1.5 的目标不是继续增加文本能力，而是把真实多模态链路从“代码入口存在”推进到“真实可验收、能定位阻塞层级”。

本轮按四段推进：

- Vision LLM
- PaddleOCR
- MinerU
- 端到端 ingest

## 2. 本轮最小实现

### 2.1 API 与版本口径

- `backend/app/main.py`
  - 版本号更新为 `v1.5`
  - 上传接口放开图片格式：
    - `.png`
    - `.jpg`
    - `.jpeg`
    - `.webp`

### 2.2 真实多模态预检

新增：

- `backend/scripts/preflight_multimodal_real.py`

它会在 `MULTIMODAL_BACKEND=real` 条件下，分别探测：

- `vision_llm_real_runtime`
- `paddleocr_real_runtime`
- `mineru_real_pdf_parsing`
- `multimodal_image_parse`
- `multimodal_pdf_parse`
- `multimodal_end_to_end_ingest`

并强制把结构化存储 / 向量库切回：

- `sqlite`
- `chroma`

避免被 PostgreSQL、Redis、Neo4j 等旁路依赖干扰。

### 2.3 统一验收报告

新增：

- `backend/scripts/run_av15_multimodal_acceptance.py`

它会基于预检结果输出统一报告，并把阻塞类型进一步区分为：

- `auth_invalid`
- `config_missing`
- `sample_invalid`
- `runtime_incompatible`
- `timeout`
- `service_unhealthy`
- `blocked`

### 2.4 测试补强

新增：

- `backend/tests/test_av15_multimodal_acceptance.py`

覆盖：

- 多模态组件阻塞分类
- preflight -> acceptance 组件映射
- summary 聚合

## 3. 2026-05-19 第一轮真实结果

生成产物：

- `docs/A-v1.5_multimodal_preflight_2026-05-19.json`
- `docs/A-v1.5_multimodal_acceptance_report_2026-05-19.json`

当前结果不是“已经全绿”，而是已经把“全部打开”拆成了可定位状态：

```text
component_count = 6
status_counts:
- auth_invalid = 1
- timeout = 1
- sample_invalid = 1
- blocked = 3
```

当前逐项判断：

- Vision LLM
  - `401 Unauthorized`
  - 当前是认证阻塞
- PaddleOCR
  - 已进入真实推理路径
  - 这次失败暴露的是样例图片本身 `libpng CRC error`
- MinerU
  - 当前 probe 超时
  - 属于服务/运行时阻塞
- image/pdf parse 与 end-to-end ingest
  - 因前置组件未 ready，被主动跳过

## 4. 当前最重要的结论

A-v1.5 第一轮的价值不在于“全都打通”，而在于已经完成下面这件更关键的事：

> 把真实多模态从“模糊地说不通”变成“明确知道是哪一层不通”。

这让下一步可以按优先级推进，而不是盲目同时修所有问题。

## 5. 下一步建议

当前建议顺序：

1. 先修 Vision LLM 认证
2. 换一份真实有效的 PNG/JPG 样例，排除测试素材损坏
3. 单独继续打 MinerU health / parse 超时
4. 在至少 1 条图片链路 ready 后，再打开端到端 ingest 验收

## 6. 2026-05-19 第二轮更新

在校准 Vision 配置口径后，A-v1.5 已经从“Vision 认证失败”推进到“Vision 真实可用”。

本轮处理：

- 显式补入：
  - `VISION_LLM_MODEL=mimo-v2-omni`
  - `VISION_LLM_API_KEY=<same mimo key>`
  - `VISION_LLM_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1`
- 修正 `preflight_multimodal_real.py`
  - 让 `.env` 覆盖当前进程旧环境变量
- 直接调用 `/models` 与图片请求后确认：
  - endpoint 支持的真实模型 id 是 `mimo-v2-omni`
  - 之前的 `MiMo-V2-Omni` 只是展示名，不是 API model id

更新后的真实结果：

- Vision LLM：`passed`
- PaddleOCR：`runtime_incompatible`
  - `NotImplementedError: ConvertPirAttribute2RuntimeAttribute`
- MinerU：`blocked`
  - `mineru` CLI 返回非零退出
- 端到端 ingest：仍因前置 OCR / PDF parser 未 ready 被跳过

当前最新报告：

- `docs/A-v1.5_multimodal_preflight_2026-05-19.json`
- `docs/A-v1.5_multimodal_acceptance_report_2026-05-19.json`

当前最重要的新结论：

- A-v1.5 已经拥有至少 1 条真实图片多模态能力：
  - `Vision LLM` 真实运行成功
- 下一优先级不再是 Vision，而是：
  - 先攻 `PaddleOCR` 运行时兼容
  - 再攻 `MinerU` CLI / 服务失败

## 7. 2026-05-19 运行时诊断收口

这一步没有继续横向加功能，而是把剩余阻塞从“知道没通”推进到“知道为什么没通”。

更新后，`docs/A-v1.5_multimodal_preflight_2026-05-19.json` 已新增 `diagnostics` 字段，直接记录当前 Python 运行时里多模态关键包的真实状态：

- `cv2=4.10.0`
- `numpy=2.3.5`
- `paddle=3.3.1`
- `paddleocr=OSError: [WinError 127] ... torch\\lib\\shm.dll`
- `paddlex=RuntimeError: PDX has already been initialized`

这让 PaddleOCR 的判断进一步收紧为：

- 不是样例图片损坏
- 不是单纯缺少 `paddleocr` 包
- 而是当前 Windows / Python / Paddle(PaddleX) 运行时存在真实兼容问题
- 在真实验收口径下，当前最合理的工程结论是：优先切 `WSL / Linux / Docker` 路径继续打通 PaddleOCR

MinerU 的判断也从“泛化 blocked”推进为更具体的服务结论：

- `mineru` CLI 可以启动本地 `mineru-api`
- 真实任务提交后失败点落在 `502 Bad Gateway`
- 因此当前更接近“服务不健康/任务状态查询失败”，不是“命令不存在”

最新验收报告 `docs/A-v1.5_multimodal_acceptance_report_2026-05-19.json` 的状态计数已经更新为：

```text
passed = 1
runtime_incompatible = 1
service_unhealthy = 1
blocked_dependency = 3
```

这份结果意味着当前 A-v1.5 的主结论已经很明确：

- `Vision LLM` 已转绿，可作为真实图片理解链路
- `PaddleOCR` 的下一步不是继续调 prompt，而是换更稳定的运行环境
- `MinerU` 的下一步不是继续猜 CLI 参数，而是围绕本地 API 502 做服务级排查

## 8. 2026-05-19 Linux 路径预检

为了避免继续在 Windows 本机上盲调 Paddle/PaddleOCR，这一轮新增了：

- `backend/scripts/preflight_multimodal_linux_runtime.py`
- `docs/A-v1.5_multimodal_linux_runtime_2026-05-19.json`

这份预检不直接宣称“Linux 已跑通 OCR”，而是先验证切环境前提是否成立。

当前实测结果：

```text
docker_daemon_ready = false
wsl_repo_mounted = true
wsl_python_ready = true
wsl_packages_ready = true
wsl_ocr_runtime_ready = false
recommended_path = wsl_shared_lib_fix
```

拆解解释：

- Docker client 在，但当前 daemon 没起来，因此这轮不适合把 Docker 当成首选验证路径
- `WSL Ubuntu-24.04` 已可进入，仓库也能挂载到 Linux 文件系统
- WSL 内已有 `python3`
- 这轮已经完成用户态 `pip` bootstrap，并安装了：
  - `numpy`
  - `paddlepaddle`
  - `paddleocr`
  - `paddlex`
  - `opencv-contrib-python`
- 但真实 OCR 仍未转绿，因为 Linux 侧进一步暴露出共享库缺失：
  - `ImportError: libgomp.so.1: cannot open shared object file`

因此 A-v1.5 当前最稳的推进顺序已经进一步明确为：

1. 在 WSL 内补 `libgomp1`
2. 重新跑 `backend/scripts/wsl_paddleocr_probe.py`
3. OCR 转绿后再继续 image parse / end-to-end ingest

当前 Linux 侧的真实证据已经从“只是建议切 WSL”升级成了：

```text
WSL 已具备 Python + 包安装条件
真实 OCR 首个明确阻塞是 libgomp.so.1 缺失
```
## 9. 2026-05-19 WSL OCR 运行时最终收口

在 Linux 路径继续推进后，A-v1.5 对 PaddleOCR 的判断已经从“缺少共享库”进一步收口成“当前 Paddle 运行时不兼容”。

最新预检报告：
- `docs/A-v1.5_multimodal_linux_runtime_2026-05-19.json`

最新关键结果：
```text
docker_daemon_ready = false
wsl_repo_mounted = true
wsl_python_ready = true
wsl_packages_ready = true
wsl_ocr_runtime_ready = false
recommended_path = wsl_runtime_incompatible
```

本轮真实推进：
- 已完成 WSL 用户态 `pip` bootstrap
- 已安装 `numpy / paddlepaddle / paddleocr / paddlex / opencv-contrib-python`
- 已通过用户态 `libgomp` 提取和 `LD_LIBRARY_PATH` 注入绕过 `libgomp.so.1` 缺失
- 真实 `wsl_paddleocr_probe.py` 继续运行后，新的首个稳定失败点变为：
  - `NotImplementedError: ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]`

这意味着当前 Linux 路径已经不再是：
- Python 不可用
- pip 不可用
- OCR 包未安装
- 缺少 `libgomp.so.1`

而是：
- 当前 `paddle==3.3.1 / paddleocr==3.5.0 / paddlex==3.5.2` 这组真实运行时仍无法稳定执行 OCR 推理

因此 A-v1.5 现在最准确的多模态结论是：
- `Vision LLM`: 已转绿
- `PaddleOCR`: Windows 与当前 WSL 路径都可复现 `runtime_incompatible`
- `MinerU`: 仍为 `service_unhealthy`

下一步不再建议继续在当前 Windows/WSL 组合里微调 OCR 参数，优先顺序应改为：
1. 记录 PaddleOCR 当前运行时不兼容边界
2. 转去验证更稳的 Paddle 容器镜像或其他 Linux 运行时组合
3. 并行继续追 `MinerU` 的本地 API `502`

## 10. 2026-05-19 MinerU 服务级根因收口

为了避免继续把 MinerU 笼统记成 `service_unhealthy`，本轮新增：
- `backend/scripts/preflight_mineru_service.py`
- `docs/A-v1.5_mineru_service_preflight_2026-05-19.json`

这份预检直接抓取真实 `mineru` CLI 全量日志，并把链路拆成：
- 本地 `mineru-api` 是否启动
- Uvicorn 是否 ready
- PDF 任务是否已提交
- VLM 模型加载是否已开始
- 最终是状态查询失败，还是模型加载本身失败

最新真实结论：
```text
local_api_started = true
uvicorn_ready = true
task_submitted = true
vlm_engine_initialized = true
model_fetch_started = true
task_status_query_failed = false
bad_gateway_502 = false
status = runtime_resource_blocked
```

这说明当前 MinerU 已经不是“CLI 没装”或“任务没发出去”，而是：
- 本地 API 正常启动
- PDF 任务正常提交
- 真正失败点落在模型加载阶段
- 直接根因是：
  - `OSError: 页面文件太小，无法完成操作。 (os error 1455)`

因此 A-v1.5 当前对 MinerU 的最准确判断已经从：
- `service_unhealthy`

收口为：
- `runtime_resource_blocked`

同步后的多模态总报告：
- `docs/A-v1.5_multimodal_acceptance_report_2026-05-19.json`

最新总口径：
```text
passed = 1
runtime_incompatible = 1
runtime_resource_blocked = 1
blocked_dependency = 3
```

## 11. 2026-05-19 WSL MinerU 手工探针

为了绕开 Windows 上的 `os error 1455`，继续在 `WSL Ubuntu-24.04` 中对 MinerU 做了一轮真实手工探针。

证据文件：
- `docs/A-v1.5_mineru_linux_runtime_raw_2026-05-19.log`
- `docs/A-v1.5_mineru_linux_manual_probe_2026-05-19.json`

本轮推进结果：
- WSL 中已安装 `mineru==3.1.14`
- `mineru -b pipeline` 能启动本地 `mineru-api`
- Uvicorn ready
- PDF 任务已提交
- 已进入 `Pipeline processing-window` 与模型初始化阶段

但新的首个阻塞点变为：
- 需要从 HuggingFace 拉取 `opendatalab/PDF-Extract-Kit-1.0`
- 当前 WSL 网络路径失败：
  - `requests.exceptions.ConnectionError: HTTPSConnectionPool(host='huggingface.co', port=443)`
  - `OSError: [Errno 101] Network is unreachable`
  - `huggingface_hub.errors.LocalEntryNotFoundError`

这说明 WSL MinerU 的结论已经比 Windows 更进一步：
- Windows：`runtime_resource_blocked`
  - 页面文件太小，模型加载失败
- WSL：`network_blocked`
  - 已进入 pipeline 与模型下载阶段，但出站网络访问 HuggingFace 失败

因此 A-v1.5 当前对 MinerU 的完整判断是：
1. Windows 侧阻塞在本机资源
2. WSL 侧阻塞在模型下载网络
3. 代码链路本身已经能跑到真实 pipeline 阶段

下一步最值得做的是：
1. 修 WSL 到 HuggingFace 的网络
2. 或预先把 MinerU 所需模型下载到本地缓存
3. 再次运行同一份 PDF 样例验证能否正式转绿

## 12. 2026-05-19 WSL MinerU local minimal 转绿

为了不继续被 WSL 出网问题卡住，本轮补了一条新的 Linux 验收路径：

- 提前在 Windows 侧下载最小 MinerU pipeline 模型集到共享目录
- 在 WSL 中使用 `MINERU_MODEL_SOURCE=local`
- 显式关闭 `formula` 与 `table`
- 固定最小命令：`backend=pipeline`、`method=ocr`、`device=cpu`

新增与更新：

- `backend/scripts/preflight_mineru_linux_runtime.py`
  - 支持 `local model source`
  - 支持 `formula/table/method/device` 参数化
  - 新增产物目录检测与 `passed/artifact_missing/config_missing` 判定
- `backend/tests/test_av15_mineru_linux_runtime.py`
  - 新增 `local minimal passed` 测试
- 新增报告：
  - `docs/A-v1.5_mineru_linux_local_minimal_2026-05-19.json`

这轮真实结果：

```text
status = passed
model_source = local
backend = pipeline
method = ocr
formula = false
table = false
device_mode = cpu
```

关键阶段全部通过：

- `local_api_started = true`
- `uvicorn_ready = true`
- `task_submitted = true`
- `pipeline_streaming_started = true`
- `pipeline_batch_started = true`
- `model_init_done = true`
- `layout_predict_completed = true`
- `ocr_det_completed = true`
- `batch_completed = true`
- `artifact_root_exists = true`
- `content_list_generated = true`

对应真实产物：

- `data/mineru_output_wsl_local_minimal/upload_pdf_sidecar/ocr/upload_pdf_sidecar.md`
- `data/mineru_output_wsl_local_minimal/upload_pdf_sidecar/ocr/upload_pdf_sidecar_content_list_v2.json`

这说明 A-v1.5 到这一步，MinerU 已经不再是“只有 blocked 证据”，而是：

- Windows 默认路径：`runtime_resource_blocked`
- WSL 默认联网路径：`network_blocked`
- WSL local minimal 路径：`passed`

也就是说，MinerU 的真实 Linux 最小可运行链路已经被打通。

## 13. 2026-05-19 MinerU Linux local minimal bad case

虽然 `WSL local minimal` 已经转绿，但它当前还不能直接当作高质量 PDF 解析默认链路。

真实 bad case：

- `upload_pdf_sidecar.md` 为空
- `upload_pdf_sidecar_content_list_v2.json` 只有空段落结构
  - `paragraph_content: []`

因此这条链路当前的最准确定义是：

```text
运行可用 = true
内容质量稳定可用 = false
```

bad case 记录：

- `docs/A-v1.5_bad_cases.md`

下一步应优先：

1. 换更标准的 PDF 样例复验内容质量
2. 在 local cache 保持不变的前提下，逐步恢复 `method=auto` 或 `table/formula`
3. 只有内容质量转绿后，才把这条链路升级成 A-v1.5 的正式 PDF 主验收链

## 14. 2026-05-20 MinerU Linux 分页采样验收

为了判断 `upload_pdf_sidecar.pdf` 的空内容现象是不是整条链路的共性问题，本轮继续用两个更标准的真实 PDF 做复验：

- `data/raw_manuals_downloaded/OM_780-3.pdf`
- `data/raw_manuals_downloaded/MPOD-AFCDNS_R0_EN.pdf`

同时把 `backend/scripts/preflight_mineru_linux_runtime.py` 补成支持：

- `--start`
- `--end`
- `timeout` 分类

对应测试：

- `backend/tests/test_av15_mineru_linux_runtime.py`

### 第一轮：整本手册

结果：

- `OM_780-3.pdf`
  - `docs/A-v1.5_mineru_linux_local_minimal_om_780_3_2026-05-20.json`
  - 状态：`failed`
  - 已进入 136 页批处理和 layout 阶段
- `MPOD-AFCDNS_R0_EN.pdf`
  - `docs/A-v1.5_mineru_linux_local_minimal_mpod_afcdns_r0_en_2026-05-20.json`
  - 状态：`timeout`

这说明当前 `local minimal profile` 的主要边界不是“完全不能解析 PDF”，而是“整本长手册吞吐量不够”。

### 第二轮：前 2 页分页采样

结果：

- `OM_780-3.pdf`
  - `docs/A-v1.5_mineru_linux_local_minimal_om_780_3_p0_p1_2026-05-20.json`
  - 状态：`passed`
- `MPOD-AFCDNS_R0_EN.pdf`
  - `docs/A-v1.5_mineru_linux_local_minimal_mpod_afcdns_r0_en_p0_p1_2026-05-20.json`
  - 状态：`passed`

两份真实手册都产出了非空正文：

- `data/mineru_output_wsl_local_om_780_3_p0_p1/OM_780-3/ocr/OM_780-3.md`
- `data/mineru_output_wsl_local_mpod_afcdns_r0_en_p0_p1/MPOD-AFCDNS_R0_EN/ocr/MPOD-AFCDNS_R0_EN.md`

并且 `content_list_v2.json` 也不再是空结构。

### 当前收口结论

到这一步，A-v1.5 对 MinerU 的最准确定义已经变成：

```text
WSL + local model cache + local minimal profile
= 真实可运行
= 小页范围可产出非空内容
!= 整本长手册稳定验收
```

因此当前最合理的正式验收口径是：

1. Vision LLM：真实转绿
2. MinerU Linux：以分页采样作为真实 PDF 验收口径
3. PaddleOCR：仍为 runtime_incompatible

## 15. 2026-05-20 A-v1.5 多模态主报告升级到 2 绿

在前面的 Linux 分页采样验收转绿之后，本轮继续把验收口径从“手工解释”升级成“主报告自动聚合”。

更新：

- `backend/scripts/run_av15_multimodal_acceptance.py`
  - 自动汇总当天的 `MinerU Linux local minimal sliced` 报告
  - 新增正式组件：
    - `mineru_linux_local_sliced_pdf_parsing`
- `backend/tests/test_av15_multimodal_acceptance.py`
  - 补齐对应聚合测试

新主报告：

- `docs/A-v1.5_multimodal_acceptance_report_2026-05-20.json`

最新统计：

```text
component_count = 7
passed = 2
runtime_incompatible = 1
runtime_resource_blocked = 1
blocked_dependency = 3
```

两条正式转绿链路：

1. `vision_llm_real_runtime`
2. `mineru_linux_local_sliced_pdf_parsing`

这一步的意义是：

- 不再只靠聊天里说明 “MinerU Linux 已部分转绿”
- 而是把它真实写进 A-v1.5 官方验收主报告

因此截至当前，A-v1.5 的最准确定义已经变成：

```text
Vision = 绿
MinerU Linux sliced = 绿
PaddleOCR = 未绿
```

## 16. 2026-05-20 PaddleOCR 最终收口

作为 A-v1.5 的最后一步，本轮把 `PaddleOCR` 做了最终一轮真实攻坚，但没有把它强行写绿。

最后一组已验证尝试：

1. 关闭 `FLAGS_enable_pir_api`
2. 关闭 `FLAGS_use_mkldnn`
3. 同时关闭 `FLAGS_enable_pir_api` 与 `FLAGS_use_mkldnn`
4. 改用 `PP-OCRv5` mobile det/rec
5. 改用 `PP-OCRv4` mobile profile

正式记录：

- `docs/A-v1.5_paddleocr_linux_final_probe_2026-05-20.json`

结果全部一致：

```text
status = runtime_incompatible
error = NotImplementedError: ConvertPirAttribute2RuntimeAttribute
```

这说明当前阻塞已经可以非常明确地定性为：

- 不是凭证问题
- 不是图片样例问题
- 不是 server/mobile 模型选择问题
- 不是简单的 `PIR/MKLDNN` 环境变量开关问题
- 而是当前 `paddle==3.3.1 / paddleocr==3.5.0 / paddlex==3.5.2` 这组运行时在本机 WSL CPU 路径下仍不兼容

因此 A-v1.5 到这里的最终验收状态应诚实写成：

1. `Vision LLM`：正式转绿
2. `MinerU Linux sliced`：正式转绿
3. `PaddleOCR`：未转绿，但已完成充分真实排查并正式收口
