# Melody Vault v2
**An AI-Powered Music Analysis & Transcription Platform**

Melody Vault is a sophisticated audio processing pipeline designed to separate, 
analyze, and visualize musical components.

## Current Project Status: Phase 2a Complete
We have successfully implemented the core analysis engine and data validation 
layer. The system now processes raw audio stems into structured, synchronized 
JSON timelines.

## Technical Stack
* **Language:** Python 3.11.9 (managed via pyenv)
* **Environment:** WSL2 (Ubuntu)
* **Dependency Management:** Poetry
* **Audio Processing:** Librosa, NumPy
* **Data Validation:** Pydantic v2
* **Testing:** Pytest

## Project Architecture
The pipeline follows a modular "micro-service" style architecture:
* `services/analysis/`: Contains specialized scripts for different stems (Drums, Bass, Vocals, Other).
* `data/raw/`: Source audio files.
* `data/processed/`: Extracted features and JSON analysis reports.

## Analysis Pipeline Features
1. **Temporal Synchronization:** All features are extracted using a 100ms 
   hop length to ensure perfect alignment in the frontend visualizer.
2. **Drum Analysis:** Rhythmic onset detection and RMS energy tracking.
3. **Bass Analysis:** Fundamental frequency tracking (YIN algorithm) 
   converted to MIDI notes.
4. **Polyphonic Analysis (Other):** 12-bin Chromagram extraction for 
   harmonic content visualization.

## Running Tests
To ensure data integrity and schema compliance, run:
```bash
export PYTHONPATH=$PYTHONPATH:.
poetry run pytest services/analysis/tests/