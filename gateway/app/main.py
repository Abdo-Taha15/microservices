from fastapi import FastAPI, Request, status, HTTPException, File, UploadFile, Depends
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from contextlib import asynccontextmanager

import os
import json
import pika

from config import init_db, set_connection, get_session

from GCP import upload, delete
from models import DeRequests, Status
from crud import (
    _create_de_request,
    _get_request_from_hash,
    _get_request_from_id,
    _update_de_request,
)
from tools import hash_file


origins = [
    "https://localhost",
    "http://localhost",
    "https://127.0.0.1",
    "http://127.0.0.1",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    global connection, channel
    connection, channel = await set_connection()
    yield
    connection.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/ocr")
async def ocr(
    request: Request,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):

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


@app.get("/ocr/")
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


@app.delete("/ocr/")
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
