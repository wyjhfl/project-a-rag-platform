import json
from pathlib import Path

from app.models import (
    AcceptanceBreakdownItem,
    AcceptanceChartBar,
    AcceptanceEvidenceItem,
    AcceptanceHighlightItem,
    AcceptanceOverviewResponse,
    AcceptancePanel,
    AcceptanceTraceCase,
    AcceptanceTraceEvent,
)

DOCS_DIR = Path(__file__).resolve().parents[3] / "docs"


def build_acceptance_overview(
    docs_dir: Path | None = None,
    version: str = "v2.0",
) -> AcceptanceOverviewResponse:
    resolved_docs_dir = docs_dir or DOCS_DIR
    panels = [
        _build_provider_panel(resolved_docs_dir),
        _build_multimodal_panel(resolved_docs_dir),
        _build_evaluation_panel(resolved_docs_dir),
        _build_bad_case_panel(resolved_docs_dir),
    ]
    generated_from: list[str] = []
    for panel in panels:
        generated_from.extend(item.path for item in panel.evidence)
    generated_from = list(dict.fromkeys(generated_from))
    overall_status = "ok" if any(panel.status == "passed" for panel in panels) else "warning"
    return AcceptanceOverviewResponse(
        status=overall_status,
        version=version,
        generated_from=generated_from,
        panels=panels,
    )


def _build_provider_panel(docs_dir: Path) -> AcceptancePanel:
    report_path = _latest_doc(docs_dir, "A-v2.2_provider_acceptance_report*.json") or _latest_doc(
        docs_dir, "A-v1.4_provider_acceptance_report*.json"
    )
    if report_path is None:
        return AcceptancePanel(
            key="provider",
            title="真实 LLM 主链",
            status="missing",
            summary="未找到 provider 验收报告。",
            metrics={},
        )

    report = _load_json(report_path)
    summary = report.get("summary", {})
    results = report.get("results", [])
    preferred = next((item for item in results if item.get("name") == "deepseek_chat"), None)
    accepted = preferred if preferred and preferred.get("status") == "accepted" else next(
        (item for item in results if item.get("status") == "accepted"), None
    )
    accepted_name = accepted.get("name", "未确定") if accepted else "未确定"
    metrics = {
        "provider_count": str(summary.get("provider_count", 0)),
        "accepted_count": str(summary.get("accepted_count", 0)),
        "blocked_count": str(summary.get("blocked_count", 0)),
        "default_candidate": accepted_name,
    }
    status = "passed" if summary.get("accepted_count", 0) >= 1 else "warning"
    breakdown = [
        AcceptanceBreakdownItem(
            label=item.get("name", "unknown"),
            status=item.get("status", "unknown"),
            summary=(
                "已通过 grounded 验收"
                if item.get("status") == "accepted"
                else f"当前阻塞: {item.get('blocker_type', 'unknown')}"
            ),
            metrics={
                "provider": str(item.get("runtime", {}).get("provider", "")),
                "model": str(item.get("runtime", {}).get("model", "")),
                "direct_llm_connected": str(item.get("direct_llm_connected", False)).lower(),
            },
        )
        for item in results
    ]
    chart = [
        AcceptanceChartBar(
            label="accepted",
            value=float(summary.get("accepted_count", 0)),
            total=float(summary.get("provider_count", 1) or 1),
            tone="success",
        ),
        AcceptanceChartBar(
            label="blocked",
            value=float(summary.get("blocked_count", 0)),
            total=float(summary.get("provider_count", 1) or 1),
            tone="danger",
        ),
    ]
    highlights = [
        AcceptanceHighlightItem(
            title="默认文本主链候选",
            summary=f"{accepted_name} 是当前公开 demo 默认主链；MiMo v2.5 已进入候选对照。",
            status="passed" if accepted else "warning",
            tags=["grounded", "default-provider"],
        )
    ]
    blocker_counts = summary.get("blocker_type_counts", {})
    if blocker_counts:
        highlights.append(
            AcceptanceHighlightItem(
                title="Provider 对比状态",
                summary="A-v2.2 起已使用 token-plan 口径重新验收，MiMo 进入 grounded 可比较状态。",
                status="passed" if summary.get("blocked_count", 0) == 0 else "warning",
                tags=[f"{key}:{value}" for key, value in blocker_counts.items()],
            )
        )
    panel_summary = (
        f"当前已有 {summary.get('accepted_count', 0)} 个真实文本 provider 通过 grounded 验收，"
        f"默认候选为 {accepted_name}。"
    )
    return AcceptancePanel(
        key="provider",
        title="真实 LLM 主链",
        status=status,
        summary=panel_summary,
        metrics=metrics,
        evidence=[AcceptanceEvidenceItem(label="provider 验收报告", path=str(report_path))],
        breakdown=breakdown,
        chart=chart,
        highlights=highlights,
    )


