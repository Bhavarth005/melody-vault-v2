import pytest
from pydantic import ValidationError
from services.analysis.schemas import StemAnalysisResult


def test_stem_analysis_valid_data():
    data = {
        "stem": "drums",
        "duration_ms": 1000.0,
        "rms_timeline": [{"t_ms": 0.0, "rms": 0.5}],
        "onsets": [],
    }

    result = StemAnalysisResult(**data)

    assert result.stem == "drums"
    assert len(result.rms_timeline) == 1
    assert result.notes is None


def test_stem_analysis_missing_field():
    incomplete_data = {"duration_ms": 1000.0, "rms_timeline": []}

    with pytest.raises(ValidationError):
        StemAnalysisResult(**incomplete_data)
