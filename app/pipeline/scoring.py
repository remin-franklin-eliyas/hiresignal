from app.core.config import Settings, get_settings
from app.models.documents import ExtractedDocument
from app.models.rubric import JobRubric, RubricCriterion
from app.models.scoring import CandidateScore, CriterionScore, ScoringCriterionName
from app.pipeline.privacy import hash_candidate_identifier
from app.services.foundry_scoring import FoundryScoringClient, FoundryScoringError


class CandidateScoringError(RuntimeError):
    pass


class CandidateScoringService:
    def __init__(
        self,
        settings: Settings,
        foundry_client: FoundryScoringClient | None = None,
    ) -> None:
        self._settings = settings
        self._foundry_client = foundry_client or FoundryScoringClient(settings)

    async def score_document(
        self,
        document: ExtractedDocument,
        rubric: JobRubric,
        candidate_identifier: str,
    ) -> CandidateScore:
        candidate_hash = hash_candidate_identifier(candidate_identifier)
        stage_scores: dict[ScoringCriterionName, CriterionScore] = {}
        for criterion_name in ("skills_match", "experience_relevance", "role_fit"):
            criterion = self._get_criterion(rubric, criterion_name)
            stage_scores[criterion_name] = await self._score_criterion(
                criterion=criterion,
                cv_text=document.text,
                job_title=rubric.title,
            )

        overall_score = self._weighted_overall_score(rubric, stage_scores)
        return CandidateScore(
            candidate_hash=candidate_hash,
            job_id=rubric.job_id,
            rubric_version=rubric.version,
            skills_match=stage_scores["skills_match"],
            experience_relevance=stage_scores["experience_relevance"],
            role_fit=stage_scores["role_fit"],
            overall_score=overall_score,
            manual_review_required=False,
        )

    async def _score_criterion(
        self,
        criterion: RubricCriterion,
        cv_text: str,
        job_title: str,
    ) -> CriterionScore:
        try:
            return await self._foundry_client.score_criterion(criterion, cv_text, job_title)
        except FoundryScoringError as exc:
            if not self._settings.use_local_scoring_fallback:
                raise CandidateScoringError("Candidate scoring failed.") from exc
            return self._local_score_criterion(criterion, cv_text)

    @staticmethod
    def _local_score_criterion(criterion: RubricCriterion, cv_text: str) -> CriterionScore:
        normalized_text = cv_text.casefold()
        matched = [
            signal for signal in criterion.required_signals if signal.casefold() in normalized_text
        ]
        missing = [
            signal
            for signal in criterion.required_signals
            if signal.casefold() not in normalized_text
        ]
        score = round((len(matched) / len(criterion.required_signals)) * 100)
        if matched:
            reasoning = (
                f"Matched {len(matched)} of {len(criterion.required_signals)} "
                "required signals."
            )
        else:
            reasoning = "No required signals were found in the extracted CV text."
        return CriterionScore(
            criterion=criterion.name,  # type: ignore[arg-type]
            score=score,
            reasoning=reasoning,
            matched_signals=matched,
            missing_signals=missing,
        )

    @staticmethod
    def _get_criterion(rubric: JobRubric, name: ScoringCriterionName) -> RubricCriterion:
        for criterion in rubric.criteria:
            if criterion.name == name:
                return criterion
        raise CandidateScoringError(f"Rubric is missing criterion: {name}")

    @staticmethod
    def _weighted_overall_score(
        rubric: JobRubric,
        stage_scores: dict[ScoringCriterionName, CriterionScore],
    ) -> int:
        total = 0.0
        for criterion in rubric.criteria:
            if criterion.name in stage_scores:
                total += stage_scores[criterion.name].score * criterion.weight
        return round(total)


def get_candidate_scoring_service() -> CandidateScoringService:
    settings = get_settings()
    return CandidateScoringService(settings=settings, foundry_client=FoundryScoringClient(settings))
