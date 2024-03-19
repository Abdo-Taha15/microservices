# from paddleocr import PaddleOCR
import pika
import os
import sys
import time
import json
from sqlmodel import Session
from dotenv import load_dotenv

from config import engine

from models import DeRequests, Status
from GCP import download
from crud import _get_request_from_hash, _update_de_request
from tools import _commit_transaction, hash_file, get_img
from process import extract_text, get_data

load_dotenv()

# ocr = PaddleOCR(use_angle_cls=True, lang="ch")


# def get_ocr_output(img):
#     return ocr.ocr(img, cls=True)


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
            json_body = json.loads(body)
            de_request = _get_request_from_hash(json_body["file_hash"], session)
            if de_request:
                try:
                    file = download(de_request.unique_filename)
                    de_request = _update_de_request(
                        de_request,
                        {
                            "ocr_model": "paddleocr",
                            "ocr_status": Status.IN_PROGRESS,
                            "status_message": "started progressing the file",
                            "num_or_retry": de_request.num_or_retry + 1,
                        },
                        session,
                    )
                    session.commit()
                    session.refresh(de_request)
                except Exception as err:
                    de_request = _update_de_request(
                        de_request,
                        {
                            "ocr_status": Status.FAILED,
                            "status": Status.FAILED,
                            "status_message": "Failed to download file from GCS",
                        },
                        session,
                    )
                    session.commit()
                    session.refresh(de_request)
                    print("Failed to download file from GCS", err.__str__())
                try:
                    img = get_img(file)
                    result = extract_text(img)
                    with open("raw_text.txt", "w") as f:
                        f.write("\n".join([line[1][0] for line in result]))
                    de_request = _update_de_request(
                        de_request,
                        {
                            "status_message": "Finished extracting raw ocr",
                            "raw_ocr": "\n".join([line[1][0] for line in result]),
                        },
                        session,
                    )
                    session.commit()
                    session.refresh(de_request)
                except Exception as err:
                    de_request = _update_de_request(
                        de_request,
                        {
                            "ocr_status": Status.FAILED,
                            "status": Status.FAILED,
                            "status_message": "Failed to extract text from file",
                        },
                        session,
                    )
                    session.commit()
                    session.refresh(de_request)
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                    print("Failed to extract text from file", err.__str__())
                    return
                try:
                    # threshold = get_threshold(result)
                    processed_output = get_data(img, result)
                    with open("processed_text.txt", "w") as f:
                        f.write("\n".join(text for text in processed_output))
                    de_request = _update_de_request(
                        de_request,
                        {
                            "ocr_status": Status.COMPLETED,
                            "status_message": "Finished processing raw ocr",
                            "processed_ocr": "\n".join(
                                text for text in processed_output
                            ),
                        },
                        session,
                    )
                    session.commit()
                    session.refresh(de_request)
                except Exception as err:
                    de_request = _update_de_request(
                        de_request,
                        {
                            "ocr_status": Status.FAILED,
                            "status": Status.FAILED,
                            "status_message": "Failed to extract text from file",
                        },
                        session,
                    )
                    session.commit()
                    session.refresh(de_request)
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                    print("Failed to extract text from file", err.__str__())
                    return

            else:
                print("Request not found")
                ch.basic_nack(delivery_tag=method.delivery_tag)
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
