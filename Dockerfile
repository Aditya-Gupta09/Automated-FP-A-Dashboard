# ─── Stage 1: dependency layer ────────────────────────────────────────────────
FROM python:3.11-slim AS deps

WORKDIR /app

# System deps for pyarrow, reportlab
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ─── Stage 2: application ────────────────────────────────────────────────────
FROM python:3.11-slim AS app

WORKDIR /app

# Copy installed packages from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Non-root user for security
RUN useradd -m -u 1001 fpa && chown -R fpa:fpa /app
USER fpa

# Copy source (code only — raw data mounted at runtime via volume)
COPY --chown=fpa:fpa src/ ./src/
COPY --chown=fpa:fpa app/ ./app/
COPY --chown=fpa:fpa config/ ./config/
COPY --chown=fpa:fpa data/raw/ ./data/raw/

# PYTHONPATH so bare imports resolve
ENV PYTHONPATH=/app/src
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