def _build_multimodal_panel(docs_dir: Path) -> AcceptancePanel:
    report_path = _latest_doc(docs_dir, "A-v1.5_multimodal_acceptance_report*.json")
    if report_path is None:
        return AcceptancePanel(
            key="multimodal",
            title="真实多模态能力",
            status="missing",
            summary="未找到 A-v1.5 多模态验收报告。",
            metrics={},
        )

    report = _load_json(report_path)
    counts = report.get("summary", {}).get("status_counts", {})
    components = report.get("components", [])
    passed_names = [item["name"] for item in components if item.get("status") == "passed"]
    blocked_names = [item["name"] for item in components if item.get("status") != "passed"]
    status = "passed" if counts.get("passed", 0) >= 2 else "warning"
    panel_summary = (
        f"真实多模态当前已转绿 {counts.get('passed', 0)} 条链路，"
        f"未转绿重点集中在 {', '.join(blocked_names[:2]) or '无'}。"
    )
    metrics = {
        "passed": str(counts.get("passed", 0)),
        "runtime_incompatible": str(counts.get("runtime_incompatible", 0)),
        "runtime_resource_blocked": str(counts.get("runtime_resource_blocked", 0)),
        "passed_components": ", ".join(passed_names) or "无",
    }
    breakdown = [
        AcceptanceBreakdownItem(
            label=item.get("name", "unknown"),
            status=item.get("status", "unknown"),
            summary=_safe_text(item.get("detail", {}).get("diagnosis"))
            or _safe_text(item.get("detail", {}).get("error"))
            or "见验收报告",
            metrics=_stringify_dict(
                {
                    key: value
                    for key, value in item.get("detail", {}).items()
                    if key in {"field_count", "confidence", "next_step", "acceptance_mode"}
                }
            ),
        )
        for item in components
    ]
    chart = [
        AcceptanceChartBar(
            label=status_name,
            value=float(count),
            total=float(report.get("summary", {}).get("component_count", 1) or 1),
            tone=_tone_for_status(status_name),
        )
        for status_name, count in counts.items()
    ]
    evidence = [AcceptanceEvidenceItem(label="A-v1.5 多模态报告", path=str(report_path))]
    paddle_probe = _latest_doc(docs_dir, "A-v2.3_paddleocr_compatibility_report*.json") or _latest_doc(
        docs_dir, "A-v1.5_paddleocr_linux_final_probe*.json"
    )
    if paddle_probe is not None:
        evidence.append(AcceptanceEvidenceItem(label="PaddleOCR 兼容性边界", path=str(paddle_probe)))
    highlights = [
        AcceptanceHighlightItem(
            title="已转绿链路",
            summary="Vision LLM 与 MinerU Linux sliced 已经形成正式可讲的绿色链路。",
            status="passed",
            tags=passed_names[:3],
        ),
        AcceptanceHighlightItem(
            title="剩余未绿重点",
            summary="PaddleOCR 已在 A-v2.3 正式定性为 runtime compatibility boundary，不进入默认 demo。",
            status="warning",
            tags=["PaddleOCR", "runtime_incompatible"],
        ),
    ]
    return AcceptancePanel(
        key="multimodal",
        title="真实多模态能力",
        status=status,
        summary=panel_summary,
        metrics=metrics,
        evidence=evidence,
        breakdown=breakdown,
        chart=chart,
        highlights=highlights,
    )


