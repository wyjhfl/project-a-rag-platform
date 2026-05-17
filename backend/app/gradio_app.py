import subprocess
import sys
from pathlib import Path

import gradio as gr

from app.config import PROJECT_DIR, get_settings
from app.rag.conversation import ConversationMemory
from app.rag.pipeline import RagPipeline
from app.rag.vector_factory import build_vector_store
from app.storage.factory import build_store
from app.ticketing.workflow import TicketWorkflowService

settings = get_settings()
conversation_memory = ConversationMemory()


def create_demo_pipeline(
    database_path: Path | None = None,
    chroma_dir: Path | None = None,
) -> RagPipeline:
    return RagPipeline(
        chroma_dir=chroma_dir or settings.chroma_dir,
        store=build_store(settings, database_path=database_path),
        prompt_path=settings.prompt_path,
        vector_store=build_vector_store(settings),
    )


pipeline = create_demo_pipeline()


def resolve_docs_dir(selection: str) -> Path:
    if selection == "real_manuals_sanitized":
        return settings.seed_docs_dir.parent / "real_manuals_sanitized"
    return settings.seed_docs_dir


def ingest_docs_with_pipeline(active_pipeline: RagPipeline, docs_dir: Path) -> str:
    result = active_pipeline.ingest_directory(docs_dir)
    return f"已入库 {result.document_count} 份文档，{result.chunk_count} 个片段。"


def ingest_docs(selection: str) -> str:
    docs_dir = resolve_docs_dir(selection)
    if not docs_dir.exists():
        return f"资料目录不存在：{docs_dir}"
    return ingest_docs_with_pipeline(pipeline, docs_dir)


def answer(question: str) -> tuple[str, str]:
    response = pipeline.answer(question)
    return response.answer, _format_citations(response.citations)


def session_answer(session_id: str, question: str) -> tuple[str, str, str]:
    resolved_question = conversation_memory.resolve_question(session_id, question)
    response = pipeline.answer(resolved_question)
    return resolved_question, response.answer, _format_citations(response.citations)


def start_ticket(question: str, idempotency_key: str) -> str:
    service = TicketWorkflowService(store=pipeline.store, rag_pipeline=pipeline)
    result = service.start(question=question, idempotency_key=idempotency_key)
    return result.model_dump_json(indent=2)


def resume_ticket(ticket_id: str, reviewer: str, decision: str) -> str:
    service = TicketWorkflowService(store=pipeline.store, rag_pipeline=pipeline)
    result = service.resume_after_human_review(
        ticket_id=ticket_id,
        reviewer=reviewer,
        decision=decision,
    )
    return result.model_dump_json(indent=2)


def close_ticket(ticket_id: str, closed_by: str) -> str:
    service = TicketWorkflowService(store=pipeline.store, rag_pipeline=pipeline)
    result = service.close_ticket(ticket_id=ticket_id, closed_by=closed_by)
    return result.model_dump_json(indent=2)


