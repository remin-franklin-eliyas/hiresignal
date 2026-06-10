from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.scoring import CandidateScore, CriterionScore


class CandidateScoreAuditRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_hash: str = Field(min_length=64, max_length=64)
    source_event_hash: str | None = Field(default=None, min_length=64, max_length=64)
    job_id: str = Field(min_length=1)
    rubric_version: str = Field(min_length=1)
    pipeline_version: str = Field(min_length=1)
    overall_score: int = Field(ge=0, le=100)
    skills_match: CriterionScore
    experience_relevance: CriterionScore
    role_fit: CriterionScore
    manual_review_required: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def from_candidate_score(
        cls,
        score: CandidateScore,
        pipeline_version: str,
        source_event_hash: str | None = None,
    ) -> "CandidateScoreAuditRecord":
        return cls(
            candidate_hash=score.candidate_hash,
            source_event_hash=source_event_hash,
            job_id=score.job_id,
            rubric_version=score.rubric_version,
            pipeline_version=pipeline_version,
            overall_score=score.overall_score,
            skills_match=score.skills_match,
            experience_relevance=score.experience_relevance,
            role_fit=score.role_fit,
            manual_review_required=score.manual_review_required,
        )

