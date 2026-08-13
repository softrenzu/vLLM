FROM vllm/vllm-openai:v0.26.0

WORKDIR /app
COPY pyproject.toml README.md /app/
COPY rooomvllm /app/rooomvllm
RUN uv pip install --system --no-deps . && uv pip install --system fastapi uvicorn pydantic PyYAML prometheus-client
COPY config.example.yaml /app/config.yaml
ENV ROOOMVLLM_CONFIG=/app/config.yaml
EXPOSE 8000
ENTRYPOINT []
CMD ["rooomvllm"]
