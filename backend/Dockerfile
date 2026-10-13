FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_PROJECT_ENVIRONMENT=/opt/venv PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir uv==0.12.23
WORKDIR /srv/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/ ./
COPY demo/ /srv/demo/
RUN useradd --create-home --uid 10001 codebuddy && mkdir -p /data/source && chown -R codebuddy /data /srv/backend
USER codebuddy
EXPOSE 5001
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "--threads", "8", "--timeout", "90", "--graceful-timeout", "30", "wsgi:app"]
