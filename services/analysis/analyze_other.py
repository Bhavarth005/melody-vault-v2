import json
import argparse
import os
from pydantic import ValidationError
from schemas import StemAnalysisResult
import librosa


def analyze(stem_path: str) -> str:
    y, sr = librosa.load(stem_path)
    samples_per_100_ms = int(sr * 0.1)
    rms_array = librosa.feature.rms(
        y=y, frame_length=samples_per_100_ms, hop_length=samples_per_100_ms
    )[0]

    rms_timeline = []

    for i, rms_val in enumerate(rms_array):
        t_ms = i * 100
        rms_timeline.append({"t_ms": t_ms, "rms": float(rms_val)})

    chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=samples_per_100_ms)
    duration_ms = len(y) / sr * 1000

    pitch_names = librosa.midi_to_note(range(12), octave=False)

    chroma_timeline = []
    for i in range(chroma.shape[1]):

        t_ms = float(i * 100)

        energy_dict = {pitch_names[j]: float(chroma[j, i]) for j in range(12)}
        chroma_timeline.append({"t_ms": t_ms, "energy": energy_dict})

    try:
        result_obj = StemAnalysisResult(
            stem="other",
            duration_ms=duration_ms,
            rms_timeline=rms_timeline,
            onsets=[],
            chroma_timeline=chroma_timeline,
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
    print(stem_analysis)


if __name__ == "__main__":
    main()
