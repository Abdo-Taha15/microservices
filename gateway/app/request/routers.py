import os
import json
import pika

from fastapi import Depends, HTTPException, APIRouter, Request, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session

from app.config import get_session, get_channel
from app.GCP import delete
from app.crud import (
    _get_request_from_id,
)

router = APIRouter(
    prefix="/requests", tags=["requests"], responses={404: {"description": "Not found"}}
)


@router.get("/")
async def get_request(
    request: Request, request_id: int, session: Session = Depends(get_session)
):
    try:
        de_request = _get_request_from_id(request_id, session)
        if not de_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "data": {}, "message": "Request not found"},
            )
        response = JSONResponse(
            content={
                "success": True,
                "data": jsonable_encoder(de_request),
                "message": "Request found",
            },
            status_code=status.HTTP_200_OK,
        )
        return response
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": "Internal Server Error",
                "detail": err.__str__(),
            },
        )


@router.delete("/")
async def delete_request(
    request: Request, request_id: int, session: Session = Depends(get_session)
):
    try:
        de_request = _get_request_from_id(request_id, session)
        if not de_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "data": {}, "message": "Request not found"},
            )
        delete(de_request.unique_filename)
        session.delete(de_request)
        session.commit()
        response = JSONResponse(
            content={
                "success": True,
                "data": {},
                "message": "Request deleted",
            },
            status_code=status.HTTP_202_ACCEPTED,
        )
        return response
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": "Internal Server Error",
                "detail": err.__str__(),
            },
        )
