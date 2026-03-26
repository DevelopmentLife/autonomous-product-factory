FROM python:3.12-slim
WORKDIR /app
RUN pip install uv
COPY . .
RUN uv pip install --system -e .
VOLUME ["/data/artifacts"]
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8001/healthz || exit 1
CMD ["uvicorn", "apf_artifact_store.main:app", "--host", "0.0.0.0", "--port", "8001"]
