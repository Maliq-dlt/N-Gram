FROM ghcr.io/astral-sh/uv:0.11.23 AS uv
FROM python:3.11-slim
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_CACHE_DIR=/app/.cache/uv UV_PYTHON_DOWNLOADS=never PATH=/app/.venv/bin:$PATH
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock ./
RUN mkdir -p .tmp .cache && uv venv --python 3.11 && uv export --frozen --no-hashes --no-emit-project --no-dev --no-emit-package torch --no-emit-package torchvision -o .tmp/requirements.txt && python -c "from pathlib import Path; p=Path('.tmp/requirements.txt'); p.write_text('\n'.join(s for s in p.read_text().splitlines() if not s.startswith(('nvidia-', 'cuda-', 'triton==')))+'\n')" && uv pip install torch==2.14.1 torchvision==0.29.1 --index-url https://download.pytorch.org/whl/cpu && uv pip install -r .tmp/requirements.txt
COPY . .
RUN groupadd --gid 10001 workspace && useradd --uid 10001 --gid workspace --no-create-home workspace && mkdir -p data models .cache .tmp && chown -R 10001:10001 data models .cache .tmp
USER 10001:10001
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import os, urllib.request; from urllib.parse import urlsplit; host=urlsplit(os.environ.get('INSIGHT_PUBLIC_URL','http://127.0.0.1:8765')).netloc; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8765/healthz',headers={'Host':host}),timeout=3)"
CMD ["python","-m","uvicorn","app:app","--host","0.0.0.0","--port","8765","--workers","1"]
