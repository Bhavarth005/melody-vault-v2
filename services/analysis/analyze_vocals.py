# This is just temporary analysis of vocals, it will be replaced by Deep Learning networks

import json
import argparse
import os
import numpy as np
from pydantic import ValidationError
from services.analysis.schemas import StemAnalysisResult
import librosa


def analyze(stem_path: str):
    y, sr = librosa.load(stem_path)
    samples_per_100_ms = int(sr * 0.1)
    rms_array = librosa.feature.rms(
        y=y, frame_length=samples_per_100_ms, hop_length=samples_per_100_ms
    )[0]

    rms_timeline = []

    for i, rms_val in enumerate(rms_array):
        t_ms = i * 100
        rms_timeline.append({"t_ms": t_ms, "rms": float(rms_val)})

    pitch = librosa.yin(
        y,
        fmin=librosa.note_to_hz("C3"),
        fmax=librosa.note_to_hz("C6"),
        hop_length=samples_per_100_ms,
    )

    notes_list = []
    duration_ms = len(y) / sr * 1000

    for i, hz in enumerate(pitch):
        if not np.isnan(hz) and hz > 0:
            t_ms = i * 100
            midi = int(librosa.hz_to_midi(hz))

            notes_list.append(
                {
                    "onset_ms": float(t_ms),
                    "pitch_midi": midi,
                    "pitch_hz": float(hz),
                    "duration_ms": 100.0,
                }
            )

    try:
        result_obj = StemAnalysisResult(
            stem="vocals",
            duration_ms=duration_ms,
            rms_timeline=rms_timeline,
            notes=notes_list,
            chroma_timeline=None,
        )
        return result_obj.model_dump_json()

    except ValidationError as e:
        return json.dumps({"error": f"Invalid Schema: {str(e)}"})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=str, help="Enter path for the stem")

    args = parser.parse_args()
    if not os.path.exists(args.path):
        print(json.dumps({"error": "File path does not exist."}))
        return

    stem_analysis = analyze(args.path)
    return stem_analysis


if __name__ == "__main__":
    main()
