import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

def main() -> None:
    from app.rag.pipeline import RagPipeline
    from app.storage.sqlite_store import SQLiteStore

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
            PROJECT_DIR / "docs/A-real-data_regression_report.json"
            if is_real_data
            else PROJECT_DIR / "docs/A-v0.5_regression_report.json"
        )
    )
    eval_name = "real_regression" if is_real_data else "regression"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    store = SQLiteStore(PROJECT_DIR / "data" / "v05_eval" / f"{eval_name}.db")
    pipeline = RagPipeline(
        PROJECT_DIR / "data" / "v05_eval" / f"chroma_{eval_name}",
        store,
        PROJECT_DIR / "prompts/rag_prompt_v0.1.txt",
    )
    pipeline.ingest_directory(docs_dir)

    results = []
    for case in cases:
        response = pipeline.answer(case["question"])
        text = response.answer + "\n" + "\n".join(
            citation.content for citation in response.citations
        )
        hits = [keyword for keyword in case["expected_keywords"] if keyword in text]
        citation_sources = [citation.source for citation in response.citations]
        expected_source = case.get("expected_source", "")
        source_hit = not expected_source or any(
            expected_source in source for source in citation_sources
        )
        results.append(
            {
                **case,
                "hit_count": len(hits),
                "source_hit": source_hit,
                "citation_sources": citation_sources,
                "passed": bool(hits) and source_hit,
                "hits": hits,
            }
        )

    report = {
        "summary": {
            "case_count": len(results),
            "passed_count": sum(1 for result in results if result["passed"]),
            "source_hit_count": sum(1 for result in results if result["source_hit"]),
        },
        "results": results,
    }
    Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
