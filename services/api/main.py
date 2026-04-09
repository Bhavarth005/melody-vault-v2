import asyncio
import uuid
import json
import aiofiles
from pathlib import Path
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
import redis
from pydantic import BaseModel
from services.worker.tasks import launch_analysis_chord
from services.worker.tasks import run_demucs_task
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


app = FastAPI(title="Melody Vault API")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
STEMS_DATA_DIR = BASE_DIR / "data" / "stems"
DEMUCS_SCRIPT = BASE_DIR / "scripts" / "run_demucs.sh"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
STEMS_DATA_DIR.mkdir(parents=True, exist_ok=True)
redis_client = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "frontend")), name="static")


class StartAnalysisRequest(BaseModel):
    job_id: str
    stem_dir: str
    extension: str = ".mp3"


def get_redis_client():
    return redis.Redis(host="redis", port=6379, db=0, decode_responses=True)


@app.get("/")
def serve_frontend():
    return FileResponse(str(BASE_DIR / "frontend" / "analyzer.html"))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload", status_code=202)
async def upload_audio(file: UploadFile = File(...)):
    """
    Receives an audio file, generates a unique ID,
    saves it, and offloads Demucs & Analysis to Celery.
    """
    extension = Path(file.filename).suffix.lower()
    if extension not in [".mp3", ".wav"]:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}{extension}"
    save_path = RAW_DATA_DIR / safe_filename

    try:
        async with aiofiles.open(save_path, "wb") as out_file:
            while content := await file.read(1024 * 1024):
                await out_file.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")
    finally:
        await file.close()

    redis_client = get_redis_client()
    redis_client.set(
        f"analysis:{file_id}",
        json.dumps(
            {"job_id": file_id, "status": "demucs_queued", "saved_as": safe_filename}
        ),
    )

    run_demucs_task.delay(str(save_path), file_id)

    return {"job_id": file_id, "status": "demucs_queued", "saved_as": safe_filename}


@app.get("/ping-redis")
def ping_redis():
    """Temporary endpoint to test Docker networking."""
    try:
        r = redis.Redis(host="redis", port=6379)
        return {"redis_ping": r.ping()}
    except Exception as e:
        return {"error": str(e)}


@app.get("/result/{job_id}")
def get_result(job_id: str):
    value = redis_client.get(f"analysis:{job_id}")
    if not value:
        return {"job_id": job_id, "status": "pending"}
    return json.loads(value)


@app.websocket("/ws/{job_id}")
async def get_analysis_progress(websocket: WebSocket, job_id: str):
    await websocket.accept()
    pubsub = redis_client.pubsub()
    channel = f"analysis_progress:{job_id}"
    pubsub.subscribe(channel)
    try:
        while True:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

            if message and message.get("type") == "message":
                data = message.get("data")
                await websocket.send_text(data)

                parsed = json.loads(data)
                if parsed.get("type") == "aggregate_ready":
                    break

            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        pass
    finally:
        pubsub.unsubscribe(channel)
        pubsub.close()
        await websocket.close()


@app.post("/analysis/start")
def start_analysis(req: StartAnalysisRequest):
    existing = redis_client.get(f"analysis:{req.job_id}")
    if not existing:
        raise HTTPException(
            status_code=404, detail="Unknown job_id. Upload file first."
        )

    stem_dir = Path(req.stem_dir)
    if not stem_dir.is_absolute():
        stem_dir = BASE_DIR / stem_dir

    ext = req.extension if req.extension.startswith(".") else f".{req.extension}"
    stem_paths = {
        "vocals": str(stem_dir / f"vocals{ext}"),
        "drums": str(stem_dir / f"drums{ext}"),
        "bass": str(stem_dir / f"bass{ext}"),
        "other": str(stem_dir / f"other{ext}"),
    }

    missing = [name for name, p in stem_paths.items() if not Path(p).exists()]
    if missing:
        raise HTTPException(
            status_code=400, detail=f"Missing stems: {', '.join(missing)}"
        )

    redis_client.set(
        f"analysis:{req.job_id}",
        json.dumps({"job_id": req.job_id, "status": "queued"}),
    )
    chord_result = launch_analysis_chord(req.job_id, stem_paths)
    return {"job_id": req.job_id, "status": "queued", "chord_id": chord_result.id}
