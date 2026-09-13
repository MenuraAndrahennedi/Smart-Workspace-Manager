from fastapi import FastAPI
from backend.config.settings import FRONTEND_ORIGIN
from backend.middleware.error_handler import register_exception_handlers
from backend.routes.health_routes import router as health_router
from backend.routes.file_routes import router as file_router
from backend.routes.dashboard_route import router as dashboard_router
from backend.routes.analysis_routes import router as analysis_router
from backend.routes.cleaning_routes import router as cleaning_router
from backend.routes.report_routes import router as report_router
from backend.routes.xlsx_routes import router as xlsx_router
from backend.routes.settings_routes import router as settings_router
from backend.routes.auth_routes import router as auth_router

from fastapi.middleware.cors import CORSMiddleware


allowed_origins = [
    FRONTEND_ORIGIN 
]

# FastAPI application
app = FastAPI(
    title="Smart Workspace Manager API",
    summary="Smart Workspace Manager API connects the React frontend and the python backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(file_router)
app.include_router(dashboard_router)
app.include_router(analysis_router)
app.include_router(cleaning_router)
app.include_router(report_router)
app.include_router(xlsx_router)
app.include_router(settings_router)
app.include_router(auth_router)

register_exception_handlers(app)
