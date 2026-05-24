# A-v2.3 Bad Cases：PaddleOCR 兼容性专项

## BC-A-v2.3-001：WSL PaddleOCR 真实推理 runtime_incompatible

现象：

```text
wsl_packages_ready = true
wsl_ocr_runtime_ready = false
recommended_path = wsl_runtime_incompatible
```

环境：

```text
WSL Ubuntu-24.04
python = 3.12.3
paddle = 3.3.1
paddleocr = 3.5.0
paddlex = 3.5.2
```

错误：

```text
NotImplementedError: ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]
```

根因判断：

- 不是缺 Python。
- 不是缺 `paddleocr` 包。
- 不是 `libgomp` 共享库问题。
- 不是单个图片样例问题。
- 当前阻塞稳定落在 PaddleX static inference runtime。

处理：

- 保留 sidecar OCR 作为默认本地兜底。
- 不把 PaddleOCR 放入公开 demo 默认路径。
- 将 PaddleOCR 正式定性为 runtime compatibility boundary。

## BC-A-v2.3-002：低成本参数尝试无法绕过 runtime 错误

已尝试：

- `FLAGS_enable_pir_api=0`
- `FLAGS_use_mkldnn=0`
- 同时关闭 PIR / MKLDNN
- PP-OCRv5 mobile det / rec
- PP-OCRv4 mobile profile

结果：

```text
全部仍触发 ConvertPirAttribute2RuntimeAttribute
```

结论：

- 继续在当前 WSL profile 上调参数收益低。
- 后续若继续攻克，应切到干净 Docker/Linux runtime matrix。

