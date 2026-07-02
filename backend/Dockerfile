FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY packs ./packs
COPY web ./web
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "mecateca.main:app", "--host", "0.0.0.0", "--port", "8000"]
