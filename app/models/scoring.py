from typing import Literal

from pydantic import BaseModel, Field

ScoringCriterionName = Literal["skills_match", "experience_relevance", "role_fit"]


class CriterionScore(BaseModel):
    criterion: ScoringCriterionName
    score: int = Field(ge=0, le=100)
    reasoning: str = Field(min_length=1)
    matched_signals: list[str] = Field(default_factory=list)
    missing_signals: list[str] = Field(default_factory=list)


class CandidateScore(BaseModel):
    candidate_hash: str = Field(min_length=32)
    job_id: str
    rubric_version: str
    skills_match: CriterionScore
    experience_relevance: CriterionScore
    role_fit: CriterionScore
    overall_score: int = Field(ge=0, le=100)
    manual_review_required: bool = False


class ScoringRequest(BaseModel):
    candidate_hash: str = Field(min_length=32)
    cv_text: str = Field(min_length=1)
    job_id: str
    rubric_version: str
