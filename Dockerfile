FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only what the API needs at runtime. Never use `COPY . .`: it would
# include .env, .git, local databases and the frontend.
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY scripts ./scripts

RUN useradd --create-home --uid 1001 taskflow \
    && mkdir -p /app/uploads \
    && chown -R taskflow:taskflow /app

USER taskflow

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live', timeout=3)"

CMD ["python", "-m", "app.main"]
