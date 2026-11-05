# For local development of the *proposed* OCI adapter only.
# Pin the FROM digest before creating a production source->artifact attestation.
FROM python:3.12-slim
RUN useradd -r -u 10001 -m contributor
WORKDIR /app
COPY worker.py /app/worker.py
USER 10001
ENTRYPOINT ["python", "/app/worker.py"]
