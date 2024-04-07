import os
import json
import pika

from fastapi import Depends, HTTPException, APIRouter, Request, status, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session

from app.config import get_session, get_channel
from app.GCP import upload, delete
from app.models import DeRequests, Status
from app.crud import (
    _create_de_request,
    _get_request_from_hash,
    _get_request_from_id,
    _update_de_request,
)
from app.tools import hash_file

router = APIRouter(
    prefix="/ocr", tags=["ocr"], responses={404: {"description": "Not found"}}
)


@router.post("")
async def ocr(
    request: Request,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    connection, channel = get_channel()
    try:
        hash = hash_file(file.file)
        de_request = _get_request_from_hash(hash, session)
        if de_request:
            de_request = _update_de_request(de_request, {"duplicate": True}, session)
        else:
            unique_filename = hash + "." + file.filename.split(".")[-1]
            blob = upload(file.file, unique_filename, file.content_type)
            de_request: DeRequests = _create_de_request(
                {
                    "original_filename": file.filename,
                    "file_hash": hash,
                    "unique_filename": unique_filename,
                    "file_url": blob.public_url,
                    "ocr_status": Status.PENDING,
                    "de_status": Status.PENDING,
                    "status": Status.PENDING,
                },
                session,
            )
    except:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "data": {}, "message": "Failed to upload file"},
        )
    try:
        message = {
            "request_id": de_request.id,
            "file_hash": hash,
        }
        de_request = _update_de_request(de_request, {"request_body": message}, session)
        channel.basic_publish(
            exchange="",
            routing_key=os.getenv("OCR_QUEUE"),
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            ),
        )

        response = JSONResponse(
            content={
                "success": True,
                "data": jsonable_encoder(de_request),
                "message": "message sent",
            },
            status_code=status.HTTP_201_CREATED,
        )
        session.commit()
        connection.close()
        return response
    except Exception as err:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": "Internal Server Error",
                "detail": err.__str__(),
            },
        )


@router.put("/")
async def update_ocr_request(
    request: Request,
    request_id: int,
    data: dict,
    session: Session = Depends(get_session),
):
    de_request = _get_request_from_id(request_id, session)
    if not de_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "data": {}, "message": "Request not found"},
        )
    try:
        de_request = _update_de_request(de_request, data, session)
    except:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "data": {},
                "message": "Failed to update request",
            },
        )
    try:
        response = JSONResponse(
            content={
                "success": True,
                "data": jsonable_encoder(de_request),
                "message": "Request updated",
            },
            status_code=status.HTTP_202_ACCEPTED,
        )
        session.commit()
        return response
    except Exception as err:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": "Internal Server Error",
                "detail": err.__str__(),
            },
        )
