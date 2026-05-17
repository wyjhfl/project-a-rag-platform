FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY backend ./backend
COPY prompts ./prompts
COPY data/seed_docs ./data/seed_docs

RUN pip install --no-cache-dir -e .

ENV APP_DATABASE_PATH=/app/data/app.db
ENV CHROMA_PERSIST_DIR=/app/data/chroma
ENV SEED_DOCS_DIR=/app/data/seed_docs
ENV RAG_PROMPT_PATH=/app/prompts/rag_prompt_v0.1.txt

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
