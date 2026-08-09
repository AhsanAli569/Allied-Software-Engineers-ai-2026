import logging
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("ase_ai.errors")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Drop `ctx`: pydantic populates it with the raw exception object from a custom
        # @model_validator (e.g. a plain ValueError), which json.dumps can't serialize and
        # would otherwise turn a clean 422 into an unrelated 500.
        errors = [{k: v for k, v in error.items() if k != "ctx"} for error in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": "Invalid request", "errors": errors})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        error_id = uuid.uuid4().hex[:12]
        logger.exception("unhandled_error", extra={"error_id": error_id, "path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={
                "detail": "ASE AI is temporarily unable to answer. Please try again.",
                "error_id": error_id,
            },
        )
