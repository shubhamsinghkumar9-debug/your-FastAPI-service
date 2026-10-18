# FastAPI Prometheus + JSON Logs service

## Deploy on Render (no Docker required)
1. Upload these files to a GitHub repository.
2. In Render, choose New > Blueprint and connect the repository (or create a Python Web Service).
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Deploy.

## Endpoints
- `GET /work?n=5`
- `GET /metrics`
- `GET /healthz`
- `GET /logs/tail?limit=20`

`http_requests_total` is a real Prometheus counter updated by middleware for every HTTP request. Request logs are emitted as JSON and retained in a bounded in-memory tail buffer. The log tail is per running process and may reset on restart.
