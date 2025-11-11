from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_user():
    return {"user": "This is a user endpoint"}
