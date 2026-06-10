import json

import pytest

from app.pipeline.rubric import RubricLoader, RubricLoadError


def valid_rubric_payload() -> dict:
    return {
        "job_id": "backend-ai-engineer-2026-06",
        "version": "2026.06.10",
        "title": "Backend AI Engineer",
        "criteria": [
            {"name": "skills_match", "weight": 0.4, "required_signals": ["Python"]},
            {"name": "experience_relevance", "weight": 0.35, "required_signals": ["APIs"]},
            {"name": "role_fit", "weight": 0.25, "required_signals": ["communication"]},
        ],
    }


def test_loads_valid_job_rubric(tmp_path) -> None:
    rubric_path = tmp_path / "rubric.json"
    rubric_path.write_text(json.dumps(valid_rubric_payload()), encoding="utf-8")

    rubric = RubricLoader(rubric_path).load()

    assert rubric.job_id == "backend-ai-engineer-2026-06"
    assert rubric.version == "2026.06.10"


def test_rejects_rubric_with_missing_required_criterion(tmp_path) -> None:
    payload = valid_rubric_payload()
    payload["criteria"] = payload["criteria"][:-1]
    rubric_path = tmp_path / "rubric.json"
    rubric_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RubricLoadError):
        RubricLoader(rubric_path).load()


def test_rejects_rubric_with_invalid_weight_total(tmp_path) -> None:
    payload = valid_rubric_payload()
    payload["criteria"][0]["weight"] = 0.2
    rubric_path = tmp_path / "rubric.json"
    rubric_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RubricLoadError):
        RubricLoader(rubric_path).load()

