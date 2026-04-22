from __future__ import annotations

import json
import time
import uuid
from pathlib import Path


DATA_DIR = Path("data")
JOBS_DIR = DATA_DIR / "render_jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)


def _path(job_id: str) -> Path:
    safe = "".join(c for c in (job_id or "") if c.isalnum() or c in ("-", "_"))[:80]
    return JOBS_DIR / f"{safe}.json"


def create_render_job(payload: dict) -> dict:
    job_id = uuid.uuid4().hex
    row = {
        "id": job_id,
        "status": "queued",
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
        "payload": payload or {},
        "output_url": "",
        "note": "MVP queue: use client-side recording while server renderer is pending.",
    }
    _path(job_id).write_text(json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8")
    return row


def get_render_job(job_id: str) -> dict | None:
    p = _path(job_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

