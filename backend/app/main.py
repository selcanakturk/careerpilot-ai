from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.analyses import router as analyses_router
from app.api.routes.cv import router as cv_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.roadmaps import router as roadmaps_router
from app.api.routes.uploads import router as uploads_router
from app.core.config import get_settings
from app.services.jobs.provider_registry import log_provider_configuration


settings = get_settings()
log_provider_configuration()

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(analyses_router, prefix="/api")
app.include_router(cv_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
app.include_router(roadmaps_router, prefix="/api")
app.include_router(uploads_router, prefix="/api")
