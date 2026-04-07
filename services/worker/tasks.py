import json
import redis
from celery import chord

from services.worker.celery_app import celery_app
from services.analysis import analyze_bass, analyze_drums, analyze_vocals, analyze_other

REDIS_HOST = "redis"
REDIS_PORT = 6379


def _redis_client() -> redis.Redis:
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)


def _progress_channel(job_id: str) -> str:
    return f"analysis_progress:{job_id}"


def _publish_progress(job_id: str, message: dict):
    _redis_client().publish(_progress_channel(job_id), json.dumps(message))


def launch_analysis_chord(job_id: str, stem_paths: dict[str, str]):
    """Launch fan-out/fan-in analysis with a Celery chord.

    Expected keys in stem_paths: vocals, drums, bass, other.
    """
    return chord(
        [
            process_vocals.s(stem_paths["vocals"], job_id),
            process_drums.s(stem_paths["drums"], job_id),
            process_bass.s(stem_paths["bass"], job_id),
            process_other.s(stem_paths["other"], job_id),
        ]
    )(aggregate_results.s(job_id))


@celery_app.task(name="analyze_vocals_task")
def process_vocals(file_path: str, job_id: str):
    _publish_progress(job_id, {"job_id": job_id, "stem": "vocals", "status": "started"})
    try:
        analysis = analyze_vocals.analyze(file_path)
    except Exception as e:
        _publish_progress(
            job_id,
            {"job_id": job_id, "stem": "vocals", "status": "failed", "error": str(e)},
        )
        return {"error": str(e), "stem": "vocals"}
    _publish_progress(
        job_id, {"job_id": job_id, "stem": "vocals", "status": "completed"}
    )
    return json.loads(analysis)


@celery_app.task(name="analyze_drums_task")
def process_drums(file_path: str, job_id: str):
    _publish_progress(job_id, {"job_id": job_id, "stem": "drums", "status": "started"})
    try:
        analysis = analyze_drums.analyze(file_path)
    except Exception as e:
        _publish_progress(
            job_id,
            {"job_id": job_id, "stem": "drums", "status": "failed", "error": str(e)},
        )
        return {"error": str(e), "stem": "drums"}
    _publish_progress(
        job_id, {"job_id": job_id, "stem": "drums", "status": "completed"}
    )
    return json.loads(analysis)


@celery_app.task(name="analyze_bass_task")
def process_bass(file_path: str, job_id: str):
    _publish_progress(job_id, {"job_id": job_id, "stem": "bass", "status": "started"})
    try:
        analysis = analyze_bass.analyze(file_path)
    except Exception as e:
        _publish_progress(
            job_id,
            {"job_id": job_id, "stem": "bass", "status": "failed", "error": str(e)},
        )
        return {"error": str(e), "stem": "bass"}
    _publish_progress(job_id, {"job_id": job_id, "stem": "bass", "status": "completed"})
    return json.loads(analysis)


@celery_app.task(name="analyze_other_task")
def process_other(file_path: str, job_id: str):
    _publish_progress(job_id, {"job_id": job_id, "stem": "other", "status": "started"})
    try:
        analysis = analyze_other.analyze(file_path)
    except Exception as e:
        _publish_progress(
            job_id,
            {"job_id": job_id, "stem": "other", "status": "failed", "error": str(e)},
        )
        return {"error": str(e), "stem": "other"}
    _publish_progress(
        job_id, {"job_id": job_id, "stem": "other", "status": "completed"}
    )
    return json.loads(analysis)


@celery_app.task(name="aggregate_results")
def aggregate_results(stem_results: list[dict], job_id: str):
    combined: dict[str, dict] = {}
    for result in stem_results:
        stem = str(result.get("stem", "unknown")).lower()
        combined[stem] = result

    payload = {"job_id": job_id, "status": "completed", "results": combined}
    _redis_client().set(f"analysis:{job_id}", json.dumps(payload))
    _publish_progress(
        job_id, {"job_id": job_id, "status": "completed", "type": "aggregate_ready"}
    )
    return payload