def run_eval_script(script_name: str, cases_path: str, docs_selection: str) -> str:
    docs_dir = resolve_docs_dir(docs_selection)
    command = [
        sys.executable,
        str(PROJECT_DIR / "backend" / "scripts" / script_name),
        "--cases",
        cases_path,
        "--docs-dir",
        str(docs_dir),
    ]
    completed = subprocess.run(
        command,
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return completed.stderr.strip() or completed.stdout.strip()
    return completed.stdout.strip()


def load_bad_cases() -> str:
    paths = [
        PROJECT_DIR / "docs" / "A-real-data_bad_cases.md",
        PROJECT_DIR / "bad_cases" / "v0.5_evaluation_deploy.md",
    ]
    sections = [path.read_text(encoding="utf-8") for path in paths if path.exists()]
    if not sections:
        return "暂无 bad case 文件。"
    return "\n\n---\n\n".join(sections)


def _format_citations(citations) -> str:
    return "\n\n".join(
        f"[{index}] {citation.source} / chunk {citation.chunk_index}\n{citation.content}"
        for index, citation in enumerate(citations, start=1)
    )


with gr.Blocks(title="Project A v0.5 RAG 演示面板") as demo:
    gr.Markdown("# Project A v0.5 设备售后 RAG 演示面板")

    docs_selection = gr.Dropdown(
        choices=["seed_docs", "real_manuals_sanitized"],
        value="seed_docs",
        label="资料目录",
    )
    ingest_button = gr.Button("入库资料")
    ingest_output = gr.Textbox(label="入库结果")
    ingest_button.click(ingest_docs, inputs=docs_selection, outputs=ingest_output)

    with gr.Tab("普通问答"):
        question = gr.Textbox(label="故障描述", placeholder="例如：A100 出现 E-17 报警怎么排查？")
        answer_box = gr.Textbox(label="诊断建议")
        citations_box = gr.Textbox(label="引用来源")
        question.submit(answer, inputs=question, outputs=[answer_box, citations_box])

    with gr.Tab("多轮问答"):
        session_id = gr.Textbox(label="Session ID", value="demo-session")
        session_question = gr.Textbox(label="本轮问题", placeholder="例如：它还能继续运行吗？")
        resolved_box = gr.Textbox(label="消解后问题")
        session_answer_box = gr.Textbox(label="诊断建议")
        session_citations_box = gr.Textbox(label="引用来源")
        session_question.submit(
            session_answer,
            inputs=[session_id, session_question],
            outputs=[resolved_box, session_answer_box, session_citations_box],
        )

    with gr.Tab("工单演示"):
        ticket_question = gr.Textbox(label="工单问题")
        idempotency_key = gr.Textbox(label="幂等 Key", value="gradio-demo-ticket")
        start_button = gr.Button("启动工单")
        ticket_result = gr.Code(label="工单结果", language="json")
        start_button.click(
            start_ticket,
            inputs=[ticket_question, idempotency_key],
            outputs=ticket_result,
        )

        ticket_id = gr.Textbox(label="Ticket ID")
        reviewer = gr.Textbox(label="人工确认人", value="王工")
        decision = gr.Textbox(label="人工决策", value="approved")
        resume_button = gr.Button("人工确认恢复")
        resume_result = gr.Code(label="恢复结果", language="json")
        resume_button.click(
            resume_ticket,
            inputs=[ticket_id, reviewer, decision],
            outputs=resume_result,
        )

        closed_by = gr.Textbox(label="关闭人", value="李工")
        close_button = gr.Button("关闭工单")
        close_result = gr.Code(label="关闭结果", language="json")
        close_button.click(close_ticket, inputs=[ticket_id, closed_by], outputs=close_result)

    with gr.Tab("评测与 bad case"):
        real_cases = gr.Textbox(
            label="回归评测集",
            value="data/eval/real_regression_cases_v1.json",
        )
        real_adv_cases = gr.Textbox(
            label="对抗评测集",
            value="data/eval/real_adversarial_cases_v1.json",
        )
        ragas_button = gr.Button("运行 RAGAS")
        regression_button = gr.Button("运行回归")
        adversarial_button = gr.Button("运行对抗")
        eval_output = gr.Code(label="评测 summary", language="json")
        bad_case_button = gr.Button("查看 bad case")
        bad_case_output = gr.Markdown(label="bad case")

        ragas_button.click(
            lambda cases, docs: run_eval_script("evaluate_ragas.py", cases, docs),
            inputs=[real_cases, docs_selection],
            outputs=eval_output,
        )
        regression_button.click(
            lambda cases, docs: run_eval_script("run_regression.py", cases, docs),
            inputs=[real_cases, docs_selection],
            outputs=eval_output,
        )
        adversarial_button.click(
            lambda cases, docs: run_eval_script("run_adversarial.py", cases, docs),
            inputs=[real_adv_cases, docs_selection],
            outputs=eval_output,
        )
        bad_case_button.click(load_bad_cases, outputs=bad_case_output)


if __name__ == "__main__":
    demo.launch()
