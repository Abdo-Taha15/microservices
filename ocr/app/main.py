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
from tools import get_img
from process import extract_text, get_data

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
                ch.basic_nack(delivery_tag=method.delivery_tag)
                return

            try:
                file = download(de_request.unique_filename)
                requests.put(
                    f"{os.getenv('GATEWAY_URL')}/ocr/",
                    json={
                        "status": Status.IN_PROGRESS.value,
                        "ocr_model": "paddleocr",
                        "ocr_status": Status.IN_PROGRESS.value,
                        "status_message": "started progressing the file",
                        "num_or_retry": de_request.num_or_retry + 1,
                    },
                    params={"request_id": de_request.id},
                    headers=headers,
                )
            except Exception as err:
                requests.put(
                    f"{os.getenv('GATEWAY_URL')}/ocr/",
                    json={
                        "ocr_status": Status.FAILED.value,
                        "status": Status.FAILED.value,
                        "status_message": "Failed to download file from GCS",
                    },
                    params={"request_id": de_request.id},
                    headers=headers,
                )
                ch.basic_nack(delivery_tag=method.delivery_tag)
                print("Failed to download file from GCS", err.__str__())
                return
            try:
                img = get_img(file)
                result = extract_text(img)
                requests.put(
                    f"{os.getenv('GATEWAY_URL')}/ocr/",
                    json={
                        "status_message": "Finished extracting raw ocr",
                        "raw_ocr": "\n".join([line[1][0] for line in result]),
                    },
                    params={"request_id": de_request.id},
                    headers=headers,
                )
            except Exception as err:
                requests.put(
                    f"{os.getenv('GATEWAY_URL')}/ocr/",
                    json={
                        "ocr_status": Status.FAILED.value,
                        "status": Status.FAILED.value,
                        "status_message": "Failed to extract text from file",
                    },
                    params={"request_id": de_request.id},
                    headers=headers,
                )
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                print("Failed to extract text from file", err.__str__())
                return
            try:
                processed_output = get_data(img, result)
                requests.put(
                    f"{os.getenv('GATEWAY_URL')}/ocr/",
                    json={
                        "ocr_status": Status.COMPLETED.value,
                        "status_message": "Finished processing raw ocr",
                        "processed_ocr": "\n".join(text for text in processed_output),
                    },
                    params={"request_id": de_request.id},
                    headers=headers,
                )
            except Exception as err:
                requests.put(
                    f"{os.getenv('GATEWAY_URL')}/ocr/",
                    json={
                        "ocr_status": Status.FAILED.value,
                        "status": Status.FAILED.value,
                        "status_message": "Failed to extract text from file",
                    },
                    params={"request_id": de_request.id},
                    headers=headers,
                )
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                print("Failed to extract text from file", err.__str__())
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
