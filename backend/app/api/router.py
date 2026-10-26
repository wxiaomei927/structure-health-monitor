from fastapi import APIRouter, Depends

from app.api.routes.alert import router as alert_router
from app.api.routes.auth import router as auth_router
from app.api.routes.device import router as device_router
from app.api.routes.export import router as export_router
from app.api.routes.health import router as health_router
from app.api.routes.measurement import router as measurement_router
from app.api.routes.structure import imaging_router
from app.api.routes.structure import router as structure_router
from app.services.auth_service import require_login

# 上报接口免鉴权，其余接口一律要求登录
api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(structure_router, dependencies=[Depends(require_login)])
api_router.include_router(imaging_router, dependencies=[Depends(require_login)])
api_router.include_router(alert_router, dependencies=[Depends(require_login)])
api_router.include_router(device_router, dependencies=[Depends(require_login)])
api_router.include_router(export_router, dependencies=[Depends(require_login)])
api_router.include_router(measurement_router)
