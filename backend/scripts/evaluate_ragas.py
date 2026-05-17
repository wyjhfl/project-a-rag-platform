import argparse
import json
import sys
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
            }
        )

    summary_scores = {
        metric: round(mean(result["scores"][metric] for result in results), 4) if results else 0.0
        for metric in METRICS
    }
    return {
        "summary": {
            "case_count": len(results),
            "average_scores": summary_scores,
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
    return [term for term in text.replace("，", " ").replace("。", " ").split() if len(term) > 1]


if __name__ == "__main__":
    main()
