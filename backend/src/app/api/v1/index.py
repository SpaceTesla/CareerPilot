from fastapi import APIRouter

router = APIRouter(prefix="", tags=["index"])


@router.get("/")
def index_route():
    return {"message": "Welcome to CareerPilot API"}


@router.get("/health")
def health_check():
    return {"status": "OK"}
