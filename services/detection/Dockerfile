FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir pip setuptools wheel

COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[dev]"
RUN python -m spacy download en_core_web_sm

COPY src/ ./src/

EXPOSE 8001

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
