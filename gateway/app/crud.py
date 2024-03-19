from sqlmodel import select, Session

from models import DeRequests
from tools import _commit_transaction


def _create_de_request(data: dict, session: Session):
    de_request = DeRequests(**data)

    _commit_transaction(de_request, session)

    return de_request


def _get_request_from_hash(hash: str, session: Session):
    return session.exec(
        select(DeRequests).where(DeRequests.file_hash == hash)
    ).one_or_none()


def _get_request_from_id(id: int, session: Session):
    return session.exec(select(DeRequests).where(DeRequests.id == id)).one_or_none()


def _update_de_request(de_request: DeRequests, data: dict, session: Session):
    for key, value in data.items():
        if value:
            setattr(de_request, key, value)

    _commit_transaction(de_request, session)

    return de_request
