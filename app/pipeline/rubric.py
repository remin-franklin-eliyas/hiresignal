import json
from pathlib import Path

from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.models.rubric import JobRubric


class RubricLoadError(RuntimeError):
    pass


class RubricLoader:
    def __init__(self, rubric_path: Path) -> None:
        self._rubric_path = rubric_path

    def load(self) -> JobRubric:
        try:
            payload = json.loads(self._rubric_path.read_text(encoding="utf-8"))
            return JobRubric.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
            raise RubricLoadError("Unable to load a valid job rubric.") from exc


def get_rubric_loader(settings: Settings | None = None) -> RubricLoader:
    resolved_settings = settings or get_settings()
    return RubricLoader(resolved_settings.job_rubric_path)

