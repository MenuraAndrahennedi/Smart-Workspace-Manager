import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.services.analysis_service import CSVAnalysisError, CSVLimitError
from backend.services.file_service import UploadValidationError
from backend.services.cleaning_service import DataCleaningError
from backend.services.report_service import ReportGenerationError
from backend.services.xlsx_to_csv_service import XLSXConversionError
from backend.services.visualization_service import VisualizationError
from backend.database.repositories import ResourceForbiddenError

logger = logging.getLogger(__name__)


def _validation_error_message(exc: RequestValidationError) -> str:
    messages: list[str] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ()))
        message = error.get("msg", "Invalid value")
        messages.append(f"{location}: {message}" if location else message)
    return "; ".join(messages) or "The request data is invalid."

def register_exception_handlers(app: FastAPI):
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ):
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation Error",
                "message": _validation_error_message(exc),
            },
        )

    @app.exception_handler(Exception)
    async def app_exception_handler(request: Request, exc: Exception):
        logger.exception("Application error: %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code= 500,
            content={"error":"Internal Server Error",
                     "message":"An unexpected server error occurred."
                    }
        )

    @app.exception_handler(FileNotFoundError)
    async def file_not_found_handler(request: Request, exc: FileNotFoundError):
        return JSONResponse(
            status_code=404,
            content={
                "error":"Not Found",
                "message": str(exc),
            },
        )

    @app.exception_handler(ResourceForbiddenError)
    async def resource_forbidden_handler(
        request: Request,
        exc: ResourceForbiddenError,
    ):
        return JSONResponse(
            status_code=403,
            content={
                "error": "Forbidden",
                "message": str(exc),
            },
        )

    @app.exception_handler(UploadValidationError)
    async def upload_validation_handler(request: Request, exc: UploadValidationError):
        return JSONResponse(
            status_code=400,
            content={
                "error":"Bad Request",
                "message": str(exc),
            },
        )

    @app.exception_handler(CSVAnalysisError)
    async def analysis_error_handler(request: Request, exc: CSVAnalysisError):
        return JSONResponse(
            status_code=400,
            content={
                "error":"Bad Request",
                "message": str(exc),
            },
        )

    @app.exception_handler(CSVLimitError)
    async def analysis_limit_error_handler(request: Request, exc: CSVLimitError):
        return JSONResponse(
            status_code=413,
            content={
                "error":"Analysis Limit Exceeded",
                "message": str(exc),
            },
        )

    @app.exception_handler(DataCleaningError)
    async def data_cleaning_error_handler(request: Request, exc: DataCleaningError):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Bad Request",
                "message": str(exc),
            },
        )

    @app.exception_handler(ReportGenerationError)
    async def report_generation_error_handler(
        request: Request,
        exc: ReportGenerationError,
    ):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Bad Request",
                "message": str(exc),
            },
        )

    @app.exception_handler(VisualizationError)
    async def visualization_error_handler(
        request: Request,
        exc: VisualizationError,
    ):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Bad Request",
                "message": str(exc),
            },
        )

    @app.exception_handler(XLSXConversionError)
    async def xlsx_conversion_error_handler(request: Request, exc: XLSXConversionError):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Bad Request",
                "message": str(exc),
            },
        )
        
    
