from fastapi import APIRouter

router = APIRouter()

@router.get("/streamers")
def get_streamers():
    return {"status": "ok"}
