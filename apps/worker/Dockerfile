FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace

COPY packages/python-common /workspace/packages/python-common
COPY apps/worker/requirements.txt /workspace/apps/worker/requirements.txt

RUN pip install --upgrade pip && \
    pip install -e /workspace/packages/python-common -r /workspace/apps/worker/requirements.txt

COPY apps/worker /workspace/apps/worker

WORKDIR /workspace/apps/worker

CMD ["python", "-m", "worker_app.main"]
