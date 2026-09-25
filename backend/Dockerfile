FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY settings.py ./
COPY backend/ ./backend/
COPY agent/ ./agent/
COPY rag/ ./rag/
COPY retrieval/ ./retrieval/
COPY database/ ./database/
COPY prompts/ ./prompts/

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