def _build_evaluation_panel(docs_dir: Path) -> AcceptancePanel:
    report_specs = [
        ("回归评测", docs_dir / "A-real-data_regression_report.json"),
        ("RAGAS 评测", docs_dir / "A-real-data_ragas_report.json"),
        ("对抗评测", docs_dir / "A-real-data_adversarial_report.json"),
    ]
    evidence = [AcceptanceEvidenceItem(label=label, path=str(path)) for label, path in report_specs if path.exists()]
    if not evidence:
        return AcceptancePanel(
            key="evaluation",
            title="评测与回归",
            status="missing",
            summary="未找到评测报告。",
            metrics={},
        )

    regression_summary = {}
    regression_path = docs_dir / "A-real-data_regression_report.json"
    if regression_path.exists():
        regression_summary = _load_json(regression_path).get("summary", {})
    ragas_path = docs_dir / "A-real-data_ragas_report.json"
    ragas_summary = _load_json(ragas_path).get("summary", {}) if ragas_path.exists() else {}
    optimized_ragas_path = docs_dir / "A-v1.2_ragas_report.json"
    optimized_ragas = _load_json(optimized_ragas_path) if optimized_ragas_path.exists() else {}
    adversarial_path = docs_dir / "A-real-data_adversarial_report.json"
    adversarial_summary = (
        _load_json(adversarial_path).get("summary", {}) if adversarial_path.exists() else {}
    )
    passed_count = regression_summary.get("passed_count", 0)
    case_count = regression_summary.get("case_count", 0)
    metrics = {
        "regression": f"{passed_count}/{case_count}",
        "source_hit_count": str(regression_summary.get("source_hit_count", 0)),
        "ragas": _format_summary_value(ragas_summary),
        "adversarial": _format_summary_value(adversarial_summary),
    }
    status = "passed" if case_count and passed_count >= case_count - 1 else "warning"
    panel_summary = (
        f"真实回归评测当前通过 {passed_count}/{case_count}，"
        "并保留 RAGAS 与对抗报告作为补充证据。"
    )
    chart = []
    average_scores = ragas_summary.get("average_scores", {})
    for label, value in average_scores.items():
        chart.append(
            AcceptanceChartBar(
                label=label,
                value=float(value),
                total=1.0,
                tone="success" if float(value) >= 0.7 else "warning",
            )
        )
    if case_count:
        chart.append(
            AcceptanceChartBar(
                label="regression_pass_rate",
                value=float(passed_count),
                total=float(case_count),
                tone="success" if passed_count >= case_count - 1 else "warning",
            )
        )
    adv_case_count = adversarial_summary.get("case_count", 0)
    adv_passed_count = adversarial_summary.get("passed_count", 0)
    if adv_case_count:
        chart.append(
            AcceptanceChartBar(
                label="adversarial_pass_rate",
                value=float(adv_passed_count),
                total=float(adv_case_count),
                tone="success" if adv_passed_count == adv_case_count else "warning",
            )
        )
    low_score_cases = optimized_ragas.get("summary", {}).get("low_score_cases", [])[:3]
    trace_cases = _extract_trace_cases(optimized_ragas, low_score_cases)
    highlights = [
        AcceptanceHighlightItem(
            title=str(item.get("id", "unknown")),
            summary=(
                f"likely_issue={item.get('likely_issue', 'unknown')}, "
                f"faithfulness={item.get('faithfulness', 0)}, "
                f"context_precision={item.get('context_precision', 0)}"
            ),
            status="warning",
            tags=[str(item.get("likely_issue", "unknown"))],
        )
        for item in low_score_cases
    ]
    failed_adv = [
        item for item in _load_json(adversarial_path).get("results", []) if not item.get("passed", False)
    ] if adversarial_path.exists() else []
    if failed_adv:
        first_failed = failed_adv[0]
        highlights.append(
            AcceptanceHighlightItem(
                title=str(first_failed.get("id", "unknown")),
                summary="对抗测试仍有失败样例，适合在演示时专门讲安全边界与后处理不足。",
                status="danger",
                tags=[str(first_failed.get("category", "adversarial"))],
            )
        )
    return AcceptancePanel(
        key="evaluation",
        title="评测与回归",
        status=status,
        summary=panel_summary,
        metrics=metrics,
        evidence=evidence,
        chart=chart,
        highlights=highlights,
        trace_cases=trace_cases,
    )


def _build_bad_case_panel(docs_dir: Path) -> AcceptancePanel:
    files = [
        ("真实数据 bad case", docs_dir / "A-real-data_bad_cases.md"),
        ("A-v1.5 bad case", docs_dir / "A-v1.5_bad_cases.md"),
    ]
    evidence = [AcceptanceEvidenceItem(label=label, path=str(path)) for label, path in files if path.exists()]
    if not evidence:
        return AcceptancePanel(
            key="badcases",
            title="Bad Case 与边界",
            status="missing",
            summary="未找到 bad case 记录。",
            metrics={},
        )

    real_case_count = _count_markdown_headings(docs_dir / "A-real-data_bad_cases.md")
    multimodal_case_count = _count_markdown_headings(docs_dir / "A-v1.5_bad_cases.md")
    metrics = {
        "real_data_cases": str(real_case_count),
        "multimodal_cases": str(multimodal_case_count),
    }
    highlights = _extract_markdown_highlights(docs_dir / "A-real-data_bad_cases.md", 3)
    highlights.extend(_extract_markdown_highlights(docs_dir / "A-v1.5_bad_cases.md", 2))
    summary = (
        f"当前已沉淀真实数据 bad case {real_case_count} 条，"
        f"多模态 bad case {multimodal_case_count} 条，可直接用于面试讲边界。"
    )
    return AcceptancePanel(
        key="badcases",
        title="Bad Case 与边界",
        status="passed",
        summary=summary,
        metrics=metrics,
        evidence=evidence,
        highlights=highlights,
    )


