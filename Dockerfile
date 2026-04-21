FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FLOW_AGENT_DIR=/app/runtime \
    API_HOST=0.0.0.0 \
    API_PORT=8100 \
    WS_HOST=0.0.0.0 \
    WS_PORT=9222

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/runtime

EXPOSE 8100 9222

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=5 \
  CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8100/health').status == 200 else 1)"

CMD ["python", "-m", "agent.main"]
