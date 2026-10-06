FROM python:3.11-slim
WORKDIR /srv
COPY pyproject.toml .
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" python-multipart httpx duckdb pandas openpyxl sqlglot langgraph pyyaml
COPY app app
COPY semantic semantic
ENV OLLAMA_URL=http://ollama:11434
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
