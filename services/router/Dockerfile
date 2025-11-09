FROM python:3.11-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN adduser --disabled-password --gecos '' --shell /bin/bash appuser

WORKDIR /app

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /app/services/router

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 80

CMD ["python", "-m", "services.router.router"]
