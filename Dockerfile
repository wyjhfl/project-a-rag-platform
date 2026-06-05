FROM python:3.11-slim

RUN groupadd -g 1000 appuser && useradd -u 1000 -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

COPY pyproject.toml README.md ./
COPY backend ./backend
COPY prompts ./prompts
COPY data/seed_docs ./data/seed_docs

RUN pip install --no-cache-dir -e .

RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

ENV APP_DATABASE_PATH=/app/data/app.db
ENV CHROMA_PERSIST_DIR=/app/data/chroma
ENV SEED_DOCS_DIR=/app/data/seed_docs
ENV RAG_PROMPT_PATH=/app/prompts/rag_prompt_v0.1.txt

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
