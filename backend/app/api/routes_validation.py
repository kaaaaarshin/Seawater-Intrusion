"""Validation endpoint, separate from dataset generation."""

from __future__ import annotations

from fastapi import APIRouter

from ..schemas import ValidationRequest, ValidationResponse
from ..services.validation_service import run_validation

router = APIRouter(prefix="/api", tags=["validation"])


@router.post("/validate", response_model=ValidationResponse)
def validate(request: ValidationRequest | None = None) -> ValidationResponse:
    body = request or ValidationRequest()
    result = run_validation(correction_mode=body.correction_mode)
    return ValidationResponse(**result)
