from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.services.audit_repository import get_audit_repository, AuditRepository
from app.core.config import get_settings

router = APIRouter()


@router.get("/explain", response_model=None)
async def explain_candidate(
    job_id: Annotated[str, Query(..., alias="jobId")],
    candidate_hash: Annotated[str, Query(..., alias="candidateHash")],
    audit_repository: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> dict:
    try:
        records = await audit_repository.list_by_job(job_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    for rec in records:
        if rec.candidate_hash == candidate_hash:
            return rec.model_dump()

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate audit record not found")
