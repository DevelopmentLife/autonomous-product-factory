FROM python:3.12-slim
WORKDIR /app
RUN pip install uv
COPY . .
RUN uv pip install --system -e .
EXPOSE 8010
CMD ["uvicorn", "apf_slack.main:app", "--host", "0.0.0.0", "--port", "8010"]
