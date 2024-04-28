import pika
import os
import sys
import json
import requests
from sqlmodel import Session
from dotenv import load_dotenv

from config import engine

from models import Status
from crud import _get_request_from_id
from process import chat

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
            de_request = _get_request_from_id(json_body["request_id"], session)

            if not de_request:
                print("Request not found")
                ch.basic_nack(delivery_tag=method.delivery_tag)
                return
            requests.put(
                f"{os.getenv('GATEWAY_URL')}/process/",
                json={
                    "status": Status.IN_PROGRESS.value,
                    "llm_model": "",
                    "de_status": Status.IN_PROGRESS.value,
                    "status_message": "started extracting data with llm model",
                    "num_of_llm_retry": de_request.num_of_llm_retry + 1,
                },
                params={"request_id": de_request.id},
                headers=headers,
            )
            try:
                response = chat(de_request.processed_ocr)
            except Exception as err:
                requests.put(
                    f"{os.getenv('GATEWAY_URL')}/process/",
                    json={
                        "de_status": Status.FAILED.value,
                        "status": Status.FAILED.value,
                        "status_message": "Failed to process text with LLM",
                    },
                    params={"request_id": de_request.id},
                    headers=headers,
                )
                print("Failed to process text with LLM ", err.__str__())
                return

    channel.basic_consume(
        queue=os.getenv("DE_QUEUE"), on_message_callback=callback, auto_ack=True
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
