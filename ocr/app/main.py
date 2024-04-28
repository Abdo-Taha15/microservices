# from paddleocr import PaddleOCR
import pika
import os
import sys
import json
import requests
from sqlmodel import Session
from dotenv import load_dotenv

from config import engine

from models import Status
from GCP import download
from crud import _get_request_from_hash
from tools import get_img, convert_pdf_to_image
from process import get_raw_text_from_pages, get_processed_text_from_pages

load_dotenv()


def main():
    # rabbitmq connection
    credentials = pika.PlainCredentials(
        os.getenv("RABBITMQ_USER"), os.getenv("RABBITMQ_PASSWORD")
    )
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            os.getenv("RABBITMQ_HOST"), os.getenv("RABBITMQ_PORT"), "/", credentials
        )
    )
    channel = connection.channel()

    def callback(ch, method, properties, body):
        with Session(engine, future=True) as session:
            headers = {"Content-Type": "application/json"}
            json_body = json.loads(body)
            de_request = _get_request_from_hash(json_body["file_hash"], session)

            if not de_request:
                print("Request not found")
                return

            try:
                file = download(de_request.unique_filename)
                requests.put(
                    f"{os.getenv('GATEWAY_URL')}/process/",
                    json={
                        "status": Status.IN_PROGRESS.value,
                        "ocr_model": "paddleocr",
                        "ocr_status": Status.IN_PROGRESS.value,
                        "status_message": "started progressing the file",
                        "num_of_ocr_retry": de_request.num_of_ocr_retry + 1,
                    },
                    params={"request_id": de_request.id},
                    headers=headers,
                )
            except Exception as err:
                requests.put(
                    f"{os.getenv('GATEWAY_URL')}/process/",
                    json={
                        "ocr_status": Status.FAILED.value,
                        "status": Status.FAILED.value,
                        "status_message": "Failed to download file from GCS",
                    },
                    params={"request_id": de_request.id},
                    headers=headers,
                )
                print("Failed to download file from GCS", err.__str__())
                return
            try:
                if de_request.original_filename.split(".")[-1].lower() != "pdf":
                    img = get_img(file)
                    pages = [img]
                else:
                    pages = convert_pdf_to_image(file)

                results, raw_text = get_raw_text_from_pages(pages)
                requests.put(
                    f"{os.getenv('GATEWAY_URL')}/process/",
                    json={
                        "status_message": "Finished extracting raw ocr",
                        "raw_ocr": raw_text,
                    },
                    params={"request_id": de_request.id},
                    headers=headers,
                )
            except Exception as err:
                requests.put(
                    f"{os.getenv('GATEWAY_URL')}/process/",
                    json={
                        "ocr_status": Status.FAILED.value,
                        "status": Status.FAILED.value,
                        "status_message": "Failed to extract text from file",
                    },
                    params={"request_id": de_request.id},
                    headers=headers,
                )
                print("Failed to extract text from file", err.__str__())
                return
            try:
                processed_text = get_processed_text_from_pages(results)
                requests.put(
                    f"{os.getenv('GATEWAY_URL')}/process/",
                    json={
                        "ocr_status": Status.COMPLETED.value,
                        "status_message": "Finished processing raw ocr",
                        "processed_ocr": processed_text,
                    },
                    params={"request_id": de_request.id},
                    headers=headers,
                )
            except Exception as err:
                requests.put(
                    f"{os.getenv('GATEWAY_URL')}/process/",
                    json={
                        "ocr_status": Status.FAILED.value,
                        "status": Status.FAILED.value,
                        "status_message": "Failed to extract text from file",
                    },
                    params={"request_id": de_request.id},
                    headers=headers,
                )
                print("Failed to extract text from file", err.__str__())
                return

            try:
                message = {"request_id": de_request.id}
                ch.basic_publish(
                    exchange="",
                    routing_key=os.getenv("DE_QUEUE"),
                    body=json.dumps(message),
                    properties=pika.BasicProperties(
                        delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
                    ),
                )
            except:
                requests.put(
                    f"{os.getenv('GATEWAY_URL')}/process/",
                    json={
                        "status": Status.FAILED.value,
                        "status_message": "Failed to push message to de queue",
                    },
                    params={"request_id": de_request.id},
                    headers=headers,
                )
                print("Failed to push message to de queue", err.__str__())
                return

    channel.basic_consume(
        queue=os.getenv("OCR_QUEUE"), on_message_callback=callback, auto_ack=True
    )

    print("Waiting for messages. To exit press CTRL+C")

    channel.start_consuming()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
