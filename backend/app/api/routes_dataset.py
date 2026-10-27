"""Dataset generation and download endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from ..schemas import DatasetGenerateRequest, DatasetGenerateResponse
from ..services.dataset_service import create_dataset_zip, generate_dataset
from ..utils.errors import ApiError

router = APIRouter(prefix="/api/dataset", tags=["dataset"])


@router.post("/generate", response_model=DatasetGenerateResponse)
def generate(request: DatasetGenerateRequest | None = None) -> DatasetGenerateResponse:
    result = generate_dataset(request)
    return DatasetGenerateResponse(**result)


@router.get("/download")
def download() -> FileResponse:
    try:
        path = create_dataset_zip()
    except FileNotFoundError as exc:
        raise ApiError(
            "DATASET_NOT_FOUND",
            str(exc),
            status_code=404,
        ) from exc
    return FileResponse(
        path,
        media_type="application/zip",
        filename="seawater_intrusion_dataset.zip",
    )
