import json
import redis
import subprocess
from pathlib import Path
from celery import chord

from services.worker.celery_app import celery_app
from services.analysis import analyze_bass, analyze_drums, analyze_vocals, analyze_other

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STEMS_DATA_DIR = BASE_DIR / "data" / "stems"
DEMUCS_SCRIPT = BASE_DIR / "scripts" / "run_demucs.sh"

REDIS_HOST = "redis"
REDIS_PORT = 6379


def _redis_client() -> redis.Redis:
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)


def _progress_channel(job_id: str) -> str:
    return f"analysis_progress:{job_id}"


def _publish_progress(job_id: str, message: dict):
    _redis_client().publish(_progress_channel(job_id), json.dumps(message))


def _resolve_demucs_output(job_id: str) -> tuple[Path, str]:
    """Find the directory containing 4 stems and infer extension."""
    output_root = STEMS_DATA_DIR / job_id
    candidates = [
        (output_root / "mdx_extra_q" / job_id, ".wav"),
        (output_root / "mdx_extra_q" / job_id, ".mp3"),
        (output_root / job_id, ".wav"),
        (output_root / job_id, ".mp3"),
    ]

    for stem_dir, ext in candidates:
        if all(
            (stem_dir / f"{stem}{ext}").exists()
            for stem in ["vocals", "drums", "bass", "other"]
        ):
            return stem_dir, ext

    for ext in [".wav", ".mp3"]:
        for vocals_file in output_root.rglob(f"vocals{ext}"):
            stem_dir = vocals_file.parent
            if all(
                (stem_dir / f"{stem}{ext}").exists()
                for stem in ["vocals", "drums", "bass", "other"]
            ):
                return stem_dir, ext

    raise FileNotFoundError("Demucs finished but expected stem files were not found.")


def launch_analysis_chord(job_id: str, stem_paths: dict[str, str]):
    """Launch fan-out/fan-in analysis with a Celery chord."""
    return chord(
        [
            process_vocals.s(stem_paths["vocals"], job_id),
            process_drums.s(stem_paths["drums"], job_id),
            process_bass.s(stem_paths["bass"], job_id),
            process_other.s(stem_paths["other"], job_id),
        ]
    )(aggregate_results.s(job_id))


@celery_app.task(name="run_demucs_task")
def run_demucs_task(save_path: str, job_id: str):
    """Runs Demucs in the background and then triggers the analysis chord."""
    _publish_progress(
        job_id, {"job_id": job_id, "stage": "demucs", "status": "started"}
    )

    demucs_output_root = STEMS_DATA_DIR / job_id

    try:
        subprocess.run(
            ["bash", str(DEMUCS_SCRIPT), save_path, str(demucs_output_root)],
            cwd=str(BASE_DIR),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        error_msg = exc.stderr[-2000:] if exc.stderr else str(exc)
        print(
            f"\n--- DEMUCS FATAL CRASH ---\n{error_msg}\n--------------------------\n"
        )
        _publish_progress(
            job_id,
            {
                "job_id": job_id,
                "stage": "demucs",
                "status": "failed",
                "error": error_msg,
            },
        )
        _redis_client().set(
            f"analysis:{job_id}",
            json.dumps(
                {
                    "job_id": job_id,
                    "status": "failed",
                    "stage": "demucs",
                    "error": error_msg,
                }
            ),
        )
        return {"error": "Demucs failed"}

    try:
        stem_dir, stem_ext = _resolve_demucs_output(job_id)
    except FileNotFoundError as exc:
        _publish_progress(
            job_id,
            {
                "job_id": job_id,
                "stage": "demucs",
                "status": "failed",
                "error": str(exc),
            },
        )
        _redis_client().set(
            f"analysis:{job_id}",
            json.dumps(
                {
                    "job_id": job_id,
                    "status": "failed",
                    "stage": "demucs",
                    "error": str(exc),
                }
            ),
        )
        return {"error": "Stem resolution failed"}

    stem_paths = {
        "vocals": str(stem_dir / f"vocals{stem_ext}"),
        "drums": str(stem_dir / f"drums{stem_ext}"),
        "bass": str(stem_dir / f"bass{stem_ext}"),
        "other": str(stem_dir / f"other{stem_ext}"),
    }

    _publish_progress(
        job_id, {"job_id": job_id, "stage": "demucs", "status": "completed"}
    )

    _redis_client().set(
        f"analysis:{job_id}",
        json.dumps(
            {
                "job_id": job_id,
                "status": "analyzing",
                "stem_dir": str(stem_dir),
                "stem_ext": stem_ext,
            }
        ),
    )

    chord_result = launch_analysis_chord(job_id, stem_paths)
    return {"job_id": job_id, "status": "demucs_completed", "chord_id": chord_result.id}


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
        if "error" in result:
            combined[result.get("stem", "unknown")] = result
        else:
            combined[result.get("stem")] = result

    payload = {"job_id": job_id, "status": "completed", "results": combined}
    _redis_client().set(f"analysis:{job_id}", json.dumps(payload))
    _publish_progress(
        job_id, {"job_id": job_id, "status": "completed", "type": "aggregate_ready"}
    )
    return payload
