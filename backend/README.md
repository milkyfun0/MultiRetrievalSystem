# Multi-modal Retrieval Backend Scaffold

A runnable FastAPI backend scaffold for the first version of the multi-modal retrieval system.

## What is included

- `POST /api/v1/search`
- `POST /api/v1/vectorize`
- `GET /api/v1/tasks/{job_id}`
- `POST/GET/PUT/DELETE /api/v1/stores*`
- `GET /api/v1/health`
- SQLite metadata storage
- simple vector index service with a NumPy fallback that mimics the required FAISS flow
- pseudo-async local jobs using a thread pool
- deterministic fake algorithm service for local tests

## Run locally

```bash
cd mmr_backend_scaffold
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

## Run tests

```bash
pytest -q
```

## Notes

- The scaffold keeps the API and data model aligned with the current backend design.
- `Text2Video` currently treats short video files as retrieval objects.
- `LongVideo` is reserved at the protocol layer but intentionally rejected in the current version.
- `algorithm_service.py` already provides an `HttpAlgorithmService` shell for connecting to the external algorithm gateway later.
- The local default uses `DeterministicAlgorithmService` so the project can run and be tested without the real model service.
