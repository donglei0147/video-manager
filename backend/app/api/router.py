from fastapi import APIRouter

from app.api import categories, health, jobs, scan_folders, system, tags, theme_backgrounds, videos

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(system.router)
api_router.include_router(scan_folders.router)
api_router.include_router(categories.router)
api_router.include_router(tags.router)
api_router.include_router(theme_backgrounds.router)
api_router.include_router(videos.router)
api_router.include_router(jobs.router)
