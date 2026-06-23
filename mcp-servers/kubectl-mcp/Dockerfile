FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir "mcp[cli]" duckdb
COPY server.py .
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "server.py"]