def _latest_doc(docs_dir: Path, pattern: str) -> Path | None:
    matches = sorted(docs_dir.glob(pattern))
    return matches[-1] if matches else None


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _format_summary_value(summary: dict) -> str:
    if not summary:
        return "未生成"
    compact = []
    for key in ("score", "pass_rate", "passed_count", "case_count"):
        if key in summary:
            compact.append(f"{key}={summary[key]}")
    return ", ".join(compact) or "已生成"


def _count_markdown_headings(path: Path) -> int:
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8", errors="ignore")
    return sum(1 for line in text.splitlines() if line.startswith("## "))


def _stringify_dict(data: dict) -> dict[str, str]:
    return {str(key): _safe_text(value) for key, value in data.items() if value not in (None, "", [])}


def _safe_text(value) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").strip()
    return text[:180] + "..." if len(text) > 180 else text


def _tone_for_status(status_name: str) -> str:
    if status_name == "passed":
        return "success"
    if status_name in {"runtime_incompatible", "runtime_resource_blocked"}:
        return "danger"
    return "warning"


def _extract_markdown_highlights(path: Path, limit: int) -> list[AcceptanceHighlightItem]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    highlights: list[AcceptanceHighlightItem] = []
    for index, line in enumerate(lines):
        if not line.startswith("## "):
            continue
        title = line[3:].strip()
        summary = ""
        for next_line in lines[index + 1 :]:
            cleaned = next_line.strip()
            if not cleaned or cleaned.startswith("## "):
                if cleaned.startswith("## "):
                    break
                continue
            summary = cleaned
            break
        highlights.append(
            AcceptanceHighlightItem(
                title=title,
                summary=_safe_text(summary) or "见 bad case 文档。",
                status="warning",
                tags=["bad-case"],
            )
        )
        if len(highlights) >= limit:
            break
    return highlights


def _extract_trace_cases(report: dict, low_score_cases: list[dict]) -> list[AcceptanceTraceCase]:
    if not report:
        return []
    result_map = {item.get("id"): item for item in report.get("results", [])}
    trace_cases: list[AcceptanceTraceCase] = []
    for item in low_score_cases:
        case_id = item.get("id")
        full_case = result_map.get(case_id)
        if not full_case:
            continue
        trace = full_case.get("trace", {})
        events = []
        for event in trace.get("events", [])[:6]:
            event_name = str(event.get("name", "unknown"))
            event_summary = _summarize_trace_event(event)
            events.append(
                AcceptanceTraceEvent(
                    name=event_name,
                    summary=event_summary,
                    inputs=_summarize_trace_map(event.get("inputs", {})),
                    outputs=_summarize_trace_map(event.get("outputs", {})),
                    metadata=_summarize_trace_map(event.get("metadata", {})),
                )
            )
        trace_cases.append(
            AcceptanceTraceCase(
                case_id=str(case_id),
                title=_safe_text(full_case.get("question")) or str(case_id),
                issue=str(item.get("likely_issue", "unknown")),
                events=events,
                raw_trace=trace,
            )
        )
    return trace_cases


def _summarize_trace_event(event: dict) -> str:
    outputs = event.get("outputs", {})
    metadata = event.get("metadata", {})
    if isinstance(outputs, dict):
        for key in ("decision", "route", "answer_source", "retrieval_queries"):
            if key in outputs:
                return _safe_text(outputs[key])
    if isinstance(metadata, dict):
        for key in ("accepted", "selected_count", "llm_used", "reason"):
            if key in metadata:
                return f"{key}={_safe_text(metadata[key])}"
    return "见原始 trace 事件。"


def _summarize_trace_map(data: dict) -> dict[str, str]:
    if not isinstance(data, dict):
        return {}
    summary: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(value, (str, int, float, bool)):
            summary[str(key)] = _safe_text(value)
        elif isinstance(value, list):
            preview = ", ".join(_safe_text(item) for item in value[:3])
            summary[str(key)] = preview
        elif isinstance(value, dict):
            compact = ", ".join(f"{nested_key}={_safe_text(nested_value)}" for nested_key, nested_value in list(value.items())[:3])
            summary[str(key)] = compact
    return summary
