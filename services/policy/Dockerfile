FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir pip setuptools wheel

COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[dev]"

COPY src/ ./src/

EXPOSE 8002

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002"]
