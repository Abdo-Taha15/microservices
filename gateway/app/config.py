from pathlib import Path
import pika
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy_utils import database_exists, create_database
import os
from dotenv import load_dotenv

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(DATABASE_URL, echo=True)


async def init_db():
    if not database_exists(engine.url):
        create_database(engine.url)
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine, future=True) as session:
        yield session


async def set_connection():
    credentials = pika.PlainCredentials(
        os.getenv("RABBITMQ_USER"), os.getenv("RABBITMQ_PASSWORD")
    )
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            os.getenv("RABBITMQ_HOST"), os.getenv("RABBITMQ_PORT"), "/", credentials
        )
    )
    channel = connection.channel()

    channel.queue_declare(queue="ocr_queue", durable=True)
    channel.queue_declare(queue="data_extraction", durable=True)

    connection.close()


def get_channel():
    credentials = pika.PlainCredentials(
        os.getenv("RABBITMQ_USER"), os.getenv("RABBITMQ_PASSWORD")
    )
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            os.getenv("RABBITMQ_HOST"), os.getenv("RABBITMQ_PORT"), "/", credentials
        )
    )
    return connection, connection.channel()
