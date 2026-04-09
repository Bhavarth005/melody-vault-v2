import argparse
import json
from pathlib import Path
from services.analysis import analyze_drums, analyze_bass, analyze_other, analyze_vocals
import os


def main():
    """
    Orchestrates the full four-stem analysis pipeline for a music track.

    Reads a directory containing Demucs-separated stems, executes individual
    analysis modules for vocals, drums, bass, and other, and aggregates
    the results into a single comprehensive JSON report stored in the
    data/processed directory.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=str, help="Path to all the stem files")
    parser.add_argument(
        "-e", "--ext", type=str, default=".wav", help="Stem file extension"
    )
    args = parser.parse_args()

    if not os.path.exists(args.path):
        return json.dumps({"error": "Stem files path doesn't exist"})

    input_path = Path(args.path)
    track_name = input_path.name if input_path.name else input_path.parent.name

    stem_analysis = {
        "drums": json.loads(
            analyze_drums.analyze(str(input_path / f"drums{args.ext}"))
        ),
        "bass": json.loads(analyze_bass.analyze(str(input_path / f"bass{args.ext}"))),
        "other": json.loads(
            analyze_other.analyze(str(input_path / f"other{args.ext}"))
        ),
        "vocals": json.loads(
            analyze_vocals.analyze(str(input_path / f"vocals{args.ext}"))
        ),
    }

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    output_dir = BASE_DIR / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)
    save_path = output_dir / f"{track_name}_analysis.json"

    with open(save_path, "w") as f:
        json.dump(stem_analysis, f, indent=2)

    print(f"--- Analysis Complete! Saved to: {save_path} ---")


if __name__ == "__main__":
    main()
