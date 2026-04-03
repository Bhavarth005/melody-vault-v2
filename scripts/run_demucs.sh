#!/bin/bash

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

echo "Done. Stems saved to: $OUTPUT_ABS"
