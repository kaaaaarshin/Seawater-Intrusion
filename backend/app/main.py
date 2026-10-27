"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes_cases import router as cases_router
from .api.routes_dataset import router as dataset_router
from .api.routes_health import router as health_router
from .api.routes_simulation import router as simulation_router
from .api.routes_validation import router as validation_router
from .config import APP_VERSION, MODEL_VERSION, PAPER_DOI, PAPER_TITLE
from .utils.errors import ApiError

app = FastAPI(
    title="Seawater Intrusion Analytical Simulator",
    description=(
        "Confined coastal aquifer with a cutoff wall; constant inland freshwater flux. "
        "Based on Sun et al. (2026), Advances in Water Resources 212, 105301."
    ),
    version=APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": {
                "code": exc.code,
                "message": exc.message,
                "field": exc.field,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    first = errors[0] if errors else {}
    field = ".".join(str(part) for part in first.get("loc", [])[1:]) or None
    safe_errors = []
    for error in errors:
        safe = {
            key: value
            for key, value in error.items()
            if key != "ctx"
        }
        if "ctx" in error:
            safe["ctx"] = {
                key: str(value) if isinstance(value, BaseException) else value
                for key, value in error["ctx"].items()
            }
        safe_errors.append(safe)
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            {
                "detail": {
                    "code": "VALIDATION_ERROR",
                    "message": first.get("msg", "Invalid request"),
                    "field": field,
                    "errors": safe_errors,
                }
            }
        ),
    )


@app.get("/")
def root() -> dict:
    return {
        "name": "Seawater Intrusion Analytical Simulator",
        "app_version": APP_VERSION,
        "model_version": MODEL_VERSION,
        "paper": {"title": PAPER_TITLE, "doi": PAPER_DOI},
        "docs": "/docs",
    }


app.include_router(health_router)
app.include_router(simulation_router)
app.include_router(cases_router)
app.include_router(dataset_router)
app.include_router(validation_router)
