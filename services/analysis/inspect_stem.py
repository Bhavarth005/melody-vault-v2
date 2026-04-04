import argparse
from pathlib import Path
import librosa
import matplotlib.pyplot as plt
import numpy as np
import os
import json


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def analyse_audio(audio_path):
    """
    Loads an audio file and calculates key metrics.
    Returns a dictionary of the results.
    """
    y, sr = librosa.load(audio_path)
    analysis = {}
    analysis["duration_seconds"] = len(y) / sr
    analysis["sample_rate"] = sr
    rms = librosa.feature.rms(y=y)
    analysis["rms_mean"] = rms.mean()
    analysis["rms_max"] = rms.max()
    analysis["rms_min"] = rms.min()
    analysis["onset_count"] = len(librosa.onset.onset_detect(y=y, sr=sr, units="time"))
    yin = librosa.yin(y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"))
    analysis["dominant_pitch_hz"] = yin.mean()
    return y, sr, analysis


def plot_features(y, sr, output_dir, stem_name):
    """
    Generates and saves a clean, two-panel visualization.
    """
    plt.figure(figsize=(10, 6))

    plt.subplot(2, 1, 1)
    M = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)
    M_db = librosa.power_to_db(M, ref=np.max)
    librosa.display.specshow(M_db, sr=sr, x_axis="time", y_axis="mel")
    plt.colorbar(format="%+2.0f dB")
    plt.title(f"{stem_name} - Mel-Spectrogram")

    plt.subplot(2, 1, 2)
    rms = librosa.feature.rms(y=y)
    frames = np.arange(rms.shape[1])
    time_ms = ((frames * 512) / sr) * 1000

    plt.fill_between(time_ms, rms[0], color="skyblue", alpha=0.4)
    plt.plot(time_ms, rms[0], color="tab:blue", label="RMS Energy", linewidth=1.5)

    plt.xlabel("Time (ms)")
    plt.ylabel("RMS")
    plt.title("RMS vs time")
    plt.grid(True, alpha=0.3)
    plt.legend()

    plt.tight_layout()

    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, f"{stem_name}_plot.png")
    plt.savefig(save_path, dpi=150)
    print(f"Plot saved to {save_path}")

    plt.show()


def main():
    parser = argparse.ArgumentParser(
        description="Analyze an audio stem and output a JSON summary."
    )
    parser.add_argument("file_path", type=str, help="Path to the stem WAV/mp3 file")
    parser.add_argument(
        "--plot", action="store_true", help="Generate and save analysis plots"
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        type=str,
        default="../../data/processed/plots/",
        help="Output directory for saving plots.",
    )
    parser.add_argument("-n", "--name", type=str, help="Stem/Audio Name.")
    args = parser.parse_args()

    if not os.path.exists(args.file_path):
        print(json.dumps({"error": "File path does not exist."}))
        return

    y, sr, analysis = analyse_audio(args.file_path)
    analysis_json = json.dumps(analysis, cls=NumpyEncoder, indent=2)
    file_stem = Path(args.file_path).stem
    parent_dir = Path(args.file_path).parent.name
    json_filename = f"{parent_dir}_{file_stem}.json"

    json_path = os.path.join("../../data/processed/", json_filename)
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w") as f:
        f.write(analysis_json)
    print("JSON object saved to analysis.json")
    if args.plot:
        plot_features(y, sr, args.output_dir, args.name)


if __name__ == "__main__":
    main()
