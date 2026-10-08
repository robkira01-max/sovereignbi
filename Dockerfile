# ── Build stage : install dependencies ───────────────────────────────────────
FROM python:3.11-slim AS builder
WORKDIR /build

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        fastapi "uvicorn[standard]" python-multipart httpx \
        duckdb pandas openpyxl xlrd sqlglot langgraph pyyaml \
        scikit-learn fpdf2 pymysql pypdf python-docx qdrant-client

# ── Runtime stage : non-root, minimal image ──────────────────────────────────
FROM python:3.11-slim AS runtime

# Non-root user for defence in depth
RUN groupadd -r sovereign && \
    useradd -r -g sovereign -d /srv -s /bin/false sovereign

WORKDIR /srv

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY app app
COPY semantic semantic

RUN chown -R sovereign:sovereign /srv
USER sovereign

# Runtime defaults (override via env or docker-compose)
ENV OLLAMA_URL=http://ollama:11434 \
    SOVEREIGN_EMBEDDER=tfidf \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/live')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
