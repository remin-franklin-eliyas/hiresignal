from pydantic import BaseModel, Field, model_validator

REQUIRED_CRITERIA = {"skills_match", "experience_relevance", "role_fit"}


class RubricCriterion(BaseModel):
    name: str
    weight: float = Field(gt=0, le=1)
    required_signals: list[str] = Field(min_length=1)


class JobRubric(BaseModel):
    job_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    title: str = Field(min_length=1)
    criteria: list[RubricCriterion] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scoring_contract(self) -> "JobRubric":
        names = {criterion.name for criterion in self.criteria}
        missing = REQUIRED_CRITERIA - names
        if missing:
            raise ValueError(f"Rubric missing required criteria: {', '.join(sorted(missing))}")

        total_weight = sum(criterion.weight for criterion in self.criteria)
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError("Rubric criteria weights must sum to 1.0.")

        return self

