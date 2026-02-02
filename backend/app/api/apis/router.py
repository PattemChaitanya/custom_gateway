from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
from typing import List

from ...db.connector import get_db
from . import schemas
from . import crud


router = APIRouter(prefix="/apis", tags=["apis"])


@router.post("/", response_model=schemas.APIMeta, status_code=status.HTTP_201_CREATED)
async def create_api(payload: schemas.CreateAPIRequest, db: AsyncSession = Depends(get_db)):
    try:
        api = await crud.create_api(db, payload.model_dump())
        return api
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/", response_model=List[schemas.APIMeta])
async def list_apis(db: AsyncSession = Depends(get_db)):
    return await crud.list_apis(db)


@router.get("/{api_id}", response_model=schemas.APIMeta)
async def get_api(api_id: int, db: AsyncSession = Depends(get_db)):
    api = await crud.get_api(db, api_id)
    if not api:
        raise HTTPException(status_code=404, detail="API not found")
    return api


@router.put("/{api_id}", response_model=schemas.APIMeta)
async def update_api(api_id: int, payload: schemas.UpdateAPIRequest, db: AsyncSession = Depends(get_db)):
    api = await crud.get_api(db, api_id)
    if not api:
        raise HTTPException(status_code=404, detail="API not found")
    patch = payload.model_dump(exclude_none=True)
    api = await crud.update_api(db, api, patch)
    return api


@router.delete("/{api_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api(api_id: int, db: AsyncSession = Depends(get_db)):
    api = await crud.get_api(db, api_id)
    if not api:
        raise HTTPException(status_code=404, detail="API not found")
    await crud.delete_api(db, api)
    return None
