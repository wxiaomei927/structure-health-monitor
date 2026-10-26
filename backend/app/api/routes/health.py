from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="服务存活探测")
def health():
    """探活接口"""
    return {"status": "ok"}
