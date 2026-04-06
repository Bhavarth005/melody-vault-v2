import uuid
import aiofiles
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
import redis

app = FastAPI(title="Melody Vault API")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    """
    Receives an audio file, generates a unique ID,
    and saves it asynchronously to the data/raw directory.
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

    return {"saved_as": safe_filename}


@app.get("/ping-redis")
def ping_redis():
    """Temporary endpoint to test Docker networking."""
    try:
        # Docker automatically resolves 'redis' to the redis container's IP
        r = redis.Redis(host="redis", port=6379)
        return {"redis_ping": r.ping()}
    except Exception as e:
        return {"error": str(e)}
