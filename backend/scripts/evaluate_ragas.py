import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]

def evaluate_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    results = []
    for case in cases:
        answer = case.get("answer", "")
        contexts = case.get("contexts", [])
        expected_keywords = case.get("expected_keywords", [])
        scores = {
            "faithfulness": _faithfulness(answer, contexts),
            "answer_relevancy": _keyword_coverage(answer, expected_keywords),
            "context_precision": _context_precision(contexts, expected_keywords),
            "context_recall": _keyword_coverage("\n".join(contexts), expected_keywords),
        }
        diagnostics = _build_diagnostics(case, scores)
        results.append(
            {
                "id": case["id"],
                "question": case["question"],
                "answer": answer,
                "contexts": contexts,
                "expected_source": case.get("expected_source", ""),
                "citation_sources": case.get("citation_sources", []),
                "source_hit": case.get("source_hit", False),
                "scores": scores,
                "diagnostics": diagnostics,
                "trace": case.get("trace", {}),
            }
        )

    summary_scores = {
        metric: round(mean(result["scores"][metric] for result in results), 4) if results else 0.0
        for metric in METRICS
    }
    issue_counts = Counter(result["diagnostics"]["likely_issue"] for result in results)
    low_score_cases = [
        {
            "id": result["id"],
            "likely_issue": result["diagnostics"]["likely_issue"],
            "faithfulness": result["scores"]["faithfulness"],
            "answer_relevancy": result["scores"]["answer_relevancy"],
            "context_precision": result["scores"]["context_precision"],
            "context_recall": result["scores"]["context_recall"],
        }
        for result in results
        if min(result["scores"].values()) < 0.5
    ]
    return {
        "summary": {
            "case_count": len(results),
            "average_scores": summary_scores,
            "issue_counts": dict(issue_counts),
            "low_score_case_count": len(low_score_cases),
            "low_score_cases": low_score_cases[:10],
        },
        "results": results,
    }


def run_pipeline_cases(
    cases: list[dict[str, Any]],
    docs_dir: Path,
    chroma_dir: Path,
    database_path: Path,
) -> list[dict[str, Any]]:
    from app.rag.pipeline import RagPipeline
    from app.storage.sqlite_store import SQLiteStore

    store = SQLiteStore(database_path)
    pipeline = RagPipeline(
        chroma_dir=chroma_dir,
        store=store,
        prompt_path=PROJECT_DIR / "prompts" / "rag_prompt_v0.1.txt",
    )
    pipeline.ingest_directory(docs_dir)
    enriched = []
    for case in cases:
        response = pipeline.answer(case["question"])
        citation_sources = [citation.source for citation in response.citations]
        expected_source = case.get("expected_source", "")
        enriched.append(
            {
                **case,
                "answer": response.answer,
                "contexts": [citation.content for citation in response.citations],
                "citation_sources": citation_sources,
                "source_hit": bool(expected_source)
                and any(expected_source in source for source in citation_sources),
                "trace": pipeline.last_trace or {},
                "agentic": (
                    {
                        "quality_score": pipeline.last_agentic_result.quality_score,
                        "retried": pipeline.last_agentic_result.retried,
                        "rewritten_query": pipeline.last_agentic_result.rewritten_query,
                        "contradictions": pipeline.last_agentic_result.contradictions,
                    }
                    if pipeline.last_agentic_result
                    else {}
                ),
            }
        )
    return enriched


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        default=str(PROJECT_DIR / "data/eval/regression_cases_v0.5.json"),
    )
    parser.add_argument(
        "--docs-dir",
        default=str(PROJECT_DIR / "data" / "seed_docs"),
    )
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    cases_path = Path(args.cases)
    docs_dir = Path(args.docs_dir)
    is_real_data = cases_path.name.startswith("real_")
    output = Path(
        args.output
        or (
            PROJECT_DIR / "docs/A-real-data_ragas_report.json"
            if is_real_data
            else PROJECT_DIR / "docs/A-v0.5_ragas_report.json"
        )
    )
    eval_name = "real_ragas" if is_real_data else "ragas"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    report = evaluate_cases(
        run_pipeline_cases(
            cases,
            docs_dir=docs_dir,
            chroma_dir=PROJECT_DIR / "data" / "v05_eval" / f"chroma_{eval_name}",
            database_path=PROJECT_DIR / "data" / "v05_eval" / f"{eval_name}.db",
        )
    )
    source_cases = [result for result in report["results"] if result.get("expected_source")]
    report["summary"]["source_hit_count"] = sum(
        1 for result in source_cases if result.get("source_hit")
    )
    report["summary"]["source_case_count"] = len(source_cases)
    Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


def _faithfulness(answer: str, contexts: list[str]) -> float:
    if not answer or not contexts:
        return 0.0
    answer_terms = set(_terms(answer))
    context_terms = set(_terms("\n".join(contexts)))
    if not answer_terms:
        return 0.0
    return round(len(answer_terms & context_terms) / len(answer_terms), 4)


def _context_precision(contexts: list[str], expected_keywords: list[str]) -> float:
    if not contexts:
        return 0.0
    useful = sum(
        1
        for context in contexts
        if any(keyword in context for keyword in expected_keywords)
    )
    return round(useful / len(contexts), 4)


def _keyword_coverage(text: str, expected_keywords: list[str]) -> float:
    if not expected_keywords:
        return 0.0
    hits = sum(1 for keyword in expected_keywords if keyword in text)
    return round(hits / len(expected_keywords), 4)


def _terms(text: str) -> list[str]:
    from app.rag.scoring import tokenize

    return [term for term in tokenize(text) if len(term) > 1]


def _build_diagnostics(case: dict[str, Any], scores: dict[str, float]) -> dict[str, Any]:
    expected_keywords = case.get("expected_keywords", [])
    answer = case.get("answer", "")
    contexts = case.get("contexts", [])
    context_text = "\n".join(contexts)
    answer_hits = [keyword for keyword in expected_keywords if keyword in answer]
    context_hits = [keyword for keyword in expected_keywords if keyword in context_text]
    answer_misses = [keyword for keyword in expected_keywords if keyword not in answer]
    context_misses = [keyword for keyword in expected_keywords if keyword not in context_text]
    likely_issue = _likely_issue(case, scores)
    return {
        "answer_keyword_hits": answer_hits,
        "answer_keyword_misses": answer_misses,
        "context_keyword_hits": context_hits,
        "context_keyword_misses": context_misses,
        "citation_count": len(case.get("citation_sources", [])),
        "context_count": len(contexts),
        "likely_issue": likely_issue,
        "source_hit": case.get("source_hit", False),
        "agentic_quality_score": case.get("agentic", {}).get("quality_score", 0.0),
        "agentic_retried": case.get("agentic", {}).get("retried", False),
        "rewritten_query": case.get("agentic", {}).get("rewritten_query", ""),
        "trace_event_names": [
            event.get("name", "")
            for event in case.get("trace", {}).get("events", [])
            if event.get("name")
        ],
    }


def _likely_issue(case: dict[str, Any], scores: dict[str, float]) -> str:
    if not case.get("source_hit", False):
        return "source_miss"
    if scores["context_precision"] < 0.5:
        return "context_noise"
    if scores["context_recall"] < 0.5:
        return "context_recall_gap"
    if scores["answer_relevancy"] < 0.5:
        return "answer_coverage_gap"
    if scores["faithfulness"] < 0.5:
        return "grounding_gap"
    if case.get("agentic", {}).get("contradictions"):
        return "contradictory_context"
    return "pass_or_minor_gap"


if __name__ == "__main__":
    main()
