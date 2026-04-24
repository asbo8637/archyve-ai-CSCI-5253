FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace

COPY packages/python-common /workspace/packages/python-common
COPY apps/api/requirements.txt /workspace/apps/api/requirements.txt

RUN pip install --upgrade pip && \
    pip install -e /workspace/packages/python-common -r /workspace/apps/api/requirements.txt

COPY apps/api /workspace/apps/api

WORKDIR /workspace/apps/api

CMD ["sh", "-c", "uvicorn api_app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
