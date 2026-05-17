import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def main() -> None:
    from app.config import get_settings
    from app.rag.experiment import run_retrieval_experiment

    parser = argparse.ArgumentParser(description="Compare v0.2 retrieval strategies.")
    parser.add_argument("--docs-dir", type=Path, default=None)
    parser.add_argument("--cases", type=Path, default=Path("data/retrieval_cases_v0.2.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/A-v0.2_retrieval_report.json"))
    parser.add_argument("--top-k", type=int, default=4)
    args = parser.parse_args()

    settings = get_settings()
    docs_dir = args.docs_dir or settings.seed_docs_dir
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    report = run_retrieval_experiment(
        docs_dir=docs_dir,
        cases=cases,
        chroma_dir=settings.chroma_dir / "v02_experiment",
        top_k=args.top_k,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
