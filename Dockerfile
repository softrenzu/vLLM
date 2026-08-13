FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md /app/
COPY rooomvllm /app/rooomvllm
RUN pip install --no-cache-dir .
COPY config.example.yaml /app/config.yaml
ENV ROOOMVLLM_CONFIG=/app/config.yaml
EXPOSE 8000
CMD ["rooomvllm"]
