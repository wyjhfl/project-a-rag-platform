import re
from dataclasses import dataclass
from enum import StrEnum


class QueryRoute(StrEnum):
    PRECISE_HYBRID = "precise_hybrid"
    ENHANCED_RETRIEVAL = "enhanced_retrieval"
    TABLE_LOOKUP = "table_lookup"
    IMAGE_EXTRACTION = "image_extraction"
    SECURITY_REVIEW = "security_review"


@dataclass(frozen=True)
class EnhancedQuery:
    route: QueryRoute
    original: str
    retrieval_queries: list[str]


class QueryEnhancer:
    def build_hyde_query(self, question: str) -> str:
        normalized = " ".join(question.split())
        signals = _extract_equipment_signals(normalized)
        signal_text = "，".join(signals) if signals else "待确认设备型号和故障码"
        return (
            f"设备售后诊断假设文档：故障现象：{normalized}。"
            f"已知信号：{signal_text}。"
            "排查方向：根据设备型号、故障码、报警灯状态、仪表读数、温度、压力、供电、"
            "传感器、散热和负载状态检索对应手册章节，并给出带引用的检查步骤。"
        )

    def build_multi_queries(self, question: str, limit: int = 4) -> list[str]:
        normalized = " ".join(question.split())
        variants = [
            normalized,
            self._replace_common_terms(normalized),
            f"{normalized} 故障原因 排查步骤",
            f"{normalized} 设备手册 报警 处理建议",
            self.build_hyde_query(normalized),
        ]
        unique: list[str] = []
        for variant in variants:
            if variant and variant not in unique:
                unique.append(variant)
            if len(unique) >= limit:
                break
        return unique

    def _replace_common_terms(self, question: str) -> str:
        replacements = {
            "不稳": "电池模式 输出波动",
            "跳停": "保护停机 报警",
            "老是": "频繁",
            "上不去": "不足 偏低",
            "切到电池": "切换到电池模式",
        }
        rewritten = question
        for source, target in replacements.items():
            rewritten = rewritten.replace(source, target)
        return rewritten if rewritten != question else f"{question} 同义症状 标准术语"


class QueryRouter:
    def route(self, question: str) -> QueryRoute:
        normalized = question.strip()
        lowered = normalized.lower()
        risky_english_terms = ["ignore previous", "system prompt", "developer message"]
        if any(term in lowered for term in risky_english_terms):
            return QueryRoute.SECURITY_REVIEW
        if any(term in normalized for term in ["忽略", "系统提示词", "越狱"]):
            return QueryRoute.SECURITY_REVIEW
        if any(term in normalized for term in ["图片", "截图", "铭牌", "报警灯", "仪表盘", "读数"]):
            return QueryRoute.IMAGE_EXTRACTION
        if any(term in normalized for term in ["表格", "参数", "规格", "范围"]):
            return QueryRoute.TABLE_LOOKUP
        if _extract_fault_codes(normalized):
            return QueryRoute.PRECISE_HYBRID
        return QueryRoute.ENHANCED_RETRIEVAL

    def build_enhanced_query(
        self,
        question: str,
        enhancer: QueryEnhancer | None = None,
    ) -> EnhancedQuery:
        enhancer = enhancer or QueryEnhancer()
        route = self.route(question)
        if route == QueryRoute.ENHANCED_RETRIEVAL:
            queries = enhancer.build_multi_queries(question)
        else:
            queries = [question]
        return EnhancedQuery(route=route, original=question, retrieval_queries=queries)


def _extract_fault_codes(text: str) -> list[str]:
    return re.findall(r"\b[A-Z]{1,6}[-_]?\d{2,4}\b|\b[EFP]\d{2,4}\b", text.upper())


def _extract_equipment_signals(text: str) -> list[str]:
    model_like = re.findall(r"\b[A-Z]{1,6}[-_]?\d{2,4}\b|\b[A-Z]\d{2,4}\b", text.upper())
    return list(dict.fromkeys(model_like))
