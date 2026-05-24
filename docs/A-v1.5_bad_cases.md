# A-v1.5 bad cases

## 2026-05-19 MinerU Linux local minimal 成功但提取内容为空

### 现象

- `WSL + local model cache + pipeline + method=ocr + formula=false + table=false` 已真实跑通。
- 产物目录存在：
  - `data/mineru_output_wsl_local_minimal/upload_pdf_sidecar/ocr/upload_pdf_sidecar.md`
  - `data/mineru_output_wsl_local_minimal/upload_pdf_sidecar/ocr/upload_pdf_sidecar_content_list_v2.json`
- 但 `upload_pdf_sidecar.md` 为空。
- `upload_pdf_sidecar_content_list_v2.json` 只包含空段落结构：
  - `paragraph_content: []`

### 真实证据

- `docs/A-v1.5_mineru_linux_local_minimal_2026-05-19.json`
- `data/mineru_output_wsl_local_minimal/upload_pdf_sidecar/ocr/upload_pdf_sidecar_content_list_v2.json`

### 根因判断

- 这不是环境没起，也不是模型没加载。
- 当前链路已经证明：
  - 本地 `mineru-api` 可启动
  - pipeline 可进入 `layout + OCR` 阶段
  - 结果文件可落盘
- 问题落在“解析质量”而不是“运行可用性”。
- 当前样例 `upload_pdf_sidecar.pdf` 在 `MinerU local minimal` 配置下，产出了结构但没有有效正文内容。

### 影响范围

- 说明 `MinerU` 的 Linux 最小链路已经能作为“真实可运行证据”。
- 但还不能直接把这条链路当作“高质量 PDF 解析默认链路”。
- 如果直接接入主链，会出现：
  - 文档看似解析成功
  - 实际正文为空
  - 后续 ingest 检索价值有限

### 当前结论

- `MinerU Linux local minimal`：
  - 运行状态：`passed`
  - 解析质量：`bad_case`

### 下一步

1. 换 1 到 2 个更标准的 PDF 样例复验，确认是样例问题还是当前最小 profile 的通病。
2. 在保持 `local model cache` 的前提下，逐步恢复 `table/formula` 或切回 `method=auto`，比较内容恢复情况。
3. 只有当内容不再为空，才把这条链路提升为 A-v1.5 的正式 PDF 主验收链。

## 2026-05-20 MinerU Linux local minimal 整本手册边界

### 现象

- 当前 `WSL + local model cache + pipeline + method=ocr + formula=false + table=false` 对整本真实手册仍有明显边界：
  - `OM_780-3.pdf` 整本运行失败
  - `MPOD-AFCDNS_R0_EN.pdf` 整本运行超时
- 但把页范围缩小到前 2 页后，两份手册都能稳定跑通，并且产出非空正文。

### 真实证据

- 整本失败：
  - `docs/A-v1.5_mineru_linux_local_minimal_om_780_3_2026-05-20.json`
  - `docs/A-v1.5_mineru_linux_local_minimal_mpod_afcdns_r0_en_2026-05-20.json`
- 分页成功：
  - `docs/A-v1.5_mineru_linux_local_minimal_om_780_3_p0_p1_2026-05-20.json`
  - `docs/A-v1.5_mineru_linux_local_minimal_mpod_afcdns_r0_en_p0_p1_2026-05-20.json`

### 根因判断

- 这不是“local minimal profile 完全不可用”。
- 更准确的判断是：
  - 小页范围真实可用
  - 整本长手册在当前 CPU + local minimal profile 下成本过高
- 当前边界落在吞吐量而不是基本解析质量：
  - `OM_780-3.pdf` 已进入 136 页批处理和 layout 阶段
  - `MPOD-AFCDNS_R0_EN.pdf` 整本运行超时

### 当前结论

- `MinerU Linux local minimal`：
  - 小页范围：`passed`
  - 整本长手册：`bad_case`

### 下一步

1. 先把 `start/end` 分页采样作为 A-v1.5 的正式 Linux PDF 验收口径。
2. 后续再单独验证：
   - 增大 timeout
   - 提升运行资源
   - 恢复 `method=auto`
3. 不把“整本长手册可稳定跑完”作为当前这条最小链路的完成标准。
