#!/bin/bash
set -euo pipefail

INPUT_PATH="$1"
OUTPUT_DIR="$2"

if [ -z "$INPUT_PATH" ] || [ -z "$OUTPUT_DIR" ]; then
    echo "Usage: $0 <input_audio_path> <output_dir>"
    exit 1
fi

INPUT_ABS=$(realpath "$INPUT_PATH")
INPUT_DIR=$(dirname "$INPUT_ABS")
INPUT_FILE=$(basename "$INPUT_ABS")
OUTPUT_ABS=$(realpath -m "$OUTPUT_DIR")

mkdir -p "$OUTPUT_ABS"

echo "Separating: $INPUT_FILE"
echo "Output to:  $OUTPUT_ABS"

if ! command -v docker >/dev/null 2>&1; then
    echo "Error: docker CLI not found in runtime environment."
    exit 127
fi

if [[ "$INPUT_ABS" == /app/* ]] && [[ -n "$HOSTNAME" ]]; then
    # Running from inside the API container: inherit mounted volumes from this container.
    docker run --rm \
        --entrypoint="" \
        --volumes-from "$HOSTNAME" \
        -v demucs_models:/data/models \
        xserrat/facebook-demucs:latest \
        python -m demucs \
        -n mdx_extra_q \
        -o "$OUTPUT_ABS" \
        "$INPUT_ABS"
else
    # Running directly on host.
    docker run --rm \
        --entrypoint="" \
        -v "$INPUT_DIR:/input" \
        -v "$OUTPUT_ABS:/output" \
        -v demucs_models:/data/models \
        xserrat/facebook-demucs:latest \
        python -m demucs \
        -n mdx_extra_q \
        -o /output \
        "/input/$INPUT_FILE"
fi

echo "Done. Stems saved to: $OUTPUT_ABS"
