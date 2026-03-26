FROM python:3.12-slim
WORKDIR /app
RUN pip install uv
COPY packages/agent-core/ ./packages/agent-core/
COPY packages/event-bus/ ./packages/event-bus/
COPY services/agent-runner/ ./services/agent-runner/
RUN uv pip install --system \
    -e ./packages/agent-core \
    -e ./packages/event-bus \
    -e ./services/agent-runner
CMD ["python", "-m", "apf_agent_runner.main"]
