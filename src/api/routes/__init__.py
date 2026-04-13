from fastapi import APIRouter

from .cities import router as cities_router
from .config import router as config_router
from .items import router as items_router

api_router = APIRouter()
api_router.include_router(items_router)
api_router.include_router(cities_router)
api_router.include_router(config_router)
