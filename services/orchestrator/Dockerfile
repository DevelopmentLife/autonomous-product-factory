FROM python:3.12-slim
WORKDIR /app
RUN pip install uv
COPY packages/db/ ./packages/db/
COPY packages/event-bus/ ./packages/event-bus/
COPY services/orchestrator/ ./services/orchestrator/
RUN uv pip install --system \
    -e ./packages/db \
    -e ./packages/event-bus \
    -e ./services/orchestrator
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8000/healthz || exit 1
CMD ["uvicorn", "apf_orchestrator.main:app", "--host", "0.0.0.0", "--port", "8000"]
