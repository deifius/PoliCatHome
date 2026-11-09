# Shared fixed-code pilot image: Commons coordinates only; optional Catbox runs signed built-in CPU work.
# No arbitrary uploaded code or Docker socket is exposed to the worker.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /opt/polic
COPY pyproject.toml README.md ./
COPY polyc ./polyc
RUN python -m pip install --no-cache-dir . \
    && useradd --system --uid 10001 --home-dir /opt/polic --shell /usr/sbin/nologin polic \
    && mkdir -p /opt/polic/runtime \
    && chown -R polic:polic /opt/polic
USER polic
EXPOSE 8765
CMD ["polyc", "serve", "--db", "runtime/browser.sqlite", "--host", "0.0.0.0", "--port", "8765", "--insecure-http-on-lan"]
